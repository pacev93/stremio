#!/usr/bin/env python3
"""Check resize propagation through real app/video functions with controlled SDL sizes.

These fixtures do not emulate the CX compositor or fullscreen transitions.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cutil import ROOT, function


PREFIX = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef struct SDL_Window { int unused; } SDL_Window;
static int logicalW=1920,logicalH=1080,drawableW=1920,drawableH=1080;
static int surfW=1920,surfH=1080,graphicsW,graphicsH,graphicsCalls,planeCalls;
static int planeW,planeH;
static uintptr_t acb;
static char expWin[64];
/* Existing presentation state must survive a surface size change. */
static int cropSX=120,cropSY=40,cropSW=1680,cropSH=960;
static int cropDX=0,cropDY=0,cropDW=1920,cropDH=1080;
static void SDL_GetWindowSize(SDL_Window *window,int *w,int *h) {
  assert(window);*w=logicalW;*h=logicalH;
}
static void SDL_GL_GetDrawableSize(SDL_Window *window,int *w,int *h) {
  assert(window);*w=drawableW;*h=drawableH;
}
static void gfx_resize(int w,int h) {
  graphicsCalls++;graphicsW=w;graphicsH=h;
}
static void apply_plane(void) {
  assert(acb || expWin[0]);planeCalls++;planeW=surfW;planeH=surfH;
  assert(cropSX==120 && cropSY==40 && cropSW==1680 && cropSH==960);
  assert(cropDX==0 && cropDY==0 && cropDW==1920 && cropDH==1080);
}
'''


TESTS = r'''
int main(int argc,char **argv) {
  assert(argc==2);SDL_Window window={0};int w=1920,h=1080,dw=1920,dh=1080;
  if(!strcmp(argv[1],"resize-720p")) {
    snprintf(expWin,sizeof expWin,"exported-video");
    logicalW=drawableW=1280;logicalH=drawableH=720;
    resize_surface(&window,&w,&h,&dw,&dh);
    assert(w==1280 && h==720 && dw==1280 && dh==720);
    assert(graphicsW==1280 && graphicsH==720 && planeW==1280 && planeH==720);
    assert(graphicsCalls==1 && planeCalls==1);
  } else if(!strcmp(argv[1],"hidpi")) {
    snprintf(expWin,sizeof expWin,"exported-video");
    logicalW=1280;logicalH=720;drawableW=2560;drawableH=1440;
    resize_surface(&window,&w,&h,&dw,&dh);
    assert(w==1280 && h==720 && dw==2560 && dh==1440);
    assert(graphicsW==2560 && graphicsH==1440 && surfW==2560 && surfH==1440);
    assert(planeCalls==1 && planeW==2560 && planeH==1440);
  } else if(!strcmp(argv[1],"invalid-size")) {
    snprintf(expWin,sizeof expWin,"exported-video");
    for(int i=0;i<4;i++) {
      logicalW=1280;logicalH=720;drawableW=2560;drawableH=1440;
      if(i==0)logicalW=0;if(i==1)logicalH=0;
      if(i==2)drawableW=0;if(i==3)drawableH=0;
      resize_surface(&window,&w,&h,&dw,&dh);
      assert(w==1920 && h==1080 && dw==1920 && dh==1080);
      assert(!graphicsCalls && !planeCalls && surfW==1920 && surfH==1080);
    }
  } else if(!strcmp(argv[1],"exported-dedupe") || !strcmp(argv[1],"acb-dedupe")) {
    int exported=!strcmp(argv[1],"exported-dedupe");
    if(exported)snprintf(expWin,sizeof expWin,"exported-video");else acb=123;
    logicalW=drawableW=1280;logicalH=drawableH=720;
    resize_surface(&window,&w,&h,&dw,&dh);assert(planeCalls==1);
    resize_surface(&window,&w,&h,&dw,&dh);assert(planeCalls==1);
    /* A changed logical size with the same drawable only changes input scaling. */
    logicalW=640;logicalH=360;
    resize_surface(&window,&w,&h,&dw,&dh);
    assert(w==640 && h==360 && dw==1280 && dh==720 && planeCalls==1);
    video_set_surface(0,0);video_set_surface(-1,720);assert(planeCalls==1);
    drawableW=1920;drawableH=1080;
    resize_surface(&window,&w,&h,&dw,&dh);assert(planeCalls==2);
    assert(exported ? !strcmp(expWin,"exported-video") : acb==123);
  } else if(!strcmp(argv[1],"before-init")) {
    logicalW=drawableW=1280;logicalH=drawableH=720;
    resize_surface(&window,&w,&h,&dw,&dh);
    assert(surfW==1280 && surfH==720 && !planeCalls && !acb && !expWin[0]);
    assert(graphicsW==1280 && graphicsH==720);
  } else assert(!"unknown geometry scenario");
  printf("PASS surface geometry %s\n",argv[1]);return 0;
}
'''


def main():
    app = (ROOT / 'src/main.c').read_text()
    video = (ROOT / 'src/platform/webos/video_webos.c').read_text()
    cases = ('resize-720p', 'hidpi', 'invalid-size',
             'exported-dedupe', 'acb-dedupe', 'before-init')
    with tempfile.TemporaryDirectory(prefix='stremio-pointer-geometry-') as folder:
        tmp = Path(folder)
        source, executable = tmp / 'geometry.c', tmp / 'geometry'
        source.write_text(PREFIX + function(video, 'video_set_surface') +
                          function(app, 'resize_surface') + TESTS)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-O1', '-g',
                        '-Wall', '-Wextra', '-Wno-misleading-indentation',
                        str(source), '-o', str(executable)], check=True)
        for case in cases:
            subprocess.run([str(executable), case], check=True, timeout=10)
    print('6 geometry scenarios passed; native CX fullscreen behavior is not emulated')


if __name__ == '__main__':
    main()
