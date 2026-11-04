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
#include <SDL2/SDL_webOS.h>
#include <assert.h>
#include <dlfcn.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>
static SDL_Window *pointerWindow;
unsigned long plat_luna_subscribe(const char *uri, const char *payload, PlatLunaCb cb, void *ud) {
  (void)uri; (void)payload; (void)cb; (void)ud;
  assert(!"Cursor lifecycle must not query a foreground service"); return 0;
}
void plat_luna_cancel(unsigned long token) { (void)token; assert(!"Cursor lifecycle must not use Luna handles"); }
Scr SCR = SCR_HOME;
static double NOW;
TopNav topNav = { .want = -1 };
static int playing = 1;
static int pointed, canceled, okDowns, okUps, navDowns;
static struct { int down; } okHold;
static int okDown, menuGuard;
static int saver_on(void) { return 0; }
static void saver_stop(void) {}
static int player_open(void) { return playing; }
void player_ptr(int type, float x, float y) { (void)x; (void)y; if (type == 3) canceled++; else pointed++; }
static void idle_touch(void) {}
static void idle_touch_by(const char *why) { (void)why; }
int app_mirror_key(int k) { return k; }
static Scr chipScr(int n) { (void)n; return SCR_HOME; }
static void topnav_paint(void) {}
static void key_core(int k, int down, int repeat) {
  (void)repeat; if (k==K_OK) { if (down) okDowns++; else okUps++; }
  if (down && k>=K_LEFT && k<=K_DOWN) navDowns++;
}
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
/* Production ordering: repair lifecycle first, then deliver the same input without dropping its action. */
static void pointer_event(SDL_Event *ev) {
  int life=plat_lifecycle(ev); if(life) app_pointer_focus(life>0);
  if(ev->type==SDL_MOUSEWHEEL) app_pointer_wheel(ev->wheel.x,ev->wheel.y);
  else if(ev->type==SDL_MOUSEMOTION) app_pointer_move(ev->motion.x,ev->motion.y);
  else if(ev->type==SDL_MOUSEBUTTONDOWN || ev->type==SDL_MOUSEBUTTONUP)
    app_pointer_button(ev->type==SDL_MOUSEBUTTONDOWN,ev->button.x,ev->button.y);
}
int main(void) {
  assert(SDL_Init(SDL_INIT_VIDEO) == 0);
  SDL_Window *win = SDL_CreateWindow("cursor test", 0, 0, 640, 480, SDL_WINDOW_SHOWN);
  assert(win); original = SDL_GetCursor(); if (!original) original = SDL_GetDefaultCursor();
  pointerWindow=win; setenv("APPID","tv.stremioorigin.app",1);
  assert(original); SDL_SetCursor(original); enabled();
  NOW = 10; app_pointer_system(1);
  NOW = 12.99; ptr_frame(); assert(is_shown());
  NOW = 13; ptr_frame(); assert(!is_shown()); enabled();
  SDL_Cursor *blank = SDL_GetCursor();
  puts("PASS real SDL: idle swaps cursor image without disabling pointer input");

  NOW = 14; app_pointer_move(PTR.x, PTR.y);
  assert(!is_shown() && !PTR.on);
  NOW = 14.1; app_pointer_system(1); app_pointer_move(2, 1); ptr_frame();
  assert(!is_shown() && !PTR.on);
  puts("PASS idle mode ignores same-position wake, tiny movement and show notices");

  SDL_Event motion; memset(&motion, 0, sizeof motion); motion.type = SDL_MOUSEMOTION;
  motion.motion.x = 100; motion.motion.y = 100;
  assert(SDL_PushEvent(&motion) == 1);
  SDL_Event event; int received = 0;
  while (SDL_PollEvent(&event)) if (event.type == SDL_MOUSEMOTION) {
    NOW = 14.2; app_pointer_move(event.motion.x, event.motion.y); received++;
  }
  assert(received && !is_shown() && !PTR.on); enabled();
  for (int i=0;i<100;i++) { NOW=15+i*.02; app_pointer_move((i*197)%1800,(i*131)%1000); ptr_frame(); assert(!is_shown()); }
  puts("PASS real SDL: even large repeated movements never wake a hidden pointer");

  NOW=18; app_pointer_wheel(0,0); assert(!is_shown());
  int beforeNav=navDowns;
  app_pointer_wheel(0,1); assert(is_shown() && PTR.on && navDowns==beforeNav);
  NOW=18.1; app_pointer_wheel(0,-1); assert(is_shown() && navDowns==beforeNav+1);
  puts("PASS first wheel notch wakes without navigating; later wheel notches retain navigation");

  NOW = 22; ptr_frame(); assert(SDL_GetCursor() == blank);
  NOW = 23; app_pointer_move(PTR.x, PTR.y); assert(!is_shown());
  NOW = 23.1; app_pointer_move(PTR.x+800, PTR.y); assert(!is_shown());
  NOW=24; app_pointer_wheel(0,-1); assert(is_shown());
  puts("PASS idle lock is released only by an actual nonzero wheel event");

  NOW = 30; app_key(K_LEFT, 1, 0); assert(!is_shown());
  NOW = 30.1; app_pointer_system(1); assert(!is_shown());
  NOW = 30.5; app_pointer_system(1); assert(!is_shown());
  int before=pointed;
  float anchorX=PTR.x, anchorY=PTR.y;
  for (int i=0;i<200;i++) {
    NOW=30.6+i*.01; app_pointer_system(1);
    app_pointer_move(anchorX+(i%3)-1,anchorY+(i%5)-2); ptr_frame();
    assert(!is_shown() && !PTR.on && pointed==before);
  }
  puts("PASS arrow mode stays inactive across repeated show notices and hand tremor");
  for (int i=0;i<12;i++) {
    NOW=33+i*.5; app_pointer_move(anchorX+i*8,anchorY); ptr_frame();
    assert(!is_shown() && !PTR.on && pointed==before);
  }
  puts("PASS isolated small motions do not accumulate into an accidental wake");
  NOW=39; app_pointer_move(PTR.x,PTR.y);
  NOW=39.1; app_pointer_move(PTR.x+800,PTR.y); assert(!is_shown());
  NOW=39.2; app_pointer_wheel(0,1); assert(is_shown());
  puts("PASS arrow mode also requires the wheel, regardless of movement distance");

  NOW=40; app_key(K_DOWN,1,0); before=pointed;
  NOW=41; app_pointer_button(1,PTR.x,PTR.y); app_key(K_OK,1,0);
  app_pointer_button(0,PTR.x,PTR.y); app_key(K_OK,0,0);
  assert(!is_shown() && !PTR.on && pointed==before && okDowns==1 && okUps==1);
  NOW=42; app_key(K_OK,1,0); app_pointer_button(1,PTR.x,PTR.y);
  app_key(K_OK,0,0); app_pointer_button(0,PTR.x,PTR.y);
  assert(!is_shown() && pointed==before && okDowns==2 && okUps==2);
  puts("PASS inactive clicks confirm keyboard focus once, in either event order");

  NOW = 43; ptr_frame(); assert(!is_shown());
  focus(0); assert(is_shown()); enabled();
  NOW = 50; app_pointer_system(1); app_pointer_move(200, 100); app_pointer_wheel(0,1); ptr_frame();
  assert(is_shown() && PTR.suspended); enabled();
  puts("PASS focus loss restores image; background events cannot hide Home pointer");
  focus(1); assert(!PTR.suspended && !is_shown());
  app_pointer_move(700,100); app_pointer_system(1); assert(!is_shown());
  NOW=50.5; app_key(K_LEFT,1,0); assert(!is_shown());
  puts("PASS arrow after foreground return hides even before the first pointer event");
  NOW = 51; app_pointer_move(210, 100);
  NOW=51.1; app_pointer_move(290,100); assert(!is_shown());
  app_pointer_wheel(0,1); assert(is_shown());
  NOW = 52; app_pointer_button(1, 290, 100); assert(is_shown());
  NOW = 61; ptr_frame(); assert(is_shown());
  app_pointer_button(0, 290, 100);
  NOW = 64; ptr_frame(); assert(!is_shown());
  NOW = 65; app_pointer_move(300,100);
  NOW = 65.1; app_pointer_move(380,100); assert(!is_shown());
  app_pointer_wheel(0,1); assert(is_shown());
  app_pointer_button(1,380,100); assert(PTR.down);
  focus(0); focus(1); assert(!PTR.down && is_shown());
  NOW = 66; app_pointer_move(390, 100);
  NOW = 69; ptr_frame(); assert(!is_shown());
  puts("PASS foreground return and held click preserve wake/idle behavior");

  playing = 0; NOW = 70; app_pointer_move(400, 100);
  NOW=70.1; app_pointer_move(480,100); assert(!is_shown());
  app_pointer_wheel(0,1); assert(is_shown());
  NOW = 73.1; ptr_frame(); assert(!is_shown());
  app_pointer_focus(0); assert(is_shown()); enabled();
  puts("PASS menu idle and exit restore original pointer image");

  app_pointer_focus(1); playing=1; NOW=80; app_pointer_wheel(0,1);
  NOW=81; app_pointer_button(1,400,100); assert(PTR.down==2);
  okHold.down=okDown=menuGuard=1; int cancels=canceled;
  NOW=82; app_key(K_LEFT,1,0);
  assert(!PTR.down && !PTR.eatOk && !PTR.eatUp && canceled==cancels+1);
  assert(!okHold.down && !okDown && !menuGuard && !is_shown());
  NOW=83; app_pointer_wheel(0,1); NOW=86; ptr_frame(); assert(!is_shown());
  int oks=okDowns; NOW=87; app_key(K_OK,1,0); app_key(K_OK,0,0); assert(okDowns==oks+1);
  puts("PASS lost mouse-up is canceled by arrow navigation without action, and idle/OK recover");

  NOW=90; app_pointer_wheel(0,1); app_pointer_button(1,400,100); cancels=canceled;
  NOW=91; app_pointer_button(1,400,100); assert(canceled==cancels+1 && PTR.down==2);
  app_pointer_button(0,400,100); assert(!PTR.down);
  puts("PASS a new physical press recovers an earlier lost release");

  NOW=94; ptr_frame(); assert(!is_shown());
  SDL_RaiseWindow(win); SDL_SetWindowInputFocus(win); SDL_PumpEvents();
  assert(SDL_GetKeyboardFocus()==win);
  focus(0); assert(PTR.suspended && is_shown());
  int life=plat_lifecycle(NULL); assert(life==1); app_pointer_focus(1);
  assert(!PTR.suspended && !is_shown());
  puts("PASS confirmed SDL keyboard focus repairs a missing foreground window event");

  SDL_Event bg; memset(&bg,0,sizeof bg); bg.type=SDL_APP_DIDENTERBACKGROUND;
  life=plat_lifecycle(&bg); assert(life==-1); app_pointer_focus(0);
  assert(plat_lifecycle(NULL)==0 && is_shown());
  bg.type=SDL_WINDOWEVENT; bg.window.event=SDL_WINDOWEVENT_SHOWN;
  assert(plat_lifecycle(&bg)==0 && plat_lifecycle(NULL)==0 && is_shown());
  bg.type=SDL_APP_DIDENTERFOREGROUND;
  life=plat_lifecycle(&bg); assert(life==1); app_pointer_focus(1);
  assert(!PTR.suspended && !is_shown());
  puts("PASS an explicit app-background state cannot be undone by stale window focus/show");

  NOW=100; app_pointer_wheel(0,1); focus(0); focus(1); assert(is_shown() && PTR.on);
  NOW=103; ptr_frame(); assert(!is_shown());
  puts("PASS returning with an active cursor still arms idle hiding without another motion event");

  NOW=110; oks=okDowns; int ups=okUps;
  app_key(K_OK,1,0); okHold.down=okDown=1;
  app_pointer_system(0); assert(okHold.down && okDown);
  app_pointer_button(1,400,100); app_key(K_OK,0,0); app_pointer_button(0,400,100);
  assert(okDowns==oks+1 && okUps==ups+1 && !PTR.down);
  okHold.down=okDown=0;
  puts("PASS a system hide between keyboard and mouse events preserves one complete OK press");

  memset(&pointerFocus,0,sizeof pointerFocus);
  SDL_Event panel; memset(&panel,0,sizeof panel); panel.type=SDL_APP_DIDENTERBACKGROUND;
  pointer_event(&panel); assert(PTR.suspended && is_shown());
  for(int i=0;i<1000;i++) assert(plat_lifecycle(NULL)==0);
  SDL_Event wheel;memset(&wheel,0,sizeof wheel);wheel.type=SDL_MOUSEWHEEL;
  wheel.wheel.windowID=SDL_GetWindowID(win);wheel.wheel.y=1;
  NOW=120;pointer_event(&wheel);assert(!PTR.suspended && is_shown());
  SDL_Event move;memset(&move,0,sizeof move);move.type=SDL_MOUSEMOTION;
  move.motion.windowID=SDL_GetWindowID(win);move.motion.x=410;move.motion.y=100;
  before=pointed;pointer_event(&move);ptr_frame();assert(pointed==before+1);
  SDL_Event button;memset(&button,0,sizeof button);button.type=SDL_MOUSEBUTTONDOWN;
  button.button.windowID=SDL_GetWindowID(win);button.button.button=SDL_BUTTON_LEFT;
  button.button.x=410;button.button.y=100;before=pointed;
  pointer_event(&button);button.type=SDL_MOUSEBUTTONUP;pointer_event(&button);
  assert(is_shown() && pointed==before+2);
  NOW=123; ptr_frame(); assert(!is_shown());
  puts("PASS wheel input repairs a missing app return without a service query; motion, clicks and idle work");

  NOW=124;pointer_event(&wheel);pointer_event(&panel);assert(PTR.suspended && is_shown());
  NOW=125;before=pointed;button.type=SDL_MOUSEBUTTONDOWN;pointer_event(&button);
  assert(!PTR.suspended && PTR.down==2 && pointed==before+1);
  assert(plat_lifecycle(&button)==0 && PTR.down==2); /* no second focus reset may cancel this press */
  button.type=SDL_MOUSEBUTTONUP;pointer_event(&button);assert(pointed==before+2 && !PTR.down);
  NOW=128;ptr_frame();assert(!is_shown());
  puts("PASS an addressed click repairs a missing return and delivers that same press/release exactly once");

  for(int i=0;i<100;i++) {
    NOW=140+i*10;pointer_event(&panel);assert(PTR.suspended && is_shown());
    pointer_event(&wheel);assert(!PTR.suspended && PTR.on && is_shown());
    move.motion.x=400+i%2;pointer_event(&move);ptr_frame();before=pointed;
    button.type=SDL_MOUSEBUTTONDOWN;pointer_event(&button);
    button.type=SDL_MOUSEBUTTONUP;pointer_event(&button);assert(pointed==before+2);
    NOW+=3;ptr_frame();assert(!is_shown());
  }
  puts("PASS 100 missing-return cycles retain wheel wake, real SDL images, click actions and idle hiding");

  SDL_WarpMouseInWindow(win,200,100);SDL_PumpEvents();assert(SDL_GetMouseFocus()==win);
  SDL_Event edge;memset(&edge,0,sizeof edge);edge.type=SDL_WINDOWEVENT;edge.window.windowID=SDL_GetWindowID(win);
  for(int i=0;i<100;i++) {
    NOW=1200+i*10;app_key(K_LEFT,1,0);assert(PTR.wheelLocked && !is_shown());
    edge.window.event=SDL_WINDOWEVENT_LEAVE;pointer_event(&edge);
    assert(PTR.suspended && is_shown() && plat_lifecycle(NULL)==0);
    NOW+=4;ptr_frame();assert(is_shown()); /* system menu retains its cursor */
    edge.window.event=SDL_WINDOWEVENT_ENTER;pointer_event(&edge);
    assert(!PTR.suspended && PTR.wheelLocked && !is_shown());
    move.motion.x=410+i%2;pointer_event(&move);assert(!is_shown());
    pointer_event(&wheel);assert(is_shown() && PTR.on && !PTR.wheelLocked);
    before=pointed;button.type=SDL_MOUSEBUTTONDOWN;pointer_event(&button);
    button.type=SDL_MOUSEBUTTONUP;pointer_event(&button);assert(pointed==before+2);
    NOW+=3;ptr_frame();assert(!is_shown());
  }
  puts("PASS 100 quick-panel handovers preserve hidden intent, system cursor, wheel activation and functional clicks");
  app_pointer_focus(0);
  SDL_DestroyWindow(win); SDL_Quit();
  puts("23 real-SDL pointer scenarios passed; LG TV verification still required");
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
static SDL_Cursor *current=&original, *nativeImage=&original;
static int mode, created, changed;
static SDL_Cursor *get(void) { return current; }
static SDL_Cursor *def(void) { return mode==3 ? NULL : &original; }
static SDL_Cursor *create(const Uint8 *data, const Uint8 *mask, int w, int h, int x, int y) {
  assert(w==8 && h==8 && x==0 && y==0);
  for (int i=0;i<8;i++) assert(data[i]==0 && mask[i]==0);
  created++; return mode==1 ? NULL : &blank;
}
static void set(SDL_Cursor *cursor) { assert(cursor); nativeImage=current=cursor; changed++; }
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
    nativeImage=&original; plat_pointer_image(0); assert(created==1 && nativeImage==&blank);
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
        focus_start=native.index('/* ---- foreground state:')
        focus_end=native.index('/* Settings > Language',focus_start)
        c.write_text(PREFIX + body + function(native,'plat_map_key') + native[focus_start:focus_end] + function(source, 'key_cancel_press') + source[start:end] + TESTS)
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
        print('31 cursor scenarios passed: 23 real-SDL, 8 controlled backend/failure cases')


if __name__ == '__main__':
    main()
