#!/usr/bin/env python3
"""Test in-session seeking and cancellation of stopped converter work.

Native service replies are controlled; this does not emulate LG decoding.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cutil import ROOT, function, sdl_include

NATIVE = r'''
#include <SDL2/SDL.h>
static Uint32 ticks=10000;
static Uint32 fake_ticks(void) { return ticks; }
#define SDL_GetTicks fake_ticks
#include "platform/webos/video_webos.c"
#include <assert.h>
static int loads, seeks, pauses, audioSelections, textSelections;
static double target;
static char address[9000];
static int converterSeeks;
static char converterUrl[4096];
void hls_conv_seek(const char *u) { converterSeeks++;snprintf(converterUrl,sizeof converterUrl,"%s",u); }
static const char *payload(LSMessage *m) { return (const char *)m; }
static void emit(const char *p) { on_event(bus,(LSMessage *)p,(void *)(uintptr_t)session); }
static bool dispatch(LSHandle *h, const char *uri, const char *p, LSFilterFunc cb,
                     void *ud, unsigned long *tok, void *err) {
  (void)tok; (void)err;
  if (strstr(uri,"/load")) {
    loads++; snprintf(address,sizeof address,"%s",p);
    assert(strstr(p,"\"bufferControl\":{\"userBufferCtrl\":false}"));
    cb(h,(LSMessage *)"{\"mediaId\":\"new-session\"}",ud);
    emit("{\"loadCompleted\":{}}");
  } else if (strstr(uri,"/seek")) { seeks++; target=num_of(p,"\"position\":")/1000; }
  else if (strstr(uri,"/pause")) pauses++;
  else if (strstr(uri,"/selectTrack") && strstr(p,"\"audio\"")) audioSelections++;
  else if (strstr(uri,"/setSubtitleEnable") || (strstr(uri,"/selectTrack") && strstr(p,"\"text\""))) textSelections++;
  return true;
}
unsigned long plat_luna_subscribe(const char *u,const char *p,PlatLunaCb cb,void *ud) { (void)u;(void)p;(void)cb;(void)ud;return 0; }
int plat_luna_send(const char *u,const char *p) { (void)u;(void)p;return 0; }
int main(int argc,char **argv) {
  assert(argc==2); ready=1; bus=(LSHandle *)1; lsCall=dispatch; lsPayload=payload;
  snprintf(url,sizeof url,"https://fixture.test/film.mkv");
  snprintf(S.mediaId,sizeof S.mediaId,"old-session");
  S.loaded=S.playing=S.live=1; S.st=VID_PLAYING; S.pos=120; posAt=10;
  S.curAud=2; S.curTxt=-1; cropSX=12;
  if (!strcmp(argv[1],"converter-debounce")) {
    snprintf(url,sizeof url,"http://127.0.0.1:123/h/42/index.m3u8");
    video_seek(80);ticks+=100;video_seek(90);ticks+=349;video_pump();
    assert(!converterSeeks && !seeks);ticks++;video_pump();
    assert(converterSeeks==1 && !strcmp(converterUrl,url) && seeks==1 && target==90 && !loads);
  } else if (!strcmp(argv[1],"empty-session")) {
    S.mediaId[0]=0;video_seek(90);ticks+=350;video_pump();assert(!converterSeeks && !seeks && !loads);
  } else if (!strcmp(argv[1],"forward")) {
    video_seek(150); ticks+=350; video_pump(); assert(!loads && seeks==1 && target==150);
  } else if (!strcmp(argv[1],"backward")) {
    video_seek(90); ticks+=349; video_pump(); assert(!loads && !seeks);
    ticks++; video_pump(); assert(!loads && seeks==1 && target==90 && cropSX==12);
    assert(S.curAud==2 && S.curTxt==-1 && !audioSelections && !textSelections);
    video_pump(); assert(!loads && seeks==1);
  } else if (!strcmp(argv[1],"coalesce")) {
    video_seek(60); ticks+=100; video_seek(70); ticks+=350;
    video_pump(); video_pump(); assert(!loads && seeks==1 && target==70);
  } else if (!strcmp(argv[1],"small-backward")) {
    video_seek(119); ticks+=350; video_pump(); assert(!loads && seeks==1 && target==119);
  } else if (!strcmp(argv[1],"repeated")) {
    for (int i=0;i<3;i++) { video_seek(110-i*10); ticks+=350; video_pump(); }
    assert(!loads && seeks==3 && target==90);
  } else if (!strcmp(argv[1],"paused")) {
    S.pausedByUs=1; S.playing=0; S.st=VID_PAUSED; S.curAud=0;
    video_seek(40); ticks+=350; video_pump(); video_pump();
    assert(!loads && seeks==1 && target==40 && S.curAud==0 && !pauses && S.pausedByUs);
    emit("{\"seekDone\":{}}"); video_pump(); assert(!pauses);
  } else if (!strcmp(argv[1],"continuous")) {
    timed.on=1; timed.dur=200; snprintf(timed.base,sizeof timed.base,"http://127.0.0.1:123/h/1/all.ts");
    video_seek(45); ticks+=350; video_pump(); video_pump();
    assert(loads==1 && !seeks && timed.off==45 && S.pos==45 && strstr(address,"all.ts?t=45.000"));
  } else if (!strcmp(argv[1],"continuous-paused")) {
    timed.on=1; timed.dur=200; snprintf(timed.base,sizeof timed.base,"http://127.0.0.1:123/h/1/all.ts");
    S.pausedByUs=1; S.playing=0; S.st=VID_PAUSED;
    video_seek(45); ticks+=350; video_pump(); video_pump(); assert(!pauses && !seeks);
    emit("{\"playing\":{}}"); video_pump(); assert(pauses==1 && S.pausedByUs);
  } else if (!strcmp(argv[1],"play-cancels-pause")) {
    timed.on=1; timed.dur=200; snprintf(timed.base,sizeof timed.base,"http://127.0.0.1:123/h/1/all.ts");
    S.pausedByUs=1; S.playing=0; S.st=VID_PAUSED;
    video_seek(40); ticks+=350; video_pump(); video_pump();
    emit("{\"seekDone\":{}}"); video_play(); emit("{\"playing\":{}}"); video_pump();
    assert(!pauses && !S.pausedByUs);
  } else if (!strcmp(argv[1],"beginning")) {
    video_seek(0); ticks+=350; video_pump(); video_pump(); assert(!loads && seeks==1 && target==0);
  } else if (!strcmp(argv[1],"new-source")) {
    video_seek(50); video_load("https://fixture.test/other.mkv"); ticks+=350; video_pump();
    assert(loads==1 && !seeks && strstr(address,"other.mkv"));
  } else assert(!"unknown case");
  printf("PASS native seek %s\n",argv[1]); return 0;
}
'''

CORE = r'''
#include "core/video.h"
#include "core/mkvsubs.h"
#include "core/hproxy.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct {
  double startAt,liveT0,seekT,seekTxtUntil;
  int live,didResume;
  char url[4096];
  struct { int conv,convOrd,dv,copyA; double convAt,convT0,okAt; } dts;
} P;
static MkvSession *mkv;
static int starts,unloads,nativeSeeks,gotFlags,gotOrd,indexed=1,isPaused;
static double nativeTarget;
static int paused(void) { return isPaused; }
static double now_(void) { return 20; }
int mkv_has_index(MkvSession *s) { (void)s; return indexed; }
void video_unload(void) { unloads++; }
void video_seek(double t) { nativeSeeks++; nativeTarget=t; }
void hls_conv_start(const char *u,int ord,int flags) {
  assert(!strcmp(u,P.url)); starts++; gotFlags=flags; gotOrd=ord;
}
'''

CORE_TEST = r'''
int main(int argc,char **argv) {
  assert(argc==2); snprintf(P.url,sizeof P.url,"https://fixture.test/film.mkv");
  P.live=1; P.didResume=1; P.dts.conv=2; P.dts.convOrd=3;
  if (!strcmp(argv[1],"direct")) P.dts.conv=0;
  if (!strcmp(argv[1],"dv-copy")) P.dts.dv=P.dts.copyA=1;
  if (!strcmp(argv[1],"no-index")) indexed=0;
  if (!strcmp(argv[1],"paused")) isPaused=1;
  int conv=P.dts.conv, dv=P.dts.dv, copy=P.dts.copyA;
  double t=!strcmp(argv[1],"beginning")?0:42; P.seekT=t; commit_seek();
  assert(!starts && !unloads && nativeSeeks==1 && nativeTarget==t && P.seekT==-1);
  assert(P.dts.conv==conv && P.dts.convOrd==3 && P.dts.dv==dv && P.dts.copyA==copy);
  assert(P.live && P.didResume);
  printf("PASS converter seek %s\n",argv[1]); return 0;
}
'''

QUEUED = r'''
#define send fixture_send
#include "core/hproxy.c"
#undef send
#include <assert.h>
static pthread_mutex_t sentMu=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t sentCv=PTHREAD_COND_INITIALIZER;
static int sent,ran;
ssize_t fixture_send(int fd,const void *p,size_t n,int flags) {
  (void)fd;(void)p;(void)flags;
  pthread_mutex_lock(&sentMu);sent=1;pthread_cond_signal(&sentCv);pthread_mutex_unlock(&sentMu);return n;
}
void net_range_free(NetRange *r) { (void)r; }
static int run(SbdSrc *s,int seg,double t,sbd_write w,void *ud,volatile int *stop,sbd_stats *st,char *err,int cap) {
  (void)s;(void)seg;(void)t;(void)w;(void)ud;(void)stop;(void)st;(void)err;(void)cap;ran++;return -2;
}
static double seg_start(SbdSrc *s,int n) { (void)s;return 2*n; }
static double seg_dur(SbdSrc *s,int n) { (void)s;(void)n;return 2; }
static void *request(void *arg) { (void)arg;conv_serve(123,1,"/h/1/0.ts",0);return NULL; }
int main(void) {
  static const sbd_api api={.run=run,.seg_start=seg_start,.seg_dur=seg_dur};D=&api;
  Conv *old=calloc(1,sizeof *old);old->id=1;old->state=1;old->refs=1;old->running=-100;
  old->info.indexed=1;old->info.nseg=10;pthread_mutex_init(&old->runMu,NULL);conv=old;
  pthread_mutex_lock(&old->runMu);
  pthread_t th;assert(!pthread_create(&th,NULL,request,NULL));
  pthread_mutex_lock(&sentMu);while(!sent)pthread_cond_wait(&sentCv,&sentMu);pthread_mutex_unlock(&sentMu);
  hls_conv_stop();assert(old->dead);pthread_mutex_unlock(&old->runMu);
  pthread_join(th,NULL);assert(!ran);
  puts("PASS queued HLS request cannot run after its converter is stopped");return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdl-include', type=Path)
    args = parser.parse_args()
    source = (ROOT/'src/screens/player.c').read_text()
    with tempfile.TemporaryDirectory(prefix='stremio-seek-') as folder:
        tmp = Path(folder)
        includes = sdl_include(tmp,args.sdl_include)
        suites = [
            ('native',NATIVE,('forward','backward','small-backward','repeated','coalesce','paused','continuous','continuous-paused','play-cancels-pause','beginning','new-source','converter-debounce','empty-session')),
            ('core',CORE+function(source,'commit_seek')+CORE_TEST,
             ('dts','dv-copy','no-index','paused','beginning','direct')),
            ('queued',QUEUED,('',)),
        ]
        for name, code, cases in suites:
            c=tmp/(name+'.c'); exe=tmp/name;c.write_text(code)
            subprocess.run([os.environ.get('CC','cc'),'-std=c11','-D_GNU_SOURCE','-O1','-g',
                            '-ffunction-sections','-fdata-sections','-Wno-misleading-indentation',
                            *includes,'-I',str(ROOT/'src'),str(c),
                            '-Wl,--gc-sections','-pthread','-ldl','-lm','-o',str(exe)],check=True)
            for case in cases:
                subprocess.run([str(exe),*([case] if case else [])],check=True,timeout=10)
        print('20 seek scenarios passed; native decoder behavior still requires TV verification')


if __name__ == '__main__':
    main()
