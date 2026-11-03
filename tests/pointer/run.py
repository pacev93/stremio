#!/usr/bin/env python3
"""Test the actual pointer handlers with a controlled clock and UI/native stubs.

The pointer section is compiled verbatim from app.c, plus the native visibility
function verbatim from plat_webos.c. This avoids linking the complete renderer
or requiring a TV. It does not validate the real LG compositor.
"""
import argparse
import os
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]

PREFIX = r'''
#include "core/app.h"
#include "core/keys.h"
#include "core/hit.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
Scr SCR = SCR_HOME;
static double NOW;
TopNav topNav = { .want = -1 };
static int visible, visibilityCalls, playing = 1;
void plat_cursor_visible(int show) { visible = show; visibilityCalls++; }
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
int main(void) {
  visible = 1; NOW = 10; app_pointer_system(1); assert(visible && PTR.on);
  NOW = 12.99; ptr_frame(); assert(visible);
  NOW = 13; ptr_frame(); assert(!visible && !PTR.on);
  int calls = visibilityCalls; NOW = 20; ptr_frame(); assert(visibilityCalls == calls);
  puts("PASS idle cursor hides even without hover/motion events, including playback");

  NOW = 21; app_pointer_move(100, 100); assert(visible);
  NOW = 23; app_pointer_move(101, 100);
  NOW = 24.1; ptr_frame(); assert(visible);
  NOW = 26; ptr_frame(); assert(!visible);
  puts("PASS real movement restores cursor and renews idle deadline");

  NOW = 30; app_pointer_move(110, 100); assert(visible);
  app_key(K_LEFT, 1, 0); assert(!visible && PTR.arrowHid);
  app_key(K_LEFT, 0, 0); app_pointer_system(1); assert(!visible);
  NOW = 30.1; app_pointer_move(111, 100); assert(!visible);
  NOW = 30.4; app_pointer_move(112, 100); assert(!visible);
  NOW = 30.5; app_pointer_move(150, 100); assert(visible);
  puts("PASS arrows hide compositor cursor; delayed system-show and tremor stay suppressed");

  NOW = 40; app_pointer_button(1, 150, 100); assert(visible && PTR.down);
  NOW = 45; ptr_frame(); assert(visible);
  app_pointer_button(0, 150, 100); assert(!PTR.down);
  NOW = 47.99; ptr_frame(); assert(visible);
  NOW = 48; ptr_frame(); assert(!visible);
  puts("PASS held click stays visible; release gets a fresh idle period");

  NOW = 50; app_pointer_system(1); assert(visible);
  NOW = 52; app_pointer_system(1);
  NOW = 53; ptr_frame(); assert(!visible);
  puts("PASS repeated system-show notices do not prevent idle hiding");

  NOW = 60; app_pointer_move(200, 100); assert(visible);
  app_pointer_system(0); assert(!visible);
  NOW = 61; app_pointer_move(201, 100); assert(visible);
  NOW = 63; app_pointer_wheel(0, -1);
  NOW = 64.1; ptr_frame(); assert(visible);
  NOW = 66; ptr_frame(); assert(!visible);
  puts("PASS system hide, movement restore, and wheel activity");
  playing = 0; NOW = 70; app_pointer_move(220, 100); assert(visible);
  NOW = 73; ptr_frame(); assert(!visible);
  puts("PASS idle cursor also hides outside the player");
  puts("7 pointer behavior scenarios passed");
  return 0;
}
'''

NATIVE_PREFIX = r'''
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
typedef enum { SDL_FALSE, SDL_TRUE } SDL_bool;
enum { SDL_DISABLE = 0, SDL_ENABLE = 1 };
static int mode, lookups, nativeCalls, fallbackCalls, lastNative, lastFallback;
static SDL_bool native_visibility(SDL_bool visible) {
  nativeCalls++; lastNative = visible; return mode == 2 ? SDL_FALSE : SDL_TRUE;
}
void *dlsym(void *handle, const char *name) {
  (void)handle; assert(!strcmp(name, "SDL_webOSCursorVisibility"));
  lookups++; return mode == 1 ? NULL : (void *)native_visibility;
}
int SDL_ShowCursor(int visible) { fallbackCalls++; lastFallback = visible; return visible; }
'''

NATIVE_TESTS = r'''
int main(int argc, char **argv) {
  assert(argc == 2); mode = argv[1][0] - '0';
  plat_cursor_visible(1); plat_cursor_visible(0);
  assert(lookups == 1);
  assert(nativeCalls == (mode == 1 ? 0 : 2));
  assert(fallbackCalls == (mode ? 2 : 0));
  if (nativeCalls) assert(lastNative == SDL_FALSE);
  if (fallbackCalls) assert(lastFallback == SDL_DISABLE);
  printf("PASS native visibility mode %d: native API / unavailable or refused API fallback\n", mode);
  return 0;
}
'''


def function(source, name):
    start = source.index("void " + name + "(")
    brace = source.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-source", type=pathlib.Path, default=ROOT / "src/core/app.c")
    args = parser.parse_args()
    source = args.app_source.read_text()
    start = source.index("/* ---- the Magic Remote pointer.")
    end = source.index("/* where the focus is,", start)
    native = function((ROOT / "src/platform/webos/plat_webos.c").read_text(), "plat_cursor_visible")
    with tempfile.TemporaryDirectory(prefix="stremio-pointer-") as tmp:
        tmp = pathlib.Path(tmp)
        for name, body in [
            ("pointer", PREFIX + source[start:end] + TESTS),
            ("native", NATIVE_PREFIX + native + NATIVE_TESTS),
        ]:
            c = tmp / (name + ".c")
            c.write_text(body)
            subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-DSB_WEBOS", "-O1",
                            "-Wall", "-Wextra", "-Wno-unused-function", "-Wno-misleading-indentation",
                            "-I", str(ROOT / "src"), "-I", str(ROOT / "third_party/cjson"),
                            str(c), "-lm", "-o", str(tmp / name)], check=True)
        subprocess.run([str(tmp / "pointer")], check=True)
        for mode in range(3):
            subprocess.run([str(tmp / "native"), str(mode)], check=True)
        print("10 cursor scenarios passed (UI/native stubs; TV verification still required)")


if __name__ == "__main__":
    main()
