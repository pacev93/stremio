#!/usr/bin/env python3
"""Exercise subtitle demand/cancellation and real hash computation without source-network reads.

Production decision/hash functions are compiled; HTTP is replaced with counted deterministic ranges.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cutil import ROOT, function

DEMAND = r'''
#include "core/subs.h"
#include "core/mkvsubs.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static struct {
 int open,autoSubDone,subListsWanted,nExt,nAdx,extLoading,adxLoading,extTry,adxTry,nSubAddons,ncues,castSubList;
 unsigned subReq,adxReq;double extRetryAt,adxRetryAt;
 Cue *cues;SubEntry *ext,*adx;char curSub[1100];
} P;
static MkvSession *mkv;
static struct { int wait; } SL;
static const char *preference="";
static SubEntry castSubs[16];static int castSubsN=-1;
static int searches,addonSearches,autoCalls,refreshes;
static const char *want_sub(void) { return preference; }
static double now_(void) { return 100; }
static void sync_stop(int n) { (void)n; }
void subs_free(Cue *c,int n) { (void)n;free(c); }
void video_select_text(int n) { assert(n==-1); }
void mkv_select(MkvSession *s,int n) { (void)s;assert(n==-1); }
static void sub_begin(void) {}
static void refresh_tray(int n) { assert(n==4);refreshes++; }
static void auto_sub(void) { autoCalls++; }
static void load_ext_subs(int n) { assert(!n);searches++;P.subReq++;P.extLoading=1; }
static void load_addon_subs(int n) { assert(!n);addonSearches++;P.adxReq++;P.adxLoading=1; }
'''

DEMAND_TEST = r'''
int main(int argc,char **argv) {
 assert(argc==2);P.open=1;P.nSubAddons=1;snprintf(P.curSub,sizeof P.curSub,"off");
 if(!strcmp(argv[1],"default-off")) {
   for(int i=0;i<100;i++)request_sub_lists(0);
   assert(!searches && !addonSearches && !P.subListsWanted);
 } else if(!strcmp(argv[1],"cast-off-metadata")) {
   castSubsN=1;strcpy(castSubs[0].url,"http://fixture/caption");take_cast_subs();request_sub_lists(0);
   assert(castSubsN==-1 && P.castSubList && P.nExt==1 && !strcmp(P.ext[0].url,castSubs[0].url));
   assert(!searches && !addonSearches);
 } else if(!strcmp(argv[1],"cast-does-not-leak")) {
   castSubsN=1;take_cast_subs();free(P.ext);memset(&P,0,sizeof P);take_cast_subs();
   assert(castSubsN==-1 && !P.castSubList && !P.ext && !P.nExt);
 } else if(!strcmp(argv[1],"default-language")) {
   preference="eng";request_sub_lists(0);request_sub_lists(0);
   assert(searches==1 && addonSearches==1 && P.subListsWanted);
 } else if(!strcmp(argv[1],"explicit-open")) {
   request_sub_lists(1);request_sub_lists(1);
   assert(searches==1 && addonSearches==1);
   on_subs(calloc(1,sizeof(SubEntry)),1,1,(void *)(uintptr_t)P.subReq);
   on_adx(calloc(1,sizeof(SubEntry)),1,1,1,(void *)(uintptr_t)P.adxReq);
   assert(P.nExt==1 && P.nAdx==1 && !P.extLoading && !P.adxLoading);
 } else if(!strcmp(argv[1],"off-cancels")) {
   preference="eng";request_sub_lists(0);unsigned ext=P.subReq,adx=P.adxReq;
   P.extRetryAt=P.adxRetryAt=115;subs_off();
   assert(P.autoSubDone && !P.subListsWanted && !P.extRetryAt && !P.adxRetryAt);
   assert(!P.extLoading && !P.adxLoading);
   on_subs(calloc(1,sizeof(SubEntry)),1,0,(void *)(uintptr_t)ext);
   on_adx(calloc(1,sizeof(SubEntry)),1,1,0,(void *)(uintptr_t)adx);
   assert(!autoCalls && !P.extRetryAt && !P.adxRetryAt && !P.nExt && !P.nAdx);
 } else if(!strcmp(argv[1],"off-reopen")) {
   request_sub_lists(1);unsigned old=P.subReq;subs_off();request_sub_lists(1);
   assert(searches==2 && addonSearches==2 && P.subListsWanted && P.subReq!=old);
   on_subs(calloc(1,sizeof(SubEntry)),1,1,(void *)(uintptr_t)P.subReq);
   assert(P.nExt==1 && P.autoSubDone);
 } else if(!strcmp(argv[1],"wanted-retries")) {
   preference="eng";request_sub_lists(0);
   on_subs(NULL,0,0,(void *)(uintptr_t)P.subReq);
   on_adx(NULL,0,1,0,(void *)(uintptr_t)P.adxReq);
   assert(P.extRetryAt==115 && P.adxRetryAt==115);
 } else if(!strcmp(argv[1],"closed-answer")) {
   request_sub_lists(1);P.open=0;
   on_subs(calloc(1,sizeof(SubEntry)),1,1,(void *)(uintptr_t)P.subReq);
   on_adx(calloc(1,sizeof(SubEntry)),1,1,1,(void *)(uintptr_t)P.adxReq);
   assert(!P.nExt && !P.nAdx && !autoCalls);
 } else assert(!"unknown demand test");
 free(P.ext);free(P.adx);printf("PASS subtitle demand %s\n",argv[1]);return 0;
}
'''

HASH = r'''
#include "core/subs.h"
#include "core/net.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static pthread_mutex_t hmu=PTHREAD_MUTEX_INITIALIZER;
static char hUrl[4096],hHash[24];static double hSize;
static int ranges,fail;
static long long sourceSize=131072;
struct NetRange { int unused; };
NetRange *net_range_new(void) { return calloc(1,sizeof(NetRange)); }
void net_range_free(NetRange *r) { free(r); }
int net_range_get(NetRange *r,const char *url,long long at,long len,unsigned char **out,long *got,long long *total,int *status,int timeout) {
 (void)r;(void)url;(void)timeout;assert(len==65536);ranges++;*out=NULL;*got=0;
 if(fail) { fail=0;return NR_TIMEOUT; }
 *out=malloc(len);for(long i=0;i<len;i++)(*out)[i]=(unsigned char)((at+i)%251);
 *got=len;if(total)*total=sourceSize;if(status)*status=206;return NR_OK;
}
'''

HASH_TEST = r'''
int main(int argc,char **argv) {
 assert(argc==2);SubQuery q;memset(&q,0,sizeof q);strcpy(q.url,"http://fixture/file");q.hashable=1;
 if(!strcmp(argv[1],"provided")) {
   strcpy(q.hash,"provided");find_hash(&q);assert(!ranges && !strcmp(q.hash,"provided"));
 } else if(!strcmp(argv[1],"not-hashable")) {
   q.hashable=0;find_hash(&q);assert(!ranges && !q.hash[0]);
 } else if(!strcmp(argv[1],"retry-cache")) {
   find_hash(&q);assert(ranges==2 && strlen(q.hash)==16 && q.size==sourceSize);
   char original[24];strcpy(original,q.hash);
   for(int i=0;i<4;i++){q.hash[0]=0;find_hash(&q);assert(ranges==2 && !strcmp(q.hash,original));}
 } else if(!strcmp(argv[1],"size-change")) {
   find_hash(&q);sourceSize=262144;q.hash[0]=0;q.size=sourceSize;find_hash(&q);
   assert(ranges==4 && q.size==sourceSize);
 } else if(!strcmp(argv[1],"different-source")) {
   find_hash(&q);q.hash[0]=0;strcpy(q.url,"http://fixture/other");find_hash(&q);assert(ranges==4);
 } else if(!strcmp(argv[1],"cached-no-read")) {
   find_hash(&q);q.hash[0]=0;q.hashable=0;find_hash(&q);assert(ranges==2 && q.hash[0]);
 } else if(!strcmp(argv[1],"failed-not-cached")) {
   fail=1;find_hash(&q);assert(ranges==1 && !q.hash[0]);
   find_hash(&q);assert(ranges==3 && q.hash[0]);
 } else assert(!"unknown hash test");
 printf("PASS subtitle hash %s\n",argv[1]);return 0;
}
'''

CAST = r'''
#include "core/cast.c"
#include <assert.h>
static int polls,demands;
static char *snapshot(int requested) {
  if(requested)demands++;else polls++;
  return strdup("{\"t\":\"tracks\",\"subs\":[],\"audio\":[]}");
}
int main(int argc,char **argv) {
  (void)argc;(void)argv;int pair[2];assert(!socketpair(AF_UNIX,SOCK_STREAM,0,pair));
  for(int i=0;i<MAXC;i++)C[i].fd=-1;
  C[0].fd=pair[0];C[0].auth=1;C[0].out=malloc(OUTCAP);H.tracks=snapshot;
  tracks(100);assert(polls==1 && !demands);
  on_msg(&C[0],"{\"t\":\"tracks?\"}");assert(polls==1 && demands==1);
  tracks(101);assert(polls==2 && demands==1);
  close(pair[0]);close(pair[1]);free(C[0].out);
  puts("PASS casting: only explicit tracks? requests subtitle discovery");return 0;
}
'''


def main():
    player=(ROOT/'src/screens/player.c').read_text()
    subs=(ROOT/'src/core/subs.c').read_text()
    suites=[('demand', DEMAND+''.join(function(player, name) for name in ('subs_off','take_cast_subs','request_sub_lists','on_subs','on_adx'))+DEMAND_TEST,
             ('default-off','cast-off-metadata','cast-does-not-leak','default-language','explicit-open','off-cancels','off-reopen','wanted-retries','closed-answer')),
            ('hash', HASH+''.join(function(subs,name) for name in ('subs_os_hash','hash_keep','subs_hash_of','find_hash'))+HASH_TEST,
             ('provided','not-hashable','retry-cache','size-change','different-source','cached-no-read','failed-not-cached')),
            ('cast', CAST, ('explicit-vs-poll',))]
    count=0
    with tempfile.TemporaryDirectory(prefix='stremio-sub-demand-') as folder:
        tmp=Path(folder)
        for name,source,cases in suites:
            c,exe=tmp/(name+'.c'),tmp/name
            c.write_text(source)
            subprocess.run([os.environ.get('CC','cc'),'-std=c11','-D_GNU_SOURCE','-O1','-g',
                            '-I',str(ROOT/'src'),'-I',str(ROOT/'third_party/cjson'),str(c),
                            str(ROOT/'third_party/cjson/cJSON.c'),'-lm','-pthread','-o',str(exe)],check=True)
            for case in cases:
                subprocess.run([str(exe),case],check=True,timeout=10)
                count+=1
    print(f'{count} subtitle demand/hash scenarios passed; no media decoding or TV emulation')


if __name__=='__main__':
    main()
