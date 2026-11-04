//! quote.rs -- the compiler side of statements (port of haskimo/src/I1/Quote.hs and pymo/quote.py).  A statement — a relation on ℝ[i],
//! a relation or predicate about an unknown, a connective with a statement operand (types.rs marks them Quote φ …) — is simplified
//! from DEFINITIONS whenever it is evaluated or output, so its checked term φ is replaced by a term that builds φ's CODE at run time:
//!
//!     numeral / Char / String / closed number or Boolean     (𝔮ⁿ value)       — decided directly (a subset of ℚ[i] or 𝔹)
//!     symbol                                                (𝔮ˢ code)        — its doc 1 code (a numeral; a local code for the program's own symbols)
//!     unknown x (declared, never defined)                   (𝔮ˢ code of x)   — program-local codes, numbered in DECLARATION order
//!     application, λ, bound variable                        (𝔮ᵃ f a) (𝔮ˡ b) (𝔮ᵛ k)   — de Bruijn indices
//!     a variable bound outside φ, not a number              (𝔮ᵛ k) with k beyond φ's binders: an unknown, the same for every use
//!     a variable bound outside φ, of class Ω                its value (a statement IS its code)
//!     prop b, decide φ, ∧Ω ∨Ω ¬Ω ⇒Ω ⇔Ω                       transparent: the code of b or φ, and the plain connectives ∧ ∨ ¬ ⇒ ⇔
//!
//! and the statement becomes  (simplify′ ε⌜⌝ ⌜φ⌝)  where  ε⌜⌝  is one table, for the whole program, of (code, ⌜definition⌝).
//! Nothing is decided here: this is a spelling of terms as numbers, like the reader's expansion of numerals.
use crate::base::*;
use crate::layers::Doc1;
use crate::syntax::*;
use crate::types::*;
use std::collections::{HashMap, HashSet};

const UNFOLD: [&str; 7] = ["exp", "sin", "cos", "sinh", "cosh", "log", "atan"];

/// the name of the table of definitions
pub const ENV_NAME: &str = "ε⌜⌝";

const TRANSPARENT: [&str; 3] = ["prop", "decide", "code_rd"];

pub struct Quoter<'a> {
    c: &'a Checker,
    /// program symbol -> (params, body, declared class)
    defs: HashMap<String, (Vec<String>, Term, Ty)>,
    /// prelude symbol -> (params, body)
    prelude: HashMap<String, (Vec<String>, Term)>,
    unknowns: Vec<(String, i64)>,
    /// definitions that contain a statement
    stmt: HashSet<String>,
}

/// state: the doc 1 table (codes are given in order of first use) and the symbols whose definitions go into the table
pub struct QS {
    pub doc: Doc1,
    pub needed: Vec<String>,
}

fn digits(text: &str) -> Term {
    app("↓ᶻ", vec![Term::Num(text.to_string())])
}

fn nat(k: usize) -> Term {
    digits(&numeral(&to_digits(&(crate::bigint::Int::from_u64(k as u64), crate::bigint::Int::zero()))))
}

pub fn has_quote(t: &Term) -> bool {
    match t {
        Term::Quote(..) => true,
        Term::App(f, args) => has_quote(f) || args.iter().any(has_quote),
        Term::Lam(_, b) => has_quote(b),
        _ => false,
    }
}

/// statements of the program, resolved: (trusted, resolved statement)
pub fn mk_quoter<'a>(c: &'a Checker, sts: &[(bool, Option<&Stmt>)], d0: &Doc1) -> R<(Quoter<'a>, Doc1)> {
    let mut defs = HashMap::new();
    let mut prelude = HashMap::new();
    for (trusted, st) in sts {
        if let Some(Stmt::Def(n, ps, b)) = *st {
            if !*trusted {
                let cls = c.sigs.get(n).and_then(|v| v.first().cloned()).unwrap_or_else(|| kk("?"));
                defs.insert(n.clone(), (ps.clone(), b.clone(), cls));
            } else if UNFOLD.contains(&n.as_str()) {
                prelude.insert(n.clone(), (ps.clone(), b.clone()));
            }
        }
    }
    let unknowns: Vec<(String, i64)> = c.unknowns.iter().filter_map(|(n, k)| k.map(|k| (n.clone(), k))).collect();
    let mut d1 = d0.clone();
    for (n, _) in &unknowns {
        d1.code(n, true)?;
    }
    let stmt: HashSet<String> = defs.iter().filter(|(_, (_, b, _))| has_quote(b)).map(|(n, _)| n.clone()).collect();
    Ok((Quoter { c, defs, prelude, unknowns, stmt }, d1))
}

impl<'a> Quoter<'a> {
    fn code(&self, st: &mut QS, name: &str) -> R<Term> {
        let real = CONN_O.iter().find(|(a, _)| *a == name).map(|(_, b)| *b).unwrap_or(name);
        let b = st.doc.code(real, true)?;
        Ok(digits(&b[1..b.len() - 1]))
    }

    fn need(&self, st: &mut QS, name: &str) {
        if (self.defs.contains_key(name) || self.prelude.contains_key(name) || self.unknowns.iter().any(|(n, _)| n == name))
            && !st.needed.iter().any(|n| n == name)
        {
            st.needed.push(name.to_string());
        }
    }

    fn is_value_class(&self, c0: Option<&Ty>) -> bool {
        match c0 {
            None => false,
            Some(c0) => {
                let c = self.c.norm(c0);
                match &c {
                    Ty::K(..) => c == bool_ty() || self.c.leq(&c, &num_ty()),
                    _ => false,
                }
            }
        }
    }

    fn has_rel(&self, t: &Term) -> bool {
        match t {
            Term::Quote(..) => true,
            Term::Var(n) => REL_R.contains(&n.as_str()) || is_conn_o(n) || self.stmt.contains(n),
            Term::App(f, args) => self.has_rel(f) || args.iter().any(|a| self.has_rel(a)),
            Term::Lam(_, b) => self.has_rel(b),
            _ => false,
        }
    }

    /// the code of a term.  ib: binders inside the quote (innermost last) with their classes; outer: classes of variables bound outside
    fn q(&self, st: &mut QS, t: &Term, ib: &[(String, Option<Ty>)], outer: &Loc, typed: bool) -> R<Term> {
        let names: Vec<&str> = ib.iter().map(|(n, _)| n.as_str()).collect();
        match t {
            Term::Quote(e, _) => self.q(st, e, ib, outer, typed),
            Term::Num(_) | Term::Chr(_) | Term::Str(_) => Ok(app("𝔮ⁿ", vec![t.clone()])),
            Term::Var(n) => {
                if let Some(idx) = names.iter().rposition(|m| *m == n.as_str()) {
                    return Ok(app("𝔮ᵛ", vec![nat(names.len() - idx)]));
                }
                if let Some(oc) = loc_lookup(outer, n) {
                    if self.is_value_class(Some(oc)) {
                        return Ok(app("𝔮ⁿ", vec![t.clone()]));
                    }
                    if self.c.is_prop(oc) {
                        return Ok(app("code_rd", vec![t.clone()]));
                    }
                    let pos = outer.iter().position(|(m, _)| m == n).unwrap_or(0);
                    return Ok(app("𝔮ᵛ", vec![nat(names.len() + 1 + pos)]));
                }
                if self.unknowns.iter().any(|(m, _)| m == n) {
                    self.need(st, n);
                    let cd = self.code(st, n)?;
                    return Ok(app("𝔮ˢ", vec![cd]));
                }
                if typed
                    && !self.defs.contains_key(n)
                    && self.c.sigs.contains_key(n)
                    && self.c.sigs[n].iter().all(|s| self.is_value_class(Some(s)))
                {
                    return Ok(app("𝔮ⁿ", vec![t.clone()]));
                }
                if let Some((_, _, dcls)) = self.defs.get(n) {
                    if self.is_value_class(Some(dcls)) && !self.stmt.contains(n) && !self.c.unknownish(n) {
                        return Ok(app("𝔮ⁿ", vec![t.clone()]));
                    }
                }
                self.need(st, n);
                let cd = self.code(st, n)?;
                Ok(app("𝔮ˢ", vec![cd]))
            }
            Term::App(f, args) => {
                if typed {
                    if let Term::Var(fn_) = &**f {
                        if TRANSPARENT.contains(&fn_.as_str()) && !names.contains(&fn_.as_str()) && !loc_member(outer, fn_) && args.len() == 1 {
                            return self.q(st, &args[0], ib, outer, typed);
                        }
                    }
                }
                if typed && !self.has_rel(t) {
                    let nameset: HashSet<String> = names.iter().map(|s| s.to_string()).collect();
                    if !free_in(t, &nameset) {
                        let mut both: HashSet<String> = loc_names(outer).into_iter().collect();
                        both.extend(nameset.iter().cloned());
                        if !self.c.mentions(t, &both) {
                            let mut loc: Loc = outer.clone();
                            for (n, mc) in ib {
                                loc_insert(&mut loc, n, mc.clone().unwrap_or(Ty::F));
                            }
                            let klass = self.c.synth(&loc, t).ok().map(|x| x.0);
                            if self.is_value_class(klass.as_ref()) {
                                return Ok(app("𝔮ⁿ", vec![t.clone()]));
                            }
                        }
                    }
                }
                let mut out = self.q(st, f, ib, outer, typed)?;
                for a in args {
                    let qa = self.q(st, a, ib, outer, typed)?;
                    out = app("𝔮ᵃ", vec![out, qa]);
                }
                Ok(out)
            }
            Term::Lam(ps, b) => {
                let mut inner: Vec<(String, Option<Ty>)> = ib.to_vec();
                inner.extend(ps.iter().cloned());
                let mut o = self.q(st, b, &inner, outer, typed)?;
                for _ in ps {
                    o = app("𝔮ˡ", vec![o]);
                }
                Ok(o)
            }
            Term::Asc(..) => parse_err("a statement cannot be written as a code: asc"),
        }
    }

    fn definition_code(&self, st: &mut QS, name: &str) -> R<Term> {
        if let Some((_, k)) = self.unknowns.iter().find(|(n, _)| n == name) {
            let cd = self.code(st, "𝔲")?;
            let kn = numeral(&to_digits(&(crate::bigint::Int::from_i64(*k), crate::bigint::Int::zero())));
            return Ok(app("𝔮ᵃ", vec![app("𝔮ˢ", vec![cd]), app("𝔮ⁿ", vec![Term::Num(kn)])]));
        }
        if let Some((params, body, cls)) = self.defs.get(name) {
            let mut ps: Vec<(String, Option<Ty>)> = vec![];
            let mut cl = cls.clone();
            for p in params {
                match self.c.norm(&cl) {
                    Ty::K(_, a) if a.len() == 2 => {
                        ps.push((p.clone(), Some(a[0].clone())));
                        cl = a[1].clone();
                    }
                    _ => {
                        ps.push((p.clone(), None));
                        cl = Ty::F;
                    }
                }
            }
            let mut out = self.q(st, body, &ps, &vec![], true)?;
            for _ in params {
                out = app("𝔮ˡ", vec![out]);
            }
            return Ok(out);
        }
        if let Some((params, body)) = self.prelude.get(name) {
            let ps: Vec<(String, Option<Ty>)> = params.iter().map(|p| (p.clone(), None)).collect();
            let mut out = self.q(st, body, &ps, &vec![], false)?;
            for _ in params {
                out = app("𝔮ˡ", vec![out]);
            }
            return Ok(out);
        }
        parse_err(format!("no definition for {} to write as a code", name))
    }

    /// replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝
    pub fn quote_replace(&self, st: &mut QS, t: &Term) -> R<Term> {
        match t {
            Term::Quote(e, loc) => {
                let cd = self.q(st, e, &[], loc, true)?;
                Ok(app("simplify′", vec![var(ENV_NAME), cd]))
            }
            Term::App(f, args) => {
                let f2 = self.quote_replace(st, f)?;
                let mut as2 = vec![];
                for a in args {
                    as2.push(self.quote_replace(st, a)?);
                }
                Ok(Term::App(Box::new(f2), as2))
            }
            Term::Lam(ps, b) => Ok(Term::Lam(ps.clone(), Box::new(self.quote_replace(st, b)?))),
            _ => Ok(t.clone()),
        }
    }

    /// the one table of definitions for the whole program
    pub fn quote_table(&self, st: &mut QS) -> R<Term> {
        let mut entries: Vec<(String, Term)> = vec![];
        let mut k = 0;
        while k < st.needed.len() {
            let name = st.needed[k].clone();
            let cd = self.code(st, &name)?;
            let dc = self.definition_code(st, &name)?;
            entries.push((name, app("⊗", vec![cd, dc])));
            k += 1;
        }
        let unk_names: Vec<&str> = self.unknowns.iter().map(|(n, _)| n.as_str()).collect();
        let mut first: Vec<(usize, Term)> = entries
            .iter()
            .filter_map(|(n, e)| unk_names.iter().position(|u| *u == n.as_str()).map(|i| (i, e.clone())))
            .collect();
        first.sort_by_key(|(i, _)| *i); // stable
        let rest = entries.iter().filter(|(n, _)| !unk_names.contains(&n.as_str())).map(|(_, e)| e.clone());
        let all: Vec<Term> = first.into_iter().map(|(_, e)| e).chain(rest).collect();
        let mut out = var("⊘");
        for e in all.into_iter().rev() {
            out = app("∷", vec![e, out]);
        }
        Ok(out)
    }
}

fn free_in(t: &Term, names: &HashSet<String>) -> bool {
    match t {
        Term::Var(n) => names.contains(n),
        Term::App(f, args) => free_in(f, names) || args.iter().any(|a| free_in(a, names)),
        Term::Lam(ps, b) => {
            let mut rest = names.clone();
            for (n, _) in ps {
                rest.remove(n);
            }
            free_in(b, &rest)
        }
        Term::Quote(e, _) => free_in(e, names),
        _ => false,
    }
}
