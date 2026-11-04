#!/usr/bin/env python3
"""Exercise production webOS focus recovery with app-directed SDL input.

These fixtures model missing return events and input addressed to the app window.
Service stubs ensure no foreground-service request can gate pointer input.
The actual LG compositor is not emulated.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cutil import ROOT, function, sdl_include

PREFIX = r'''
#include "platform/plat.h"
#include "core/keys.h"
#include "cJSON.h"
#include <SDL2/SDL_webOS.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static SDL_Window *pointerWindow=(SDL_Window *)1;
static SDL_Window *keyboard=(SDL_Window *)1, *mouse;
static Uint32 ticks=100, windowFlags=SDL_WINDOW_SHOWN;
static Uint32 test_ticks(void) { return ticks; }
static SDL_Window *test_keyboard(void) { return keyboard; }
static SDL_Window *test_mouse(void) { return mouse; }
static Uint32 test_flags(SDL_Window *w) { (void)w;return windowFlags; }
static Uint32 test_id(SDL_Window *w) { return (Uint32)(uintptr_t)w; }
#define SDL_GetTicks test_ticks
#define SDL_GetKeyboardFocus test_keyboard
#define SDL_GetMouseFocus test_mouse
#define SDL_GetWindowFlags test_flags
#define SDL_GetWindowID test_id
static PlatLunaCb reply;
static void *replyData;
static int requests,cancels;
unsigned long plat_luna_subscribe(const char *u,const char *p,PlatLunaCb cb,void *ud) {
  assert(strstr(u,"getForegroundAppInfo") && !strcmp(p,"{}"));
  reply=cb;replyData=ud;return ++requests;
}
void plat_luna_cancel(unsigned long t) { assert(t);cancels++; }
'''

TESTS = r'''
static void background(void) {
  SDL_Event e;memset(&e,0,sizeof e);e.type=SDL_APP_DIDENTERBACKGROUND;
  assert(plat_lifecycle(&e)==-1 && pointerFocus.away && pointerFocus.background);
}
static SDL_Event navigation(Uint32 window) {
  SDL_Event e;memset(&e,0,sizeof e);e.type=SDL_KEYDOWN;e.key.windowID=window;
  e.key.keysym.sym=SDLK_LEFT;e.key.keysym.scancode=SDL_SCANCODE_LEFT;return e;
}
static SDL_Event wheel(Uint32 window) {
  SDL_Event e;memset(&e,0,sizeof e);e.type=SDL_MOUSEWHEEL;e.wheel.windowID=window;e.wheel.y=1;return e;
}
static SDL_Event click(Uint32 window) {
  SDL_Event e;memset(&e,0,sizeof e);e.type=SDL_MOUSEBUTTONDOWN;e.button.windowID=window;e.button.button=SDL_BUTTON_LEFT;return e;
}
static SDL_Event motion(Uint32 window) {
  SDL_Event e;memset(&e,0,sizeof e);e.type=SDL_MOUSEMOTION;e.motion.windowID=window;e.motion.x=400;return e;
}
static SDL_Event window_event(Uint32 window,Uint8 kind) {
  SDL_Event e;memset(&e,0,sizeof e);e.type=SDL_WINDOWEVENT;e.window.windowID=window;e.window.event=kind;return e;
}
int main(int argc,char **argv) {
  assert(argc==2);setenv("APPID","tv.stremioorigin.app",1);
  if (!strcmp(argv[1],"request-free-loop")) {
    for(int i=0;i<10000;i++) { ticks+=20;assert(plat_lifecycle(NULL)==0); }
    assert(!pointerFocus.away && !requests);
  } else if (!strcmp(argv[1],"wheel-return")) {
    background();keyboard=mouse=NULL;SDL_Event e=wheel(1);
    assert(plat_lifecycle(&e)==1 && !pointerFocus.away && !pointerFocus.background);
    assert(plat_lifecycle(&e)==0);
  } else if (!strcmp(argv[1],"click-return")) {
    background();keyboard=mouse=NULL;SDL_Event e=click(1);
    assert(plat_lifecycle(&e)==1 && !pointerFocus.away);
  } else if (!strcmp(argv[1],"motion-return")) {
    background();keyboard=NULL;mouse=pointerWindow;SDL_Event e=motion(1);
    assert(plat_lifecycle(&e)==1 && !pointerFocus.background);
  } else if (!strcmp(argv[1],"navigation-return")) {
    background();keyboard=NULL;SDL_Event e=navigation(1);assert(plat_lifecycle(&e)==1);
  } else if (!strcmp(argv[1],"legacy-navigation")) {
    background();keyboard=NULL;SDL_Event e=navigation(0);assert(plat_lifecycle(&e)==1);
  } else if (!strcmp(argv[1],"panel-open")) {
    background();assert(plat_lifecycle(NULL)==0 && pointerFocus.away);
    SDL_Event e=window_event(1,SDL_WINDOWEVENT_SHOWN);assert(plat_lifecycle(&e)==0);
    e.window.event=SDL_WINDOWEVENT_RESTORED;assert(plat_lifecycle(&e)==0);
    e=navigation(1);e.key.keysym.sym=0;e.key.keysym.scancode=SDL_WEBOS_SCANCODE_CURSOR_SHOW;
    assert(plat_lifecycle(&e)==0 && pointerFocus.away);
  } else if (!strcmp(argv[1],"foreign-input")) {
    background();keyboard=mouse=NULL;
    SDL_Event events[]={navigation(2),wheel(2),click(2),motion(2),window_event(2,SDL_WINDOWEVENT_FOCUS_GAINED)};
    for(unsigned i=0;i<sizeof events/sizeof events[0];i++) assert(plat_lifecycle(&events[i])==0);
    assert(pointerFocus.away);
  } else if (!strcmp(argv[1],"unaddressed-pointer")) {
    background();mouse=pointerWindow;
    SDL_Event events[]={wheel(0),click(0),motion(0)};
    for(unsigned i=0;i<sizeof events/sizeof events[0];i++) assert(plat_lifecycle(&events[i])==0);
    assert(pointerFocus.away);
  } else if (!strcmp(argv[1],"hidden-window")) {
    background();windowFlags=SDL_WINDOW_HIDDEN;
    SDL_Event events[]={wheel(1),click(1),navigation(1)};
    for(unsigned i=0;i<sizeof events/sizeof events[0];i++) assert(plat_lifecycle(&events[i])==0);
    SDL_Event e;memset(&e,0,sizeof e);e.type=SDL_APP_DIDENTERFOREGROUND;
    assert(plat_lifecycle(&e)==0 && pointerFocus.away);
    windowFlags=SDL_WINDOW_SHOWN;e=window_event(1,SDL_WINDOWEVENT_SHOWN);
    assert(plat_lifecycle(&e)==1 && !pointerFocus.away);
  } else if (!strcmp(argv[1],"orphan-release")) {
    background();SDL_Event e=click(1);e.type=SDL_MOUSEBUTTONUP;assert(plat_lifecycle(&e)==0);
    e=click(1);e.button.button=SDL_BUTTON_RIGHT;assert(plat_lifecycle(&e)==0);
    e=navigation(1);e.key.repeat=1;assert(plat_lifecycle(&e)==0);
    e.key.repeat=0;e.type=SDL_KEYUP;assert(plat_lifecycle(&e)==0);
    e=navigation(1);e.key.keysym.sym=0;e.key.keysym.scancode=450;assert(plat_lifecycle(&e)==0);
    e=wheel(1);e.wheel.x=e.wheel.y=0;assert(plat_lifecycle(&e)==0 && pointerFocus.away);
  } else if (!strcmp(argv[1],"enter-return")) {
    background();keyboard=NULL;mouse=pointerWindow;
    SDL_Event e=window_event(1,SDL_WINDOWEVENT_ENTER);assert(plat_lifecycle(&e)==1);
  } else if (!strcmp(argv[1],"enter-without-focus")) {
    background();keyboard=mouse=NULL;SDL_Event e=window_event(1,SDL_WINDOWEVENT_ENTER);
    assert(plat_lifecycle(&e)==1 && !pointerFocus.away); /* addressed enter wins over lagging SDL cache */
  } else if (!strcmp(argv[1],"quick-panel")) {
    mouse=pointerWindow;SDL_Event e=window_event(1,SDL_WINDOWEVENT_LEAVE);
    assert(plat_lifecycle(&e)==-1);assert(plat_lifecycle(NULL)==0 && pointerFocus.away);
    mouse=NULL;assert(plat_lifecycle(NULL)==0); /* system owns the pointer, keyboard may stay here */
    background();e=window_event(1,SDL_WINDOWEVENT_SHOWN);assert(plat_lifecycle(&e)==0);
    e=navigation(1);e.key.keysym.sym=0;e.key.keysym.scancode=SDL_WEBOS_SCANCODE_BACK;
    assert(plat_lifecycle(&e)==0); /* Back alone must not claim system focus */
    mouse=pointerWindow;assert(plat_lifecycle(NULL)==1 && !pointerFocus.away);
  } else if (!strcmp(argv[1],"stale-pointer-focus")) {
    mouse=pointerWindow;background();for(int i=0;i<100;i++)assert(plat_lifecycle(NULL)==0);
    assert(pointerFocus.away); /* no departure was observed */
  } else if (!strcmp(argv[1],"leave-enter-cycles")) {
    for(int i=0;i<2000;i++) {
      mouse=pointerWindow;SDL_Event e=window_event(1,SDL_WINDOWEVENT_LEAVE);
      assert(plat_lifecycle(&e)==-1 && plat_lifecycle(NULL)==0);
      mouse=NULL;e=window_event(1,SDL_WINDOWEVENT_ENTER);
      assert(plat_lifecycle(&e)==1 && !pointerFocus.away && !pointerFocus.pointerLeft);
    }
  } else if (!strcmp(argv[1],"soft-missing-return")) {
    keyboard=NULL;SDL_Event e=window_event(1,SDL_WINDOWEVENT_FOCUS_LOST);assert(plat_lifecycle(&e)==-1);
    assert(plat_lifecycle(NULL)==0);keyboard=pointerWindow;assert(plat_lifecycle(NULL)==1);
  } else if (!strcmp(argv[1],"foreground-return")) {
    background();SDL_Event e;memset(&e,0,sizeof e);e.type=SDL_APP_DIDENTERFOREGROUND;
    assert(plat_lifecycle(&e)==1);assert(plat_lifecycle(&e)==0);
    background();e=window_event(1,SDL_WINDOWEVENT_FOCUS_GAINED);assert(plat_lifecycle(&e)==1);
  } else if (!strcmp(argv[1],"repeated-panels")) {
    keyboard=mouse=NULL;
    for(int i=0;i<2000;i++) {
      background();assert(plat_lifecycle(NULL)==0);
      SDL_Event e=i%2?wheel(1):click(1);assert(plat_lifecycle(&e)==1);
      assert(!pointerFocus.away && !pointerFocus.background);ticks+=20;
    }
  } else assert(!"unknown case");
  assert(!requests && !cancels);
  printf("PASS input-based focus recovery %s\n",argv[1]);return 0;
}
'''

CASES = ('request-free-loop','wheel-return','click-return','motion-return',
         'navigation-return','legacy-navigation','panel-open','foreign-input',
         'unaddressed-pointer','hidden-window','orphan-release','enter-return',
         'enter-without-focus','quick-panel','stale-pointer-focus','leave-enter-cycles','soft-missing-return','foreground-return','repeated-panels')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdl-include',type=Path)
    parser.add_argument('--case',choices=CASES)
    args=parser.parse_args()
    native=(ROOT/'src/platform/webos/plat_webos.c').read_text()
    start=native.index('/* ---- foreground state:')
    end=native.index('/* Settings > Language',start)
    with tempfile.TemporaryDirectory(prefix='stremio-focus-') as folder:
        tmp=Path(folder);c=tmp/'focus.c';exe=tmp/'focus'
        c.write_text(PREFIX+function(native,'plat_map_key')+native[start:end]+TESTS)
        subprocess.run([os.environ.get('CC','cc'),'-std=c11','-D_GNU_SOURCE','-O1','-g',
                        '-Wno-switch','-Wno-misleading-indentation',*sdl_include(tmp,args.sdl_include),
                        '-I',str(ROOT/'src'),'-I',str(ROOT/'third_party/cjson'),str(c),
                        str(ROOT/'third_party/cjson/cJSON.c'),'-lm','-o',str(exe)],check=True)
        selected=(args.case,) if args.case else CASES
        for case in selected:
            result=subprocess.run([str(exe),case],timeout=10,
                                  stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            if result.returncode:
                sys.stderr.write(result.stdout+result.stderr)
                result.check_returncode()
            print('PASS input-based focus recovery '+case)
        print(f'{len(selected)} focus-recovery scenarios passed; LG compositor is not emulated')


if __name__=='__main__':
    main()
