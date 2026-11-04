#!/usr/bin/env python3
"""Exercise production webOS foreground reconciliation with controlled SDL/Luna input.

These fixtures model system panels and stale/missing notifications; they do not
emulate the LG compositor or assert its actual service-response shape.
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
static const char *own="{\"foregroundAppInfo\":[{\"appId\":\"tv.stremioorigin.app\",\"displayId\":0}]}";
static const char *settings="{\"foregroundAppInfo\":[{\"appId\":\"com.webos.app.settings\",\"displayId\":0}]}";
static const char *denied="{\"returnValue\":false,\"errorText\":\"Denied\"}";
static void background(void) {
  SDL_Event e;memset(&e,0,sizeof e);e.type=SDL_APP_DIDENTERBACKGROUND;
  assert(plat_lifecycle(&e)==-1 && pointerFocus.away && pointerFocus.background);
}
static int snapshot(const char *json) {
  if (!pointerFocus.request) { pointerFocus.nextAt=0;assert(plat_lifecycle(NULL)==0); }
  assert(pointerFocus.request && reply);reply(json,replyData);return plat_lifecycle(NULL);
}
static SDL_Event navigation(Uint32 window) {
  SDL_Event e;memset(&e,0,sizeof e);e.type=SDL_KEYDOWN;e.key.windowID=window;
  e.key.keysym.sym=SDLK_LEFT;e.key.keysym.scancode=SDL_SCANCODE_LEFT;return e;
}
static SDL_Event wheel(Uint32 window) {
  SDL_Event e;memset(&e,0,sizeof e);e.type=SDL_MOUSEWHEEL;e.wheel.windowID=window;e.wheel.y=1;return e;
}
int main(int argc,char **argv) {
  assert(argc==2);setenv("APPID","tv.stremioorigin.app",1);background();
  if (!strcmp(argv[1],"native-return")) {
    assert(snapshot(settings)==0);assert(snapshot(own)==1);
    assert(!pointerFocus.away && !pointerFocus.background);
  } else if (!strcmp(argv[1],"panel-open")) {
    keyboard=NULL;assert(snapshot(settings)==0);
    SDL_Event e=wheel(1);assert(plat_lifecycle(&e)==0 && pointerFocus.away);
  } else if (!strcmp(argv[1],"home-stale-sdl")) {
    assert(snapshot("{\"foregroundAppInfo\":[{\"appId\":\"com.webos.app.home\"}]}")==0);
    assert(keyboard==pointerWindow && plat_lifecycle(NULL)==0 && pointerFocus.away);
  } else if (!strcmp(argv[1],"mixed-overlay")) {
    assert(snapshot("{\"foregroundAppInfo\":[{\"appId\":\"tv.stremioorigin.app\"},{\"appId\":\"com.webos.app.settings\"}]}")==0);
    SDL_Event e=wheel(1);assert(plat_lifecycle(&e)==0 && !pointerFocus.ownForeground);
  } else if (!strcmp(argv[1],"navigation-return")) {
    keyboard=NULL;SDL_Event e=navigation(1);assert(plat_lifecycle(&e)==1);
    assert(!pointerFocus.background && !pointerFocus.away);
  } else if (!strcmp(argv[1],"unavailable")) {
    keyboard=NULL;assert(snapshot(denied)==0 && pointerFocus.source==1);
    assert(snapshot(denied)==0 && pointerFocus.away);
    SDL_Event e=navigation(1);assert(plat_lifecycle(&e)==1);
  } else if (!strcmp(argv[1],"stale-reply")) {
    pointerFocus.nextAt=0;assert(plat_lifecycle(NULL)==0);unsigned epoch=pointerFocus.epoch;
    background();assert(pointerFocus.epoch!=epoch);reply(own,replyData);
    assert(plat_lifecycle(NULL)==0 && pointerFocus.away);
  } else if (!strcmp(argv[1],"obsolete-ticket")) {
    assert(snapshot(settings)==0);void *old=replyData;
    pointerFocus.nextAt=0;plat_lifecycle(NULL);assert(pointerFocus.request);
    pointer_foreground_reply(own,old);assert(!pointerFocus.done);
    reply(own,replyData);assert(plat_lifecycle(NULL)==1);
  } else if (!strcmp(argv[1],"wheel-proof")) {
    keyboard=NULL;SDL_Event e=wheel(1);assert(plat_lifecycle(&e)==0);
    assert(snapshot(own)==0 && pointerFocus.ownForeground && pointerFocus.away);
    SDL_Event bad=wheel(2);assert(plat_lifecycle(&bad)==0);
    assert(plat_lifecycle(&e)==1 && !pointerFocus.away);
  } else if (!strcmp(argv[1],"hidden-window")) {
    windowFlags=SDL_WINDOW_HIDDEN;assert(snapshot(own)==0);
    SDL_Event e=navigation(1);assert(plat_lifecycle(&e)==0 && pointerFocus.away);
  } else if (!strcmp(argv[1],"foreign-input")) {
    keyboard=NULL;SDL_Event e=navigation(2);assert(plat_lifecycle(&e)==0);
    e=navigation(1);e.key.repeat=1;assert(plat_lifecycle(&e)==0);
    e.key.repeat=0;e.type=SDL_KEYUP;assert(plat_lifecycle(&e)==0);
    e.type=SDL_KEYDOWN;e.key.keysym.sym=0;e.key.keysym.scancode=SDL_WEBOS_SCANCODE_CURSOR_SHOW;
    assert(plat_lifecycle(&e)==0 && pointerFocus.away);
  } else if (!strcmp(argv[1],"malformed")) {
    keyboard=NULL;assert(snapshot("invalid JSON")==0 && pointerFocus.away);
    assert(snapshot("{\"returnValue\":true}")==0 && pointerFocus.away);
  } else if (!strcmp(argv[1],"fallback-card")) {
    pointerFocus.source=1;keyboard=NULL;
    assert(snapshot("{\"returnValue\":true,\"appId\":\"tv.stremioorigin.app\"}")==0);
    keyboard=pointerWindow;
    assert(snapshot("{\"returnValue\":true,\"appId\":\"tv.stremioorigin.app\"}")==1);
  } else if (!strcmp(argv[1],"timeout")) {
    keyboard=NULL;pointerFocus.nextAt=0;plat_lifecycle(NULL);assert(requests==1);
    ticks+=2001;assert(plat_lifecycle(NULL)==0 && requests==2 && pointerFocus.source==1);
    ticks+=2001;assert(plat_lifecycle(NULL)==0 && !pointerFocus.request && pointerFocus.away);
    for(int i=0;i<100;i++)plat_lifecycle(NULL);assert(requests==2 && cancels==2);
  } else if (!strcmp(argv[1],"repeated-panels")) {
    for(int i=0;i<2000;i++) {
      if(i)background();assert(snapshot(settings)==0);assert(snapshot(own)==1);
      assert(!pointerFocus.away && !pointerFocus.background);ticks+=20;
    }
  } else if (!strcmp(argv[1],"display-filter")) {
    assert(snapshot("{\"foregroundAppInfo\":[{\"appId\":\"other.app\",\"displayId\":1},{\"appId\":\"tv.stremioorigin.app\",\"displayId\":0}]}")==1);
  } else assert(!"unknown case");
  printf("PASS foreground reconciliation %s\n",argv[1]);return 0;
}
'''

CASES = ('native-return','panel-open','home-stale-sdl','mixed-overlay',
         'navigation-return','unavailable','stale-reply','obsolete-ticket',
         'wheel-proof','hidden-window','foreign-input','malformed',
         'fallback-card','timeout','repeated-panels','display-filter')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdl-include',type=Path)
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
        for case in CASES:
            result=subprocess.run([str(exe),case],timeout=10,
                                  stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            if result.returncode:
                sys.stderr.write(result.stdout+result.stderr)
                result.check_returncode()
            print('PASS foreground reconciliation '+case)
        print(f'{len(CASES)} foreground-state scenarios passed; LG event/API behavior is not emulated')


if __name__=='__main__':
    main()
