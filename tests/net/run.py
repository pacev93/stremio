#!/usr/bin/env python3
"""Compile the actual range reader and test HTTP framing and connection reuse.

Requires a host C compiler, libcurl headers/runtime, and SDL2 headers (system or
SDK/usr/include passed as --sdl-include). No media, accounts, or external network.
"""
import argparse
import collections
import http.server
import json
import os
import pathlib
import subprocess
import tempfile
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = bytes(i % 251 for i in range(65536))
CONNECTIONS = collections.defaultdict(set)


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_GET(self):
        CONNECTIONS[self.path].add(self.client_address)
        start, end = map(int, self.headers["Range"][6:].split("-"))
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/range")
            body = b"redirect body"
        elif self.path in ("/busy", "/missing"):
            self.send_response(429 if self.path == "/busy" else 404)
            body = b""
        elif self.path == "/no-range":
            self.send_response(200)
            body = DATA
        else:
            if self.path == "/oversized":
                end += 32
            end = min(end, len(DATA) - 1)
            if self.path == "/wrong-range":
                start += 1
                end += 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(DATA)}")
            body = DATA[start:end + 1]
        if self.path == "/chunked":
            self.send_header("Transfer-Encoding", "chunked")
        else:
            self.send_header("Content-Length", str(len(body)))
        if self.path == "/short":
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        try:
            if self.path == "/timeout":
                time.sleep(0.8)
            if self.path == "/short":
                self.wfile.write(body[:len(body) // 2])
            elif self.path == "/chunked":
                for at in range(0, len(body), 257):
                    chunk = body[at:at + 257]
                    self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                self.wfile.write(b"0\r\n\r\n")
            else:
                self.wfile.write(body)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdl-include", type=pathlib.Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="stremio-range-") as tmp:
        tmp = pathlib.Path(tmp)
        includes = []
        if args.sdl_include:
            # Only SDL headers: never mix the ARM SDK's libc with host headers.
            (tmp / "SDL2").symlink_to(args.sdl_include / "SDL2", target_is_directory=True)
            includes = ["-I", str(tmp)]
        binary = tmp / "range_test"
        subprocess.run([
            os.environ.get("CC", "cc"), "-std=c11", "-D_GNU_SOURCE", "-O1", "-g",
            "-ffunction-sections", "-fdata-sections", *includes,
            "-I", str(ROOT / "src"), "-I", str(ROOT / "third_party/cjson"),
            str(ROOT / "tests/net/range_test.c"), str(ROOT / "src/core/net.c"),
            "-Wl,--gc-sections", "-ldl", "-lpthread", "-o", str(binary),
        ], check=True)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        checks = 0

        def run(path, start=0, length=4096, count=1):
            nonlocal checks
            result = subprocess.run([
                str(binary), f"http://127.0.0.1:{server.server_port}{path}",
                str(start), str(length), str(count),
            ], check=True, capture_output=True, text=True)
            rows = [json.loads(line) for line in result.stdout.splitlines()]
            assert len(rows) == count, result.stdout
            assert all(row["valid"] and row["got"] <= length for row in rows), rows
            checks += 1
            return rows

        try:
            for path in ("/range", "/chunked"):
                rows = run(path, count=4)
                assert all(r == dict(result=0, status=206, got=4096, total=65536, valid=1) for r in rows), rows
                assert len(CONNECTIONS[path]) == 1, f"{path}: {len(CONNECTIONS[path])} connections for 4 complete ranges (expected 1)"
                print(f"PASS {path}: 4 byte-exact ranges, 1 HTTP connection")
            rows = run("/redirect", count=3)
            assert all(r["result"] == 0 and r["status"] == 206 and r["got"] == 4096 for r in rows), rows
            assert len(CONNECTIONS["/redirect"]) == 1, CONNECTIONS["/redirect"]
            assert len(CONNECTIONS["/range"]) == 2, CONNECTIONS["/range"]
            print("PASS redirects: body ignored, complete ranges reuse connection")
            r, = run("/range", start=65000)
            assert (r["result"], r["got"]) == (0, 536), r
            print("PASS EOF: shorter final range")
            r, = run("/no-range")
            assert (r["result"], r["status"], r["got"]) == (0, 200, 4096), r
            r, = run("/no-range", start=4096)
            assert (r["result"], r["got"]) == (1, 0), r
            print("PASS ignored ranges: bounded first read, nonzero offset rejected")
            r, = run("/wrong-range", start=4096)
            assert (r["result"], r["got"]) == (1, 0), r
            print("PASS mismatched Content-Range rejected")
            r, = run("/short", start=4096)
            assert (r["result"], r["got"]) == (0, 2048), r
            print("PASS interrupted response: partial bytes preserved")
            r, = run("/oversized", start=4096)
            assert (r["result"], r["got"]) == (0, 4096), r
            print("PASS oversized response: requested buffer limit preserved")
            for path, error in (("/busy", 3), ("/missing", 2), ("/timeout", 4)):
                r, = run(path)
                assert (r["result"], r["got"]) == (error, 0), r
                print(f"PASS {path}: existing error result preserved")
            print(f"{checks} scenarios passed")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
