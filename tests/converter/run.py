#!/usr/bin/env python3
"""Controlled concurrent requests through production conv_serve and seek signalling.

Only the muxer and socket writes are fixtures. Tests real locking, admission,
completion framing and obsolete-work rejection; does not emulate LG decoding.
"""
import argparse
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cutil import ROOT, sdl_include

HARNESS = r'''
#include <pthread.h>
static int watch_lock(pthread_mutex_t *);
#define pthread_mutex_lock watch_lock
#define send fixture_send
#include "CONVERTER_SOURCE"
#undef send
#undef pthread_mutex_lock
#include <assert.h>
static pthread_mutex_t fx=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cv=PTHREAD_COND_INITIALIZER;
static pthread_mutex_t *runLock;
static _Thread_local int requestId;
static int queued[8],entered[8],released[8],ended[8],terminal[8],headers[8],headerRelease[8];
static int calls[8],active,peak,closed,failFd,blockHeader;
static int watch_lock(pthread_mutex_t *p) {
  if(p==runLock) {
    pthread_mutex_lock(&fx);queued[requestId]=1;pthread_cond_broadcast(&cv);pthread_mutex_unlock(&fx);
  }
  return pthread_mutex_lock(p);
}
ssize_t fixture_send(int fd,const void *p,size_t n,int flags) {
  (void)flags;int id=fd-100;assert(id>0 && id<8);
  pthread_mutex_lock(&fx);
  if(n>=5 && !memcmp(p,"HTTP/",5)) {
    headers[id]++;pthread_cond_broadcast(&cv);
    while(blockHeader==id && !headerRelease[id])pthread_cond_wait(&cv,&fx);
  }
  if(n==5 && !memcmp(p,"0\r\n\r\n",5))terminal[id]++;
  int fail=failFd==id;pthread_mutex_unlock(&fx);return fail?-1:(ssize_t)n;
}
void net_range_free(NetRange *r) {(void)r;}
static void close_src(SbdSrc *s) {(void)s;closed++;}
static int run(SbdSrc *s,int seg,double t,sbd_write w,void *ud,volatile int *stop,sbd_stats *st,char *err,int cap) {
  (void)s;(void)seg;(void)t;(void)st;(void)err;(void)cap;
  int id=requestId;pthread_mutex_lock(&fx);calls[id]++;entered[id]=1;
  active++;if(active>peak)peak=active;pthread_cond_broadcast(&cv);
  while(!released[id])pthread_cond_wait(&cv,&fx);
  int aborted=*stop;active--;pthread_mutex_unlock(&fx);
  if(aborted)return -2;
  static const unsigned char b[]={1,2,3};return w(ud,b,sizeof b)==sizeof b?0:-1;
}
static double seg_start(SbdSrc *s,int n) {(void)s;return 2*n;}
static double seg_dur(SbdSrc *s,int n) {(void)s;(void)n;return 2;}
typedef struct { int id,head;char path[80];pthread_t thread; } Req;
static void *serve_request(void *p) {
  Req *r=p;requestId=r->id;conv_serve(100+r->id,9,r->path,r->head);
  pthread_mutex_lock(&fx);ended[r->id]=1;pthread_cond_broadcast(&cv);pthread_mutex_unlock(&fx);return NULL;
}
static Req requests[8];
static void start_request(int id,int seg) {
  Req *r=&requests[id];r->id=id;
  if(seg>=0)snprintf(r->path,sizeof r->path,"/h/9/%d.ts",seg);
  else snprintf(r->path,sizeof r->path,"/h/9/all.ts?t=%d",id*20);
  assert(!pthread_create(&r->thread,NULL,serve_request,r));
}
static void wait_for(int *state,int id) {
  pthread_mutex_lock(&fx);while(!state[id])pthread_cond_wait(&cv,&fx);pthread_mutex_unlock(&fx);
}
static void release(int id) {
  pthread_mutex_lock(&fx);released[id]=headerRelease[id]=1;pthread_cond_broadcast(&cv);pthread_mutex_unlock(&fx);
}
static void join(int id) {assert(!pthread_join(requests[id].thread,NULL));}
static void seek(void) {hls_conv_seek("http://127.0.0.1:123/h/9/index.m3u8");}
static void no_stop(Conv *c) {pthread_mutex_lock(&mu);assert(!c->stop);pthread_mutex_unlock(&mu);}
int main(int argc,char **argv) {
  assert(argc==2);port=123;
  static const sbd_api api={.run=run,.close=close_src,.seg_start=seg_start,.seg_dur=seg_dur};D=&api;
  Conv *c=calloc(1,sizeof *c);assert(c);c->id=9;c->state=1;c->refs=1;c->running=-100;
  c->src=(SbdSrc *)1;c->info.indexed=strncmp(argv[1],"continuous",10)!=0;c->info.nseg=100;
  pthread_mutex_init(&c->runMu,NULL);runLock=&c->runMu;conv=c;
  start_request(1,c->info.indexed?5:-1);wait_for(entered,1);
  if(!strcmp(argv[1],"ahead-two") || !strcmp(argv[1],"duplicate") || !strcmp(argv[1],"backward-request")) {
    int seg=!strcmp(argv[1],"duplicate")?5:!strcmp(argv[1],"backward-request")?3:6;
    start_request(2,seg);wait_for(queued,2);
    if(!strcmp(argv[1],"ahead-two")){start_request(3,7);wait_for(queued,3);}
    no_stop(c);release(2);release(3);release(1);join(1);join(2);
    if(!strcmp(argv[1],"ahead-two")){join(3);assert(calls[3]==1 && terminal[3]==1);}
    assert(calls[1]==1 && calls[2]==1 && terminal[1]==1 && terminal[2]==1);
  } else if(!strcmp(argv[1],"seek") || !strcmp(argv[1],"seek-again")) {
    start_request(2,6);wait_for(queued,2);seek();
    start_request(3,50);wait_for(queued,3);
    int last=3;
    if(!strcmp(argv[1],"seek-again")){seek();start_request(4,10);wait_for(queued,4);last=4;}
    release(1);release(3);release(4);join(1);join(2);join(3);if(last==4)join(4);
    assert(!terminal[1] && !calls[2] && !terminal[2]);
    if(last==4)assert(!calls[3] && !terminal[3]);
    assert(calls[last]==1 && terminal[last]==1);
  } else if(!strcmp(argv[1],"stop")) {
    start_request(2,6);wait_for(queued,2);hls_conv_stop();release(1);join(1);join(2);
    assert(!terminal[1] && !calls[2] && closed==1);c=NULL;
  } else if(!strcmp(argv[1],"head") || !strcmp(argv[1],"playlist")) {
    Req r={.id=2,.head=!strcmp(argv[1],"head")};
    snprintf(r.path,sizeof r.path,"/h/9/%s",r.head?"7.ts":"index.m3u8");serve_request(&r);
    no_stop(c);release(1);join(1);assert(!calls[2] && headers[2]==1 && terminal[1]==1);
  } else if(!strcmp(argv[1],"wrong-url")) {
    hls_conv_seek(NULL);hls_conv_seek("https://source/film.mkv");
    hls_conv_seek("http://127.0.0.1:123/h/8/index.m3u8");
    hls_conv_seek("http://127.0.0.1:123/h/9/all.ts");
    no_stop(c);release(1);join(1);assert(terminal[1]==1);
  } else if(!strcmp(argv[1],"continuous") || !strcmp(argv[1],"continuous-header")) {
    int slow=!strcmp(argv[1],"continuous-header");if(slow)blockHeader=2;
    start_request(2,-1);wait_for(slow?headers:queued,2);start_request(3,-1);wait_for(queued,3);
    if(slow){release(2);wait_for(queued,2);}
    release(1);release(3);join(1);join(2);join(3);
    assert(!terminal[1] && !calls[2] && !terminal[2] && calls[3]==1 && terminal[3]==1);
  } else if(!strcmp(argv[1],"header-failure")) {
    failFd=2;start_request(2,7);join(2);no_stop(c);release(1);join(1);
    assert(!calls[2] && terminal[1]==1);
  } else if(!strcmp(argv[1],"seek-during-header")) {
    blockHeader=2;start_request(2,6);wait_for(headers,2);seek();release(2);
    wait_for(queued,2);start_request(3,50);wait_for(queued,3);
    release(1);release(3);join(1);join(2);join(3);
    assert(!terminal[1] && !calls[2] && !terminal[2] && calls[3]==1 && terminal[3]==1);
  } else assert(!"unknown scenario");
  assert(peak==1 && !active);if(c)hls_conv_stop();assert(closed==1);
  printf("PASS converter scheduling %s\n",argv[1]);return 0;
}
'''


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdl-include', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='stremio-converter-') as folder:
        tmp = Path(folder)
        includes = sdl_include(tmp, args.sdl_include)
        old = tmp/'old-converter.c'
        old.write_bytes(subprocess.check_output(['git','show',
            '0a35b99c20537ed88b53cf5cebc47ddc0a4bc8eb:src/core/hproxy.c'],cwd=ROOT))
        bins = []
        for name, source in [('current',ROOT/'src/core/hproxy.c'),('old',old)]:
            c, exe = tmp/(name+'.c'), tmp/name
            code = HARNESS.replace('CONVERTER_SOURCE',str(source))
            if name == 'old':
                code += '\nvoid hls_conv_seek(const char *u) { (void)u; }\n'
            c.write_text(code)
            subprocess.run([os.environ.get('CC','cc'),'-std=c11','-D_GNU_SOURCE',
                '-O1','-g','-ffunction-sections','-fdata-sections',*includes,
                '-I',str(ROOT/'src'),str(c),'-Wl,--gc-sections','-pthread','-ldl',
                '-lm','-o',str(exe)],check=True)
            bins.append(exe)
        cases = ('ahead-two','duplicate','backward-request','seek','seek-again',
                 'stop','head','playlist','wrong-url','continuous','header-failure',
                 'seek-during-header','continuous-header')
        before = subprocess.run([str(bins[1]),'ahead-two'],capture_output=True,
            text=True,timeout=10,preexec_fn=no_core)
        assert before.returncode != 0 and 'c->stop' in before.stderr, before.stderr
        print('PASS regression reproduced on 1.0.15: second-ahead request stops active output')
        for case in cases:
            result = subprocess.run([str(bins[0]),case],capture_output=True,
                text=True,timeout=10,preexec_fn=no_core)
            assert result.returncode == 0, result.stdout+result.stderr
            print(result.stdout,end='')
        print(f'{len(cases)} concurrent converter scenarios passed; real TV request pattern not captured')


if __name__ == '__main__':
    main()
