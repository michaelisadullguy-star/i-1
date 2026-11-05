//! types.rs -- the class checker of i-1 (port of haskimo/src/I1/Types.hs and pymo/imotypes.py).
//!
//! Rules (all enforced here)
//!   * every symbol must be DECLARED  (name ∶ class)  before it is defined or used;
//!   * classes are terms:  atoms (ℕ ℤ ℚ ℝ ℤ[i] ℚ[i] ℝ[i] 𝔹 𝕮 𝕊 𝔻 …)  and constructors  (→ A B) (𝔏 A) (𝔖 A) (𝔗 A) (𝔄 A) (𝔓 A B);
//!   * a symbol may carry several declarations (overloads = an intersection of classes);
//!   * facts   (⊆ A B)  subclass,   (≣ A B)  class equation,   (↪ f)  f is a canonical (widening) coercion;
//!   * lambda binders must be annotated   (x ∶ A ↦ …);   definition parameters take their classes from the declaration;
//!   * numerals get the smallest class containing their value:  ℕ ⊆ ℤ ⊆ ℤ[i] ⊆ ℚ[i],  ℤ ⊆ ℚ ⊆ ℚ[i],  radix numerals are ℚ or ℚ[i];
//!   * 'trusted' files (the prelude) have their signatures recorded but their bodies are NOT checked.
//!
//! Statements (the class Prop, spec Ω): a user symbol that is declared and never defined is an UNKNOWN; STATEMENTS have class Ω and
//! are marked  Quote φ (classes of the variables bound outside φ); quote.rs writes φ as a code and the simplifier computes its
//! simplest form when it is evaluated.
//!
//! A class error is a value (`Err(String)` of `Check`), not an exception: the program is checked statement by statement and every
//! error is collected.
use crate::base::*;
use crate::bigint::Int;
use crate::syntax::*;
use std::collections::{BTreeMap, HashMap, HashSet};

pub type Check<T> = Result<T, String>;

/// the covariant class constructors
const COV: [&str; 4] = ["𝔏", "𝔖", "𝔗", "𝔓"];

pub const REL_R: [&str; 6] = ["≐ᴿ", "≠ᴿ", "≺ᴿ", "⩽ᴿ", "≻ᴿ", "⩾ᴿ"];

/// connectives on statements -> the connective their code uses
pub const CONN_O: [(&str, &str); 5] = [("∧Ω", "∧"), ("∨Ω", "∨"), ("¬Ω", "¬"), ("⇒Ω", "⇒"), ("⇔Ω", "⇔")];

pub fn is_conn_o(n: &str) -> bool {
    CONN_O.iter().any(|(a, _)| *a == n)
}

fn coercion_cost(name: &str) -> i32 {
    if name == "decide" {
        2
    } else {
        1
    }
}

/// the domains of unknowns: the first number class (in this order) that contains the declared class
const DOMAINS: [(&str, i64); 7] = [("ℕ", 6), ("ℤ", 5), ("ℚ", 3), ("ℤ[i]", 4), ("ℚ[i]", 2), ("ℝ", 1), ("ℝ[i]", 0)];

pub fn prop_ty() -> Ty {
    kk("Ω")
}
pub fn bool_ty() -> Ty {
    kk("𝔹")
}
pub fn num_ty() -> Ty {
    kk("ℚ[i]")
}

const ARROW: &str = "→";

// ---------------------------------------------------------------- the checker
#[derive(Clone)]
pub struct Checker {
    /// name -> arity
    pub classes: HashMap<String, usize>,
    /// symbols whose declared result is 𝒮
    pub formers: HashSet<String>,
    /// value symbol -> classes
    pub sigs: HashMap<String, Vec<Ty>>,
    /// (sub, super)
    pub facts: Vec<(Ty, Ty)>,
    /// normalised sub -> its supers, in order
    pub fact_idx: HashMap<Ty, Vec<Ty>>,
    /// atom -> class
    pub eqs: HashMap<String, Ty>,
    pub coercions: Vec<String>,
    /// the covariant class constructors: the built-in ones and those declared with (↗ C)
    pub cov: HashSet<String>,
    pub defined: HashSet<String>,
    /// human symbol -> spec symbols
    pub overloads: BTreeMap<String, Vec<String>>,
    /// unknown -> its domain code, in declaration order
    pub unknowns: Vec<(String, Option<i64>)>,
    pub user_defined: HashSet<String>,
    /// program symbols whose definitions mention an unknown (estimated before checking)
    pub raw_taint: HashSet<String>,
    /// program symbol -> does its checked body need the value of an unknown?
    pub taint: HashMap<String, bool>,
}

impl Checker {
    pub fn new() -> Checker {
        let mut classes = HashMap::new();
        classes.insert("→".to_string(), 2);
        classes.insert("𝒦".to_string(), 0);
        classes.insert("𝒮".to_string(), 0);
        Checker {
            classes,
            formers: HashSet::new(),
            sigs: HashMap::new(),
            facts: vec![],
            fact_idx: HashMap::new(),
            eqs: HashMap::new(),
            coercions: vec![],
            cov: COV.iter().map(|s| s.to_string()).collect(),
            defined: HashSet::new(),
            overloads: BTreeMap::new(),
            unknowns: vec![],
            user_defined: HashSet::new(),
            raw_taint: HashSet::new(),
            taint: HashMap::new(),
        }
    }

    // ------------------------------------------------------------ class terms
    pub fn term_to_type(t: &Term) -> Check<Ty> {
        match t {
            Term::Var(n) => Ok(if is_class_var(n) { Ty::V(n.clone()) } else { kk(n) }),
            Term::App(f, args) => match &**f {
                Term::Var(n) => Ok(Ty::K(n.clone(), args.iter().map(Checker::term_to_type).collect::<Check<Vec<_>>>()?)),
                _ => Err(format!("not a class expression: {}", repr_term(t))),
            },
            _ => Err(format!("not a class expression: {}", repr_term(t))),
        }
    }

    // ------------------------------------------------------------ classes
    pub fn norm(&self, t: &Ty) -> Ty {
        match t {
            Ty::K(n, a) if a.is_empty() => match self.eqs.get(n) {
                Some(e) => self.norm(e),
                None => t.clone(),
            },
            Ty::K(n, a) => Ty::K(n.clone(), a.iter().map(|x| self.norm(x)).collect()),
            _ => t.clone(),
        }
    }

    pub fn wf(&self, t: &Ty) -> Check<()> {
        match t {
            Ty::V(_) | Ty::F => Ok(()),
            Ty::K(name, args) => match self.classes.get(name) {
                None => Err(format!("undeclared class {}", name)),
                Some(&k) => {
                    if k != args.len() {
                        Err(format!("class {} takes {} argument(s), got {}", name, k, args.len()))
                    } else {
                        args.iter().try_for_each(|a| self.wf(a))
                    }
                }
            },
        }
    }

    pub fn leq(&self, a: &Ty, b: &Ty) -> bool {
        let mut seen: Vec<(Ty, Ty)> = vec![];
        self.leq_s(&mut seen, a, b)
    }

    fn leq_s(&self, seen: &mut Vec<(Ty, Ty)>, a0: &Ty, b0: &Ty) -> bool {
        let a = self.norm(a0);
        let b = self.norm(b0);
        if a == b || a == Ty::F {
            return true;
        }
        if let (Ty::K(n, xs), Ty::K(m, ys)) = (&a, &b) {
            if n == m && !xs.is_empty() && xs.len() == ys.len() {
                let s = if n == ARROW {
                    self.leq_s(seen, &ys[0], &xs[0]) && self.leq_s(seen, &xs[1], &ys[1])
                } else if self.cov.contains(n) {
                    xs.iter().zip(ys.iter()).all(|(x, y)| self.leq_s(seen, x, y))
                } else {
                    flex_eq(&a, &b)
                };
                if s {
                    return true;
                }
            }
        }
        if let Some(supers) = self.fact_idx.get(&a) {
            for y in supers {
                let key = (a.clone(), y.clone());
                if seen.contains(&key) {
                    continue;
                }
                seen.push(key);
                let r = self.leq_s(seen, y, &b);
                seen.pop();
                if r {
                    return true;
                }
            }
        }
        false
    }

    /// a and every class that contains it, by the declared subclass facts
    fn ups(&self, a: &Ty) -> Vec<Ty> {
        let mut todo: Vec<Ty> = vec![self.norm(a)];
        let mut out: Vec<Ty> = vec![];
        while let Some(x) = todo.pop() {
            if out.contains(&x) {
                continue;
            }
            if let Some(supers) = self.fact_idx.get(&x) {
                for y in supers {
                    todo.push(self.norm(y));
                }
            }
            out.push(x);
        }
        out
    }

    /// the least class containing both a and b (e.g. ℤ[i] and ℚ give ℚ[i]); None if there is none or it is not unique
    pub fn join(&self, a0: &Ty, b0: &Ty) -> Option<Ty> {
        let a = self.norm(a0);
        let b = self.norm(b0);
        if let (Ty::K(n, xs), Ty::K(m, ys)) = (&a, &b) {
            if n == m && self.cov.contains(n) && !xs.is_empty() && xs.len() == ys.len() {
                let mut js = vec![];
                for (x, y) in xs.iter().zip(ys.iter()) {
                    let j = if self.leq(y, x) {
                        Some(x.clone())
                    } else if self.leq(x, y) {
                        Some(y.clone())
                    } else {
                        self.join(x, y)
                    };
                    match j {
                        Some(j) => js.push(j),
                        None => return None,
                    }
                }
                return Some(Ty::K(n.clone(), js));
            }
        }
        let ub = self.ups(&b);
        let common: Vec<Ty> = self.ups(&a).into_iter().filter(|x| ub.contains(x)).collect();
        let least: Vec<&Ty> = common.iter().filter(|x| !common.iter().any(|d| d != *x && self.leq(d, x))).collect();
        if least.len() == 1 {
            Some(least[0].clone())
        } else {
            None
        }
    }

    // ------------------------------------------------------------ matching a pattern against an actual class
    fn do_match(&self, p0: &Ty, a0: &Ty, s: &Subst, mode: Mode) -> Option<Subst> {
        let p = self.norm(p0);
        let a = self.norm(a0);
        match &p {
            Ty::V(pn) => match s.get(pn) {
                Some(b) => {
                    if a == Ty::F {
                        Some(s.clone())
                    } else if *b == Ty::F {
                        Some(s.insert(pn, a.clone()))
                    } else if mode == Mode::Eq {
                        if flex_eq(b, &a) {
                            Some(s.clone())
                        } else {
                            None
                        }
                    } else if self.leq(&a, b) {
                        Some(s.clone())
                    } else if self.leq(b, &a) {
                        Some(if mode == Mode::Pos { s.insert(pn, a.clone()) } else { s.clone() })
                    } else if mode == Mode::Pos {
                        self.join(&a, b).map(|j| s.insert(pn, j))
                    } else {
                        None
                    }
                }
                None => Some(s.insert(pn, a.clone())),
            },
            _ => {
                if !has_var(&p) {
                    if a == Ty::F {
                        return Some(s.clone());
                    }
                    let ok = match mode {
                        Mode::Pos => self.leq(&a, &p),
                        Mode::Neg => self.leq(&p, &a),
                        Mode::Eq => flex_eq(&p, &a),
                    };
                    return if ok { Some(s.clone()) } else { None };
                }
                if a == Ty::F {
                    return Some(s.clone());
                }
                let structural = match (&p, &a) {
                    (Ty::K(pn, pas), Ty::K(an, aas)) if pn == an && pas.len() == aas.len() => {
                        let mut cur = Some(s.clone());
                        for (i, (pp, aa)) in pas.iter().zip(aas.iter()).enumerate() {
                            let m = if pn == ARROW {
                                if i == 0 {
                                    mode.flip()
                                } else {
                                    mode
                                }
                            } else if self.cov.contains(pn) {
                                mode
                            } else {
                                Mode::Eq
                            };
                            cur = cur.and_then(|c| self.do_match(pp, aa, &c, m));
                            if cur.is_none() {
                                break;
                            }
                        }
                        cur
                    }
                    _ => None,
                };
                if structural.is_some() {
                    return structural;
                }
                if mode == Mode::Pos {
                    if let Some(supers) = self.fact_idx.get(&a) {
                        for y in supers {
                            if let Some(r) = self.do_match(&p, y, s, mode) {
                                return Some(r);
                            }
                        }
                    }
                }
                None
            }
        }
    }

    /// the domain code of an unknown of class t: the first number class, in the order ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i], that contains t
    pub fn domain(&self, t0: &Ty) -> Option<i64> {
        let t = self.norm(t0);
        match &t {
            Ty::K(..) if !has_var(&t) => DOMAINS.iter().find(|(name, _)| self.classes.contains_key(*name) && self.leq(&t, &kk(name))).map(|(_, k)| *k),
            _ => None,
        }
    }

    /// is `name` an unknown, or a program symbol whose value needs the value of an unknown?
    pub fn unknownish(&self, name: &str) -> bool {
        if self.unknowns.iter().any(|(n, _)| n == name) {
            return true;
        }
        match self.taint.get(name) {
            Some(b) => *b,
            None => self.raw_taint.contains(name),
        }
    }

    /// does the (checked) term t mention an unknown (or a symbol that needs one) — outside quoted statements?
    pub fn mentions(&self, t: &Term, bound: &HashSet<String>) -> bool {
        match t {
            Term::Var(n) => !bound.contains(n) && self.unknownish(n),
            Term::App(f, args) => self.mentions(f, bound) || args.iter().any(|a| self.mentions(a, bound)),
            Term::Lam(ps, b) => {
                let mut bd = bound.clone();
                for (n, _) in ps {
                    bd.insert(n.clone());
                }
                self.mentions(b, &bd)
            }
            _ => false,
        }
    }

    pub fn is_prop(&self, t: &Ty) -> bool {
        self.norm(t) == prop_ty()
    }

    // ------------------------------------------------------------ declarations and facts
    pub fn declare(&mut self, name: &str, t: &Ty) -> Check<()> {
        let (ps, r) = chain(t);
        if r == kk("𝒦") {
            if ps.iter().any(|p| *p != kk("𝒦")) {
                return Err(format!("{}: a class constructor takes classes only", name));
            }
            self.classes.insert(name.to_string(), ps.len());
            Ok(())
        } else if r == kk("𝒮") {
            self.formers.insert(name.to_string());
            Ok(())
        } else {
            self.wf(t)?;
            let old = self.sigs.entry(name.to_string()).or_default();
            if !old.contains(t) {
                old.push(t.clone());
            }
            Ok(())
        }
    }

    fn reindex(&mut self) {
        let mut idx: HashMap<Ty, Vec<Ty>> = HashMap::new();
        for (x, y) in &self.facts {
            idx.entry(self.norm(x)).or_default().push(y.clone());
        }
        self.fact_idx = idx;
    }

    /// returns Err(Err) for the exceptions of the host, Ok(Err(msg)) for class errors
    fn fact(&mut self, term: &Term) -> R<Check<()>> {
        if let Term::App(f, args) = term {
            if let Term::Var(h) = &**f {
                if self.formers.contains(h) {
                    let arg = |i: usize| -> R<&Term> { args.get(i).ok_or_else(|| Err::Parse("Prelude.!!: index too large".to_string())) };
                    return match h.as_str() {
                        "⊆" | "≣" => {
                            let a0 = arg(0)?;
                            let b0 = arg(1)?;
                            let ab = Checker::term_to_type(a0).and_then(|a| Checker::term_to_type(b0).map(|b| (a, b)));
                            let (a, b) = match ab {
                                Ok(x) => x,
                                Err(e) => return Ok(Err(e)),
                            };
                            if let Err(e) = self.wf(&a).and_then(|_| self.wf(&b)) {
                                return Ok(Err(e));
                            }
                            if h == "⊆" {
                                self.facts.push((a, b));
                                self.reindex();
                                Ok(Ok(()))
                            } else {
                                match a {
                                    Ty::K(n, xs) if xs.is_empty() => {
                                        self.eqs.insert(n, b);
                                        self.reindex();
                                        Ok(Ok(()))
                                    }
                                    _ => parse_err("class equation: left side must be an atomic class"),
                                }
                            }
                        }
                        "↗" => match args.first() {
                            Some(Term::Var(n)) => {
                                if self.classes.get(n).copied().unwrap_or(0) >= 1 {
                                    self.cov.insert(n.clone());
                                    Ok(Ok(()))
                                } else {
                                    Ok(Err(format!("covariant: {} is not a class constructor", n)))
                                }
                            }
                            _ => Ok(Err("covariant:  is not a class constructor".to_string())),
                        },
                        "↪" => match args.first() {
                            Some(Term::Var(f)) => {
                                if self.sigs.contains_key(f) {
                                    self.coercions.push(f.clone());
                                    Ok(Ok(()))
                                } else {
                                    Ok(Err(format!("coercion {} is not declared", f)))
                                }
                            }
                            _ => Ok(Err("coercion  is not declared".to_string())),
                        },
                        _ => Ok(Err(format!("unknown statement {}", h))),
                    };
                }
            }
        }
        Ok(Err(format!("not a declared statement: {}", repr_term(term))))
    }

    // ------------------------------------------------------------ terms
    /// candidate (symbol, class) pairs for a head symbol
    fn entries_for(&self, hd: &str) -> Check<Vec<(String, Ty)>> {
        let default = vec![hd.to_string()];
        let names = self.overloads.get(hd).unwrap_or(&default);
        let mut out = vec![];
        for n in names {
            match self.sigs.get(n) {
                None => return Err(format!("undeclared symbol {}", n)),
                Some(es) => {
                    for e in es {
                        out.push((n.clone(), e.clone()));
                    }
                }
            }
        }
        Ok(out)
    }

    /// apply a class `entry` to args [(class, term)].  -> (result class, new args, cost) or None
    fn try_apply(&self, entry: &Ty, args: &[(Ty, Term)]) -> Option<(Ty, Vec<Term>, i32)> {
        let mut t = entry.clone();
        let mut s = Subst::new();
        let mut cost = 0;
        let mut new: Vec<Term> = vec![];
        for (a_ty, term) in args {
            match self.norm(&t) {
                Ty::K(n, ps) if n == ARROW && ps.len() == 2 => {
                    let (p, r) = (&ps[0], &ps[1]);
                    match self.do_match(p, a_ty, &s, Mode::Pos) {
                        Some(s2) => {
                            s = s2;
                            new.push(term.clone());
                        }
                        None => match self.best_coercion(p, a_ty, &s) {
                            None => return None,
                            Some((cname, s1)) => {
                                s = s1;
                                cost += coercion_cost(&cname);
                                new.push(Term::App(Box::new(var(&cname)), vec![term.clone()]));
                            }
                        },
                    }
                    t = r.clone();
                }
                _ => return None,
            }
        }
        Some((subst(&t, &s, true), new, cost))
    }

    fn best_coercion(&self, p: &Ty, a_ty: &Ty, s: &Subst) -> Option<(String, Subst)> {
        let mut best: Option<(String, Ty, Subst)> = None;
        for cn in &self.coercions {
            for ce in self.sigs.get(cn).map(|v| v.as_slice()).unwrap_or(&[]) {
                let (cps, cr) = chain(ce);
                if cps.len() != 1 || !self.leq(a_ty, &cps[0]) {
                    continue;
                }
                if let Some(s1) = self.do_match(p, &subst(&cr, &Subst::new(), false), s, Mode::Pos) {
                    best = match best {
                        None => Some((cn.clone(), cr, s1)),
                        Some(b) => {
                            if self.leq(&cr, &b.1) {
                                Some((cn.clone(), cr, s1))
                            } else {
                                Some(b)
                            }
                        }
                    };
                }
            }
        }
        best.map(|(cn, _, s1)| (cn, s1))
    }

    fn resolve_app(&self, hd: &str, args: &[(Ty, Term)], label: &str) -> Check<(String, Ty, Vec<Term>)> {
        let ents = self.entries_for(hd)?;
        let mut cands: Vec<(String, Ty, (Ty, Vec<Term>, i32))> = vec![];
        for (name, entry) in &ents {
            if let Some(r) = self.try_apply(entry, args) {
                cands.push((name.clone(), entry.clone(), r));
            }
        }
        if cands.is_empty() {
            return Err(format!(
                "no declaration of {} accepts ({});  candidates: {}",
                label,
                comma_sep(&args.iter().map(|a| show_type(&a.0)).collect::<Vec<_>>()),
                comma_sep(&ents.iter().map(|(n, e)| format!("{} ∶ {}", n, show_type(e))).collect::<Vec<_>>())
            ));
        }
        let mn = cands.iter().map(|c| (c.2).2).min().unwrap();
        let cands2: Vec<&(String, Ty, (Ty, Vec<Term>, i32))> = cands.iter().filter(|c| (c.2).2 == mn).collect();
        let more_specific = |x: &(String, Ty, (Ty, Vec<Term>, i32)), y: &(String, Ty, (Ty, Vec<Term>, i32))| -> bool {
            let (p1, _) = chain(&x.1);
            let (p2, _) = chain(&y.1);
            let n = args.len().min(p1.len()).min(p2.len());
            p1.iter().take(n).zip(p2.iter().take(n)).all(|(a, b)| self.leq(a, b))
        };
        let best: Vec<&&(String, Ty, (Ty, Vec<Term>, i32))> = cands2.iter().filter(|x| cands2.iter().all(|y| more_specific(x, y))).collect();
        let pool: Vec<&(String, Ty, (Ty, Vec<Term>, i32))> = if best.is_empty() { cands2.clone() } else { best.iter().map(|x| **x).collect() };
        if best.len() != 1 {
            let mut sigs: Vec<(String, Ty)> = vec![];
            for c in &pool {
                let s = (c.0.clone(), (c.2).0.clone());
                if !sigs.contains(&s) {
                    sigs.push(s);
                }
            }
            if sigs.len() != 1 {
                return Err(format!(
                    "ambiguous use of {}: {}",
                    label,
                    semi_sep(&cands2.iter().map(|c| format!("{} ∶ {}", c.0, show_type(&c.1))).collect::<Vec<_>>())
                ));
            }
        }
        let (name, _, (rt, new, _)) = pool[0].clone();
        Ok((name, rt, new))
    }

    pub fn synth(&self, loc: &Loc, t: &Term) -> Check<(Ty, Term)> {
        match t {
            Term::Num(s) => Ok((num_class(s), t.clone())),
            Term::Chr(_) => Ok((kk("𝕮"), t.clone())),
            Term::Str(_) => Ok((kk("𝕊"), t.clone())),
            Term::Var(n) => match loc_lookup(loc, n) {
                Some(ty) => Ok((ty.clone(), t.clone())),
                None => {
                    let ents = self.entries_for(n)?;
                    if ents.len() == 1 {
                        let (name, e) = &ents[0];
                        Ok((subst(e, &Subst::new(), true), var(name)))
                    } else {
                        Err(format!("{} is overloaded ({} declarations): use it applied to arguments", n, ents.len()))
                    }
                }
            },
            Term::Asc(e, ty) => {
                self.wf(ty)?;
                let (got, term) = self.synth(loc, e)?;
                match self.fit(&term, &got, ty) {
                    Some(fixed) => Ok((ty.clone(), fixed)),
                    None => Err(format!("ascription: a term of class {} is not in {}", show_type(&got), show_type(ty))),
                }
            }
            Term::Lam(ps, body) => {
                let mut loc2 = loc.clone();
                let mut ptys = vec![];
                for (n, mty) in ps {
                    match mty {
                        None => return Err(format!("binder {} has no class: write ({} ∶ class ↦ …)", n, n)),
                        Some(ty) => {
                            self.wf(ty)?;
                            loc_insert(&mut loc2, n, ty.clone());
                            ptys.push(ty.clone());
                        }
                    }
                }
                let (rt, body2) = self.synth(&loc2, body)?;
                Ok((mk_chain(&ptys, rt), Term::Lam(ps.clone(), Box::new(body2))))
            }
            Term::Quote(..) => Ok((prop_ty(), t.clone())),
            Term::App(f, as_) => {
                let args = as_.iter().map(|a| self.synth(loc, a)).collect::<Check<Vec<_>>>()?;
                match &**f {
                    Term::Var(h) if !loc_member(loc, h) => match self.resolve_app(h, &args, h) {
                        Err(e) => match self.join_list(loc, t)? {
                            None => Err(e),
                            Some(j) => Ok(j),
                        },
                        Ok((name, rt, new)) => Ok(self.statement(loc, &name, rt, new)),
                    },
                    _ => {
                        let (ft, fterm) = self.synth(loc, f)?;
                        match self.try_apply(&ft, &args) {
                            None => Err(format!(
                                "cannot apply a function of class {} to ({})",
                                show_type(&ft),
                                comma_sep(&args.iter().map(|a| show_type(&a.0)).collect::<Vec<_>>())
                            )),
                            Some((r, new, _)) => Ok((r, Term::App(Box::new(fterm), new))),
                        }
                    }
                }
            }
        }
    }

    /// the checked application (name new…) of class rt — marked as a quoted statement (class Ω) when it is one
    fn statement(&self, loc: &Loc, name: &str, rt: Ty, new: Vec<Term>) -> (Ty, Term) {
        let app_t = Term::App(Box::new(var(name)), new.clone());
        let bound: HashSet<String> = loc_names(loc).into_iter().collect();
        let r = self.norm(&rt);
        if REL_R.contains(&name) && new.len() == 2 {
            return (prop_ty(), Term::Quote(Box::new(app_t), loc.clone()));
        }
        if is_conn_o(name) && self.is_prop(&rt) {
            return (prop_ty(), Term::Quote(Box::new(app_t), loc.clone()));
        }
        if (r == prop_ty() || r == bool_ty()) && new.iter().any(|a| self.mentions(a, &bound)) {
            return (prop_ty(), Term::Quote(Box::new(app_t), loc.clone()));
        }
        (rt, app_t)
    }

    /// a cons chain (a list literal) whose elements are truth values and statements is a list of statements: the truth values are
    /// made statements (prop).  None when that is not the case.
    fn join_list(&self, loc: &Loc, t: &Term) -> Check<Option<(Ty, Term)>> {
        // collect the chain
        let mut items: Vec<&Term> = vec![];
        let mut tl = t;
        loop {
            match tl {
                Term::App(f, xs) if xs.len() == 2 => match &**f {
                    Term::Var(h) if (h == "∷" || h == "hum:cons") && !loc_member(loc, h) => {
                        items.push(&xs[0]);
                        tl = &xs[1];
                    }
                    _ => break,
                },
                _ => break,
            }
        }
        if items.is_empty() || !self.sigs.contains_key("∷") {
            return Ok(None);
        }
        let mut el = vec![];
        for x in &items {
            el.push(self.synth(loc, x)?);
        }
        let (tc, tt) = self.synth(loc, tl)?;
        let list_prop = Ty::K("𝔏".to_string(), vec![prop_ty()]);
        if !(el.iter().any(|(c, _)| self.is_prop(c)) || self.norm(&tc) == list_prop) || !self.leq(&tc, &list_prop) {
            return Ok(None);
        }
        // build from the last element outwards
        let mut out = tt;
        for (cl, x) in el.into_iter().rev() {
            if self.is_prop(&cl) {
                out = Term::App(Box::new(var("∷")), vec![x, out]);
            } else if self.leq(&cl, &bool_ty()) {
                out = Term::App(Box::new(var("∷")), vec![Term::App(Box::new(var("prop")), vec![x]), out]);
            } else {
                return Ok(None);
            }
        }
        Ok(Some((list_prop, out)))
    }

    /// term (of class got) made to fit the class want: as it is, through one coercion, element by element for a list or pair
    /// literal, or — for a λ — by fitting its body.  None when it does not fit.
    pub fn fit(&self, term: &Term, got: &Ty, want: &Ty) -> Option<Term> {
        if self.leq(got, want) {
            return Some(term.clone());
        }
        let g = self.norm(got);
        let w = self.norm(want);
        // through one coercion
        let mut via: Option<Term> = None;
        for cn in &self.coercions {
            for ce in self.sigs.get(cn).map(|v| v.as_slice()).unwrap_or(&[]) {
                let (cps, cr) = chain(ce);
                if cps.len() == 1 && self.leq(got, &cps[0]) && self.leq(&cr, want) {
                    via = Some(Term::App(Box::new(var(cn)), vec![term.clone()]));
                }
            }
        }
        if via.is_some() {
            return via;
        }
        if *term == var("⊘") {
            if let Ty::K(n, _) = &w {
                if n == "𝔏" {
                    return Some(term.clone());
                }
            }
        }
        // a list or pair literal, element by element
        if let (Term::App(f, ab), Ty::K(gn, gargs), Ty::K(wn, wargs)) = (term, &g, &w) {
            if let (Term::Var(h), true) = (&**f, ab.len() == 2) {
                if gn == wn {
                    if h == "∷" && gn == "𝔏" {
                        if let Some(h2) = self.fit(&ab[0], &gargs[0], &wargs[0]) {
                            if let Some(t2) = self.fit(&ab[1], got, want) {
                                return Some(Term::App(Box::new(var("∷")), vec![h2, t2]));
                            }
                        }
                    }
                    if h == "⊗" && gn == "𝔓" {
                        if let Some(x) = self.fit(&ab[0], &gargs[0], &wargs[0]) {
                            if let Some(y) = self.fit(&ab[1], &gargs[1], &wargs[1]) {
                                return Some(Term::App(Box::new(var("⊗")), vec![x, y]));
                            }
                        }
                    }
                }
            }
        }
        // a lambda: fit its body
        if let Term::Lam(ps, b) = term {
            let n = ps.len();
            let (pg, rg) = chain(&g);
            let (pw, rw) = chain(&w);
            if pg.len() >= n && pw.len() >= n && pg.iter().take(n).zip(pw.iter().take(n)).all(|(x, y)| self.leq(y, x)) {
                let rest_g = mk_chain(&pg[n..], rg);
                let rest_w = mk_chain(&pw[n..], rw);
                return self.fit(b, &rest_g, &rest_w).map(|nb| Term::Lam(ps.clone(), Box::new(nb)));
            }
        }
        None
    }

    /// after checking: which program symbols need the value of an unknown (the least fixed point over their checked bodies)
    pub fn settle_taint(&mut self, defs: &[(String, Vec<String>, Term)]) {
        self.taint = defs.iter().map(|(n, _, _)| (n.clone(), false)).collect();
        loop {
            let mut changed = false;
            for (n, ps, body) in defs {
                if !self.taint.get(n).copied().unwrap_or(false) {
                    let bound: HashSet<String> = ps.iter().cloned().collect();
                    if self.mentions(body, &bound) {
                        self.taint.insert(n.clone(), true);
                        changed = true;
                    }
                }
            }
            if !changed {
                break;
            }
        }
    }

    // ------------------------------------------------------------ statements
    /// check one statement; the checker keeps the effects it has before an error (as Python's checker does) and the resolved
    /// statement or the class error is returned (None: the statement is as it was written).  `Err` is an exception of the host.
    pub fn check_statement(&mut self, st: &Stmt, trusted: bool) -> R<Check<Option<Stmt>>> {
        match st {
            Stmt::Decl(name, ty) => {
                if let Err(e) = self.declare(name, ty) {
                    return Ok(Err(e));
                }
                if !trusted && self.unknowns.iter().any(|(n, _)| n == name) {
                    if self.sigs.get(name).map_or(0, |v| v.len()) > 1 {
                        return Ok(Err(format!("{} is declared but never defined, so it is an unknown, and an unknown has one class", name)));
                    }
                    return Ok(match self.domain(ty) {
                        None => Err(format!(
                            "{} is declared but never defined, so it is an unknown; an unknown must be a number (a class below ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i] — human \\NN \\ZZ \\QQ \\Z \\Q \\RR \\CC), not {}",
                            name,
                            show_type(ty)
                        )),
                        Some(k) => {
                            for u in self.unknowns.iter_mut() {
                                if u.0 == *name {
                                    u.1 = Some(k);
                                }
                            }
                            Ok(None)
                        }
                    });
                }
                Ok(Ok(None))
            }
            Stmt::Fact(t) => match self.fact(t)? {
                Err(e) => Ok(Err(e)),
                Ok(()) => Ok(Ok(None)),
            },
            Stmt::Def(name, params, body) => {
                if self.defined.contains(name) {
                    return Ok(Err(format!("{} is defined twice", name)));
                }
                if !self.sigs.contains_key(name) {
                    return Ok(Err(format!("{} is defined before it is declared:  write  {} ∶ <class>  first", name, name)));
                }
                self.defined.insert(name.clone());
                if trusted {
                    return Ok(Ok(None));
                }
                let entries = self.sigs.get(name).cloned().unwrap_or_default();
                let mut out: Option<Option<Stmt>> = None;
                for entry in &entries {
                    match self.check_entry(name, params, body, entry) {
                        Err(e) => return Ok(Err(e)),
                        Ok(newbody) => {
                            if out.is_none() {
                                let bound: HashSet<String> = params.iter().cloned().collect();
                                let t = self.mentions(&newbody, &bound);
                                self.taint.insert(name.clone(), t);
                                out = Some(Some(Stmt::Def(name.clone(), params.clone(), newbody)));
                            }
                        }
                    }
                }
                Ok(match out {
                    Some(s) => Ok(s),
                    None => Err("no declaration".to_string()),
                })
            }
        }
    }

    fn check_entry(&self, name: &str, params: &[String], body: &Term, entry: &Ty) -> Check<Term> {
        let (ps, r) = chain(entry);
        if params.len() > ps.len() {
            return Err(format!(
                "{} has {} parameters but its class {} has only {}",
                name,
                params.len(),
                show_type(entry),
                ps.len()
            ));
        }
        let mut loc: Loc = vec![];
        for (i, p) in params.iter().enumerate() {
            loc_insert(&mut loc, p, ps[i].clone());
        }
        let want = mk_chain(&ps[params.len()..], r);
        let (got, newbody) = self.synth(&loc, body)?;
        match self.fit(&newbody, &got, &want) {
            None => Err(format!("{}: the body has class {} but {} was declared", name, show_type(&got), show_type(&want))),
            Some(fixed) => Ok(fixed),
        }
    }
}

// ---------------------------------------------------------------- substitutions of class variables
#[derive(Clone, Copy, PartialEq, Eq)]
enum Mode {
    Pos,
    Neg,
    Eq,
}

impl Mode {
    fn flip(self) -> Mode {
        match self {
            Mode::Pos => Mode::Neg,
            Mode::Neg => Mode::Pos,
            Mode::Eq => Mode::Eq,
        }
    }
}

/// class variable -> class, small and persistent (cloned on change)
#[derive(Clone, Default)]
struct Subst(Vec<(String, Ty)>);

impl Subst {
    fn new() -> Subst {
        Subst(vec![])
    }
    fn get(&self, n: &str) -> Option<&Ty> {
        self.0.iter().find(|e| e.0 == n).map(|e| &e.1)
    }
    fn insert(&self, n: &str, t: Ty) -> Subst {
        let mut v = self.0.clone();
        match v.iter_mut().find(|e| e.0 == n) {
            Some(e) => e.1 = t,
            None => v.push((n.to_string(), t)),
        }
        Subst(v)
    }
}

pub fn chain(t: &Ty) -> (Vec<Ty>, Ty) {
    let mut ps = vec![];
    let mut cur = t;
    loop {
        match cur {
            Ty::K(n, a) if n == ARROW && a.len() == 2 => {
                ps.push(a[0].clone());
                cur = &a[1];
            }
            _ => return (ps, cur.clone()),
        }
    }
}

pub fn mk_chain(ps: &[Ty], r: Ty) -> Ty {
    let mut out = r;
    for p in ps.iter().rev() {
        out = Ty::K(ARROW.to_string(), vec![p.clone(), out]);
    }
    out
}

/// the same class, where the flexible class ⊥ (an unconstrained polymorphic constant, e.g. emptydict ∶ Dict α) equals anything
pub fn flex_eq(x: &Ty, y: &Ty) -> bool {
    if x == y || *x == Ty::F || *y == Ty::F {
        return true;
    }
    match (x, y) {
        (Ty::K(n, xs), Ty::K(m, ys)) => n == m && xs.len() == ys.len() && xs.iter().zip(ys.iter()).all(|(p, q)| flex_eq(p, q)),
        _ => false,
    }
}

pub fn has_var(t: &Ty) -> bool {
    match t {
        Ty::V(_) => true,
        Ty::K(_, a) => a.iter().any(has_var),
        Ty::F => false,
    }
}

/// substitute class variables; with flex, the unbound ones become the flexible class ⊥
fn subst(t: &Ty, s: &Subst, flex: bool) -> Ty {
    match t {
        Ty::V(n) => match s.get(n) {
            Some(r) => r.clone(),
            None => {
                if flex {
                    Ty::F
                } else {
                    t.clone()
                }
            }
        },
        Ty::K(n, a) => Ty::K(n.clone(), a.iter().map(|x| subst(x, s, flex)).collect()),
        Ty::F => Ty::F,
    }
}

fn comma_sep(xs: &[String]) -> String {
    xs.join(", ")
}

fn semi_sep(xs: &[String]) -> String {
    xs.join("; ")
}

/// the smallest class containing the value of a numeral written in base i-1
pub fn num_class(text: &str) -> Ty {
    let (bits, k) = match text.split_once('.') {
        None => (text.to_string(), 0usize),
        Some((a, b)) => (format!("{}{}", a, b), b.chars().count()),
    };
    let digits: Vec<u8> = bits.chars().rev().map(|c| if c == '1' { 1 } else { 0 }).collect();
    let z = val_digits(&digits);
    // den = b^k, n = |den|^2 = 2^k
    let mut den: GI = (Int::from_i64(1), Int::zero());
    for _ in 0..k {
        den = (den.0.add(&den.1).neg(), den.0.sub(&den.1));
    }
    let n = den.0.mul(&den.0).add(&den.1.mul(&den.1));
    let re_num = z.0.mul(&den.0).add(&z.1.mul(&den.1));
    let im_num = z.1.mul(&den.0).sub(&z.0.mul(&den.1));
    let divisible = |x: &Int| x.divrem(&n).1.is_zero();
    if im_num.is_zero() {
        if divisible(&re_num) {
            if !re_num.is_neg() {
                kk("ℕ")
            } else {
                kk("ℤ")
            }
        } else {
            kk("ℚ")
        }
    } else if divisible(&re_num) && divisible(&im_num) {
        kk("ℤ[i]")
    } else {
        kk("ℚ[i]")
    }
}

#[allow(dead_code)]
fn _keep(_: &Int) {}
