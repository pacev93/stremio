"""Helpers for compiling selected production C functions in focused harnesses."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def function(source, name):
    match = re.search(r'(?m)^(?:static\s+)?[A-Za-z_][\w \t*]*\b' + re.escape(name) +
                      r'\([^;{}]*\)\s*\{', source)
    if not match:
        raise ValueError('Function definition missing: ' + name)
    depth, state, at = 1, 'code', match.end()
    while at < len(source):
        c = source[at]
        pair = source[at:at + 2]
        if state == 'code':
            if pair in ('/*', '//'):
                state = pair
                at += 2
                continue
            if c in ('"', "'"):
                state = c
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if not depth:
                    return source[match.start():at + 1]
        elif state in ('"', "'"):
            if c == '\\':
                at += 2
                continue
            if c == state:
                state = 'code'
        elif state == '/*' and pair == '*/':
            state = 'code'
            at += 2
            continue
        elif state == '//' and c == '\n':
            state = 'code'
        at += 1
    raise ValueError('Unclosed function: ' + name)


def sdl_include(tmp, sdk_include):
    if not sdk_include:
        return []
    # Use just SDL headers, never the ARM SDK's libc headers in a host build.
    folder = pathlib.Path(tmp) / 'headers'
    folder.mkdir()
    (folder / 'SDL2').symlink_to(pathlib.Path(sdk_include) / 'SDL2', target_is_directory=True)
    return ['-I', str(folder)]
