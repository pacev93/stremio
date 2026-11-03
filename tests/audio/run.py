#!/usr/bin/env python3
"""Test production DTS decisions against controlled stream/capability fixtures.

These tests exercise the real player functions with transport/player boundaries
stubbed. They do not decode media or emulate the TV pipeline.
"""
import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cutil import ROOT, function

PREFIX = r'''
#include "core/video.h"
#include "core/mkvsubs.h"
#include "core/hproxy.h"
#include "core/best.h"
#include <assert.h>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
static struct {
  int isTrailer, isHls, live, curAud, didResume, failed, autoAudDone;
  char url[4096], sname[600], infoKey[256]; double startAt, liveT0, lastPos;
  struct {
    int conv, convOrd, hevc, dv, copyA, dvTried, dvSeen, gaveUp, said, nbad, switches;
    double convT0, convAt, okAt, dvAt, playAt; char bad[4][16];
  } dts;
} P;
static MkvSession *mkv;
static int mode, hevc, hevcLearned, dtsLearned, dvLearned, available, ntracks, languageEnabled;
static int starts, stops, selects, failures, flags, selectedOrdinal;
static VidState state;
static double clockNow;
static VidTrack tracks[2]; static MkvAudio audio[2];
int best_dts_mode(void) { return mode; }
int best_learned(const char *what) {
  return !strcmp(what,"hlsHevcOk") ? hevcLearned : !strcmp(what,"dts") ? dtsLearned : dvLearned;
}
void best_learn(const char *what, int yes) {
  if (!strcmp(what,"hlsHevcOk")) hevcLearned = yes;
  else if (!strcmp(what,"dts")) dtsLearned = yes;
  else dvLearned = yes;
}
static const char *store_get(const char *key, const char *fallback) {
  if (languageEnabled && !strcmp(key,"enableDefaultAudioTrack")) return "true";
  if (languageEnabled && !strcmp(key,"defaultAudioTrack")) return "eng";
  return fallback;
}
static void lower(const char *in, char *out, size_t cap) {
  size_t i=0; for (; in[i] && i+1<cap; i++) out[i]=(char)tolower((unsigned char)in[i]); out[i]=0;
}
static int has_word(const char *text, const char *word) { return strcasestr(text,word)!=NULL; }
static int lang_match(const char *a, const char *b) { return !strcasecmp(a,b); }
static double now_(void) { return clockNow; }
static const char *T(const char *s) { return s; }
static const char *T1(const char *s, const char *k, const char *v) { (void)k; (void)v; return s; }
static void toast(const char *s, int ms, void *fn) { (void)s; (void)ms; (void)fn; }
static void fail(const char *s) { (void)s; failures++; P.failed=1; }
static int dv7_wanted(void) { return 0; }
static int dv7_convert(const char *why) { (void)why; return 0; }
int hls_conv_available(void) { return available; }
void hls_conv_start(const char *url, int ord, int fl) { (void)url; starts++; selectedOrdinal=ord; flags=fl; }
void hls_conv_stop(void) { stops++; }
int hls_conv_poll(char *url, size_t cap, char *why, size_t wc, HlsConvInfo *info) {
  (void)url; (void)cap; (void)why; (void)wc; (void)info; return 0;
}
int mkv_listed(MkvSession *s) { (void)s; return 1; }
int mkv_has_index(MkvSession *s) { (void)s; return 1; }
int mkv_video_codec(MkvSession *s, char *out, int cap) {
  (void)s; snprintf(out,cap,"%s",hevc ? "V_MPEGH/ISO/HEVC" : "V_MPEG4/ISO/AVC"); return 1;
}
int mkv_audio_tracks(MkvSession *s, MkvAudio *out, int cap) {
  (void)s; int n=ntracks<cap?ntracks:cap; memcpy(out,audio,(size_t)n*sizeof *out); return n;
}
int video_audio_tracks(VidTrack *out, int cap) {
  int n=ntracks<cap?ntracks:cap; memcpy(out,tracks,(size_t)n*sizeof *out); return n;
}
void video_select_audio(int index) { (void)index; selects++; }
int video_audio_current(void) { return 0; }
int video_audio_unsupported(void) { return 0; }
double video_time(void) { return 12; }
VidState video_state(void) { return state; }
int video_live(void) { return state==VID_PLAYING; }
int video_has_media(void) { return 1; }
int video_hdr(char *out, int cap) { (void)out; (void)cap; return 0; }
void video_load(const char *url) { (void)url; }
void video_load_timed(const char *url, double duration) { (void)url; (void)duration; }
static int conv_flags(int ord) { (void)ord; return 0; }
'''

TESTS = r'''
static void reset(void) {
  memset(&P,0,sizeof P); snprintf(P.url,sizeof P.url,"http://example.test/movie.mkv");
  mode=1; hevc=1; hevcLearned=-1; dtsLearned=0; dvLearned=-1; available=1;
  starts=stops=selects=failures=flags=0; selectedOrdinal=-99; state=VID_PLAYING; clockNow=10;
  tracks[0]=(VidTrack){.idx=0,.codec="dts",.channels=6,.lang="eng"};
  tracks[1]=(VidTrack){.idx=1,.codec="ac3",.channels=2,.lang="eng"};
  audio[0]=(MkvAudio){.n=0,.num=1,.codec="A_DTS",.channels=6,.lang="eng"};
  audio[1]=(MkvAudio){.n=1,.num=2,.codec="A_AC3",.channels=2,.lang="eng"};
  ntracks=2; P.live=1; languageEnabled=0;
}
int main(int argc, char **argv) {
  assert(argc==2); reset();
  if (!strcmp(argv[1],"force-cache")) {
    hevcLearned=0;
    assert(dts_convert(0,"forced after previous failure")==1);
    assert(starts==1 && selectedOrdinal==0 && !(flags & HC_COPYAUDIO));
  } else if (!strcmp(argv[1],"force-priority")) {
    dtsLearned=1; dts_tick();
    assert(starts==1 && selects==0 && selectedOrdinal==0 && !P.dts.copyA);
  } else if (!strcmp(argv[1],"dv-audio-force")) {
    int copy=1; assert(dv7_audio(&copy)==0 && copy==0);
  } else if (!strcmp(argv[1],"dv-audio-auto")) {
    mode=0; int copy=0; assert(dv7_audio(&copy)==1 && copy==1);
  } else if (!strcmp(argv[1],"language-force")) {
    languageEnabled=1; auto_audio(); assert(P.autoAudDone && P.curAud==0);
    dts_tick(); assert(starts==1 && selectedOrdinal==0);
  } else if (!strcmp(argv[1],"language-auto")) {
    languageEnabled=1; mode=0; auto_audio(); assert(P.autoAudDone && P.curAud==1);
  } else if (!strcmp(argv[1],"auto-cache")) {
    mode=0; hevcLearned=0; assert(!dts_convert(0,"auto")); assert(starts==0);
  } else if (!strcmp(argv[1],"auto-fallback")) {
    mode=0; dts_tick(); assert(selects==1 && starts==0);
  } else if (!strcmp(argv[1],"off")) {
    mode=2; dts_tick(); assert(selects==0 && starts==0);
  } else if (!strcmp(argv[1],"transient-failure")) {
    P.dts.conv=2; P.dts.hevc=1;
    dts_conv_failed("no picture after 25 s");
    assert(hevcLearned==-1 && stops==1 && failures==1 && P.dts.gaveUp);
  } else if (!strcmp(argv[1],"preserve-success")) {
    hevcLearned=1; P.dts.conv=2; P.dts.hevc=1;
    dts_conv_failed("source interrupted"); assert(hevcLearned==1);
  } else if (!strcmp(argv[1],"recover-old-negative")) {
    hevcLearned=0; P.dts.conv=2; P.dts.hevc=1;
    dts_conv_tick(); clockNow=13.1; dts_conv_tick(); assert(hevcLearned==1);
  } else if (!strcmp(argv[1],"source-guards")) {
    P.isHls=1; assert(!dts_convert(0,"HLS source"));
    P.isHls=0; P.isTrailer=1; assert(!dts_convert(0,"trailer"));
    P.isTrailer=0; available=0; assert(!dts_convert(0,"missing library")); assert(starts==0);
  } else if (!strcmp(argv[1],"bounded-failure")) {
    P.dts.gaveUp=1; dts_tick(); assert(starts==0 && selects==0);
  } else { assert(!"unknown test case"); }
  printf("PASS DTS %s\n",argv[1]); return 0;
}
'''

CASES = ['force-cache', 'force-priority', 'dv-audio-force', 'dv-audio-auto', 'language-force', 'language-auto', 'auto-cache', 'auto-fallback', 'off',
         'transient-failure', 'preserve-success', 'recover-old-negative',
         'source-guards', 'bounded-failure']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--player-source', type=pathlib.Path, default=ROOT / 'src/screens/player.c')
    parser.add_argument('--case', choices=CASES)
    args = parser.parse_args()
    source = args.player_source.read_text()
    names = ['set_audio', 'aud_kind', 'aud_bad', 'aud_list', 'aud_label',
             'aud_copyable', 'mkv_aud_bad', 'dv7_audio',
             'dts_convert', 'dts_conv_tick', 'dts_conv_failed', 'dts_tick']
    body = '\n'.join(function(source,n) for n in names)
    body += ('\n' + function(source,'aud_auto_bad') if 'static int aud_auto_bad(' in source else '')
    body += '\n' + function(source,'auto_audio')
    with tempfile.TemporaryDirectory(prefix='stremio-audio-') as folder:
        tmp = pathlib.Path(folder); c=tmp/'audio.c'; binary=tmp/'audio'
        c.write_text(PREFIX + body + TESTS)
        subprocess.run([os.environ.get('CC','cc'), '-std=c11', '-D_GNU_SOURCE', '-O1', '-g',
                        '-Wall', '-Wextra', '-Wno-unused-function', '-Wno-misleading-indentation',
                        '-I', str(ROOT/'src'), '-I', str(ROOT/'third_party/cjson'),
                        str(c), '-lm', '-o', str(binary)], check=True)
        cases=[args.case] if args.case else CASES
        for case in cases:
            subprocess.run([str(binary),case],check=True)
        print(f'{len(cases)} DTS policy scenarios passed; real media playback not emulated')


if __name__ == '__main__':
    main()
