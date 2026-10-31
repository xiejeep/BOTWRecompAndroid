#!/usr/bin/env python3
"""Exercise the real snapshot binding function with a fake transient allocator."""
import pathlib, subprocess, tempfile
root = pathlib.Path(__file__).resolve().parents[1]
source = (root/'runtime/nvn/vulkan/exec.c').read_text()
start = source.index('static bool cbwin_bind(int stage, int k, uint64_t addr, uint64_t size, VkDescriptorBufferInfo *out) {')
body = source[start:source.index('static bool gmem_placed_', start)]
preamble = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
typedef struct { uint64_t buf, off; void *ptr; } VkSpan;
typedef struct { uint64_t buffer, offset, range; } VkDescriptorBufferInfo;
static unsigned char guest[65536], arena[1<<20];
#define HEAP_BASE ((uint64_t)(uintptr_t)guest)
#define HEAP_MAX 65536
#define AB(x) (-1)
static bool gmem_placed;
static uint64_t gmem_size, gmem_buf, gcopy_gen, stat_cbwin, stat_cb_copied, top, seq=1;
static struct { struct { struct { uint64_t minUniformBufferOffsetAlignment, maxUniformBufferRange; } limits; } props; } g_vk = {{{1,65536}}};
static struct { uint32_t m[4], rows[64][4]; } cbw_patch[2];
static bool cbwin_snapshot_on(void) {return true;}
static uint64_t rows;
static uint64_t cbwin_rows(uint64_t a,uint64_t s) {return rows;}
static uint64_t vk_pending_seq(void) {return seq;}
static VkSpan vk_transient_copy(const void *p,uint64_t n,int alignment) {
    assert(top+n<=sizeof arena); VkSpan r={1,top,arena+top}; memcpy(r.ptr,p,n);top+=n;return r;
}
static VkDescriptorBufferInfo ubo_span(VkSpan s,uint64_t n) {return (VkDescriptorBufferInfo){s.buf,s.off,n};}
static VkDescriptorBufferInfo bind(void) {
    VkDescriptorBufferInfo out; memset(cbw_patch,0,sizeof cbw_patch);
    assert(cbwin_bind(0,3,HEAP_BASE,4096,&out));return out;
}
'''
# bind needs a declaration before the extracted function.
preamble=preamble.replace('static VkDescriptorBufferInfo bind(void)', 'static bool cbwin_bind(int,int,uint64_t,uint64_t,VkDescriptorBufferInfo*);\nstatic VkDescriptorBufferInfo bind(void)')
tests=r'''
int main(void) {
    memset(guest,7,sizeof guest); rows=HEAP_BASE+112;
    VkDescriptorBufferInfo a=bind(); assert(top==4096);
    guest[112]=21; VkDescriptorBufferInfo b=bind();
    assert(a.offset==b.offset && top==4096);
    assert(((unsigned char*)cbw_patch[0].rows)[0]==21);
    assert(arena[a.offset+112]==7);
    guest[2048]=99; VkDescriptorBufferInfo c=bind();
    assert(c.offset!=a.offset && arena[c.offset+2048]==99 && arena[a.offset+2048]==7);
    seq++; VkDescriptorBufferInfo d=bind();assert(d.offset!=c.offset);
    gcopy_gen++; VkDescriptorBufferInfo e=bind();assert(e.offset!=d.offset);
    // Expanding/shrinking the window must validate newly exposed base bytes.
    rows=HEAP_BASE+128; VkDescriptorBufferInfo f=bind();assert(arena[f.offset+112]==21);
    memset(cbw_patch,0,sizeof cbw_patch);rows=0;
    assert(!cbwin_bind(0,3,HEAP_BASE,4096,&a));
    rows=HEAP_BASE+112;
    assert(!cbwin_bind(5,3,HEAP_BASE,4096,&a));
    assert(!cbwin_bind(0,3,HEAP_BASE+HEAP_MAX-10,4096,&a));
    puts("snapshot tests passed: patch updates, immutable old draws, outside writes, submission/reset invalidation, window changes and fallback");
}
'''
with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);(p/'test.c').write_text(preamble+body+tests)
    subprocess.run(['clang','-std=c11','-O2','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
