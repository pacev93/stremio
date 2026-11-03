#!/usr/bin/env python3
"""Exercise production pointer handlers with the real host SDL and a test X display.

Usage: DISPLAY=:97 python3 tests/pointer/run.py --sdl-include "$SDK/usr/include"
The UI callbacks are stubbed; cursor creation, state and image changes use SDL.
This does not emulate LG's compositor. No global cursor visibility API is used.
"""
import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cutil import ROOT, function, sdl_include

PREFIX = r'''
#include "core/app.h"
#include "core/keys.h"
#include "core/hit.h"
#include "platform/plat.h"
#include <assert.h>
#include <dlfcn.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
Scr SCR = SCR_HOME;
static double NOW;
TopNav topNav = { .want = -1 };
static int playing = 1;
static int saver_on(void) { return 0; }
static void saver_stop(void) {}
static int player_open(void) { return playing; }
void player_ptr(int type, float x, float y) { (void)type; (void)x; (void)y; }
static void idle_touch(void) {}
static void idle_touch_by(const char *why) { (void)why; }
int app_mirror_key(int k) { return k; }
static Scr chipScr(int n) { (void)n; return SCR_HOME; }
static void topnav_paint(void) {}
static void key_core(int k, int down, int repeat) { (void)k; (void)down; (void)repeat; }
const Hit *hit_at(float x, float y) { (void)x; (void)y; return NULL; }
const Hit *hit_find(const Hit *like) { return like; }
int hit_same(const Hit *a, const Hit *b) { return a == b; }
'''

TESTS = r'''
static SDL_Cursor *original;
static int is_shown(void) { return SDL_GetCursor() == original; }
static void enabled(void) { assert(SDL_ShowCursor(SDL_QUERY) == SDL_ENABLE); }
static void focus(int active) {
  SDL_Event ev; memset(&ev, 0, sizeof ev); ev.type = SDL_WINDOWEVENT;
  ev.window.event = active ? SDL_WINDOWEVENT_FOCUS_GAINED : SDL_WINDOWEVENT_FOCUS_LOST;
  int life = plat_lifecycle(&ev); if (life) app_pointer_focus(life > 0);
}
int main(void) {
  assert(SDL_Init(SDL_INIT_VIDEO) == 0);
  SDL_Window *win = SDL_CreateWindow("cursor test", 0, 0, 640, 480, SDL_WINDOW_SHOWN);
  assert(win); original = SDL_GetCursor(); if (!original) original = SDL_GetDefaultCursor();
  assert(original); SDL_SetCursor(original); enabled();
  NOW = 10; app_pointer_system(1);
  NOW = 12.99; ptr_frame(); assert(is_shown());
  NOW = 13; ptr_frame(); assert(!is_shown()); enabled();
  SDL_Cursor *blank = SDL_GetCursor();
  puts("PASS real SDL: idle swaps cursor image without disabling pointer input");

  SDL_Event motion; memset(&motion, 0, sizeof motion); motion.type = SDL_MOUSEMOTION;
  motion.motion.x = 100; motion.motion.y = 100;
  assert(SDL_PushEvent(&motion) == 1);
  SDL_Event event; int received = 0;
  while (SDL_PollEvent(&event)) if (event.type == SDL_MOUSEMOTION) {
    NOW = 14; app_pointer_move(event.motion.x, event.motion.y); received++;
  }
  assert(received && is_shown()); enabled();
  puts("PASS real SDL: motion event reaches handler and restores original image");

  NOW = 20; ptr_frame(); assert(SDL_GetCursor() == blank);
  NOW = 21; app_pointer_move(PTR.x, PTR.y); assert(is_shown());
  puts("PASS wake at unchanged coordinates restores image after idle");

  NOW = 30; app_key(K_LEFT, 1, 0); assert(!is_shown());
  NOW = 30.1; app_pointer_system(1); assert(!is_shown());
  NOW = 30.5; app_pointer_system(1); assert(is_shown());
  puts("PASS arrow suppression expires; later system wake is accepted");

  NOW = 40; ptr_frame(); assert(!is_shown());
  focus(0); assert(is_shown()); enabled();
  NOW = 50; app_pointer_system(1); app_pointer_move(200, 100); ptr_frame();
  assert(is_shown() && PTR.suspended); enabled();
  puts("PASS focus loss restores image; background events cannot hide Home pointer");
  focus(1); assert(!PTR.suspended && is_shown());
  NOW = 51; app_pointer_move(210, 100);
  NOW = 54; ptr_frame(); assert(!is_shown());
  NOW = 55; app_pointer_button(1, 210, 100); assert(is_shown());
  NOW = 61; ptr_frame(); assert(is_shown());
  app_pointer_button(0, 210, 100);
  NOW = 64; ptr_frame(); assert(!is_shown());
  NOW = 65; app_pointer_button(1, 210, 100); assert(PTR.down);
  focus(0); focus(1); assert(!PTR.down && is_shown());
  NOW = 66; app_pointer_move(211, 100);
  NOW = 69; ptr_frame(); assert(!is_shown());
  puts("PASS foreground return and held click preserve wake/idle behavior");

  playing = 0; NOW = 70; app_pointer_move(220, 100); assert(is_shown());
  NOW = 73; ptr_frame(); assert(!is_shown());
  app_pointer_focus(0); assert(is_shown()); enabled();
  SDL_DestroyWindow(win); SDL_Quit();
  puts("PASS menu idle and exit restore original pointer image");
  puts("7 real-SDL pointer scenarios passed; LG TV verification still required");
  return 0;
}
'''

FAILURE_PREFIX = r'''
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned char Uint8;
typedef struct { int id; } SDL_Cursor;
static SDL_Cursor original={1}, alternate={2}, blank={3};
static SDL_Cursor *current=&original;
static int mode, created, changed;
static SDL_Cursor *get(void) { return current; }
static SDL_Cursor *def(void) { return mode==3 ? NULL : &original; }
static SDL_Cursor *create(const Uint8 *data, const Uint8 *mask, int w, int h, int x, int y) {
  assert(w==8 && h==8 && x==0 && y==0);
  for (int i=0;i<8;i++) assert(data[i]==0 && mask[i]==0);
  created++; return mode==1 ? NULL : &blank;
}
static void set(SDL_Cursor *cursor) { assert(cursor); current=cursor; changed++; }
void *dlsym(void *handle, const char *name) {
  (void)handle;
  if (!strcmp(name,"SDL_GetCursor")) return mode==2 ? NULL : (void *)get;
  if (!strcmp(name,"SDL_GetDefaultCursor")) return mode==6 ? NULL : (void *)def;
  if (!strcmp(name,"SDL_CreateCursor")) return mode==5 ? NULL : (void *)create;
  if (!strcmp(name,"SDL_SetCursor")) return mode==7 ? NULL : (void *)set;
  assert(!"Cursor policy / other native APIs must never be looked up"); return NULL;
}
'''

FAILURE_TESTS = r'''
int main(int argc, char **argv) {
  assert(argc==2); mode=atoi(argv[1]);
  if (mode==3 || mode==4) current=NULL;
  SDL_Cursor *before=current;
  plat_pointer_image(0);
  if (mode==1 || mode==2 || mode==3 || mode==5 || mode==7) {
    assert(current==before && changed==0);
    plat_pointer_image(0); plat_pointer_image(1);
    assert(current==before && changed==0 && created<=1);
  } else {
    assert(current==&blank && created==1);
    plat_pointer_image(0); assert(created==1);
    plat_pointer_image(1); assert(current==&original);
    current=&alternate; plat_pointer_image(0); plat_pointer_image(1);
    assert(current==&alternate && created==1);
  }
  printf("PASS cursor image backend case %d: restore or leave original intact\n",mode);
  return 0;
}
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdl-include', type=pathlib.Path)
    args = parser.parse_args()
    source = (ROOT / 'src/core/app.c').read_text()
    start = source.index('/* ---- the Magic Remote pointer.')
    end = source.index('/* where the focus is,', start)
    # A build using either old visibility switch must fail the safety guard.
    native = (ROOT / 'src/platform/webos/plat_webos.c').read_text()
    body = function(native, 'plat_pointer_image')
    assert 'SDL_ShowCursor' not in body and 'SDL_webOSCursorVisibility' not in body
    main_source = (ROOT / 'src/main.c').read_text()
    assert 'app_pointer_focus(life > 0)' in main_source and 'app_pointer_focus(0)' in main_source
    with tempfile.TemporaryDirectory(prefix='stremio-pointer-') as folder:
        tmp = pathlib.Path(folder); c = tmp / 'pointer.c'; binary = tmp / 'pointer'
        c.write_text(PREFIX + body + function(native, 'plat_lifecycle') + source[start:end] + TESTS)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-D_GNU_SOURCE', '-DSB_WEBOS',
                        '-O1', '-g', '-Wall', '-Wextra', '-Wno-unused-function',
                        '-Wno-misleading-indentation', *sdl_include(tmp, args.sdl_include),
                        '-I', str(ROOT / 'src'), '-I', str(ROOT / 'third_party/cjson'),
                        str(c), '-Wl,--export-dynamic', '-l:libSDL2-2.0.so.0', '-ldl', '-lm',
                        '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True, env={**os.environ, 'SDL_VIDEODRIVER': 'x11'})
        failures=tmp/'failures.c';failbin=tmp/'failures'
        failures.write_text(FAILURE_PREFIX+body+FAILURE_TESTS)
        subprocess.run([os.environ.get('CC','cc'),'-std=c11','-D_GNU_SOURCE','-O1',
                        '-Werror=implicit-function-declaration',str(failures),'-o',str(failbin)],check=True)
        for mode in range(8):
            subprocess.run([str(failbin),str(mode)],check=True)
        print('15 cursor scenarios passed: 7 real-SDL, 8 controlled backend/failure cases')


if __name__ == '__main__':
    main()
