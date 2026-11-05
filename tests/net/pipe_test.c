/* Real upstream HTTP connections through production net_pipe_sync and the existing header proxy. */
#include "core/net.h"
#include "core/hproxy.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void plat_thread_background(int n) { (void)n; }
typedef struct { int status, valid, stop; long start, got; } Capture;
static pthread_mutex_t readyMu=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t readyCv=PTHREAD_COND_INITIALIZER;
static int notifyReady,ready;
static void header(const char *line, void *ud) {
  Capture *c=ud;int status;
  if(sscanf(line,"HTTP/%*s %d",&status)==1) { c->status=status;c->got=0;
    if(notifyReady && status==206) { pthread_mutex_lock(&readyMu);ready++;pthread_cond_signal(&readyCv);pthread_mutex_unlock(&readyMu); }
  }
}
static int body(const unsigned char *p,size_t n,void *ud) {
  Capture *c=ud;if(!p || (c->status>=300 && c->status<400))return 1;
  for(size_t i=0;i<n;i++)if(p[i]!=(unsigned char)((c->start+c->got+(long)i)%251))c->valid=0;
  c->got+=(long)n;return !c->stop;
}
static Capture read_(const char *url,const char *tag,const char *auth,const char *range,int head,int stop,long start,int *result) {
  char headers[600];snprintf(headers,sizeof headers,"X-Test: %s\n%s%s%s%s%s",tag,auth?"Authorization: ":"",auth?auth:"",auth?"\n":"",range?"Range: ":"",range?range:"");
  Capture c={.valid=1,.stop=stop,.start=start};
  *result=net_pipe_sync(url,headers,head,header,body,&c,2);return c;
}
typedef struct { char url[512];const char *tag;long start; } Job;
static void *parallel(void *ud) {
  Job *j=ud;char range[80];snprintf(range,sizeof range,"bytes=%ld-%ld",j->start,j->start+4095);
  int rc;Capture c=read_(j->url,j->tag,NULL,range,0,0,j->start,&rc);
  assert(rc==206 && c.valid && c.got==4096);return NULL;
}
int main(int argc,char **argv) {
  assert(argc==3);char url[512];const char *mode=argv[2];int rc;
  /* Initializes curl on the main thread before any proxy/concurrent workers start. */
  NetRange *init=net_range_new();assert(init);net_range_free(init);
  snprintf(url,sizeof url,"%s/%s",argv[1],!strcmp(mode,"chunked")?"chunked":!strcmp(mode,"redirect")?"redirect":!strcmp(mode,"partial")?"partial":!strcmp(mode,"parallel")?"parallel":"file");
  if(!strcmp(mode,"ranges") || !strcmp(mode,"chunked") || !strcmp(mode,"redirect")) {
    for(int i=0;i<4;i++) { char rg[80];snprintf(rg,sizeof rg,"bytes=%d-%d",i*4096,i*4096+4095);
      Capture c=read_(url,mode,NULL,rg,0,0,i*4096,&rc);assert(rc==206 && c.valid && c.got==4096); }
  } else if(!strcmp(mode,"head-get")) {
    Capture c=read_(url,mode,NULL,"bytes=0-4095",1,0,0,&rc);assert(rc==206 && !c.got);
    c=read_(url,mode,NULL,"bytes=0-4095",0,0,0,&rc);assert(rc==206 && c.valid && c.got==4096);
  } else if(!strcmp(mode,"headers")) {
    const char *auth[]={"fake-a","fake-b","fake-a",NULL};
    for(int i=0;i<4;i++) { Capture c=read_(url,mode,auth[i],i==3?NULL:"bytes=4096-8191",0,0,i==3?0:4096,&rc);
      assert(rc==(i==3?200:206) && c.valid && c.got==(i==3?65536:4096)); }
  } else if(!strcmp(mode,"cancel") || !strcmp(mode,"partial")) {
    Capture c=read_(url,mode,NULL,"bytes=0-4095",0,!strcmp(mode,"cancel"),0,&rc);
    assert(rc==(!strcmp(mode,"cancel")?-1:0));
    c=read_(url,mode,NULL,"bytes=0-4095",0,0,0,&rc);assert(rc==206 && c.valid && c.got==4096);
  } else if(!strcmp(mode,"parallel") || !strcmp(mode,"capacity") || !strcmp(mode,"busy-no-block")) {
    int count=!strcmp(mode,"parallel")?2:!strcmp(mode,"capacity")?5:4;
    if(strcmp(mode,"parallel"))snprintf(url,sizeof url,"%s/%s",argv[1],!strcmp(mode,"capacity")?"capacity":"wait");
    notifyReady=!strcmp(mode,"busy-no-block");
    Job jobs[5];pthread_t threads[5];for(int i=0;i<count;i++){snprintf(jobs[i].url,sizeof jobs[i].url,"%s",url);jobs[i].tag=mode;jobs[i].start=i*4096;assert(!pthread_create(&threads[i],NULL,parallel,&jobs[i]));}
    if(notifyReady) {
      pthread_mutex_lock(&readyMu);while(ready<4)pthread_cond_wait(&readyCv,&readyMu);pthread_mutex_unlock(&readyMu);
      char quick[512];snprintf(quick,sizeof quick,"%s/file",argv[1]);
      Capture c=read_(quick,mode,NULL,"bytes=0-4095",0,0,0,&rc);
      assert(rc==206 && c.valid && c.got==4096);
    }
    for(int i=0;i<count;i++)pthread_join(threads[i],NULL);
  } else if(!strcmp(mode,"bridge")) {
    char local[1024];assert(hproxy_url(url,"X-Test: bridge\nAuthorization: fake-bridge\n","Content-Type: video/x-matroska\n",local,sizeof local));
    NetRange *r=net_range_new();assert(r);
    for(int i=0;i<4;i++) { unsigned char *b=NULL;long got=0;long long total;int status;
      assert(net_range_get(r,local,i*4096,4096,&b,&got,&total,&status,4000)==NR_OK && status==206 && got==4096);
      for(long j=0;j<got;j++)assert(b[j]==(unsigned char)((i*4096+j)%251));free(b); }
    net_range_free(r);
  } else assert(!"unknown pipe scenario");
  printf("PASS upstream pipe %s\n",mode);return 0;
}
