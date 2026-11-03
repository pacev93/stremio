/* Exercise the real libcurl range reader against tests/net/run.py's local HTTP server. */
#include "core/net.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
  if (argc != 5) return 2;
  NetRange *r = net_range_new();
  if (!r) return 3;
  long long start = atoll(argv[2]);
  long len = atol(argv[3]);
  int count = atoi(argv[4]);
  for (int i = 0; i < count; i++) {
    unsigned char *out = NULL;
    long got = 0; long long total = -1; int status = 0, valid = 1;
    int result = net_range_get(r, argv[1], start, len, &out, &got, &total, &status, 400);
    for (long j = 0; j < got; j++) if (out[j] != (unsigned char)((start + j) % 251)) valid = 0;
    printf("{\"result\":%d,\"status\":%d,\"got\":%ld,\"total\":%lld,\"valid\":%d}\n",
           result, status, got, total, valid);
    free(out); start += len;
  }
  net_range_free(r);
  return 0;
}
