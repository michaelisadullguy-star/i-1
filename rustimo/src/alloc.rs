//! alloc.rs -- a small-block allocator for the evaluator.
//!
//! The evaluator makes and frees very many small objects (thunks, closures, argument arrays).  The general-purpose allocator of the C
//! library costs more than the evaluation itself, so blocks of up to 256 bytes come from per-thread free lists in 16-byte size classes,
//! carved from 1 MB chunks that are never given back; everything else goes to the system allocator.  A block freed on another thread
//! than the one that allocated it just joins that thread's list.
use std::alloc::{GlobalAlloc, Layout, System};
use std::cell::UnsafeCell;
use std::ptr::null_mut;

const MAX_SMALL: usize = 256;
const NCLASS: usize = MAX_SMALL / 16 + 1;
const CHUNK: usize = 1 << 20;

struct Pool {
    free: [*mut u8; NCLASS],
    bump: *mut u8,
    end: *mut u8,
}

thread_local! {
    static POOL: UnsafeCell<Pool> = const { UnsafeCell::new(Pool { free: [null_mut(); NCLASS], bump: null_mut(), end: null_mut() }) };
}

pub struct Alloc;

#[inline(always)]
fn small(l: &Layout) -> bool {
    l.size() <= MAX_SMALL && l.align() <= 16
}

unsafe impl GlobalAlloc for Alloc {
    #[inline]
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        if small(&l) {
            let k = (l.size() + 15) >> 4;
            POOL.with(|p| {
                let p = &mut *p.get();
                let head = p.free[k];
                if !head.is_null() {
                    p.free[k] = *(head as *mut *mut u8);
                    return head;
                }
                let sz = k << 4;
                if (p.end as usize) - (p.bump as usize) < sz {
                    let chunk = System.alloc(Layout::from_size_align_unchecked(CHUNK, 16));
                    if chunk.is_null() {
                        return null_mut();
                    }
                    p.bump = chunk;
                    p.end = chunk.add(CHUNK);
                }
                let r = p.bump;
                p.bump = r.add(sz);
                r
            })
        } else {
            System.alloc(l)
        }
    }

    #[inline]
    unsafe fn dealloc(&self, ptr: *mut u8, l: Layout) {
        if small(&l) {
            let k = (l.size() + 15) >> 4;
            POOL.with(|p| {
                let p = &mut *p.get();
                *(ptr as *mut *mut u8) = p.free[k];
                p.free[k] = ptr;
            })
        } else {
            System.dealloc(ptr, l)
        }
    }

    unsafe fn realloc(&self, ptr: *mut u8, l: Layout, new_size: usize) -> *mut u8 {
        let new_layout = Layout::from_size_align_unchecked(new_size, l.align());
        if !small(&l) && !small(&new_layout) {
            return System.realloc(ptr, l, new_size);
        }
        let np = self.alloc(new_layout);
        if !np.is_null() {
            std::ptr::copy_nonoverlapping(ptr, np, l.size().min(new_size));
            self.dealloc(ptr, l);
        }
        np
    }
}
