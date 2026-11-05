//! gen.rs -- from de Bruijn terms to C.
//!
//! The input is the program as the front end leaves it: global definitions, each an untyped lambda term (`Core`).  The output is C that is compiled with the
//! run-time system (rt/imo_rt.c).  The prelude (about 7000 definitions) is translated and compiled ONCE into a shared library (in several files, compiled in
//! parallel), and a program is translated on its own and calls the prelude through the names `p<i>` (functions) and `PG[i]` (objects).  What the translation does:
//!
//!   * a global that is a lambda of arity n becomes a C function of n arguments (n <= 6: C parameters, otherwise an array), called directly when it
//!     is applied to at least n arguments;  a chain `λx.λy.…` is one function and a chain `((f a) b) c` one call;
//!   * a global whose body is `λ f1..fn k1..km. kj f1..fn` is a CONSTRUCTOR (booleans, the cells of lists, pairs, the constructors of the library's
//!     own data): applied to its n fields it is a data object at once (no function call, no thunk) and a pattern match is a selection;
//!   * an argument that is a variable, a global or a lambda is passed as it is, a constructor application is built at once, every other argument
//!     becomes a thunk that captures exactly the variables it uses; a closed argument is built once, at start-up, and shared;
//!   * nothing is evaluated that the program does not ask for (call by need), so the result is the value the interpreters compute.
use crate::syntax::Core;
use std::collections::HashMap;
use std::fmt::Write as _;

/// a global definition handed to the generator
pub struct Def {
    pub name: String,
    pub core: Option<Core>, // None: a global provided by the host (an unknown: a thunk that fails)
}

#[derive(Clone, Debug)]
enum E {
    V(u32),                        // a variable, by level (0 = the outermost binder)
    G(usize),                      // a global (index into the table)
    App(Box<E>, Vec<E>, Vec<u32>), // head, arguments (at least one), free levels
    Lam(u32, Box<E>, Vec<u32>),    // arity, body, free levels (below the lambda's own parameters)
}

fn fvs(e: &E) -> &[u32] {
    match e {
        E::V(l) => std::slice::from_ref(l),
        E::G(_) => &[],
        E::App(_, _, f) | E::Lam(_, _, f) => f,
    }
}

fn union(xs: &[&[u32]]) -> Vec<u32> {
    let mut v: Vec<u32> = xs.iter().flat_map(|x| x.iter().copied()).collect();
    v.sort_unstable();
    v.dedup();
    v
}

#[derive(Clone, Debug, PartialEq)]
pub enum Kind {
    Func(u32),
    Caf,
    Con { nf: u32, m: u32, j: u32, arity: u32 },
    Host, // provided by the host at run time (or an undefined name: it fails)
}

#[derive(Clone, Debug)]
pub struct Info {
    pub name: String,
    pub kind: Kind,
    pub pre: bool,   // a global of the prelude library
    pub idx: usize,  // the index inside its module
}

/// the globals of the prelude and of the program
pub struct Table {
    pub info: Vec<Info>,
    index: HashMap<String, usize>,
    npre: usize,
    /// small prelude functions that programs may inline: (name, arity, encoded body)
    inl_lines: Vec<(String, u32, String)>,
}

impl Table {
    pub fn new() -> Table {
        Table { info: vec![], index: HashMap::new(), npre: 0, inl_lines: vec![] }
    }
    fn add(&mut self, name: &str, kind: Kind, pre: bool) -> usize {
        let i = self.info.len();
        let idx = if pre { self.npre } else { i - self.npre };
        if pre {
            self.npre += 1;
        }
        self.info.push(Info { name: name.to_string(), kind, pre, idx });
        self.index.insert(name.to_string(), i);
        i
    }
    /// the sidecar of a compiled prelude: one line per global
    pub fn sidecar(&self) -> String {
        let mut s = String::new();
        for i in &self.info {
            if !i.pre {
                continue;
            }
            let k = match &i.kind {
                Kind::Func(a) => format!("F\t{}", a),
                Kind::Caf => "A".to_string(),
                Kind::Con { nf, m, j, arity } => format!("C\t{}\t{}\t{}\t{}", nf, m, j, arity),
                Kind::Host => "H".to_string(),
            };
            let _ = writeln!(s, "{}\t{}", k, i.name);
        }
        for (n, k, enc) in &self.inl_lines {
            let _ = writeln!(s, "I\t{}\t{}\t{}", k, n, enc);
        }
        s
    }
    pub fn from_sidecar(text: &str) -> Table {
        let mut t = Table::new();
        for ln in text.lines() {
            let parts: Vec<&str> = ln.split('\t').collect();
            if parts[0] == "I" {
                t.inl_lines.push((parts[2].to_string(), parts[1].parse().unwrap(), parts[3].to_string()));
                continue;
            }
            let (kind, rest) = match parts[0] {
                "F" => (Kind::Func(parts[1].parse().unwrap()), 2),
                "A" => (Kind::Caf, 1),
                "C" => (Kind::Con { nf: parts[1].parse().unwrap(), m: parts[2].parse().unwrap(), j: parts[3].parse().unwrap(), arity: parts[4].parse().unwrap() }, 5),
                _ => (Kind::Host, 1),
            };
            let name = parts[rest..].join("\t");
            t.add(&name, kind, true);
        }
        t
    }
    pub fn has(&self, name: &str) -> bool {
        self.index.contains_key(name)
    }
}

/// prelude functions that have a native version in the run-time system (rt/imo_rt.c): the arithmetic on digit strings
const NATIVES: &[(&str, &str)] = &[("⊞ᶻ", "nat_addz"), ("⊟ᶻ", "nat_subz"), ("⊠ᶻ", "nat_mulz"), ("⊖ᶻ", "nat_negz"), ("≡", "nat_eqv"), ("⊡", "nat_canon"), ("∅ᶻ", "nat_isz"), ("⋚ʳ", "nat_cmpr"), ("⋚ⁱ", "nat_cmpi")];

// ------------------------------------------------------------------------------------ analysis
/// the number of leading lambdas, and the body below them
fn peel(c: &Core) -> (u32, &Core) {
    let mut n = 0;
    let mut cur = c;
    while let Core::L(b) = cur {
        n += 1;
        cur = b;
    }
    (n, cur)
}

/// is the definition a constructor λ f1..fn k1..km. kj f1..fn ?
fn classify(c: &Core) -> Kind {
    let (k, body) = peel(c);
    if k == 0 {
        return Kind::Caf;
    }
    let mut args: Vec<&Core> = vec![];
    let mut cur = body;
    while let Core::A(f, x) = cur {
        args.push(x);
        cur = f;
    }
    args.reverse();
    if let Core::V(idx) = cur {
        if *idx >= 1 && *idx <= k as usize {
            let q = k - *idx as u32;
            let nf = args.len() as u32;
            if nf <= q && args.iter().enumerate().all(|(i, a)| matches!(a, Core::V(j) if *j == (k as usize) - i)) {
                let m = k - nf;
                let j = q - nf;
                if nf >= 1 || m >= 2 {
                    return Kind::Con { nf, m, j, arity: k };
                }
            }
        }
    }
    Kind::Func(k)
}

fn c_string(s: &str) -> String {
    let mut r = String::from("\"");
    for b in s.bytes() {
        match b {
            b'"' => r.push_str("\\\""),
            b'\\' => r.push_str("\\\\"),
            0x20..=0x7e => r.push(b as char),
            _ => {
                let _ = write!(r, "\\{:03o}", b);
            }
        }
    }
    r.push('"');
    r
}

/// Core -> E, for a body below `depth` binders.  Unknown names become globals that fail.
fn build(t: &mut Table, c: &Core, depth: u32, pre: bool) -> E {
    match c {
        Core::V(i) => E::V(depth - *i as u32),
        Core::G(n) => match t.index.get(n) {
            Some(&g) => E::G(g),
            None => E::G(t.add(n, Kind::Host, pre)),
        },
        Core::L(_) => {
            let (k, body) = peel(c);
            let b = build(t, body, depth + k, pre);
            let f: Vec<u32> = fvs(&b).iter().copied().filter(|l| *l < depth).collect();
            E::Lam(k, Box::new(b), f)
        }
        Core::A(_, _) => {
            let mut args: Vec<&Core> = vec![];
            let mut cur = c;
            while let Core::A(f, x) = cur {
                args.push(x);
                cur = f;
            }
            args.reverse();
            let head = build(t, cur, depth, pre);
            let args: Vec<E> = args.into_iter().map(|a| build(t, a, depth, pre)).collect();
            let mut sets: Vec<&[u32]> = vec![fvs(&head)];
            for a in &args {
                sets.push(fvs(a));
            }
            let f = union(&sets);
            E::App(Box::new(head), args, f)
        }
    }
}



// ------------------------------------------------------------------------------------ inlining of small functions
/// the number of nodes of a term
fn esize(e: &E) -> usize {
    match e {
        E::V(_) | E::G(_) => 1,
        E::App(h, a, _) => 1 + esize(h) + a.iter().map(esize).sum::<usize>(),
        E::Lam(_, b, _) => 1 + esize(b),
    }
}

fn mentions(e: &E, g: usize) -> bool {
    match e {
        E::V(_) => false,
        E::G(x) => *x == g,
        E::App(h, a, _) => mentions(h, g) || a.iter().any(|x| mentions(x, g)),
        E::Lam(_, b, _) => mentions(b, g),
    }
}

/// how often the parameter p occurs, and whether it occurs under a lambda
fn occurrences(e: &E, p: u32, under: bool, n: &mut usize, lam: &mut bool) {
    match e {
        E::V(l) => {
            if *l == p {
                *n += 1;
                if under {
                    *lam = true;
                }
            }
        }
        E::G(_) => {}
        E::App(h, a, _) => {
            occurrences(h, p, under, n, lam);
            for x in a {
                occurrences(x, p, under, n, lam);
            }
        }
        E::Lam(_, b, _) => occurrences(b, p, true, n, lam),
    }
}

fn mk_app(h: E, args: Vec<E>) -> E {
    if args.is_empty() {
        return h;
    }
    let mut sets: Vec<&[u32]> = vec![fvs(&h)];
    for a in &args {
        sets.push(fvs(a));
    }
    let f = union(&sets);
    match h {
        E::App(h2, mut a2, _) => {
            // (f a) b  is  f a b
            a2.extend(args);
            mk_app(*h2, a2)
        }
        h => E::App(Box::new(h), args, f),
    }
}

/// is e at most `left` nodes big?
fn small(e: &E, left: &mut i32) -> bool {
    *left -= 1;
    if *left < 0 {
        return false;
    }
    match e {
        E::V(_) | E::G(_) => true,
        E::App(h, a, _) => small(h, left) && a.iter().all(|x| small(x, left)),
        E::Lam(_, b, _) => small(b, left),
    }
}

/// an atom: duplicating it costs nothing and loses no sharing.  A closed application is a shared constant (all copies of it become the same object), but only a
/// small one is copied freely: copies of a big one, made at every level of a nest of calls, make the term (and the work on it) grow exponentially with the nesting
fn is_atom(e: &E) -> bool {
    match e {
        E::V(_) | E::G(_) => true,
        E::App(_, _, f) | E::Lam(_, _, f) => f.is_empty() && small(e, &mut 12),
    }
}

/// an argument moved under `delta` more binders: the levels of the binders inside it (those from `from` up) move too; `o` is the number of binders around the term
fn shift(e: &E, from: u32, delta: u32, o: u32) -> E {
    if delta == 0 {
        return e.clone();
    }
    match e {
        E::V(l) => E::V(if *l >= from { *l + delta } else { *l }),
        E::G(g) => E::G(*g),
        E::App(h, a, _) => mk_app(shift(h, from, delta, o), a.iter().map(|x| shift(x, from, delta, o)).collect()),
        E::Lam(a, b, _) => {
            let nb = shift(b, from, delta, o + a);
            let f: Vec<u32> = fvs(&nb).iter().copied().filter(|l| *l < o + delta).collect();
            E::Lam(*a, Box::new(nb), f)
        }
    }
}

/// is inlining switched off (COMPIMO_NOINLINE)?  read once: the pass asks at every node
fn no_inline() -> bool {
    static F: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *F.get_or_init(|| std::env::var("COMPIMO_NOINLINE").is_ok())
}

/// the body of a callee (parameters at the levels 0..k-1, its own binders above) in a caller whose binder depth at the call is d, with the parameters replaced by
/// the arguments (which are final: they are not walked again) and the calls inside the body inlined in the same pass.  `cur` is the binder depth inside the body.
fn inline_body(body: &E, k: u32, params: &[E], d: u32, cur: u32, inl: &HashMap<usize, (u32, E)>, fuel: u32) -> E {
    match body {
        E::V(l) => {
            if *l < k {
                shift(&params[*l as usize], d, cur - k, d)
            } else {
                E::V(*l - k + d)
            }
        }
        E::G(g) => E::G(*g),
        E::App(h, a, _) => {
            let nh = inline_body(h, k, params, d, cur, inl, fuel);
            let nargs: Vec<E> = a.iter().map(|x| inline_body(x, k, params, d, cur, inl, fuel)).collect();
            try_inline(nh, nargs, cur - k + d, inl, fuel)
        }
        E::Lam(a, b, _) => {
            let nb = inline_body(b, k, params, d, cur + a, inl, fuel);
            let new_depth = cur - k + d;
            let f: Vec<u32> = fvs(&nb).iter().copied().filter(|l| *l < new_depth).collect();
            E::Lam(*a, Box::new(nb), f)
        }
    }
}

/// a call of a global with its (final) arguments, at binder depth `depth`: if the global is a small function whose parameters can be replaced without losing
/// sharing, its body takes the place of the call
fn try_inline(nh: E, nargs: Vec<E>, depth: u32, inl: &HashMap<usize, (u32, E)>, fuel: u32) -> E {
    if let E::G(g) = &nh {
        if fuel > 0 {
            if let Some((k, body)) = inl.get(g) {
                if nargs.len() as u32 >= *k {
                    let ok = (0..*k).all(|p| {
                        let (mut n, mut lam) = (0, false);
                        occurrences(body, p, false, &mut n, &mut lam);
                        is_atom(&nargs[p as usize]) || (n <= 1 && !lam)
                    });
                    if ok {
                        let r = inline_body(body, *k, &nargs[..*k as usize], depth, *k, inl, fuel - 1);
                        return mk_app(r, nargs[*k as usize..].to_vec());
                    }
                }
            }
        }
    }
    mk_app(nh, nargs)
}

/// inline calls of small functions, bottom-up; `depth` is the number of binders around e.  Every node is walked once (the cost is linear in the size of the result:
/// an earlier version walked the arguments again after each substitution, which is exponential in the depth of nested calls)
fn inline_pass(e: &E, inl: &HashMap<usize, (u32, E)>, depth: u32, fuel: u32) -> E {
    if no_inline() {
        return e.clone();
    }
    match e {
        E::V(_) | E::G(_) => e.clone(),
        E::Lam(a, b, _) => {
            let nb = inline_pass(b, inl, depth + a, fuel);
            let f: Vec<u32> = fvs(&nb).iter().copied().filter(|l| *l < depth).collect();
            E::Lam(*a, Box::new(nb), f)
        }
        E::App(h, args, _) => {
            let nh = inline_pass(h, inl, depth, fuel);
            let nargs: Vec<E> = args.iter().map(|x| inline_pass(x, inl, depth, fuel)).collect();
            try_inline(nh, nargs, depth, inl, fuel)
        }
    }
}

fn enc_core(c: &Core, out: &mut String) {
    match c {
        Core::V(i) => {
            let _ = write!(out, "v{};", i);
        }
        Core::G(n) => {
            let _ = write!(out, "g{}:{}", n.len(), n);
        }
        Core::L(b) => {
            out.push('l');
            enc_core(b, out);
        }
        Core::A(f, x) => {
            out.push('a');
            enc_core(f, out);
            enc_core(x, out);
        }
    }
}

fn dec_core(s: &[u8], pos: &mut usize) -> Core {
    let c = s[*pos];
    *pos += 1;
    match c {
        b'v' => {
            let st = *pos;
            while s[*pos] != b';' {
                *pos += 1;
            }
            let n: usize = std::str::from_utf8(&s[st..*pos]).unwrap().parse().unwrap();
            *pos += 1;
            Core::V(n)
        }
        b'g' => {
            let st = *pos;
            while s[*pos] != b':' {
                *pos += 1;
            }
            let len: usize = std::str::from_utf8(&s[st..*pos]).unwrap().parse().unwrap();
            *pos += 1;
            let name = String::from_utf8(s[*pos..*pos + len].to_vec()).unwrap();
            *pos += len;
            Core::G(name)
        }
        b'l' => Core::L(Box::new(dec_core(s, pos))),
        _ => {
            let f = dec_core(s, pos);
            let x = dec_core(s, pos);
            Core::A(Box::new(f), Box::new(x))
        }
    }
}

// ------------------------------------------------------------------------------------ the carry tables of the adder and the subtractor
/// `⌕′ ξ`, `⌕⁺ ξ`, `⌕⁻ ξ` of lib/number.imo are decision trees on the first digits of a tail ξ: `((⌃ ξ′) then else)` with ξ′ = ⌄ᵏ ξ, and the leaves `(◀ numeral)`.
/// They become C functions  int f(const uint8_t *t, int n, uint8_t *out)  (the tail t of n digits, least significant first; the result digits; their number).
fn spine<'c>(c: &'c Core) -> (&'c Core, Vec<&'c Core>) {
    let mut args = vec![];
    let mut cur = c;
    while let Core::A(f, x) = cur {
        args.push(&**x);
        cur = f;
    }
    args.reverse();
    (cur, args)
}

fn list_digits(c: &Core) -> Option<Vec<u8>> {
    // (∷ d (∷ d … ⊥)), the head is the least significant digit
    let mut v = vec![];
    let mut cur = c;
    loop {
        match cur {
            Core::G(n) if n == "⊥" || n == "⊘" => return Some(v),
            _ => {
                let (h, a) = spine(cur);
                match (h, a.as_slice()) {
                    (Core::G(n), [d, rest]) if n == "∷" => {
                        match d {
                            Core::G(b) if b == "⊤" => v.push(1),
                            Core::G(b) if b == "⊥" => v.push(0),
                            _ => return None,
                        }
                        cur = rest;
                    }
                    _ => return None,
                }
            }
        }
    }
}

fn carry_tree(c: &Core, out: &mut String) -> Option<()> {
    let (h, a) = spine(c);
    match (h, a.as_slice()) {
        (Core::G(n), [chain, then, els]) if n == "⌃" => {
            let mut k = 0;
            let mut cur = *chain;
            loop {
                match cur {
                    Core::V(1) => break,
                    Core::A(f, x) if matches!(&**f, Core::G(n) if n == "⌄") => {
                        k += 1;
                        cur = x;
                    }
                    _ => return None,
                }
            }
            let _ = write!(out, "if (D({})) {{ ", k);
            carry_tree(then, out)?;
            out.push_str(" } else { ");
            carry_tree(els, out)?;
            out.push_str(" }");
            Some(())
        }
        (Core::G(n), [pair]) if n == "◀" => {
            let (ph, pa) = spine(pair);
            match (ph, pa.as_slice()) {
                (Core::G(m), [digits, _den]) if m == "⊗" => {
                    let ds = list_digits(digits)?;
                    let body: Vec<String> = ds.iter().map(|d| d.to_string()).collect();
                    let _ = write!(out, "static const uint8_t r[] = {{{}}}; memcpy(out, r, {}); return {};", if body.is_empty() { "0".to_string() } else { body.join(",") }, ds.len(), ds.len());
                    Some(())
                }
                _ => None,
            }
        }
        _ => None,
    }
}

fn carry_function(cname: &str, c: Option<&Core>) -> String {
    let mut body = String::new();
    let ok = match c {
        Some(Core::L(b)) => carry_tree(b, &mut body).is_some(),
        _ => false,
    };
    if ok {
        format!("int {}(const uint8_t *t, int n, uint8_t *out) {{\n#define D(k) ((k) < n ? t[k] : 0)\n  {}\n#undef D\n}}\n", cname, body)
    } else {
        format!("int {}(const uint8_t *t, int n, uint8_t *out) {{ (void)t; (void)n; (void)out; return -1; }}\n", cname)
    }
}

// ------------------------------------------------------------------------------------ the emitter
struct Cx {
    names: HashMap<u32, String>,
}

struct Shard<'a> {
    t: &'a Table,
    pre: bool,                       // emitting the prelude (exported names) or a program
    decls: String,
    code: String,
    init: String,
    nk: usize,
    nl: usize,
    consts: HashMap<String, usize>,
    descs: HashMap<(u32, u32, u32), usize>,
    const_inits: Vec<String>,
    used_pre: std::collections::BTreeSet<usize>, // prelude functions called from here (to declare them)
}

impl<'a> Shard<'a> {
    fn new(t: &'a Table, pre: bool) -> Shard<'a> {
        Shard { t, pre, decls: String::new(), code: String::new(), init: String::new(), nk: 0, nl: 0, consts: HashMap::new(), descs: HashMap::new(), const_inits: vec![], used_pre: Default::default() }
    }

    fn desc(&mut self, nf: u32, m: u32, j: u32) -> usize {
        if let Some(&d) = self.descs.get(&(nf, m, j)) {
            return d;
        }
        let d = self.descs.len();
        self.descs.insert((nf, m, j), d);
        let _ = writeln!(self.decls, "static const Desc D{} = {{{}, {}, {}}};", d, nf, m, j);
        d
    }

    fn new_const(&mut self) -> usize {
        let k = self.nk;
        self.nk += 1;
        k
    }

    /// the C name of the function of a global
    fn fname(&mut self, g: usize) -> String {
        let i = &self.t.info[g];
        if i.pre {
            self.used_pre.insert(g);
            format!("p{}", i.idx)
        } else {
            format!("u{}", i.idx)
        }
    }

    /// the C expression for the object of a global
    fn gobj(&self, g: usize) -> String {
        let i = &self.t.info[g];
        if i.pre {
            format!("PG[{}]", i.idx)
        } else {
            format!("UG[{}]", i.idx)
        }
    }

    fn sig(k: u32) -> String {
        if k <= 6 {
            (0..k).map(|l| format!("V a{}", l)).collect::<Vec<_>>().join(", ")
        } else {
            "V *a".to_string()
        }
    }

    fn emit_global(&mut self, g: usize, body: &E) {
        let kind = self.t.info[g].kind.clone();
        let name = self.t.info[g].name.replace("*/", "* /");
        let obj = self.gobj(g);
        let storage = if self.t.info[g].pre { "" } else { "static " };
        match kind {
            Kind::Caf => {
                let mut cx = Cx { names: HashMap::new() };
                let e = self.strict(body, &mut cx, 0);
                let n = self.t.info[g].idx;
                let tag = if self.t.info[g].pre { "c" } else { "uc" };
                let _ = writeln!(self.decls, "static V {}{}(V *fv);", tag, n);
                let _ = writeln!(self.code, "/* {} */\nstatic V {}{}(V *fv) {{ (void)fv; return {}; }}", name, tag, n, e);
                let _ = writeln!(self.init, "  {} = rt_mkthunk({}{}, 0, NULL);", obj, tag, n);
            }
            Kind::Func(k) | Kind::Con { arity: k, .. } => {
                let mut cx = Cx { names: HashMap::new() };
                let direct = k <= 6;
                for l in 0..k {
                    cx.names.insert(l, if direct { format!("a{}", l) } else { format!("a[{}]", l) });
                }
                let e = self.strict(body, &mut cx, k);
                let f = self.fname(g);
                let sig = Self::sig(k);
                let prof = if self.t.info[g].pre { format!("PROF({}); ", self.t.info[g].idx) } else { String::new() };
                let native = if self.t.info[g].pre && k <= 6 { NATIVES.iter().find(|(n, _)| *n == self.t.info[g].name).map(|(_, c)| *c) } else { None };
                if let Some(nat) = native {
                    // the definition is compiled as q<i>; p<i> tries the native version first
                    let ps = (0..k).map(|l| format!("a{}", l)).collect::<Vec<_>>().join(", ");
                    let _ = writeln!(self.code, "/* {} */\nstatic V q{}({}) {{ return {}; }}", name, self.t.info[g].idx, sig, e);
                    let _ = writeln!(self.code, "V {}({}) {{ {}V r = {}({}); if (r) return r; return q{}({}); }}", f, sig, prof, nat, ps, self.t.info[g].idx, ps);
                } else {
                    let _ = writeln!(self.code, "/* {} */\n{}V {}({}) {{ {}return {}; }}", name, storage, f, sig, prof, e);
                }
                if !self.pre || true {
                    let _ = writeln!(self.decls, "{}V {}({});", if self.t.info[g].pre { "extern " } else { "static " }, f, sig);
                }
                let args = if direct { (0..k).map(|l| format!("a[{}]", l)).collect::<Vec<_>>().join(", ") } else { "a".to_string() };
                let en = format!("e{}{}", if self.t.info[g].pre { "p" } else { "u" }, self.t.info[g].idx);
                let _ = writeln!(self.decls, "static V {}(V *fv, V *a);", en);
                let _ = writeln!(self.code, "static V {}(V *fv, V *a) {{ (void)fv; return {}({}); }}", en, f, args);
                match kind {
                    Kind::Con { nf, m, j, .. } if nf == 0 => {
                        let d = self.desc(nf, m, j);
                        let _ = writeln!(self.init, "  {} = rt_data0(&D{});", obj, d);
                    }
                    _ => {
                        let _ = writeln!(self.init, "  {} = rt_mkclo({}, {}, 0, NULL);", obj, en, k);
                    }
                }
            }
            Kind::Host => {}
        }
        let _ = writeln!(self.init, "  rt_register({}, &{});", c_string(&self.t.info[g].name), obj);
    }

    // ------------------------------------------------------------------------------------ expressions
    /// a C expression for the weak head normal form of e
    fn strict(&mut self, e: &E, cx: &mut Cx, depth: u32) -> String {
        match e {
            E::V(l) => format!("EVAL({})", cx.names[l]),
            E::G(g) => match self.t.info[*g].kind {
                Kind::Func(_) | Kind::Con { .. } => self.gobj(*g),
                _ => format!("EVAL({})", self.gobj(*g)),
            },
            E::Lam(..) => self.lam(e, cx, depth),
            E::App(h, args, _) => self.app_strict(h, args, cx, depth),
        }
    }

    /// a C expression for a V that may be unevaluated
    fn lazy(&mut self, e: &E, cx: &mut Cx, depth: u32) -> String {
        match e {
            E::V(l) => cx.names[l].clone(),
            E::G(g) => self.gobj(*g),
            E::Lam(..) => self.lam(e, cx, depth),
            E::App(h, args, f) => {
                if let E::G(g) = &**h {
                    if let Kind::Con { nf, m, j, .. } = self.t.info[*g].kind {
                        if args.len() as u32 == nf {
                            return self.mkdata(nf, m, j, args, cx, depth, f.is_empty());
                        }
                    }
                }
                if f.is_empty() {
                    return self.constant(e, depth);
                }
                self.thunk(e, f, cx, depth)
            }
        }
    }

    fn mkdata(&mut self, nf: u32, m: u32, j: u32, args: &[E], cx: &mut Cx, depth: u32, closed: bool) -> String {
        let d = self.desc(nf, m, j);
        if closed {
            let key = format!("D{:?}", (d, args));
            if let Some(&k) = self.consts.get(&key) {
                return format!("K[{}]", k);
            }
            let fields: Vec<String> = args.iter().map(|a| self.lazy(a, cx, depth)).collect();
            let k = self.new_const();
            self.consts.insert(key, k);
            self.const_inits.push(format!("  K[{}] = rt_mkdata(&D{}, {}, (V[]){{{}}});\n", k, d, nf, fields.join(", ")));
            return format!("K[{}]", k);
        }
        let fields: Vec<String> = args.iter().map(|a| self.lazy(a, cx, depth)).collect();
        format!("rt_mkdata(&D{}, {}, (V[]){{{}}})", d, nf, fields.join(", "))
    }

    /// a shared object for a closed application: made once, at start-up
    fn constant(&mut self, e: &E, depth: u32) -> String {
        let key = format!("{:?}", e);
        if let Some(&k) = self.consts.get(&key) {
            return format!("K[{}]", k);
        }
        let n = self.nl;
        self.nl += 1;
        let mut cx = Cx { names: HashMap::new() };
        let body = self.strict(e, &mut cx, depth);
        let _ = writeln!(self.decls, "static V kc{}(V *fv);", n);
        let _ = writeln!(self.code, "static V kc{}(V *fv) {{ (void)fv; return {}; }}", n, body);
        let k = self.new_const();
        self.consts.insert(key, k);
        self.const_inits.push(format!("  K[{}] = rt_mkthunk(kc{}, 0, NULL);\n", k, n));
        format!("K[{}]", k)
    }

    fn thunk(&mut self, e: &E, f: &[u32], cx: &mut Cx, depth: u32) -> String {
        let (name, caps) = self.lift_thunk(e, f, cx, depth);
        format!("rt_mkthunk({}, {}, {})", name, caps.len(), if caps.is_empty() { "NULL".to_string() } else { format!("(V[]){{{}}}", caps.join(", ")) })
    }

    /// a lambda as a lifted C function: its name, the C expressions of the variables it captures, its arity
    fn lift_lam(&mut self, e: &E, cx: &mut Cx, depth: u32) -> (String, Vec<String>, u32) {
        if let E::Lam(k, body, f) = e {
            let n = self.nl;
            self.nl += 1;
            let mut inner = Cx { names: HashMap::new() };
            for (i, l) in f.iter().enumerate() {
                inner.names.insert(*l, format!("fv[{}]", i));
            }
            for p in 0..*k {
                inner.names.insert(depth + p, format!("a[{}]", p));
            }
            let b = self.strict(body, &mut inner, depth + k);
            let _ = writeln!(self.decls, "static V l{}(V *fv, V *a);", n);
            let _ = writeln!(self.code, "static V l{}(V *fv, V *a) {{ (void)fv; (void)a; return {}; }}", n, b);
            let caps: Vec<String> = f.iter().map(|l| cx.names[l].clone()).collect();
            return (format!("l{}", n), caps, *k);
        }
        unreachable!()
    }

    fn lam(&mut self, e: &E, cx: &mut Cx, depth: u32) -> String {
        let (name, caps, k) = self.lift_lam(e, cx, depth);
        if caps.is_empty() {
            let k2 = self.new_const();
            self.const_inits.push(format!("  K[{}] = rt_mkclo({}, {}, 0, NULL);\n", k2, name, k));
            return format!("K[{}]", k2);
        }
        format!("rt_mkclo({}, {}, {}, (V[]){{{}}})", name, k, caps.len(), caps.join(", "))
    }

    /// an expression as a lifted thunk function (it returns the value, evaluated): its name and the captured variables
    fn lift_thunk(&mut self, e: &E, f: &[u32], cx: &mut Cx, depth: u32) -> (String, Vec<String>) {
        let n = self.nl;
        self.nl += 1;
        let mut inner = Cx { names: HashMap::new() };
        for (i, l) in f.iter().enumerate() {
            inner.names.insert(*l, format!("fv[{}]", i));
        }
        let body = self.strict(e, &mut inner, depth);
        let _ = writeln!(self.decls, "static V t{}(V *fv);", n);
        let _ = writeln!(self.code, "static V t{}(V *fv) {{ (void)fv; return {}; }}", n, body);
        let caps: Vec<String> = f.iter().map(|l| cx.names[l].clone()).collect();
        (format!("t{}", n), caps)
    }

    /// a pattern match: the head is applied to alternatives.  If the head turns out to be data with as many alternatives, the one it selects is entered at
    /// once (no closure, no thunk, no generic application); otherwise the application is made as usual.
    fn try_case(&mut self, h: &E, args: &[E], cx: &mut Cx, depth: u32) -> Option<String> {
        static NOCASE: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
        if *NOCASE.get_or_init(|| std::env::var("COMPIMO_NOCASE").is_ok()) {
            return None;
        }
        let n = args.len();
        if n > 8 || (n == 1 && !matches!(args[0], E::Lam(..))) {
            return None;
        }
        let id = self.nl;
        self.nl += 1;
        let head = self.strict(h, cx, depth);
        let caps_arr = |caps: &Vec<String>| if caps.is_empty() { "NULL".to_string() } else { format!("(V[]){{{}}}", caps.join(", ")) };
        let mut arms = vec![];
        let mut fallbacks = vec![];
        for a in args {
            match a {
                E::Lam(..) => {
                    let (name, caps, k) = self.lift_lam(a, cx, depth);
                    arms.push((k, format!("{}({}, df)", name, caps_arr(&caps))));
                    fallbacks.push(if caps.is_empty() { format!("rt_mkclo({}, {}, 0, NULL)", name, k) } else { format!("rt_mkclo({}, {}, {}, {})", name, k, caps.len(), caps_arr(&caps)) });
                }
                E::V(_) | E::G(_) => {
                    arms.push((0, self.strict(a, cx, depth)));
                    fallbacks.push(self.lazy(a, cx, depth));
                }
                E::App(_, _, f) => {
                    let (name, caps) = self.lift_thunk(a, f, cx, depth);
                    arms.push((0, format!("{}({})", name, caps_arr(&caps))));
                    fallbacks.push(format!("rt_mkthunk({}, {}, {})", name, caps.len(), caps_arr(&caps)));
                }
            }
        }
        let mut s = String::new();
        let _ = write!(s, "({{ V s{id} = {head}; V r{id} = NULL; if (s{id}->h.tag == T_DATA) {{ const Desc *ds{id} = ((Data *)s{id})->d; V *df = ((Data *)s{id})->f; (void)df; if (ds{id}->m == {n}) {{ switch (ds{id}->j) {{", id = id, head = head, n = n);
        for (j, (k, call)) in arms.iter().enumerate() {
            let _ = write!(s, " case {}: if (ds{}->nf == {}) r{} = {}; break;", j, id, k, id, call);
        }
        let _ = write!(s, " }} }} }} if (!r{id}) r{id} = rt_apply(s{id}, {n}, (V[]){{{fb}}}); r{id}; }})", id = id, n = n, fb = fallbacks.join(", "));
        Some(s)
    }

    fn app_strict(&mut self, h: &E, args: &[E], cx: &mut Cx, depth: u32) -> String {
        let n = args.len() as u32;
        if let E::G(g) = h {
            let kind = self.t.info[*g].kind.clone();
            match kind {
                Kind::Func(k) | Kind::Con { arity: k, .. } if n >= k => {
                    let first: Vec<String> = args[..k as usize].iter().map(|a| self.lazy(a, cx, depth)).collect();
                    let f = self.fname(*g);
                    let call = if k <= 6 { format!("{}({})", f, first.join(", ")) } else { format!("{}((V[]){{{}}})", f, first.join(", ")) };
                    if n == k {
                        return call;
                    }
                    let rest: Vec<String> = args[k as usize..].iter().map(|a| self.lazy(a, cx, depth)).collect();
                    return format!("rt_apply({}, {}, (V[]){{{}}})", call, rest.len(), rest.join(", "));
                }
                Kind::Con { nf, m, j, .. } if n == nf => {
                    return self.mkdata(nf, m, j, args, cx, depth, false);
                }
                _ => {}
            }
        }
        if !matches!(h, E::G(_)) || matches!(h, E::G(g) if matches!(self.t.info[*g].kind, Kind::Caf | Kind::Host)) {
            if let Some(s) = self.try_case(h, args, cx, depth) {
                return s;
            }
        }
        let hs = match h {
            E::V(l) => cx.names[l].clone(),
            E::G(g) => self.gobj(*g),
            _ => self.lazy(h, cx, depth),
        };
        let a: Vec<String> = args.iter().map(|x| self.lazy(x, cx, depth)).collect();
        format!("rt_apply({}, {}, (V[]){{{}}})", hs, a.len(), a.join(", "))
    }

    /// the text of the translation unit
    fn finish(self, module: &str, nglobals: usize, split: bool) -> String {
        let mut out = String::new();
        out.push_str("/* generated by compimo */\n#include \"imo_rt.h\"\n#include <stdint.h>\n#ifndef IMO_NOGC\n#include <gc.h>\n#endif\n");
        out.push_str("extern V PG[];\nextern V UG[];\nvoid rt_register(const char *name, V *slot);\n");
        let _ = writeln!(out, "static V K[{}];", self.nk.max(1));
        for g in &self.used_pre {
            let i = &self.t.info[*g];
            if let Kind::Func(k) | Kind::Con { arity: k, .. } = i.kind {
                let _ = writeln!(out, "extern V p{}({});", i.idx, Self::sig(k));
            }
        }
        out.push_str(&self.decls);
        out.push_str(&self.code);
        let _ = writeln!(out, "void {}(void) {{", module);
        let _ = writeln!(out, "#ifndef IMO_NOGC\n  GC_add_roots((char *)K, (char *)(K + {}));\n#endif", self.nk.max(1));
        let _ = nglobals;
        out.push_str(&self.init);
        if split {
            // the constants (closed terms) are built by a second function, run after the globals of ALL shards exist: a constant may refer to a global
            // of a later shard (a list of values that are defined further down the library), and that slot is empty until its shard has run
            out.push_str("}\n");
            let _ = writeln!(out, "void {}_k(void) {{", module);
        }
        for s in &self.const_inits {
            out.push_str(s);
        }
        out.push_str("}\n");
        out
    }
}

// ------------------------------------------------------------------------------------ the two entry points
/// the prelude: C in `nshards` files, and the sidecar that tells programs what is in it
pub fn generate_prelude(defs: Vec<Def>, nshards: usize) -> (Vec<String>, String) {
    let mut t = Table::new();
    let mut cores: Vec<Core> = vec![];
    for d in defs {
        if let Some(c) = d.core {
            t.add(&d.name, classify(&c), true);
            cores.push(c);
        }
    }
    let mut carry = String::from("#include <stdint.h>\n#include <string.h>\n");
    for (name, cname) in [("⌕′", "imo_carry_p"), ("⌕⁺", "imo_carry_sp"), ("⌕⁻", "imo_carry_sm")] {
        let c = t.index.get(name).map(|&i| &cores[i]);
        carry.push_str(&carry_function(cname, c));
    }
    let mut bodies: Vec<E> = vec![];
    for c in &cores {
        let (arity, inner) = peel(c);
        bodies.push(build(&mut t, inner, arity, true));
    }
    // small functions are inlined at their call sites (a pattern match then needs no call)
    let mut inl: HashMap<usize, (u32, E)> = HashMap::new();
    for (g, b) in bodies.iter().enumerate() {
        if let Kind::Func(k) = t.info[g].kind {
            let limit: usize = std::env::var("COMPIMO_INL_LIMIT").ok().and_then(|s| s.parse().ok()).unwrap_or(usize::MAX);
            let lo: usize = std::env::var("COMPIMO_INL_LOW").ok().and_then(|s| s.parse().ok()).unwrap_or(0);
            let only: Option<Vec<usize>> = std::env::var("COMPIMO_INL_ONLY").ok().map(|s| s.split(',').filter_map(|x| x.parse().ok()).collect());
            if only.as_ref().map_or(true, |v| v.contains(&g)) && g >= lo && g < limit && k >= 1 && k <= 4 && esize(b) <= 16 && !mentions(b, g) && !NATIVES.iter().any(|(n, _)| *n == t.info[g].name) {
                inl.insert(g, (k, b.clone()));
            }
        }
    }
    let mut lines: Vec<(usize, String, u32, String)> = vec![];
    for (g, (k, _)) in &inl {
        let mut enc = String::new();
        enc_core(peel(&cores[*g]).1, &mut enc);
        lines.push((*g, t.info[*g].name.clone(), *k, enc));
    }
    lines.sort();
    t.inl_lines = lines.into_iter().map(|(_, n, k, e)| (n, k, e)).collect();
    for g in 0..bodies.len() {
        let arity = match t.info[g].kind {
            Kind::Func(k) | Kind::Con { arity: k, .. } => k,
            _ => 0,
        };
        let nb = inline_pass(&bodies[g], &inl, arity, 3);
        bodies[g] = nb;
    }
    let n = t.info.iter().filter(|i| i.pre).count();
    let per = (n + nshards - 1) / nshards.max(1);
    let mut files = vec![];
    let mut it = bodies.into_iter().enumerate().peekable();
    for s in 0..nshards {
        let mut sh = Shard::new(&t, true);
        let mut count = 0;
        while count < per {
            match it.next() {
                Some((g, b)) => {
                    sh.emit_global(g, &b);
                    count += 1;
                }
                None => break,
            }
        }
        if s + 1 == nshards {
            // names that the prelude uses and nothing defines: objects that fail
            for g in 0..t.info.len() {
                if t.info[g].pre && t.info[g].kind == Kind::Host {
                    let obj = sh.gobj(g);
                    let msg = format!("i-1: {} is not defined", t.info[g].name);
                    let _ = writeln!(sh.init, "  {} = rt_failobj(0, {});", obj, c_string(&msg));
                    let _ = writeln!(sh.init, "  rt_register({}, &{});", c_string(&t.info[g].name), obj);
                }
            }
        }
        files.push(sh.finish(&format!("imo_init_s{}", s), n, true));
    }
    // the prelude module: the table of the objects and the initialisation
    let mut m = String::from("/* generated by compimo: the prelude module */\n#include \"imo_rt.h\"\n");
    m.push_str("#ifdef IMO_PROF\nconst char *const imo_pnames[] = {\n");
    for i in t.info.iter().filter(|i| i.pre) {
        let _ = writeln!(m, "  {},", c_string(&i.name));
    }
    m.push_str("};\n#endif\n");
    let _ = writeln!(m, "V PG[{}];\nconst int imo_npre = {};", n.max(1), n);
    for s in 0..nshards {
        let _ = writeln!(m, "extern void imo_init_s{}(void);\nextern void imo_init_s{}_k(void);", s, s);
    }
    m.push_str("#ifndef IMO_NOGC\n#include <gc.h>\n#endif\nvoid imo_init_pre(void) {\n#ifndef IMO_NOGC\n  GC_add_roots((char *)PG, (char *)(PG + ");
    let _ = write!(m, "{}));\n#endif\n", n.max(1));
    for s in 0..nshards {
        let _ = writeln!(m, "  imo_init_s{}();", s);
    }
    for s in 0..nshards {
        let _ = writeln!(m, "  imo_init_s{}_k();", s);
    }
    m.push_str("}\n");
    files.push(m);
    files.push(carry);
    (files, t.sidecar())
}

/// a program, against a compiled prelude
pub fn generate_program(sidecar: &str, defs: Vec<Def>) -> String {
    let mut t = Table::from_sidecar(sidecar);
    let mut order: Vec<(usize, Core)> = vec![];
    let mut hostnames: Vec<usize> = vec![];
    for d in defs {
        match d.core {
            Some(c) => {
                let g = t.add(&d.name, classify(&c), false);
                order.push((g, c));
            }
            None => {
                let g = t.add(&d.name, Kind::Host, false);
                hostnames.push(g);
            }
        }
    }
    let mut inl: HashMap<usize, (u32, E)> = HashMap::new();
    let raw = std::mem::take(&mut t.inl_lines);
    for (name, k, enc) in &raw {
        if let Some(&g) = t.index.get(name) {
            if !t.info[g].pre {
                continue; // the program defines the name itself
            }
            let mut pos = 0;
            let core = dec_core(enc.as_bytes(), &mut pos);
            let e = build(&mut t, &core, *k, true);
            inl.insert(g, (*k, e));
        }
    }
    t.inl_lines = raw;
    let mut bodies: Vec<(usize, E)> = vec![];
    for (g, c) in &order {
        let (arity, inner) = peel(c);
        let b = build(&mut t, inner, arity, false);
        bodies.push((*g, inline_pass(&b, &inl, arity, 3)));
    }
    let mut sh = Shard::new(&t, false);
    for (g, b) in &bodies {
        sh.emit_global(*g, b);
    }
    // globals that fail: the unknowns of the program and the names that nothing defines
    let nuser = t.info.iter().filter(|i| !i.pre).count();
    for g in 0..t.info.len() {
        if !t.info[g].pre && t.info[g].kind == Kind::Host {
            let obj = sh.gobj(g);
            let msg = format!("i-1: {} is not defined", t.info[g].name);
            let _ = writeln!(sh.init, "  {} = rt_failobj(0, {});", obj, c_string(&msg));
            let _ = writeln!(sh.init, "  rt_register({}, &{});", c_string(&t.info[g].name), obj);
        }
    }
    sh.init = format!("#ifndef IMO_NOGC\n  GC_add_roots((char *)UG, (char *)(UG + {}));\n#endif\n{}", nuser.max(1), sh.init);
    let mut out = sh.finish("imo_init_usr", nuser, false);
    let _ = writeln!(out, "V UG[{}];\nconst int imo_nuser = {};", nuser.max(1), nuser);
    out
}
