#!/usr/bin/env python3
"""Verify real TCP reuse, request isolation and concurrent playback/metadata through production HTTP code.

Local deterministic HTTP only; no media decoding, accounts or TV emulation.
"""
import argparse
import collections
import http.server
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cutil import ROOT, sdl_include

DATA = bytes(i % 251 for i in range(65536))
CONNECTIONS = collections.defaultdict(set)
REQUESTS = collections.defaultdict(list)
LOCK = threading.Lock()
PARALLEL = threading.Barrier(2, timeout=4)
ACTIVE = collections.Counter()
PEAK = collections.Counter()
BYPASS_WHILE_BUSY = False


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        global BYPASS_WHILE_BUSY
        tag = self.headers.get('X-Test', '')
        with LOCK:
            CONNECTIONS[tag].add(self.client_address)
            REQUESTS[tag].append((self.command, self.headers.get('Authorization'), self.headers.get('Range')))
            number = len(REQUESTS[tag])
            if tag == 'busy-no-block' and self.path == '/file':
                BYPASS_WHILE_BUSY = ACTIVE[tag] == 4
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/file')
            payload = b'redirect body'
        else:
            rg = self.headers.get('Range')
            start, end = map(int, rg[6:].split('-')) if rg else (0, len(DATA)-1)
            payload = DATA[start:end+1]
            self.send_response(206 if rg else 200)
            if rg:
                self.send_header('Content-Range', f'bytes {start}-{end}/{len(DATA)}')
        if self.path == '/chunked':
            self.send_header('Transfer-Encoding', 'chunked')
        else:
            self.send_header('Content-Length', str(len(payload)))
        self.send_header('Content-Type', 'application/octet-stream')
        self.end_headers()
        if self.command == 'HEAD':
            return
        try:
            if self.path == '/parallel':
                PARALLEL.wait()
            if self.path in ('/capacity', '/wait'):
                self.wfile.flush()
                with LOCK:
                    ACTIVE[tag] += 1
                    PEAK[tag] = max(PEAK[tag], ACTIVE[tag])
                time.sleep(1 if self.path == '/wait' else 0.2)
            if self.path == '/partial' and number == 1:
                self.wfile.write(payload[:len(payload)//2])
                self.wfile.flush()
                self.close_connection = True
            elif self.path == '/chunked':
                for at in range(0, len(payload), 257):
                    chunk = payload[at:at+257]
                    self.wfile.write(f'{len(chunk):x}\r\n'.encode()+chunk+b'\r\n')
                self.wfile.write(b'0\r\n\r\n')
                self.wfile.flush()
            else:
                self.wfile.write(payload)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            if self.path in ('/capacity', '/wait'):
                with LOCK:
                    ACTIVE[tag] -= 1

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdl-include', type=Path)
    args = parser.parse_args()
    cases = ('ranges', 'chunked', 'redirect', 'head-get', 'headers', 'cancel', 'partial', 'parallel', 'capacity', 'busy-no-block', 'bridge')
    with tempfile.TemporaryDirectory(prefix='stremio-pipe-') as folder:
        tmp = Path(folder)
        exe = tmp/'pipe_test'
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-D_GNU_SOURCE', '-O1', '-g',
                        '-ffunction-sections', '-fdata-sections', *sdl_include(tmp, args.sdl_include),
                        '-I', str(ROOT/'src'), '-I', str(ROOT/'third_party/cjson'),
                        str(ROOT/'tests/net/pipe_test.c'), str(ROOT/'src/core/net.c'), str(ROOT/'src/core/hproxy.c'),
                        '-Wl,--gc-sections', '-l:libSDL2-2.0.so.0', '-ldl', '-pthread', '-lm', '-o', str(exe)], check=True)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            for case in cases:
                result = subprocess.run([str(exe), f'http://127.0.0.1:{server.server_port}', case],
                                        capture_output=True, text=True, timeout=15)
                if result.returncode:
                    sys.stderr.write(result.stdout+result.stderr)
                    result.check_returncode()
                if case in ('ranges', 'chunked', 'redirect', 'head-get', 'bridge'):
                    assert len(CONNECTIONS[case]) == 1, (case, CONNECTIONS[case])
                if case in ('cancel', 'partial', 'parallel'):
                    assert len(CONNECTIONS[case]) == 2, (case, CONNECTIONS[case])
                if case == 'headers':
                    assert [r[1] for r in REQUESTS[case]] == ['fake-a', 'fake-b', 'fake-a', None]
                    assert REQUESTS[case][-1][2] is None
                    assert len(CONNECTIONS[case]) == 3
                if case == 'head-get':
                    assert [r[0] for r in REQUESTS[case]] == ['HEAD', 'GET']
                if case == 'capacity':
                    assert len(REQUESTS[case]) == 5 and PEAK[case] == 5
                    assert len(CONNECTIONS[case]) == 5
                if case == 'busy-no-block':
                    assert len(REQUESTS[case]) == 5 and BYPASS_WHILE_BUSY
                print(result.stdout.strip())
        finally:
            server.shutdown()
            server.server_close()
    print(f'{len(cases)} real-HTTP pipe scenarios passed; bridge reuses upstream despite local Connection: close')


if __name__ == '__main__':
    main()
