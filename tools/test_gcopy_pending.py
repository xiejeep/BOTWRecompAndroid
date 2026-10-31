#!/usr/bin/env python3
"""Ordering tests for the actual resident writeback duplicate detector."""
import pathlib, subprocess, tempfile
root=pathlib.Path(__file__).resolve().parents[1]
s=(root/'runtime/nvn/vulkan/exec.c').read_text()
a=s.index('static bool gcopy_pending_duplicate(');b=s.index('// LARECOMP_GCOPY_STATS',a)
code=r'''
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <stdio.h>
#include <stddef.h>
typedef struct {const uint8_t *src; uint64_t addr,len,seq; uint8_t *shadow;const uint64_t *bseq;} GcBack;
static GcBack gc_back[256]; static int gc_nback;
'''+s[a:b]+r'''
int main(void) {
 uint8_t src[1024],shadow[1024];uint64_t seqs[4];
 GcBack x={src,4096,256,7,shadow,seqs};
 assert(!gcopy_pending_duplicate(&x));
 gc_back[gc_nback++]=x;assert(gcopy_pending_duplicate(&x));
 GcBack other={src+256,8192,256,7,shadow+256,seqs+1};
 gc_back[gc_nback++]=other;assert(gcopy_pending_duplicate(&x));
 other.addr=4096;other.src=src+512;gc_back[1]=other;
 assert(!gcopy_pending_duplicate(&x)); // never cross a conflicting source
 other.addr=4096+128;gc_back[1]=other;assert(!gcopy_pending_duplicate(&x));
 other.addr=8192;other.seq=8;gc_back[1]=other;assert(!gcopy_pending_duplicate(&x));
 gc_nback=1;x.seq=8;assert(!gcopy_pending_duplicate(&x));
 x.seq=7;x.shadow=NULL;assert(!gcopy_pending_duplicate(&x));
 puts("writeback tests passed: disjoint duplicates, overlapping source/order boundaries, different submissions and direct copies");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);(p/'test.c').write_text(code)
 subprocess.run(['clang','-std=c11','-O2','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
