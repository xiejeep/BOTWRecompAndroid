#!/usr/bin/env python3
"""Exercise production guest-copy invalidation after repeated UBO updates."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'runtime/nvn/vulkan/exec.c').read_text()
a=s.index('#define GCOPY_TAB 4096');b=s.index('// ================================================================== worker threads',a)
pre=r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
typedef struct {uint64_t buf,off;void *ptr;} VkSpan;
static uint64_t seq=1,stat_cb_copied;
static unsigned char guest[1<<20],copies[1<<24];
static unsigned used;
#define AB(x) (-1)
static uint64_t vk_pending_seq(void){return seq;}
static VkSpan vk_transient_copy(const void *p,uint64_t n,uint64_t align){
 assert(used+n<sizeof copies);VkSpan s={1,used,copies+used};memcpy(s.ptr,p,n);used+=n;return s;
}
'''
test=r'''
static unsigned slot(uint64_t a,uint64_t n){uint64_t h=a*0x9E3779B97F4A7C15ull ^ n*0xC2B2AE3D27D4EB4Full;return (h^(h>>32))&(GCOPY_TAB-1);}
int main(void){
 unsetenv("LARECOMP_CB_ACTIVE_UNIQUE"); // Exercise the production default.
 uint64_t a=(uint64_t)(uintptr_t)guest,b=a+256;
 while(slot(a,64)==slot(b,64)) b+=256;
 memset(guest,7,sizeof guest); VkSpan first=guest_copy(a,64);
 assert(guest_copy(a,64).ptr==first.ptr);
 guest_copy_invalidate(a+64,a+65);assert(guest_copy(a,64).ptr==first.ptr);
 // More invalidations of one slot than the old list's whole capacity.
 for(int i=0;i<GCOPY_TAB+1000;i++){
  guest[4]=(unsigned char)i;guest_copy_invalidate(a+4,a+5);
  VkSpan next=guest_copy(a,64);assert(((unsigned char*)next.ptr)[4]==guest[4]);
 }
 assert(gcopy_nactive==1);assert(((unsigned char*)first.ptr)[4]==7);
 VkSpan old=guest_copy(b,64);assert(gcopy_nactive==2);
 *(unsigned char*)(uintptr_t)b=99;guest_copy_invalidate(b,b+1);
 VkSpan fresh=guest_copy(b,64);assert(fresh.ptr!=old.ptr && *(unsigned char*)fresh.ptr==99);
 // Fill every hash slot, then keep invalidating/reusing them: none may go missing.
 seq++;uint64_t addresses[GCOPY_TAB]={0};int found=0;
 for(unsigned i=0;i+64<sizeof guest && found<GCOPY_TAB;i++){
  uint64_t x=a+i;unsigned k=slot(x,64);
  if(!addresses[k]){addresses[k]=x;guest_copy(x,64);found++;}
 }
 assert(found==GCOPY_TAB && gcopy_nactive==GCOPY_TAB);
 for(int i=0;i<GCOPY_TAB;i++){
  uint64_t x=addresses[i];guest_copy_invalidate(x,x+64);
  VkSpan oldcopy=guest_copy(x,64);*(unsigned char*)(uintptr_t)x^=1;
  guest_copy_invalidate(x,x+1);VkSpan newcopy=guest_copy(x,64);
  assert(oldcopy.ptr!=newcopy.ptr && *(unsigned char*)newcopy.ptr==*(unsigned char*)(uintptr_t)x);
 }
 assert(gcopy_nactive==GCOPY_TAB);
 guest_copy_flush();assert(guest_copy(a,64).ptr!=first.ptr && gcopy_nactive==1);
 seq++;guest_copy(a,64);assert(gcopy_nactive==1);
 puts("guest copy tests passed: repeated invalidation, immutable snapshots, full table, overlap, flush and submission reuse");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(pre+s[a:b]+test)
 subprocess.run(['clang','-std=c11','-O2','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
