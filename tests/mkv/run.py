#!/usr/bin/env python3
"""Exercise the real MKV worker against a seekable in-memory Matroska fixture.

Counts actual Range calls and verifies off/selection/track-switch behavior,
including the unindexed scan path. No network or TV decoder is simulated.
"""
import argparse
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cutil import ROOT, sdl_include


def elem(tag, value):
    tag = tag.to_bytes((tag.bit_length() + 7) // 8, 'big')
    width = next(n for n in range(1, 9) if len(value) < (1 << (7 * n)) - 1)
    return tag + ((1 << (7 * width)) | len(value)).to_bytes(width, 'big') + value


def uint(tag, value, width=None):
    return elem(tag, value.to_bytes(width or max(1, (value.bit_length() + 7) // 8), 'big'))


def fixture():
    def track(num, kind, codec, extra=b''):
        return elem(0xAE, uint(0xD7, num) + uint(0x83, kind)
                    + elem(0x86, codec.encode()) + elem(0x22B59C, b'eng') + extra)

    dv = elem(0x41E4, uint(0x41E7, 0x64766343) + elem(0x41ED, bytes([1, 0, 14, 2])))
    tracks = elem(0x1654AE6B,
                  track(1, 1, 'V_MPEGH/ISO/HEVC', dv)
                  + track(2, 2, 'A_DTS', elem(0xE1, uint(0x9F, 6)))
                  + track(3, 17, 'S_TEXT/UTF8') + track(4, 17, 'S_TEXT/UTF8'))
    info = elem(0x1549A966, uint(0x2AD7B1, 1000000)
                + elem(0x4489, struct.pack('>d', 200000.0)))
    chapters = elem(0x1043A770, elem(0x45B9, elem(0xB6,
                    uint(0x91, 0) + uint(0x92, 10000000000)
                    + elem(0x80, elem(0x85, b'Intro')))))

    def seek(cues):
        return elem(0x114D9B74, elem(0x4DBB,
                    elem(0x53AB, bytes.fromhex('1c53bb6b')) + uint(0x53AC, cues, 8)))

    before = seek(0) + info + tracks + chapters + elem(0xEC, bytes(70000))
    clusters = []
    offsets = []
    size = len(before)
    for timestamp in (0, 10000, 120000):
        offsets.append(size)
        blocks = uint(0xE7, timestamp)
        for num, word in ((3, b'English'), (4, b'German')):
            blocks += elem(0xA3, bytes([0x80 | num, 0, 0, 0x80]) + word)
        c = elem(0x1F43B675, blocks)
        clusters.append(c)
        size += len(c)
    cues = b''
    for timestamp, offset in zip((0, 10000, 120000), offsets):
        positions = b''.join(elem(0xB7, uint(0xF7, n) + uint(0xF1, offset)) for n in (3, 4))
        cues += elem(0xBB, uint(0xB3, timestamp) + positions)
    before = seek(size) + before[len(seek(0)):]
    body = before + b''.join(clusters) + elem(0x1C53BB6B, cues)
    return elem(0x1A45DFA3, elem(0x4282, b'matroska')) + elem(0x18538067, body)


HARNESS = r'''
#include "core/mkvsubs.c"
#include <assert.h>
#include <unistd.h>
#include <stdatomic.h>
#include "fixture.h"
struct NetRange { int unused; };
static atomic_int reads, failNext;
void plat_thread_background(int priority) { (void)priority; }
NetRange *net_range_new(void) { return calloc(1, sizeof(NetRange)); }
void net_range_free(NetRange *r) { free(r); }
int net_range_get(NetRange *r, const char *url, long long start, long len,
                  unsigned char **out, long *got, long long *total, int *status, int timeout) {
  (void)r; (void)url; (void)timeout;
  assert(start >= 0); atomic_fetch_add(&reads, 1);
  if (atomic_load(&failNext)>0) {
    atomic_fetch_sub(&failNext,1); *got=0; *out=NULL;
    if (total) *total=sizeof data; if (status) *status=0; return NR_TIMEOUT;
  }
  *got = start >= (long long)sizeof data ? 0 : (long)fmin(len, sizeof data - start);
  *out = *got ? malloc((size_t)*got) : NULL;
  if (*got) memcpy(*out, data + start, (size_t)*got);
  if (total) *total = sizeof data; if (status) *status = 206;
  return NR_OK;
}
static int wait_metadata(MkvSession *s) {
  for (int i=0;i<300;i++) {
    MkvChapter c[4]; if (mkv_listed(s) && mkv_chapters(s,c,4)>=0) return 1;
    usleep(10000);
  }
  return 0;
}
static int wait_line(MkvSession *s, int track, const char *word) {
  for (int i=0;i<400;i++) {
    MkvLine line[4]; char text[512];
    int n=mkv_lines_at(s,track,1,line,4,text,sizeof text);
    if (n && strstr(line[0].t,word)) return 1;
    usleep(10000);
  }
  return 0;
}
int main(int argc, char **argv) {
  assert(argc==2); int scan=!strcmp(argv[1],"scan");
  if (scan) setenv("SB_MKV_NOCUES","1",1);
  MkvSession *s=mkv_open("http://fixture.test/film.mkv",1,0); assert(s && wait_metadata(s));
  MkvAudio audio[4]; assert(mkv_audio_tracks(s,audio,4)==1);
  assert(!strcmp(audio[0].codec,"A_DTS") && audio[0].channels==6);
  int el=0; assert(mkv_dovi(s,&el)==7 && el==1);
  MkvChapter chapters[4]; assert(mkv_chapters(s,chapters,4)==1 && !strcmp(chapters[0].name,"Intro"));
  assert(mkv_has_index(s)==1);
  int before=atomic_load(&reads); usleep(1200000); assert(atomic_load(&reads)==before);
  if (!strcmp(argv[1],"retry-off")) {
    atomic_store(&failNext,3); mkv_select(s,0);
    for(int i=0;i<300 && atomic_load(&reads)<before+3;i++) usleep(10000);
    assert(atomic_load(&reads)==before+3); mkv_select(s,-1); before=atomic_load(&reads);
    usleep(2000000); assert(atomic_load(&reads)==before); mkv_close(s); usleep(50000);
    puts("PASS switching off during a failed index fetch prevents later index retries"); return 0;
  }
  printf("PASS %s: audio, DV7 and chapters available; off makes no subtitle Range calls\n",argv[1]);

  mkv_select(s,0); assert(wait_line(s,0,"English"));
  assert(atomic_load(&reads)>before);
  if (!scan) {
    MkvLine line[4]; char text[512]; assert(!mkv_lines_at(s,1,1,line,4,text,sizeof text));
    lock(s); int far=0; for (int i=0;i<s->nall;i++) if (s->all[i].t>100) { assert(s->status[i]==0); far++; }
    assert(far); unlock(s);
  }
  printf("PASS %s: selected subtitles render; no whole-track harvest\n",argv[1]);

  mkv_select(s,-1); usleep(200000); before=atomic_load(&reads);
  usleep(1200000); assert(atomic_load(&reads)==before);
  printf("PASS %s: switching off stops further Range calls\n",argv[1]);
  mkv_select(s,1); assert(wait_line(s,1,"German"));
  printf("PASS %s: changing the selected language still works\n",argv[1]);
  mkv_select(s,-1); usleep(200000); before=atomic_load(&reads);
  usleep(1200000); assert(atomic_load(&reads)==before);
  mkv_close(s); usleep(50000);
  return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdl-include', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='stremio-mkv-') as folder:
        tmp = Path(folder)
        (tmp / 'fixture.h').write_text('static const unsigned char data[]={'
                                      + ','.join(map(str, fixture())) + '};\n')
        c = tmp / 'mkv.c'
        c.write_text(HARNESS)
        exe = tmp / 'mkv'
        subprocess.run([os.environ.get('CC','cc'), '-std=c11', '-D_GNU_SOURCE', '-O1', '-g',
                        '-Wno-misleading-indentation', *sdl_include(tmp,args.sdl_include),
                        '-I',str(ROOT/'src'),'-I',str(tmp),str(c),
                        '-pthread','-lz','-lm','-o',str(exe)],check=True)
        for path in ('indexed','scan','retry-off'):
            subprocess.run([str(exe),path],check=True,timeout=15)
        print('9 MKV worker scenarios passed, plus off-after-language-switch checks')


if __name__ == '__main__':
    main()
