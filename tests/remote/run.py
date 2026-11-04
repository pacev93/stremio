#!/usr/bin/env python3
"""Exercise real LG key mapping and the player's media-command handling."""
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
#include <SDL2/SDL.h>
#include <SDL2/SDL_webOS.h>
#include "core/keys.h"
#include "core/video.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct { int open, live, started, failed, canNext, ssOn, mode, hvOn; double lastAct; struct { int pauseAfterSeek; } dts; } P;
static VidState state = VID_PLAYING;
static int plays, pauses;
VidState video_state(void) { return state; }
void video_play(void) { plays++; state = VID_PLAYING; }
void video_pause(void) { pauses++; state = VID_PAUSED; }
static void save_progress(int force) { (void)force; }
static void show_osd(int keep) { (void)keep; }
static void app_touch(void) {}
static double now_(void) { return 10; }
static void ss_exit(void) { P.ssOn=0; }
static void try_next(void) {}
static void close_player(int n, int s) { (void)n; (void)s; }
'''

TESTS = r'''
static int map(int sym, int sc) {
  SDL_KeyboardEvent event; memset(&event,0,sizeof event);
  event.keysym.sym=(SDL_Keycode)sym; event.keysym.scancode=(SDL_Scancode)sc;
  return plat_map_key(&event);
}
int main(void) {
  /* LG's native SDL table maps Linux KEY_PLAY (207) to private scancode 450.
     The symbol is zero on the documented firmware, so web keyCode 415 cannot help. */
  assert(map(0,450)==K_PLAY);
  assert(map(SDLK_SCANCODE_MASK|450,450)==K_PLAY);
  puts("PASS native LG Play scancode 450, with absent or scancode-based symbol");
  assert(map(SDLK_AUDIOPLAY,SDL_SCANCODE_AUDIOPLAY)==K_PLAYPAUSE);
  assert(map(SDLK_PAUSE,SDL_SCANCODE_PAUSE)==K_PAUSE);
  assert(map(SDLK_LEFT,SDL_SCANCODE_LEFT)==K_LEFT);
  assert(map(0,SDL_WEBOS_SCANCODE_BACK)==K_BACK);
  assert(map(0,SDL_WEBOS_SCANCODE_CURSOR_SHOW)==K_CURSOR_SHOW);
  assert(map(0,SDL_WEBOS_SCANCODE_CURSOR_HIDE)==K_CURSOR_HIDE);
  assert(map(0,SDL_SCANCODE_UNKNOWN)==K_NONE);
  puts("PASS normalised SDL keys and existing navigation/cursor mappings retained");
  P.open=P.live=P.started=1;
  player_key(map(SDLK_PAUSE,SDL_SCANCODE_PAUSE),1);
  assert(state==VID_PAUSED && pauses==1);
  player_key(map(0,450),1);
  assert(state==VID_PLAYING && plays==1);
  player_key(map(0,450),1);
  player_key(map(0,450),0);
  assert(state==VID_PLAYING && plays==1 && pauses==1);
  puts("PASS Pause then Play resumes; repeated dedicated Play never pauses again");
  player_key(map(SDLK_AUDIOPLAY,SDL_SCANCODE_AUDIOPLAY),1); assert(state==VID_PAUSED);
  player_key(map(SDLK_AUDIOPLAY,SDL_SCANCODE_AUDIOPLAY),1); assert(state==VID_PLAYING);
  puts("PASS combined Play/Pause key still toggles");
  P.dts.pauseAfterSeek=1; player_key(map(0,450),1);
  assert(!P.dts.pauseAfterSeek && state==VID_PLAYING);
  puts("PASS explicit Play cancels a pending pause restoration after converted seeking");
  puts("5 media-key scenarios passed; actual remote event encoding not observed on TV");
  return 0;
}
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdl-include',type=pathlib.Path)
    parser.add_argument('--platform-source',type=pathlib.Path,default=ROOT/'src/platform/webos/plat_webos.c')
    args=parser.parse_args()
    platform=args.platform_source.read_text();player=(ROOT/'src/screens/player.c').read_text()
    commands=function(player,'player_key')
    # Only the actual media-command prefix; remaining branches are UI navigation.
    commands=commands[:commands.index('  if (k == K_STOP')]+'}\n'
    code=PREFIX+function(platform,'plat_map_key')+function(player,'paused')+function(player,'toggle')+commands+TESTS
    with tempfile.TemporaryDirectory(prefix='stremio-remote-') as folder:
        tmp=pathlib.Path(folder);c=tmp/'remote.c';binary=tmp/'remote';c.write_text(code)
        subprocess.run([os.environ.get('CC','cc'),'-std=c11','-O1','-g',
                        '-Wno-switch',*sdl_include(tmp,args.sdl_include),
                        '-I',str(ROOT/'src'),str(c),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)


if __name__=='__main__':
    main()
