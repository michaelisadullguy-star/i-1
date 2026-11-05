//! core.rs -- the machine of Compimo: the program is translated to C (gen.rs), compiled with the run-time system (rt/imo_rt.c) into a shared
//! library, loaded, and driven through a handful of C functions.  This module has the interface of the Machine of Rustimo (core.rs there), so that the
//! front end, the printer and the quoter are the same code.
//!
//! A value of the language is a handle into a table of the run-time system (`V`: cloning makes a new handle, dropping releases it); what the
//! decoders get back from a value in weak head normal form is a `Val`.
use crate::base::*;
use crate::gen::{generate_prelude, generate_program, Def};
use crate::syntax::{erase_def, Core, Term};
use std::collections::{HashMap, HashSet};
use std::ffi::{c_char, c_int, c_void, CStr, CString};

pub enum Source {
    Core(Core),
    Term(Vec<String>, Term),
}

// ---------------------------------------------------------------- the C interface
#[repr(C)]
#[derive(Clone, Copy)]
struct RtVal {
    kind: c_int,
    a: u32,
    b: u32,
    k: i32,
}

struct Rt {
    dup: unsafe extern "C" fn(u32) -> u32,
    drop: unsafe extern "C" fn(u32),
    marker: unsafe extern "C" fn(c_int) -> u32,
    app: unsafe extern "C" fn(u32, c_int, *const u32) -> u32,
    apply_whnf: unsafe extern "C" fn(u32, c_int, *const u32, *mut RtVal) -> c_int,
    error_msg: unsafe extern "C" fn() -> *const c_char,
    error_kind: unsafe extern "C" fn() -> c_int,
    fail_thunk: unsafe extern "C" fn(c_int, *const c_char) -> u32,
    set_global: unsafe extern "C" fn(*const c_char, u32),
    lookup: unsafe extern "C" fn(*const c_char) -> u32,
}

static mut RT: Option<Rt> = None;

fn rt() -> &'static Rt {
    // SAFETY: the machine is built once, on the thread that evaluates, and used only by that thread.
    unsafe { (*std::ptr::addr_of!(RT)).as_ref().expect("the run-time system is not loaded") }
}

#[link(name = "dl")]
extern "C" {
    fn dlopen(path: *const c_char, flags: c_int) -> *mut c_void;
    fn dlsym(h: *mut c_void, s: *const c_char) -> *mut c_void;
    fn dlerror() -> *const c_char;
}

// ---------------------------------------------------------------- values
pub struct V(u32);

impl Clone for V {
    fn clone(&self) -> V {
        V(unsafe { (rt().dup)(self.0) })
    }
}

impl Drop for V {
    fn drop(&mut self) {
        unsafe { (rt().drop)(self.0) }
    }
}

/// a value in weak head normal form, or what a decoder gets back from one
#[derive(Clone)]
pub enum Val {
    Fun(V),
    T,
    F,
    Cons(V, V),
    Nil,
    Pair(V, V),
    Int(i32),
    CN(V),
    CS(V),
    CA(V, V),
    CL(V),
    CV(V),
}

fn val_of(r: RtVal) -> Val {
    match r.kind {
        0 => Val::Fun(V(r.a)),
        1 => Val::T,
        2 => Val::F,
        3 => Val::Nil,
        4 => Val::Cons(V(r.a), V(r.b)),
        5 => Val::Pair(V(r.a), V(r.b)),
        6 => Val::Int(r.k),
        7 => Val::CN(V(r.a)),
        8 => Val::CS(V(r.a)),
        9 => Val::CA(V(r.a), V(r.b)),
        10 => Val::CL(V(r.a)),
        _ => Val::CV(V(r.a)),
    }
}

// ---------------------------------------------------------------- building the machine
pub struct Machine {
    pub vt: V,
    pub vf: V,
    pub vnil: V,
    pub cons_cb: V,
    pub pair_cb: V,
    pub ints: [V; 3],
    pub code_cbs: [V; 5],
}

/// the names that the printer and the commands apply by name
const ROOTS: &[&str] = &["main", "⊜", "showq", "showc", "ℜ", "ℑ", "≐", "decimals", "⊗", "◀", "▶", "⊤", "⊥", "∷", "⊘"];

fn fnv(h: &mut u64, bytes: &[u8]) {
    for b in bytes {
        *h ^= *b as u64;
        *h = h.wrapping_mul(0x100000001b3);
    }
}

fn cache_dir() -> std::path::PathBuf {
    if let Ok(d) = std::env::var("COMPIMO_CACHE") {
        return d.into();
    }
    if let Ok(h) = std::env::var("HOME") {
        return std::path::Path::new(&h).join(".cache").join("compimo");
    }
    "/tmp/compimo-cache".into()
}

const RT_C: &str = include_str!("../rt/imo_rt.c");
const RT_H: &str = include_str!("../rt/imo_rt.h");

fn core_refs(c: &Core, out: &mut Vec<String>) {
    let mut stack: Vec<&Core> = vec![c];
    while let Some(c) = stack.pop() {
        match c {
            Core::G(g) => out.push(g.clone()),
            Core::L(b) => stack.push(b),
            Core::A(f, x) => {
                stack.push(x);
                stack.push(f);
            }
            Core::V(_) => {}
        }
    }
}

const GEN_RS: &str = include_str!("gen.rs");

fn cc() -> String {
    std::env::var("COMPIMO_CC").unwrap_or_else(|_| "gcc".to_string())
}

fn open_lib(path: &std::path::Path, global: bool) -> R<*mut c_void> {
    let cpath = CString::new(path.to_str().unwrap()).unwrap();
    let lib = unsafe { dlopen(cpath.as_ptr(), 2 | if global { 0x100 } else { 0 }) };
    if lib.is_null() {
        let e = unsafe { CStr::from_ptr(dlerror()) }.to_string_lossy().to_string();
        return Err(Err::Eval(format!("compimo: cannot load {}: {}", path.display(), e)));
    }
    Ok(lib)
}

/// compile the prelude into a library: the definitions in several C files, compiled in parallel, and the run-time system
fn build_prelude(dir: &std::path::Path, h: u64, pflags: &str, defs: Vec<(String, Source)>) -> R<()> {
    let mut gdefs: Vec<Def> = vec![];
    for (n, s) in defs {
        let core = match s {
            Source::Term(ps, b) => erase_def(&n, &ps, &b)?.1,
            Source::Core(c) => c,
        };
        gdefs.push(Def { name: n, core: Some(core) });
    }
    let ncpu = std::thread::available_parallelism().map(|n| n.get()).unwrap_or(2);
    let nshards = (ncpu * 4).max(8);
    let (files, sidecar) = generate_prelude(gdefs, nshards);
    let work = dir.join(format!("w{:016x}-{}", h, std::process::id()));
    std::fs::create_dir_all(&work).map_err(|e| Err::Eval(format!("compimo: {}", e)))?;
    let w = |name: &str, text: &str| std::fs::write(work.join(name), text).map_err(|e| Err::Eval(format!("compimo: {}", e)));
    w("imo_rt.c", RT_C)?;
    w("imo_rt.h", RT_H)?;
    let mut srcs: Vec<String> = vec!["imo_rt.c".to_string()];
    for (i, f) in files.iter().enumerate() {
        let name = format!("s{}.c", i);
        w(&name, f)?;
        srcs.push(name);
    }
    // compile, ncpu at a time
    let mut running: Vec<(String, std::process::Child)> = vec![];
    let mut objs: Vec<String> = vec![];
    let mut queue = srcs.clone();
    queue.reverse();
    let mut failure: Option<String> = None;
    while !queue.is_empty() || !running.is_empty() {
        while running.len() < ncpu && !queue.is_empty() {
            let src = queue.pop().unwrap();
            let obj = src.replace(".c", ".o");
            let mut cmd = std::process::Command::new(cc());
            cmd.current_dir(&work).arg("-c").arg("-fPIC").arg("-w").arg("-fno-strict-aliasing").arg("-fno-semantic-interposition");
            for f in pflags.split_whitespace() {
                cmd.arg(f);
            }
            cmd.arg(&src).arg("-o").arg(&obj).stderr(std::process::Stdio::piped());
            let child = cmd.spawn().map_err(|e| Err::Eval(format!("compimo: cannot run the C compiler: {}", e)))?;
            objs.push(obj.clone());
            running.push((src, child));
        }
        let (src, child) = running.remove(0);
        let out = child.wait_with_output().map_err(|e| Err::Eval(format!("compimo: {}", e)))?;
        if !out.status.success() && failure.is_none() {
            failure = Some(format!("{}: {}", src, String::from_utf8_lossy(&out.stderr).chars().take(1500).collect::<String>()));
        }
    }
    if let Some(f) = failure {
        return Err(Err::Eval(format!("compimo: the C compiler failed on the prelude:\n{}", f)));
    }
    let mut cmd = std::process::Command::new(cc());
    cmd.current_dir(&work).arg("-shared").arg("-Wl,-Bsymbolic").arg("-o").arg("out.so");
    for o in &objs {
        cmd.arg(o);
    }
    cmd.arg("-lgc");
    let out = cmd.output().map_err(|e| Err::Eval(format!("compimo: {}", e)))?;
    if !out.status.success() {
        return Err(Err::Eval(format!("compimo: linking the prelude failed:\n{}", String::from_utf8_lossy(&out.stderr))));
    }
    std::fs::write(dir.join(format!("prelude-{:016x}.idx", h)), sidecar).map_err(|e| Err::Eval(format!("compimo: {}", e)))?;
    std::fs::rename(work.join("out.so"), dir.join(format!("prelude-{:016x}.so", h))).map_err(|e| Err::Eval(format!("compimo: {}", e)))?;
    if std::env::var("COMPIMO_KEEP").is_err() {
        let _ = std::fs::remove_dir_all(&work);
    }
    Ok(())
}

impl Machine {
    /// translate, compile and load.  `defs`: every definition of the prelude and of the program; `extra`: globals that fail when they are used (unknowns).
    /// The prelude is compiled once into a library (cached); the program is compiled on its own.
    pub fn build(defs: Vec<(String, Source)>, extra: Vec<(String, Err)>, roots: &[String]) -> R<Machine> {
        let dir = cache_dir();
        let _ = std::fs::create_dir_all(&dir);
        let flags = std::env::var("COMPIMO_CFLAGS").unwrap_or_else(|_| "-O1".to_string());
        let pflags = std::env::var("COMPIMO_PFLAGS").unwrap_or_else(|_| "-O2".to_string());
        // ---- 1. the prelude library
        let mut h: u64 = 0xcbf29ce484222325;
        for (path, text) in crate::data::lib_files() {
            fnv(&mut h, path.as_bytes());
            fnv(&mut h, text.as_bytes());
        }
        fnv(&mut h, crate::data::DOC1.as_bytes());
        fnv(&mut h, crate::data::DOC2.as_bytes());
        fnv(&mut h, RT_C.as_bytes());
        fnv(&mut h, RT_H.as_bytes());
        fnv(&mut h, GEN_RS.as_bytes());
        fnv(&mut h, pflags.as_bytes());
        for var in ["COMPIMO_NOCASE", "COMPIMO_NOINLINE", "COMPIMO_INL_LIMIT", "COMPIMO_INL_LOW", "COMPIMO_INL_ONLY"] {
            if let Ok(v) = std::env::var(var) {
                fnv(&mut h, var.as_bytes());
                fnv(&mut h, v.as_bytes());
            }
        }
        let pso = dir.join(format!("prelude-{:016x}.so", h));
        let pidx = dir.join(format!("prelude-{:016x}.idx", h));
        let mut term_defs: Vec<(String, Source)> = vec![];
        let mut user_defs: Vec<(String, Core)> = vec![];
        for (n, s) in defs {
            match s {
                Source::Term(..) => term_defs.push((n, s)),
                Source::Core(c) => user_defs.push((n, c)),
            }
        }
        if !pso.exists() || !pidx.exists() {
            build_prelude(&dir, h, &pflags, term_defs)?;
        }
        let sidecar = std::fs::read_to_string(&pidx).map_err(|e| Err::Eval(format!("compimo: {}", e)))?;
        // ---- 2. load the prelude library and start the run-time system
        let plib = open_lib(&pso, true)?;
        macro_rules! sym {
            ($lib:expr, $name:expr) => {{
                let c = CString::new($name).unwrap();
                let p = unsafe { dlsym($lib, c.as_ptr()) };
                if p.is_null() {
                    return Err(Err::Eval(format!("compimo: {} is missing in the library", $name)));
                }
                unsafe { std::mem::transmute(p) }
            }};
        }
        let init: unsafe extern "C" fn() = sym!(plib, "rt_init");
        let reg: unsafe extern "C" fn() = sym!(plib, "rt_thread_register");
        let r = Rt {
            dup: sym!(plib, "rt_dup"),
            drop: sym!(plib, "rt_drop"),
            marker: sym!(plib, "rt_marker"),
            app: sym!(plib, "rt_app"),
            apply_whnf: sym!(plib, "rt_apply_whnf"),
            error_msg: sym!(plib, "rt_error_msg"),
            error_kind: sym!(plib, "rt_error_kind"),
            fail_thunk: sym!(plib, "rt_fail_thunk"),
            set_global: sym!(plib, "rt_set_global"),
            lookup: sym!(plib, "rt_lookup"),
        };
        unsafe {
            RT = Some(r);
            init();
            reg();
        }
        // ---- 3. the program: what is reachable from its own definitions (and the roots), against the prelude's names
        let pre = crate::gen::Table::from_sidecar(&sidecar);
        let mut table: HashMap<String, Core> = user_defs.into_iter().collect();
        let mut order: Vec<String> = table.keys().cloned().collect();
        order.sort();
        let mut seen: HashSet<String> = HashSet::new();
        let mut work: Vec<String> = vec![];
        let want: Vec<String> = order.iter().cloned().chain(roots.iter().cloned()).collect();
        for r in want {
            if seen.insert(r.clone()) {
                work.push(r);
            }
        }
        let mut kept: HashMap<String, Core> = HashMap::new();
        while let Some(n) = work.pop() {
            let c = match table.remove(&n) {
                Some(c) => c,
                None => continue,
            };
            let mut refs = vec![];
            core_refs(&c, &mut refs);
            for r in refs {
                if seen.insert(r.clone()) {
                    work.push(r);
                }
            }
            kept.insert(n, c);
        }
        let _ = pre;
        let mut gdefs: Vec<Def> = vec![];
        for n in &order {
            if let Some(c) = kept.remove(n) {
                gdefs.push(Def { name: n.clone(), core: Some(c) });
            }
        }
        for (n, _) in &extra {
            gdefs.push(Def { name: n.clone(), core: None });
        }
        let csrc = generate_program(&sidecar, gdefs);
        if let Ok(path) = std::env::var("COMPIMO_DUMP") {
            let _ = std::fs::write(path, &csrc);
        }
        let mut uh: u64 = h ^ 0x9e3779b97f4a7c15;
        fnv(&mut uh, csrc.as_bytes());
        fnv(&mut uh, flags.as_bytes());
        let uso = dir.join(format!("user-{:016x}.so", uh));
        if !uso.exists() {
            let work = dir.join(format!("w{:016x}-{}", uh, std::process::id()));
            std::fs::create_dir_all(&work).map_err(|e| Err::Eval(format!("compimo: {}", e)))?;
            std::fs::write(work.join("prog.c"), &csrc).map_err(|e| Err::Eval(format!("compimo: {}", e)))?;
            std::fs::write(work.join("imo_rt.h"), RT_H).map_err(|e| Err::Eval(format!("compimo: {}", e)))?;
            let tmp = work.join("out.so");
            let mut cmd = std::process::Command::new(cc());
            cmd.arg("-fPIC").arg("-shared").arg("-w").arg("-fno-strict-aliasing");
            for f in flags.split_whitespace() {
                cmd.arg(f);
            }
            cmd.arg("-I").arg(&work).arg(work.join("prog.c")).arg("-o").arg(&tmp);
            let out = cmd.output().map_err(|e| Err::Eval(format!("compimo: cannot run the C compiler: {}", e)))?;
            if !out.status.success() {
                let msg = String::from_utf8_lossy(&out.stderr);
                let keep = dir.join("failed.c");
                let _ = std::fs::copy(work.join("prog.c"), &keep);
                return Err(Err::Eval(format!("compimo: the C compiler failed (the source is in {}):\n{}", keep.display(), msg.chars().take(2000).collect::<String>())));
            }
            std::fs::rename(&tmp, &uso).map_err(|e| Err::Eval(format!("compimo: {}", e)))?;
            let _ = std::fs::remove_dir_all(&work);
        }
        let ulib = open_lib(&uso, false)?;
        let uinit: unsafe extern "C" fn() = sym!(ulib, "imo_init_usr");
        unsafe { uinit() };
        for (name, e) in &extra {
            let (kind, msg) = match e {
                Err::Unknown(m) => (1, m.clone()),
                other => (0, other.text().to_string()),
            };
            let c = CString::new(msg).unwrap_or_default();
            let n = CString::new(name.as_str()).unwrap();
            let hnd = unsafe { (rt().fail_thunk)(kind, c.as_ptr()) };
            unsafe { (rt().set_global)(n.as_ptr(), hnd) };
            unsafe { (rt().drop)(hnd) };
        }
        let mk = |w: c_int| V(unsafe { (rt().marker)(w) });
        Ok(Machine { vt: mk(3), vf: mk(4), vnil: mk(5), cons_cb: mk(9), pair_cb: mk(10), ints: [mk(6), mk(7), mk(8)], code_cbs: [mk(11), mk(12), mk(13), mk(14), mk(15)] })
    }

    pub fn global(&self, g: &str) -> R<V> {
        let c = CString::new(g).unwrap_or_default();
        let h = unsafe { (rt().lookup)(c.as_ptr()) };
        if h == 0 {
            return Err(Err::Eval(format!("i-1: {} is not defined", g)));
        }
        Ok(V(h))
    }

    #[allow(dead_code)]
    pub fn has_global(&self, g: &str) -> bool {
        self.global(g).is_ok()
    }

    /// the lazy application of f to args: a thunk that is evaluated when it is needed
    pub fn app(&self, f: &V, args: &[V]) -> V {
        let hs: Vec<u32> = args.iter().map(|a| a.0).collect();
        V(unsafe { (rt().app)(f.0, hs.len() as c_int, hs.as_ptr()) })
    }

    #[allow(dead_code)]
    pub fn whnf(&self, v: &V) -> R<Val> {
        self.apply_whnf(v, &[])
    }

    /// evaluate  f args  to weak head normal form
    pub fn apply_whnf(&self, f: &V, args: &[V]) -> R<Val> {
        let hs: Vec<u32> = args.iter().map(|a| a.0).collect();
        let mut out = RtVal { kind: 0, a: 0, b: 0, k: 0 };
        let rc = unsafe { (rt().apply_whnf)(f.0, hs.len() as c_int, hs.as_ptr(), &mut out) };
        if rc != 0 {
            let msg = unsafe { CStr::from_ptr((rt().error_msg)()) }.to_string_lossy().to_string();
            return Err(if unsafe { (rt().error_kind)() } == 1 { Err::Unknown(msg) } else { Err::Eval(msg) });
        }
        Ok(val_of(out))
    }

    pub fn to_bool(&self, v: &V) -> R<bool> {
        Ok(matches!(self.apply_whnf(v, &[self.vt.clone(), self.vf.clone()])?, Val::T))
    }

    /// the truth value that a Boolean selects between the markers: Some(true), Some(false), or None for anything else (⍰)
    pub fn tri(&self, v: &V) -> R<Option<bool>> {
        Ok(match self.apply_whnf(v, &[self.vt.clone(), self.vf.clone()])? {
            Val::T => Some(true),
            Val::F => Some(false),
            _ => None,
        })
    }

    /// take a list cell apart: Cons, Nil, or (for an undetermined value) something else
    pub fn cell_or_nil(&self, v: &V) -> R<Val> {
        self.apply_whnf(v, &[self.cons_cb.clone(), self.vnil.clone()])
    }

    /// an ordering (lib/bounded.imo): a Scott value with three alternatives, read as 0, 1 or 2
    pub fn to_ord(&self, v: &V) -> R<i32> {
        match self.apply_whnf(v, &[self.ints[0].clone(), self.ints[1].clone(), self.ints[2].clone()])? {
            Val::Int(r) => Ok(r),
            _ => Err(Err::Eval("an ordering was expected".to_string())),
        }
    }

    /// a list of booleans (digits, least significant first)
    pub fn to_list(&self, v: &V) -> R<Vec<u8>> {
        let mut out = vec![];
        let mut cur = v.clone();
        loop {
            match self.cell_or_nil(&cur)? {
                Val::Cons(h, t) => {
                    out.push(if self.to_bool(&h)? { 1 } else { 0 });
                    cur = t;
                }
                Val::Nil => return Ok(out),
                _ => return Err(Err::Eval("a list was expected".to_string())),
            }
        }
    }

    pub fn to_pair(&self, v: &V) -> R<(V, V)> {
        match self.apply_whnf(v, &[self.pair_cb.clone()])? {
            Val::Pair(a, b) => Ok((a, b)),
            _ => Err(Err::Eval("a pair was expected".to_string())),
        }
    }

    /// element n (from 0) of a stream
    pub fn stream_nth(&self, v: &V, n: usize) -> R<V> {
        let mut cur = v.clone();
        let mut k = n;
        loop {
            match self.cell_or_nil(&cur)? {
                Val::Cons(h, t) => {
                    if k == 0 {
                        return Ok(h);
                    }
                    k -= 1;
                    cur = t;
                }
                _ => return Err(Err::Eval("a stream was expected".to_string())),
            }
        }
    }

    /// the digit list (LSB first) as a language value
    pub fn list_value(&self, ds: &[u8]) -> R<V> {
        let tv = self.global("⊤")?;
        let fv = self.global("⊥")?;
        let cons = self.global("∷")?;
        let mut acc = fv.clone();
        for &d in ds.iter().rev() {
            acc = self.app(&cons, &[if d != 0 { tv.clone() } else { fv.clone() }, acc]);
        }
        Ok(acc)
    }

    /// the lazy application of the global f to the arguments
    pub fn call_g(&self, f: &str, args: &[V]) -> R<V> {
        Ok(self.app(&self.global(f)?, args))
    }

    // ---------------------------------------------------------------- numbers read back from values
    /// the Gaussian integer of a digit-list value
    pub fn gi_of(&self, v: &V) -> R<GI> {
        Ok(val_digits(&self.to_list(v)?))
    }
}

fn err_text(e: &Err) -> String {
    match e {
        other => other.text().to_string(),
    }
}
