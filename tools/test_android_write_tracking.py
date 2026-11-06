#!/usr/bin/env python3
"""Run production fault recovery and diagnostics with 64 KB pages under ASan/UBSan."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'runtime/platform/android.c').read_text()
a=s.index('static uint64_t wt_odd,');b=s.index('\n\nint plat_protect(',a)
disable=s[s.index('static bool wt_disable_locked(const char *why, int error) {'):s.index('\nvoid plat_write_tracking_enable(')]
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#define WT_PAGE 65536ull
#define PROT_READ 1
#define PROT_WRITE 2
static uint64_t wt_lo=0x100000,wt_hi=0x140000;
static uint8_t state[4],*wt_state=state;
static uint64_t last_addr,last_size;static int fail;
static bool wt_broken;
static uint64_t plat_now_ns(void){return 1;}
static void wt_lock(void){} static void wt_unlock(void){}
// fail=1: permanent failure; fail=2: fail once, then allow whole-window recovery.
static int mprotect(void *p,uint64_t size,int prot){
 last_addr=(uintptr_t)p;last_size=size;
 if(fail){if(fail==2)fail=0;errno=ENOMEM;return -1;}return 0;
}
'''
tests=r'''
int main(void){
 uint64_t odd,pages[4],page;
 assert(plat_write_tracking_state(wt_lo+3*WT_PAGE+5,&odd)==0);
 assert(wt_fault(wt_lo+3*WT_PAGE+5));
 assert(last_addr==wt_lo+3*WT_PAGE && last_size==WT_PAGE);
 state[2]=1;assert(wt_fault(wt_lo+2*WT_PAGE+10));assert(state[2]==2);
 assert(plat_write_tracking_state(wt_lo+2*WT_PAGE+10,&odd)==2);
 assert(!wt_fault(wt_hi) && !wt_fault(wt_lo-1));
 state[3]=1;fail=1;assert(!wt_fault(wt_lo+3*WT_PAGE+7));assert(wt_reopened==0);
 state[3]=1;fail=2;assert(wt_fault(wt_lo+3*WT_PAGE+7));
 assert(last_addr==wt_lo && last_size==wt_hi-wt_lo && wt_reopened==1);
 for(int i=0;i<4;i++)assert(state[i]==0);
 fail=2;assert(wt_fault(wt_lo+1));assert(wt_reopened==2); // untracked ENOMEM, too
 state[1]=state[2]=1;assert(wt_fault(wt_lo+2*WT_PAGE-1));
 assert(state[1]==2 && state[2]==2); // crossing a tracking-unit boundary
 memset(state,0,sizeof state);
 assert(plat_written_pages(wt_lo,wt_hi-wt_lo,pages,4,&page)==4 && page==WT_PAGE);
 for(int i=0;i<4;i++)assert(pages[i]==wt_lo+i*WT_PAGE && state[i]==1);
 assert(plat_written_pages(wt_lo,wt_hi-wt_lo,pages,4,&page)==0);
 plat_write_prepare(wt_lo+3*WT_PAGE+1,1);assert(state[3]==2);
 fail=2;assert(plat_written_pages(wt_lo,wt_hi-wt_lo,pages,4,&page)==-1);
 assert(wt_reopened==3 && !wt_broken); // recovered; tracking can start again
 for(int i=0;i<4;i++)assert(state[i]==0);
 assert(plat_written_pages(wt_lo,wt_hi-wt_lo,pages,4,&page)==4);
 fail=2;plat_write_prepare(wt_lo+1,1);assert(wt_broken); // local safe fallback
 assert(plat_written_pages(wt_lo,wt_hi-wt_lo,pages,4,&page)==-1);
 puts("write tracking tests passed: 64 KB bounds, crossing stores, ENOMEM reopen, resumed tracking and safe fallback");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(pre+disable+s[a:b]+tests)
 subprocess.run(['clang','-std=c11','-O2','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
