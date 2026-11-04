//! core.rs -- the lazy evaluator of i-1 (counterpart of haskimo/src/I1/Core.hs and the Machine of pymo/imo_core.py).
//!
//! A definition is an untyped lambda term in de Bruijn form.  Evaluation is call-by-need, on an explicit stack, so that the depth of
//! a computation is limited by memory and not by the stack of the host:
//!
//!   * every term is compiled once to `Code` with FLAT closures: a lambda captures exactly the variables it uses, a delayed argument
//!     (a thunk) too; a frame is the captured values followed by the arguments of the call;
//!   * a chain of applications `((f a) b) c` is one call `f [a, b, c]`, a chain of lambdas `λx.λy.…` one lambda of arity n (eval/apply:
//!     a call with fewer arguments makes a partial application, with more applies the result to the rest);
//!   * an argument that is a variable or a global is passed as the pointer that is already there, a lambda is built at once, every
//!     other argument becomes a thunk that is evaluated at most once (update frames);
//!   * every closed application is evaluated at most once for the whole run (it is floated out into a shared thunk), as Haskimo does;
//!   * the decoders apply a language value to builder constants of the host (markers, list and pair builders, ...) and read what
//!     comes back.
//!
//! A value that is shared is a `V`, a reference-counted thunk.  Dropping a long chain of them is iterative (see `Drop for Thunk`).
use crate::base::*;
use crate::syntax::{erase_def, Core, Term};
use std::cell::{RefCell, UnsafeCell};
use std::collections::HashMap;
use std::rc::Rc;

// ---------------------------------------------------------------- values
pub type V = Rc<Thunk>;

pub struct Thunk {
    st: UnsafeCell<St>,
}

/// the variables a closure or a delayed expression captured; up to three live in the thunk itself
pub enum Caps {
    C0,
    C1(V),
    C2(V, V),
    C3(V, V, V),
    Many(Box<[V]>),
}

impl Caps {
    #[inline(always)]
    fn pick(frame: &[V], idx: &[u32]) -> Caps {
        match idx.len() {
            0 => Caps::C0,
            1 => Caps::C1(frame[idx[0] as usize].clone()),
            2 => Caps::C2(frame[idx[0] as usize].clone(), frame[idx[1] as usize].clone()),
            3 => Caps::C3(frame[idx[0] as usize].clone(), frame[idx[1] as usize].clone(), frame[idx[2] as usize].clone()),
            _ => Caps::Many(idx.iter().map(|&i| frame[i as usize].clone()).collect()),
        }
    }
    fn from_vec(mut v: Vec<V>) -> Caps {
        match v.len() {
            0 => Caps::C0,
            1 => Caps::C1(v.pop().unwrap()),
            2 => {
                let b = v.pop().unwrap();
                let a = v.pop().unwrap();
                Caps::C2(a, b)
            }
            3 => {
                let c = v.pop().unwrap();
                let b = v.pop().unwrap();
                let a = v.pop().unwrap();
                Caps::C3(a, b, c)
            }
            _ => Caps::Many(v.into_boxed_slice()),
        }
    }
    fn len(&self) -> usize {
        match self {
            Caps::C0 => 0,
            Caps::C1(_) => 1,
            Caps::C2(..) => 2,
            Caps::C3(..) => 3,
            Caps::Many(v) => v.len(),
        }
    }
    fn to_vec(&self) -> Vec<V> {
        let mut v = Vec::with_capacity(self.len());
        self.clone_into(&mut v);
        v
    }
    /// move the captured values to the end of the frame
    #[inline(always)]
    fn move_into(self, frame: &mut Vec<V>) {
        match self {
            Caps::C0 => {}
            Caps::C1(a) => frame.push(a),
            Caps::C2(a, b) => {
                frame.push(a);
                frame.push(b);
            }
            Caps::C3(a, b, c) => {
                frame.push(a);
                frame.push(b);
                frame.push(c);
            }
            Caps::Many(v) => frame.extend(Vec::from(v)),
        }
    }
    /// copy the captured values to the end of the frame
    #[inline(always)]
    fn clone_into(&self, frame: &mut Vec<V>) {
        match self {
            Caps::C0 => {}
            Caps::C1(a) => frame.push(a.clone()),
            Caps::C2(a, b) => {
                frame.push(a.clone());
                frame.push(b.clone());
            }
            Caps::C3(a, b, c) => {
                frame.push(a.clone());
                frame.push(b.clone());
                frame.push(c.clone());
            }
            Caps::Many(v) => frame.extend(v.iter().cloned()),
        }
    }
}

pub enum St {
    /// evaluated, and not a function
    Done(Val),
    /// not evaluated yet
    Delayed(&'static ThunkInfo, Caps),
    /// a function value: a lambda with what it captured
    Clo(&'static LamInfo, Caps),
    /// a partial application of a Clo or a Prim (never of another Pap): the function and the arguments held so far
    Pap(V, Caps),
    /// a global that is not compiled yet (the index of its source)
    Lazy(u32),
    /// a builder of the host
    Prim(Prim),
    Running,
    Fail(Err),
}

/// a value of the language in weak head normal form, or what a decoder gets back from one
#[derive(Clone)]
#[allow(dead_code)]
pub enum Val {
    /// a thunk in the state Clo, Pap or Prim
    Fun(V),
    /// results of applying a Church boolean to the markers
    T,
    F,
    /// results of applying a Scott list to the list builders
    Cons(V, V),
    Nil,
    /// result of applying a pair to the pair builder
    Pair(V, V),
    /// result of applying an ordering to numbers
    Int(i32),
    /// the five constructors of a code (lib/prove.imo)
    CN(V),
    CS(V),
    CA(V, V),
    CL(V),
    CV(V),
}

/// the builders the host hands to the language
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Prim {
    Cons,
    Pair,
    CodeN,
    CodeS,
    CodeA,
    CodeL,
    CodeV,
}

impl Prim {
    fn arity(self) -> usize {
        match self {
            Prim::Cons | Prim::Pair | Prim::CodeA => 2,
            _ => 1,
        }
    }
    fn run(self, a: &[V]) -> Val {
        match self {
            Prim::Cons => Val::Cons(a[0].clone(), a[1].clone()),
            Prim::Pair => Val::Pair(a[0].clone(), a[1].clone()),
            Prim::CodeN => Val::CN(a[0].clone()),
            Prim::CodeS => Val::CS(a[0].clone()),
            Prim::CodeA => Val::CA(a[0].clone(), a[1].clone()),
            Prim::CodeL => Val::CL(a[0].clone()),
            Prim::CodeV => Val::CV(a[0].clone()),
        }
    }
}

fn describe(v: &Val) -> String {
    match v {
        Val::Fun(_) => "function".to_string(),
        Val::T => "true".to_string(),
        Val::F => "false".to_string(),
        Val::Cons(..) => "cons cell".to_string(),
        Val::Nil => "nil".to_string(),
        Val::Pair(..) => "pair".to_string(),
        Val::Int(k) => k.to_string(),
        Val::CN(_) => "number code".to_string(),
        Val::CS(_) => "symbol code".to_string(),
        Val::CA(..) => "application code".to_string(),
        Val::CL(_) => "lambda code".to_string(),
        Val::CV(_) => "variable code".to_string(),
    }
}

impl Thunk {
    #[inline(always)]
    pub fn new(st: St) -> V {
        Rc::new(Thunk { st: UnsafeCell::new(st) })
    }
    pub fn done(v: Val) -> V {
        Thunk::new(St::Done(v))
    }
    #[inline(always)]
    fn state(&self) -> &mut St {
        // SAFETY: the evaluator is single-threaded and never keeps a reference into a thunk's state across a call that could
        // change that state (every access copies out what it needs at once).
        unsafe { &mut *self.st.get() }
    }
}

/// the value of a thunk that is already evaluated, if it is
#[inline(always)]
fn evaluated(t: &V) -> Option<Val> {
    match t.state() {
        St::Done(v) => Some(v.clone()),
        St::Clo(..) | St::Pap(..) | St::Prim(_) => Some(Val::Fun(t.clone())),
        _ => None,
    }
}

// Dropping a long list or a deep chain of thunks must not recurse as deep as the chain: beyond a small depth the states still to be
// dropped are queued and the outermost drop empties the queue.  Thunks are made and dropped by the interpreter thread only, so the
// counters are plain statics.
static mut DROP_DEPTH: u32 = 0;
static mut DROP_QUEUE: Vec<St> = Vec::new();

impl Drop for Thunk {
    #[inline]
    fn drop(&mut self) {
        let st = std::mem::replace(self.st.get_mut(), St::Running);
        match &st {
            St::Running | St::Prim(_) | St::Lazy(_) => return,
            St::Done(Val::T) | St::Done(Val::F) | St::Done(Val::Nil) | St::Done(Val::Int(_)) => return,
            St::Clo(_, Caps::C0) | St::Delayed(_, Caps::C0) => return,
            _ => {}
        }
        // SAFETY: only the interpreter thread drops thunks (see above).
        unsafe {
            let d = DROP_DEPTH;
            if d >= 200 {
                (*std::ptr::addr_of_mut!(DROP_QUEUE)).push(st);
                return;
            }
            DROP_DEPTH = d + 1;
            drop(st);
            DROP_DEPTH = d;
            if d == 0 {
                let q = &mut *std::ptr::addr_of_mut!(DROP_QUEUE);
                while let Some(s) = q.pop() {
                    DROP_DEPTH = 1;
                    drop(s);
                    DROP_DEPTH = 0;
                }
            }
        }
    }
}

// ---------------------------------------------------------------- code
pub enum Code {
    /// a variable of the frame
    Var(u32),
    /// a global, or a shared closed term or lambda
    Const(V),
    /// build a closure from the frame
    Lam(&'static LamInfo),
    /// call a function expression with arguments
    App(Box<Code>, Box<[Arg]>),
    /// call a global lambda of known arity with at least that many arguments
    Call(V, Box<[Arg]>),
    /// call a variable of the frame: a closure of the right arity that is already evaluated is entered at once
    CallVar(u32, Box<[Arg]>),
    /// a global lambda of known arity applied to fewer arguments: the partial application is built at once
    Pap(&'static PapSpec),
}

pub enum Arg {
    Var(u32),
    Const(V),
    Lam(&'static LamInfo),
    Delay(&'static ThunkInfo),
    Pap(&'static PapSpec),
}

pub struct PapSpec {
    g: V,
    args: Box<[Arg]>,
}

pub struct LamInfo {
    arity: u32,
    caps: Box<[u32]>,
    body: Code,
}

pub struct ThunkInfo {
    caps: Box<[u32]>,
    body: Code,
}

// ---------------------------------------------------------------- compiling de Bruijn terms
/// a term with the levels (absolute binder depths) of its free variables
enum Ann {
    V(u32),
    G(String),
    L { arity: u32, body: Box<Ann>, fv: Vec<u32> },
    A { f: Box<Ann>, a: Box<Ann>, fv: Vec<u32> },
}

fn fv_of(a: &Ann) -> &[u32] {
    match a {
        Ann::V(_) | Ann::G(_) => &[],
        Ann::L { fv, .. } | Ann::A { fv, .. } => fv,
    }
}

fn union_sorted(a: &[u32], b: &[u32]) -> Vec<u32> {
    let mut out = Vec::with_capacity(a.len() + b.len());
    let (mut i, mut j) = (0, 0);
    while i < a.len() || j < b.len() {
        if j >= b.len() || (i < a.len() && a[i] < b[j]) {
            out.push(a[i]);
            i += 1;
        } else if i >= a.len() || b[j] < a[i] {
            out.push(b[j]);
            j += 1;
        } else {
            out.push(a[i]);
            i += 1;
            j += 1;
        }
    }
    out
}

/// annotate a term at binder depth `depth`; a run of lambdas becomes one lambda of that arity
fn annotate(t: &Core, depth: u32) -> Ann {
    match t {
        Core::V(k) => Ann::V(depth - *k as u32),
        Core::G(g) => Ann::G(g.clone()),
        Core::L(_) => {
            let mut n = 0u32;
            let mut cur = t;
            while let Core::L(b) = cur {
                n += 1;
                cur = b;
            }
            let body = annotate(cur, depth + n);
            // the free levels of the body that are bound outside this lambda
            let fv: Vec<u32> = free_levels(&body).into_iter().filter(|&l| l < depth).collect();
            Ann::L { arity: n, body: Box::new(body), fv }
        }
        Core::A(f, x) => {
            let fa = annotate(f, depth);
            let xa = annotate(x, depth);
            let fv = union_sorted(&free_levels(&fa), &free_levels(&xa));
            Ann::A { f: Box::new(fa), a: Box::new(xa), fv }
        }
    }
}

/// the free levels of any annotated term (a variable's own level included)
fn free_levels(a: &Ann) -> Vec<u32> {
    match a {
        Ann::V(l) => vec![*l],
        Ann::G(_) => vec![],
        Ann::L { fv, .. } | Ann::A { fv, .. } => fv.clone(),
    }
}

fn is_closed(a: &Ann) -> bool {
    match a {
        Ann::V(_) => false,
        Ann::G(_) => true,
        Ann::L { fv, .. } | Ann::A { fv, .. } => fv.is_empty(),
    }
}

/// level -> slot of the frame being compiled for
struct Scope {
    slots: Vec<u32>,
}

const NO_SLOT: u32 = u32::MAX;

impl Scope {
    fn new() -> Scope {
        Scope { slots: vec![] }
    }
    fn set(&mut self, level: u32, slot: u32) {
        let l = level as usize;
        if self.slots.len() <= l {
            self.slots.resize(l + 1, NO_SLOT);
        }
        self.slots[l] = slot;
    }
    fn slot(&self, level: u32) -> u32 {
        let s = self.slots.get(level as usize).copied().unwrap_or(NO_SLOT);
        assert!(s != NO_SLOT, "i-1: internal error: a free variable is not in the frame");
        s
    }
}

pub struct Linker<'a> {
    globals: &'a HashMap<String, V>,
    /// the arity of the globals that are closed lambdas
    arity: &'a HashMap<String, u32>,
}

/// the chain of applications of an open application, as its head and its arguments in order; a closed inner application is the
/// head (it is shared), not part of the chain
fn spine(a: &Ann) -> (&Ann, Vec<&Ann>) {
    let mut args: Vec<&Ann> = vec![];
    let mut cur = a;
    loop {
        match cur {
            Ann::A { f, a: x, .. } if std::ptr::eq(cur, a) || !is_closed(cur) => {
                args.push(x);
                cur = f;
            }
            _ => break,
        }
    }
    args.reverse();
    (cur, args)
}

impl<'a> Linker<'a> {
    fn global(&self, g: &str) -> V {
        match self.globals.get(g) {
            Some(v) => v.clone(),
            None => Thunk::new(St::Fail(Err::Eval(format!("i-1: {} has no compiled body", g)))),
        }
    }

    fn gen_lam(&self, a: &Ann, depth: u32, scope: &Scope) -> &'static LamInfo {
        let (arity, body, fv) = match a {
            Ann::L { arity, body, fv } => (*arity, body, fv),
            _ => unreachable!(),
        };
        let caps: Box<[u32]> = fv.iter().map(|&l| scope.slot(l)).collect();
        let mut inner = Scope::new();
        for (j, &l) in fv.iter().enumerate() {
            inner.set(l, j as u32);
        }
        for p in 0..arity {
            inner.set(depth + p, fv.len() as u32 + p);
        }
        let body = self.gen(body, depth + arity, &inner, false);
        Box::leak(Box::new(LamInfo { arity, caps, body }))
    }

    /// the code of a delayed argument: a frame of its own free variables
    fn gen_thunk(&self, a: &Ann, depth: u32, scope: &Scope) -> &'static ThunkInfo {
        let fv = fv_of(a);
        let caps: Box<[u32]> = fv.iter().map(|&l| scope.slot(l)).collect();
        let mut inner = Scope::new();
        for (j, &l) in fv.iter().enumerate() {
            inner.set(l, j as u32);
        }
        let body = self.gen(a, depth, &inner, true);
        Box::leak(Box::new(ThunkInfo { caps, body }))
    }

    /// a closed term as a shared value: a closure is made now, an application is a thunk evaluated at most once
    fn shared(&self, a: &Ann, depth: u32) -> V {
        match a {
            Ann::L { .. } => {
                let info = self.gen_lam(a, depth, &Scope::new());
                Thunk::new(St::Clo(info, Caps::C0))
            }
            _ => {
                let body = self.gen(a, depth, &Scope::new(), true);
                let info: &'static ThunkInfo = Box::leak(Box::new(ThunkInfo { caps: Box::new([]), body }));
                Thunk::new(St::Delayed(info, Caps::C0))
            }
        }
    }

    fn gen_arg(&self, a: &Ann, depth: u32, scope: &Scope) -> Arg {
        match a {
            Ann::V(l) => Arg::Var(scope.slot(*l)),
            Ann::G(g) => Arg::Const(self.global(g)),
            _ if is_closed(a) => Arg::Const(self.shared(a, depth)),
            Ann::L { .. } => Arg::Lam(self.gen_lam(a, depth, scope)),
            Ann::A { .. } => {
                // a known function applied to too few arguments is a value: build it now instead of delaying the work
                let (head, args) = spine(a);
                if let Ann::G(g) = head {
                    if let Some(&n) = self.arity.get(g.as_str()) {
                        if args.len() < n as usize {
                            return Arg::Pap(self.gen_pap(g, &args, depth, scope));
                        }
                    }
                }
                Arg::Delay(self.gen_thunk(a, depth, scope))
            }
        }
    }

    fn gen_pap(&self, g: &str, args: &[&Ann], depth: u32, scope: &Scope) -> &'static PapSpec {
        let args: Box<[Arg]> = args.iter().map(|x| self.gen_arg(x, depth, scope)).collect();
        Box::leak(Box::new(PapSpec { g: self.global(g), args }))
    }

    /// `root`: the term is the body of a thunk or of a global (it is evaluated once, so it is not floated out again)
    fn gen(&self, a: &Ann, depth: u32, scope: &Scope, root: bool) -> Code {
        match a {
            Ann::V(l) => Code::Var(scope.slot(*l)),
            Ann::G(g) => Code::Const(self.global(g)),
            Ann::L { .. } => {
                if is_closed(a) {
                    Code::Const(self.shared(a, depth))
                } else {
                    Code::Lam(self.gen_lam(a, depth, scope))
                }
            }
            Ann::A { .. } => {
                if !root && is_closed(a) {
                    return Code::Const(self.shared(a, depth));
                }
                let (cur, args) = spine(a);
                if let Ann::G(g) = cur {
                    if let Some(&n) = self.arity.get(g.as_str()) {
                        if args.len() >= n as usize {
                            let args: Box<[Arg]> = args.iter().map(|x| self.gen_arg(x, depth, scope)).collect();
                            return Code::Call(self.global(g), args);
                        }
                        return Code::Pap(self.gen_pap(g, &args, depth, scope));
                    }
                }
                if let Ann::V(l) = cur {
                    let slot = scope.slot(*l);
                    let args: Box<[Arg]> = args.iter().map(|x| self.gen_arg(x, depth, scope)).collect();
                    return Code::CallVar(slot, args);
                }
                let head = self.gen(cur, depth, scope, false);
                let args: Box<[Arg]> = args.iter().map(|x| self.gen_arg(x, depth, scope)).collect();
                Code::App(Box::new(head), args)
            }
        }
    }

    /// the state of a global definition: a closed lambda is a function value at once, anything else a delayed expression
    fn gen_def(&self, c: &Core) -> St {
        let a = annotate(c, 0);
        if let Ann::L { .. } = &a {
            let info = self.gen_lam(&a, 0, &Scope::new());
            return St::Clo(info, Caps::C0);
        }
        let body = self.gen(&a, 0, &Scope::new(), true);
        St::Delayed(Box::leak(Box::new(ThunkInfo { caps: Box::new([]), body })), Caps::C0)
    }
}

// ---------------------------------------------------------------- the machine
enum Cont {
    /// write the value into the thunk
    Update(V),
    /// apply the value to this argument
    Arg(V),
}

struct MState {
    conts: Vec<Cont>,
    frame: Vec<V>,
    scratch: Vec<V>,
}

/// where the code of a global comes from: a term already in de Bruijn form, or a checked definition to erase when it is first needed
pub enum Source {
    Core(Core),
    Term(Vec<String>, Term),
}

/// the number of arguments a definition takes before its value is no longer a lambda (0: it is not a lambda)
fn term_arity(ps: &[String], body: &Term) -> u32 {
    fn lams(t: &Term) -> u32 {
        match t {
            Term::Lam(ps, b) => ps.len() as u32 + lams(b),
            Term::Asc(e, _) | Term::Quote(e, _) => lams(e),
            _ => 0,
        }
    }
    ps.len() as u32 + lams(body)
}

fn core_arity(c: &Core) -> u32 {
    let mut n = 0;
    let mut cur = c;
    while let Core::L(b) = cur {
        n += 1;
        cur = b;
    }
    n
}

pub struct Machine {
    globals: HashMap<String, V>,
    arity: HashMap<String, u32>,
    lazy: RefCell<Vec<Option<Source>>>,
    st: RefCell<MState>,
    pub vt: V,
    pub vf: V,
    pub vnil: V,
    pub cons_cb: V,
    pub pair_cb: V,
    pub ints: [V; 3],
    pub code_cbs: [V; 5],
    app_infos: RefCell<Vec<&'static ThunkInfo>>,
}

/// what the evaluator does next: force a thunk, or evaluate code in the current frame
enum Next {
    Force(V),
    Eval(&'static Code),
}

/// the result of applying a function to arguments
enum Enter {
    /// evaluate this code in the (new) frame
    Eval(&'static Code),
    /// a value (a partial application, or what a builder of the host makes)
    Value(Val),
}

/// how many further arguments (at most `want`) are waiting on the stack above `base`
#[inline(always)]
fn waiting(conts: &[Cont], base: usize, want: usize) -> usize {
    let top = conts.len();
    let mut n = 0;
    while n < want && top > base + n && matches!(conts[top - 1 - n], Cont::Arg(_)) {
        n += 1;
    }
    n
}

/// the value of an argument: a variable and a global are passed as they are, a lambda is built at once, a partial application of a
/// known function too, anything else is delayed
#[inline(always)]
fn make_arg(a: &'static Arg, frame: &[V]) -> V {
    match a {
        Arg::Var(i) => frame[*i as usize].clone(),
        Arg::Const(c) => c.clone(),
        Arg::Lam(info) => Thunk::new(St::Clo(info, Caps::pick(frame, &info.caps))),
        Arg::Delay(info) => Thunk::new(St::Delayed(info, Caps::pick(frame, &info.caps))),
        Arg::Pap(spec) => make_pap(spec, frame),
    }
}

fn make_pap(spec: &'static PapSpec, frame: &[V]) -> V {
    let caps = match &*spec.args {
        [a] => Caps::C1(make_arg(a, frame)),
        [a, b] => Caps::C2(make_arg(a, frame), make_arg(b, frame)),
        [a, b, c] => Caps::C3(make_arg(a, frame), make_arg(b, frame), make_arg(c, frame)),
        many => Caps::from_vec(many.iter().map(|x| make_arg(x, frame)).collect()),
    };
    Thunk::new(St::Pap(spec.g.clone(), caps))
}

/// apply a lambda (`clo` is the thunk that holds it; `held` the arguments of the partial application it may be inside)
#[inline(always)]
fn call_clo(info: &'static LamInfo, caps: &Caps, held: &Caps, clo: &V, first: V, conts: &mut Vec<Cont>, frame: &mut Vec<V>, base: usize) -> Enter {
    let need = info.arity as usize - held.len();
    let extra = waiting(conts, base, need - 1);
    if extra + 1 < need {
        // not enough arguments yet: a partial application
        let mut h: Vec<V> = Vec::with_capacity(held.len() + 1 + extra);
        held.clone_into(&mut h);
        h.push(first);
        for _ in 0..extra {
            if let Some(Cont::Arg(a)) = conts.pop() {
                h.push(a);
            }
        }
        return Enter::Value(Val::Fun(Thunk::new(St::Pap(clo.clone(), Caps::from_vec(h)))));
    }
    frame.clear();
    caps.clone_into(frame);
    held.clone_into(frame);
    frame.push(first);
    for _ in 1..need {
        if let Some(Cont::Arg(a)) = conts.pop() {
            frame.push(a);
        }
    }
    Enter::Eval(&info.body)
}

fn call_prim(p: Prim, held: &Caps, prim_v: &V, first: V, conts: &mut Vec<Cont>, base: usize) -> Enter {
    let need = p.arity() - held.len();
    let extra = waiting(conts, base, need - 1);
    let mut args: Vec<V> = held.to_vec();
    args.push(first);
    for _ in 0..extra {
        if let Some(Cont::Arg(a)) = conts.pop() {
            args.push(a);
        }
    }
    if extra + 1 < need {
        return Enter::Value(Val::Fun(Thunk::new(St::Pap(prim_v.clone(), Caps::from_vec(args)))));
    }
    Enter::Value(p.run(&args))
}

impl Machine {
    /// link the definitions (a global that is used and not defined is an error when it is evaluated); `extra` are globals given
    /// as ready values (the unknowns, whose value is an error)
    pub fn build(defs: Vec<(String, Source)>, extra: Vec<(String, V)>) -> Machine {
        let mut globals: HashMap<String, V> = HashMap::new();
        // the ready values first (they win over a definition of the same name), then the placeholders: definitions refer to each
        // other (and to themselves) through them, and are compiled when they are first needed
        for (n, v) in extra {
            globals.insert(n, v);
        }
        let mut arity: HashMap<String, u32> = HashMap::new();
        let mut last: HashMap<String, usize> = HashMap::new();
        for (i, (n, _)) in defs.iter().enumerate() {
            last.insert(n.clone(), i); // a later definition of the same name wins
        }
        let mut lazy: Vec<Option<Source>> = Vec::with_capacity(defs.len());
        for (i, (n, src)) in defs.into_iter().enumerate() {
            if last[&n] != i || globals.contains_key(&n) {
                lazy.push(None);
                continue;
            }
            let ar = match &src {
                Source::Core(c) => core_arity(c),
                Source::Term(ps, b) => term_arity(ps, b),
            };
            if ar > 0 {
                arity.insert(n.clone(), ar);
            }
            globals.insert(n, Thunk::new(St::Lazy(i as u32)));
            lazy.push(Some(src));
        }
        let mk = |v: Val| Thunk::done(v);
        let prim = |p: Prim| Thunk::new(St::Prim(p));
        Machine {
            globals,
            arity,
            lazy: RefCell::new(lazy),
            st: RefCell::new(MState { conts: Vec::new(), frame: Vec::new(), scratch: Vec::new() }),
            vt: mk(Val::T),
            vf: mk(Val::F),
            vnil: mk(Val::Nil),
            cons_cb: prim(Prim::Cons),
            pair_cb: prim(Prim::Pair),
            ints: [mk(Val::Int(0)), mk(Val::Int(1)), mk(Val::Int(2))],
            code_cbs: [prim(Prim::CodeN), prim(Prim::CodeS), prim(Prim::CodeA), prim(Prim::CodeL), prim(Prim::CodeV)],
            app_infos: RefCell::new(Vec::new()),
        }
    }

    /// compile a global that has not been needed before
    fn compile_global(&self, idx: u32) -> St {
        let src = self.lazy.borrow_mut()[idx as usize].take();
        let core = match src {
            Some(Source::Core(c)) => c,
            Some(Source::Term(ps, b)) => match erase_def("", &ps, &b) {
                Ok((_, c)) => c,
                Err(e) => return St::Fail(e),
            },
            None => return St::Fail(Err::Eval("i-1: internal error: a global was compiled twice".to_string())),
        };
        Linker { globals: &self.globals, arity: &self.arity }.gen_def(&core)
    }

    pub fn global(&self, g: &str) -> R<V> {
        match self.globals.get(g) {
            Some(v) => Ok(v.clone()),
            None => Err(Err::Eval(format!("i-1: {} is not defined", g))),
        }
    }

    pub fn has_global(&self, g: &str) -> bool {
        self.globals.contains_key(g)
    }


    /// the lazy application of f to args: a thunk that is evaluated when it is needed
    pub fn app(&self, f: &V, args: &[V]) -> V {
        let n = args.len();
        let info = {
            let mut infos = self.app_infos.borrow_mut();
            while infos.len() <= n {
                let k = infos.len() as u32;
                // frame: [f, a1 .. ak]; body: f a1 .. ak
                let body = if k == 0 {
                    Code::Var(0)
                } else {
                    Code::App(Box::new(Code::Var(0)), (1..=k).map(Arg::Var).collect())
                };
                infos.push(Box::leak(Box::new(ThunkInfo { caps: (0..=k).collect(), body })));
            }
            infos[n]
        };
        let mut caps: Vec<V> = Vec::with_capacity(n + 1);
        caps.push(f.clone());
        caps.extend(args.iter().cloned());
        Thunk::new(St::Delayed(info, Caps::from_vec(caps)))
    }

    /// evaluate a value to weak head normal form
    #[allow(dead_code)]
    pub fn whnf(&self, v: &V) -> R<Val> {
        self.run(v, &[])
    }

    /// evaluate  f args  to weak head normal form
    pub fn apply_whnf(&self, f: &V, args: &[V]) -> R<Val> {
        self.run(f, args)
    }

    fn run(&self, start: &V, args: &[V]) -> R<Val> {
        let mut guard = self.st.borrow_mut();
        let MState { conts, frame, scratch } = &mut *guard;
        let base = conts.len();
        for a in args.iter().rev() {
            conts.push(Cont::Arg(a.clone()));
        }
        let mut next = Next::Force(start.clone());
        let err: Err = 'main: loop {
            // ---- evaluate until there is a value
            let mut val: Val = loop {
                match next {
                    Next::Force(t) => {
                        if let Some(v) = evaluated(&t) {
                            break v;
                        }
                        match t.state() {
                            St::Running => break 'main Err::Eval("<<loop>>".to_string()),
                            St::Fail(e) => break 'main e.clone(),
                            St::Lazy(i) => {
                                let st = self.compile_global(*i);
                                *t.state() = st;
                                next = Next::Force(t);
                            }
                            St::Delayed(..) => match std::mem::replace(t.state(), St::Running) {
                                St::Delayed(info, caps) => {
                                    frame.clear();
                                    caps.move_into(frame);
                                    conts.push(Cont::Update(t));
                                    next = Next::Eval(&info.body);
                                }
                                _ => unreachable!(),
                            },
                            _ => unreachable!(),
                        }
                    }
                    Next::Eval(code) => match code {
                        Code::Var(i) => {
                            let t = &frame[*i as usize];
                            match evaluated(t) {
                                Some(v) => break v,
                                None => next = Next::Force(t.clone()),
                            }
                        }
                        Code::Const(t) => match evaluated(t) {
                            Some(v) => break v,
                            None => next = Next::Force(t.clone()),
                        },
                        Code::Lam(info) => break Val::Fun(Thunk::new(St::Clo(info, Caps::pick(frame, &info.caps)))),
                        Code::Call(g, args) => {
                            if let St::Lazy(i) = g.state() {
                                let st = self.compile_global(*i);
                                *g.state() = st;
                            }
                            match g.state() {
                                St::Clo(info, _) if info.arity as usize <= args.len() => {
                                    let n = info.arity as usize;
                                    for a in args[n..].iter().rev() {
                                        conts.push(Cont::Arg(make_arg(a, frame)));
                                    }
                                    scratch.clear();
                                    for a in &args[..n] {
                                        scratch.push(make_arg(a, frame));
                                    }
                                    std::mem::swap(frame, scratch);
                                    scratch.clear();
                                    next = Next::Eval(&info.body);
                                }
                                _ => {
                                    for a in args.iter().rev() {
                                        conts.push(Cont::Arg(make_arg(a, frame)));
                                    }
                                    next = Next::Force(g.clone());
                                }
                            }
                        }
                        Code::CallVar(i, args) => {
                            let t = &frame[*i as usize];
                            match t.state() {
                                St::Clo(info, caps) if info.arity as usize == args.len() => {
                                    let info: &'static LamInfo = *info;
                                    scratch.clear();
                                    caps.clone_into(scratch);
                                    for a in args.iter() {
                                        scratch.push(make_arg(a, frame));
                                    }
                                    std::mem::swap(frame, scratch);
                                    scratch.clear();
                                    next = Next::Eval(&info.body);
                                }
                                _ => {
                                    let t = t.clone();
                                    for a in args.iter().rev() {
                                        conts.push(Cont::Arg(make_arg(a, frame)));
                                    }
                                    match evaluated(&t) {
                                        Some(v) => break v,
                                        None => next = Next::Force(t),
                                    }
                                }
                            }
                        }
                        Code::Pap(spec) => break Val::Fun(make_pap(spec, frame)),
                        Code::App(f, args) => {
                            for a in args.iter().rev() {
                                conts.push(Cont::Arg(make_arg(a, frame)));
                            }
                            next = Next::Eval(&**f);
                        }
                    },
                }
            };
            // ---- deliver the value to what is waiting for it
            loop {
                if conts.len() <= base {
                    return Ok(val);
                }
                match conts.pop() {
                    Some(Cont::Update(t)) => {
                        *t.state() = St::Done(val.clone());
                    }
                    Some(Cont::Arg(first)) => {
                        let f = match val {
                            Val::Fun(f) => f,
                            other => break 'main Err::Eval(format!("a value that is not a function was applied: {}", describe(&other))),
                        };
                        let entered = match f.state() {
                            St::Clo(info, caps) => call_clo(info, caps, &Caps::C0, &f, first, conts, frame, base),
                            St::Prim(p) => call_prim(*p, &Caps::C0, &f, first, conts, base),
                            St::Pap(b, held) => {
                                if let St::Lazy(i) = b.state() {
                                    let st = self.compile_global(*i);
                                    *b.state() = st;
                                }
                                match b.state() {
                                    St::Clo(info, caps) => call_clo(info, caps, held, b, first, conts, frame, base),
                                    St::Prim(p) => call_prim(*p, held, b, first, conts, base),
                                    _ => unreachable!(),
                                }
                            }
                            _ => unreachable!(),
                        };
                        match entered {
                            Enter::Eval(code) => {
                                next = Next::Eval(code);
                                continue 'main;
                            }
                            Enter::Value(v) => val = v,
                        }
                    }
                    None => return Ok(val),
                }
            }
        };
        // an error: the thunks under evaluation keep it (evaluating them again gives the same error), the rest of the work is dropped
        while conts.len() > base {
            if let Some(Cont::Update(t)) = conts.pop() {
                *t.state() = St::Fail(err.clone());
            }
        }
        Err(err)
    }

    // ---------------------------------------------------------------- decoding
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
