#!/usr/bin/env python3
"""Exercise the production converter reader with real HTTP and byte-exact seeks.

Compares the sequential request count to the pre-1.0.15 reader. No TV decoding.
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

MIB = 1 << 20
DATA = (bytes(range(251)) * ((48*MIB)//251+1))[:48*MIB]
REQUESTS = collections.defaultdict(list)
CONNECTIONS = collections.defaultdict(set)


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass

    def do_GET(self):
        start, end = map(int, self.headers['Range'][6:].split('-'))
        REQUESTS[self.path].append((start, end))
        CONNECTIONS[self.path].add(self.client_address)
        if self.path == '/retry' and len(REQUESTS[self.path]) < 3:
            self.send_response(503)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        if self.path == '/error':
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        size = 3*MIB+19 if self.path == '/eof' else len(DATA)
        end = min(end, size-1)
        self.send_response(206)
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end-start+1))
        if self.path == '/partial':
            self.send_header('Connection', 'close')
            self.close_connection = True
        self.end_headers()
        if self.path == '/stop-during':
            time.sleep(0.15)
        if self.path == '/partial':
            end = min(end, start+(128 << 10)-1)
        try:
            self.wfile.write(DATA[start:end+1])
        except (BrokenPipeError, ConnectionResetError):
            pass


HARNESS = r'''
#include "READER_SOURCE"
#include <assert.h>
void plat_thread_background(int n) { (void)n; }
static void check(Reader *r,long long pos,int n) {
  unsigned char b[32768];assert(n<=(int)sizeof b);
  int got=rd_read(r,pos,b,n);assert(got>0 && got<=n);
  for(int i=0;i<got;i++)assert(b[i]==(unsigned char)((pos+i)%251));
}
static void warm(Reader *r,long long end) {
  unsigned char b[32768];long long pos=0;
  while(pos<end) {
    int n=(int)(end-pos);if(n>(int)sizeof b)n=sizeof b;
    int got=rd_read(r,pos,b,n);assert(got>0 && got<=n);
    for(int i=0;i<got;i++)assert(b[i]==(unsigned char)((pos+i)%251));
    pos+=got;
  }
}
static void *stop_later(void *p) { usleep(30000);*(volatile int *)p=1;return NULL; }
int main(int argc,char **argv) {
  assert(argc==3);Reader r={0};volatile int stop=0;
  r.stop=&stop;r.net=net_range_new();r.ring=malloc(RING);r.size=-1;
  assert(r.net && r.ring);snprintf(r.url,sizeof r.url,"%s/%s",argv[1],argv[2]);
  unsigned char b[16];
  if(!strcmp(argv[2],"bridge")) {
    char local[4096];assert(hproxy_url(r.url,"X-Reader-Test: bridge\n","",local,sizeof local));
    snprintf(r.url,sizeof r.url,"%s",local);warm(&r,32LL<<20);
  } else if(!strcmp(argv[2],"steady") || !strcmp(argv[2],"baseline")) warm(&r,32LL<<20);
  else if(!strcmp(argv[2],"seek")) {
    warm(&r,10LL<<20);check(&r,40LL<<20,16);check(&r,r.start+r.len,16);
  } else if(!strcmp(argv[2],"backward")) {
    warm(&r,10LL<<20);check(&r,r.start+4096,16);check(&r,0,16);
  } else if(!strcmp(argv[2],"wrap")) {
    warm(&r,6LL<<20);check(&r,(8LL<<20)-100,500);
  } else if(!strcmp(argv[2],"forward") || !strcmp(argv[2],"partial")) {
    check(&r,0,16);check(&r,r.start+r.len+(768<<10),16);
  } else if(!strcmp(argv[2],"eof")) {
    warm(&r,(3LL<<20)+19);assert(!rd_read(&r,(3LL<<20)+19,b,sizeof b));
  } else if(!strcmp(argv[2],"stop-before")) {
    check(&r,0,16);stop=1;assert(rd_read(&r,0,b,sizeof b)==-1);
    assert(rd_read(&r,10LL<<20,b,sizeof b)==-1);
  } else if(!strcmp(argv[2],"stop-during")) {
    pthread_t t;assert(!pthread_create(&t,NULL,stop_later,(void *)&stop));
    assert(rd_read(&r,0,b,sizeof b)==-1);pthread_join(t,NULL);assert(!r.len);
  } else if(!strcmp(argv[2],"retry")) check(&r,0,16);
  else if(!strcmp(argv[2],"error")) assert(rd_read(&r,0,b,sizeof b)==-1);
  else assert(!"unknown scenario");
  free(r.ring);net_range_free(r.net);
  printf("PASS converter reader %s\n",argv[2]);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdl-include', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='stremio-reader-') as folder:
        tmp = Path(folder)
        includes = sdl_include(tmp, args.sdl_include)
        old = tmp/'old-reader.c'
        old.write_bytes(subprocess.check_output(['git', 'show',
            'f43c152b7ce732fa34d08bb82b50d520bc81e8c6:src/core/hproxy.c'], cwd=ROOT))
        binaries = []
        for name, reader in [('current', ROOT/'src/core/hproxy.c'), ('old', old)]:
            c, exe = tmp/(name+'.c'), tmp/name
            c.write_text(HARNESS.replace('READER_SOURCE', str(reader)))
            subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-D_GNU_SOURCE',
                '-O1', '-g', '-ffunction-sections', '-fdata-sections',
                *includes, '-I', str(ROOT/'src'), '-I', str(ROOT/'third_party/cjson'),
                str(c), str(ROOT/'src/core/net.c'),
                '-Wl,--gc-sections', '-Wl,-l:libSDL2-2.0.so.0', '-pthread', '-ldl',
                '-lm', '-o', str(exe)], check=True)
            binaries.append(exe)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        cases = ('steady','bridge','seek','backward','wrap','forward','partial','eof',
                 'stop-before','stop-during','retry','error')
        try:
            for case in cases:
                subprocess.run([str(binaries[0]), url, case], check=True, timeout=12)
            subprocess.run([str(binaries[1]), url, 'baseline'], check=True, timeout=12)
        finally:
            server.shutdown(); server.server_close(); thread.join()
        current, baseline = REQUESTS['/steady'], REQUESTS['/baseline']
        assert len(current) == 11 and len(baseline) == 19
        assert len(CONNECTIONS['/steady']) == len(CONNECTIONS['/baseline']) == 1
        assert REQUESTS['/bridge'] == current and len(CONNECTIONS['/bridge']) == 1
        assert all(b-a+1 == 512 << 10 for a,b in current[:3])
        assert all(b-a+1 == 4*MIB for a,b in current[3:])
        for path in ('/seek','/backward'):
            a,b = REQUESTS[path][-1]
            assert b-a+1 == 512 << 10
        assert len(REQUESTS['/wrap']) == 5
        assert len(REQUESTS['/forward']) == 3
        assert len(REQUESTS['/stop-before']) == len(REQUESTS['/stop-during']) == 1
        assert len(REQUESTS['/retry']) == 3 and len(REQUESTS['/error']) == 1
        assert REQUESTS['/eof'][-1][1] == 3*MIB+18
        print('PASS comparison: 32 MiB byte-exact playback, 19 -> 11 requests, one TCP connection each')
        print(f'{len(cases)} real-HTTP reader scenarios plus baseline comparison passed; TV playback not emulated')


if __name__ == '__main__':
    main()
