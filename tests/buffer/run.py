#!/usr/bin/env python3
"""Test the real native video backend's buffer options and bounded fallback.

Luna replies and the SDL clock are controlled; no LG media decoder is emulated.
"""
import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cutil import ROOT, sdl_include

HARNESS = r'''
#include <assert.h>
#include "platform/webos/video_webos.c"
#include "cJSON.h"
static const char *testDevice="LG webOS 5.5.0", *testSetting="20", *testReply;
static Uint32 testClock=10000;
static int loads;
static char loadJson[10000];
static LSFilterFunc pending;
static void *pendingCtx;
Uint32 SDL_GetTicks(void) { return testClock; }
const char *plat_device_name(void) { return testDevice; }
const char *store_get(const char *key, const char *fallback) {
  return !strcmp(key,"nativeBufferSeconds") ? testSetting : fallback;
}
unsigned long plat_luna_subscribe(const char *uri,const char *payload,PlatLunaCb cb,void *ud) {
  (void)uri;(void)payload;(void)cb;(void)ud;return 0;
}
int plat_luna_send(const char *uri,const char *payload) { (void)uri;(void)payload;return 1; }
static const char *reply_payload(LSMessage *m) { (void)m;return testReply; }
static bool capture_call(LSHandle *handle,const char *uri,const char *payload,
                        LSFilterFunc callback,void *ctx,unsigned long *token,void *err) {
  (void)handle;(void)token;(void)err;
  if (!strcmp(uri,"luna://com.webos.media/load")) {
    loads++;snprintf(loadJson,sizeof loadJson,"%s",payload);pending=callback;pendingCtx=ctx;
  }
  return true;
}
static void load_reply(const char *json) {
  LSFilterFunc cb=pending;void *ctx=pendingCtx;testReply=json;
  assert(cb && cb(bus,(LSMessage *)1,ctx));
}
static void event(const char *json) {
  testReply=json;assert(on_event(bus,(LSMessage *)1,(void *)(uintptr_t)session));
}
static void check_payload(int target) {
  cJSON *j=cJSON_Parse(loadJson);assert(j);
  cJSON *opts=cJSON_GetObjectItem(cJSON_GetObjectItem(j,"payload"),"option");
  cJSON *b=cJSON_GetObjectItem(opts,"bufferControl");assert(cJSON_IsObject(b));
  assert(cJSON_IsFalse(cJSON_GetObjectItem(b,"userBufferCtrl")));
  assert(cJSON_IsTrue(cJSON_GetObjectItem(opts,"useSeekableRanges")));
  assert(!strcmp(cJSON_GetStringValue(cJSON_GetObjectItem(opts,"appId")),SB_APP_ID));
  assert(!strcmp(cJSON_GetStringValue(cJSON_GetObjectItem(j,"uri")),url));
  assert(!strcmp(cJSON_GetStringValue(cJSON_GetObjectItem(j,"type")),"media"));
  if (!target) assert(cJSON_GetArraySize(b)==1);
  else {
    assert(cJSON_GetArraySize(b)==4);
    assert(cJSON_GetNumberValue(cJSON_GetObjectItem(b,"preBufferTime"))==target/2);
    assert(cJSON_GetNumberValue(cJSON_GetObjectItem(b,"bufferingMinTime"))==(target==10?2:5));
    assert(cJSON_GetNumberValue(cJSON_GetObjectItem(b,"bufferingMaxTime"))==target);
  }
  cJSON_Delete(j);
}
int main(int argc,char **argv) {
  assert(argc==2);ready=1;bus=(LSHandle *)1;lsCall=capture_call;lsPayload=reply_payload;
  const char *movie="https://example.test/film.mkv?x=1&y=2";
  if (!strcmp(argv[1],"auto")) {
    const char *values[]={"auto","","9999","20x"};
    for (int i=0;i<4;i++) { testSetting=values[i];video_load(movie);check_payload(0); }
  } else if (!strcmp(argv[1],"targets")) {
    const char *values[]={"10","20","30"};int targets[]={10,20,30};
    for (int i=0;i<3;i++) { testSetting=values[i];video_load(movie);check_payload(targets[i]); }
  } else if (!strcmp(argv[1],"firmware")) {
    const char *devices[]={"LG webOS 3.9.3","LG webOS 4.4.0","LG webOS 5.5.0","LG webOS 6.5.3","LG webOS 22.0","LG webOS 25.0","unknown"};
    for (int i=0;i<7;i++) { testDevice=devices[i];video_load(movie);check_payload(i==2||i==3?20:0); }
  } else if (!strcmp(argv[1],"local")) {
    const char *sources[]={"http://127.0.0.1:8190/hls.m3u8","http://localhost:8190/hls.m3u8","http://[::1]:8190/hls.m3u8","file:///tmp/movie.mkv"};
    for (int i=0;i<4;i++) { video_load(sources[i]);check_payload(0); }
    video_load_timed(sources[0],7200);check_payload(0); /* original DTS path */
  } else if (!strcmp(argv[1],"reject")) {
    video_load(movie);check_payload(20);
    load_reply("{\"returnValue\":false,\"errorCode\":1}");assert(!S.error);
    video_pump();assert(loads==2);check_payload(0);
    load_reply("{\"returnValue\":false,\"errorCode\":1}");video_pump();
    assert(loads==2 && S.error && video_state()==VID_ERROR);
  } else if (!strcmp(argv[1],"timeout")) {
    video_load(movie);load_reply("{\"returnValue\":true,\"mediaId\":\"test\"}");
    testClock+=27999;video_pump();assert(loads==1);
    testClock++;video_pump();assert(loads==2);check_payload(0);
    testClock+=100000;video_pump();assert(loads==2);
  } else if (!strcmp(argv[1],"playing")) {
    video_load(movie);load_reply("{\"returnValue\":true,\"mediaId\":\"test\"}");
    event("{\"playing\":{\"mediaId\":\"test\"}}");
    testClock+=100000;video_pump();assert(loads==1);
    event("{\"bufferingStart\":{\"mediaId\":\"test\"}}");
    testClock+=100000;video_pump();assert(loads==1 && S.live && video_state()==VID_BUFFERING);
  } else if (!strcmp(argv[1],"paused")) {
    video_load(movie);load_reply("{\"returnValue\":true,\"mediaId\":\"test\"}");
    video_pause();testClock+=100000;video_pump();assert(loads==1 && video_state()==VID_PAUSED);
  } else if (!strcmp(argv[1],"new-source")) {
    video_load(movie);load_reply("{\"returnValue\":false}");video_pump();assert(loads==2);check_payload(0);
    video_load("https://example.test/other.mkv");assert(loads==3);check_payload(20);
    video_unload();video_load(movie);check_payload(20);
  } else if (!strcmp(argv[1],"stale")) {
    video_load(movie);LSFilterFunc old=pending;void *oldCtx=pendingCtx;
    load_reply("{\"returnValue\":false}");video_pump();check_payload(0);
    testReply="{\"returnValue\":false}";old(bus,(LSMessage *)1,oldCtx);
    assert(!S.error && !S.bufferRejected);video_pump();assert(loads==2);
  } else assert(!"unknown case");
  printf("PASS native buffer %s\n",argv[1]);return 0;
}
'''

CASES = ['auto', 'targets', 'firmware', 'local', 'reject', 'timeout',
         'playing', 'paused', 'new-source', 'stale']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdl-include', type=pathlib.Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='stremio-buffer-') as folder:
        tmp = pathlib.Path(folder); c = tmp/'buffer.c'; binary = tmp/'buffer'
        c.write_text(HARNESS)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-D_GNU_SOURCE', '-O1', '-g',
                        '-Wno-unused-function', '-Wno-misleading-indentation',
                        *sdl_include(tmp, args.sdl_include), '-I', str(ROOT/'src'),
                        '-I', str(ROOT/'third_party/cjson'), str(c),
                        str(ROOT/'third_party/cjson/cJSON.c'), '-lpthread', '-ldl', '-lm',
                        '-o', str(binary)], check=True)
        for case in CASES:
            subprocess.run([str(binary), case], check=True)
        print('10 native-buffer request/fallback scenarios passed; effective TV buffering not emulated')


if __name__ == '__main__':
    main()
