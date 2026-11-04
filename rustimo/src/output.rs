//! output.rs -- printing values: the output side of the three notations, and the `main` entry point (port of
//! haskimo/src/I1/Output.hs and pymo/output.py).
//!
//! A value is printed as a NORMAL-FORM TERM in the chosen notation, so that what is printed can be read back, in that notation, as a
//! term that denotes the same value.  Nothing is computed on the host:
//!   * the normal forms are computed IN THE LANGUAGE:  ⊜ (canonical z/m) for spec and bin numbers, showq / showc (decimal text,
//!     reduced real and imaginary parts) for human numbers, decimals for the approximations shown next to stream elements;
//!   * the host walks the value as its declared class describes it (a list cell by cell, a pair as two parts, a tree node by node),
//!     reads digit strings (a digit is ⊤ or ⊥) and spells them, and turns code points into characters.
//!
//! `main`
//!   * main ∶ 𝕊           its text is the output, written as it is (the program formats itself: lib/text.imo);
//!   * main ∶ 𝔏 𝕊 / 𝔖 𝕊   one line per element (a stream of lines is printed as long as it lasts, or `n` lines);
//!   * any other class    the value, as a normal-form term in the output notation, and a newline.
//!
//! Statements (class Prop, spec Ω): a value of Ω is the CODE of a statement in simplest form (computed in the language by
//! simplify′).  The host spells the code in the human notation (Speller); for spec and bin output that text is read again — in the
//! program's context — by the human reader and the class checker, and the resulting spec term is printed.
use crate::base::*;
use crate::core::*;
use crate::hum::*;
use crate::layers::*;
use crate::program::Program;
use crate::syntax::*;
use crate::types::*;
use std::collections::{HashMap, HashSet};

pub const MODES: [&str; 3] = ["bin", "spec", "hum"];

pub const UNDETERMINED: &str = "undetermined: this truth value is neither proved nor refuted — a statement that depends on its unknowns, or a relation on ℝ[i] that no rule decides (declare it Prop to print its simplest form instead of a Bool)";

pub enum Cell {
    Cons(V, V),
    Nil,
}

pub struct Printer<'a> {
    pub p: &'a Program,
    pub mode: String,
    pub n: usize,
}

fn esc(q: char, s: &str) -> String {
    let mut out = String::new();
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\t' => out.push_str("\\t"),
            c if c == q => {
                out.push('\\');
                out.push(c);
            }
            c => out.push(c),
        }
    }
    out
}

impl<'a> Printer<'a> {
    pub fn new(p: &'a Program, mode: &str, n: usize) -> Printer<'a> {
        Printer { p, mode: mode.to_string(), n }
    }

    fn m(&self) -> &Machine {
        self.p.machine()
    }

    fn c(&self) -> &Checker {
        &self.p.checker
    }

    fn hum(&self) -> bool {
        self.mode == "hum"
    }

    /// take a list / string cell apart; ⍰ (an undetermined Boolean inside the text) is reported, never printed as text
    pub fn cell_of(&self, v: &V) -> R<Cell> {
        match self.m().cell_or_nil(v)? {
            Val::Cons(h, t) => Ok(Cell::Cons(h, t)),
            Val::Nil => Ok(Cell::Nil),
            _ => print_err(UNDETERMINED),
        }
    }

    fn boolean_of(&self, v: &V) -> R<bool> {
        match self.m().apply_whnf(v, &[self.m().vt.clone(), self.m().vf.clone()])? {
            Val::T => Ok(true),
            Val::F => Ok(false),
            _ => print_err(UNDETERMINED),
        }
    }

    fn call(&self, f: &str, args: &[V]) -> R<V> {
        self.m().call_g(f, args)
    }

    /// a 𝕊 value -> String (code point by code point)
    pub fn text_of(&self, v: &V) -> R<String> {
        let mut out = String::new();
        let mut cell = self.cell_of(v)?;
        loop {
            match cell {
                Cell::Nil => return Ok(out),
                Cell::Cons(h, t) => {
                    out.push(self.char_of(&h)?);
                    cell = self.cell_of(&t)?;
                }
            }
        }
    }

    /// a 𝕮 value (a natural numeral, as a ℚ[i] pair) -> character; its canonical form is a pair (n, 1)
    pub fn char_of(&self, v: &V) -> R<char> {
        let canon = self.call("⊜", &[v.clone()])?;
        let (z, m) = self.m().to_pair(&canon)?;
        let zd = self.m().to_list(&z)?;
        let ok_den = self.m().to_list(&m)? == vec![1u8];
        let cp = match val_digits_small(&zd) {
            Some((re, im)) => {
                if im == 0 && (0..=0x10FFFF).contains(&re) {
                    Some(re as u32)
                } else {
                    None
                }
            }
            None => None,
        };
        Ok(match (cp, ok_den) {
            (Some(c), true) => char::from_u32(c).unwrap_or('\u{fffd}'),
            _ => '\u{fffd}',
        })
    }

    fn digits_str(&self, v: &V) -> R<String> {
        Ok(numeral(&self.m().to_list(v)?))
    }

    fn is_class(&self, cls: &Ty, name: &str) -> bool {
        self.c().leq(cls, &kk(name)) && self.c().leq(&kk(name), cls)
    }

    /// the normal-form term of v (of class cls) in spec or hum notation (bin is spelled from spec)
    pub fn term_of(&self, v: &V, raw: &Ty) -> R<String> {
        let c = self.c();
        let hum = self.hum();
        let cls = c.norm(raw);
        let (hd, args) = match &cls {
            Ty::K(hd, args) => (hd.as_str(), args),
            _ => return print_err(format!("cannot print a value whose class is not known ({})", show_type(raw))),
        };
        if cls == prop_ty() {
            return self.statement(v);
        }
        if self.is_class(raw, "𝕊") || (hd == "𝔏" && !args.is_empty() && c.norm(&args[0]) == kk("𝕮")) {
            let s = self.text_of(v)?;
            return Ok(format!("\"{}\"", esc('"', &s)));
        }
        if c.leq(raw, &kk("𝕮")) {
            let ch = self.char_of(v)?;
            return Ok(format!("'{}'", esc('\'', &ch.to_string())));
        }
        if c.leq(raw, &num_ty()) {
            return self.number(v, raw);
        }
        if hd == "𝔹" {
            let b = self.boolean_of(v)?;
            return Ok(if hum {
                if b { "true" } else { "false" }
            } else if b {
                "⊤"
            } else {
                "⊥"
            }
            .to_string());
        }
        if hd == "𝔒" {
            let k = self.m().to_ord(v)? as usize;
            let names = if hum { ["less", "same", "greater"] } else { ["⋖", "≖", "⋗"] };
            return Ok(names[k.min(2)].to_string());
        }
        if hd == "𝔏" {
            let el = &args[0];
            self.cell_of(v)?;
            if c.norm(el) == bool_ty() && !hum {
                return Ok(format!("(◀ {})", self.digits_str(v)?));
            }
            let mut items = vec![];
            let mut cell = self.cell_of(v)?;
            loop {
                match cell {
                    Cell::Nil => break,
                    Cell::Cons(h, t) => {
                        items.push(self.term_of(&h, el)?);
                        cell = self.cell_of(&t)?;
                    }
                }
            }
            if hum {
                return Ok(format!("[{}]", items.join(", ")));
            }
            let mut out = "⊘".to_string();
            for x in items.into_iter().rev() {
                out = format!("(∷ {} {})", x, out);
            }
            return Ok(out);
        }
        if hd == "𝔓" {
            let (a, b) = self.m().to_pair(v)?;
            let x = self.term_of(&a, &args[0])?;
            let y = self.term_of(&b, &args[1])?;
            return Ok(if hum { format!("pair({}, {})", x, y) } else { format!("(⊗ {} {})", x, y) });
        }
        if hd == "𝔗" {
            let (tag, body) = self.m().to_pair(v)?;
            if self.m().to_bool(&tag)? {
                let (a, b) = self.m().to_pair(&body)?;
                let x = self.term_of(&a, &cls)?;
                let y = self.term_of(&b, &cls)?;
                return Ok(if hum { format!("node({}, {})", x, y) } else { format!("(❁ {} {})", x, y) });
            }
            let x = self.term_of(&body, &args[0])?;
            return Ok(if hum { format!("leaf({})", x) } else { format!("(❀ {})", x) });
        }
        if hd == "𝔖" {
            let e = self.m().stream_nth(v, self.n)?;
            return self.term_of(&e, &args[0]);
        }
        if hd == "→" || hd == "𝔄" {
            return print_err(format!("a value of class {} has no normal form to print (it is a function)", show_type(raw)));
        }
        print_err(format!("cannot print a value of class {}", show_type(raw)))
    }

    fn number(&self, v: &V, cls: &Ty) -> R<String> {
        if self.hum() {
            let f = if self.c().leq(cls, &kk("ℚ")) { "showq" } else { "showc" };
            let t = self.call(f, &[v.clone()])?;
            return self.text_of(&t);
        }
        let canon = self.call("⊜", &[v.clone()])?;
        let (z, m) = self.m().to_pair(&canon)?;
        let zt = self.digits_str(&z)?;
        let mt = self.digits_str(&m)?;
        Ok(if mt == "1" { zt } else { format!("(÷ {} {})", zt, mt) })
    }

    // ------------------------------------------------------------ statements (class Ω)
    fn statement(&self, v: &V) -> R<String> {
        let text = self.spell(v)?;
        if self.hum() {
            Ok(text)
        } else {
            self.reread(&text)
        }
    }

    /// the spec term of a human statement, read in the program's context (unknowns declared): the checker chooses ≐ or ≐ᴿ, inserts
    /// ⇡ and prop, and marks statements — the marks are dropped, the term is what a reader of the output reads back
    fn reread(&self, text: &str) -> R<String> {
        let c = self.c();
        let parsed: R<Term> = (|| {
            let ts = lex_hum(text)?;
            let (term, rest) = hum_expr(&self.p.hum, &ts, 0, &HashSet::new())?;
            if let Some(t) = rest.first() {
                return parse_err(format!("unexpected {}", show_tok(t)));
            }
            Ok(term)
        })();
        let term = match parsed {
            Ok(t) => t,
            Err(Err::Parse(e)) => return print_err(format!("the statement {} cannot be read in the human notation ({})", py_repr(text), e)),
            Err(e) => return Err(e),
        };
        match c.synth(&vec![], &term) {
            Err(e) => print_err(format!("the statement {} does not read back in this program: {}", py_repr(text), e)),
            Ok((cls, t)) => match c.fit(&t, &cls, &prop_ty()) {
                None => print_err(format!("{} reads back as a {}, not as a statement", py_repr(text), show_type(&cls))),
                Some(fitted) => Ok(pp_term(&strip_quotes(&fitted))),
            },
        }
    }

    /// the remark printed after a stream element (none in bin: the binary notation has no comments)
    fn comment(&self, v: &V, cls0: &Ty) -> R<String> {
        let c = self.c();
        let cls = c.norm(cls0);
        if let Ty::K(hd, args) = &cls {
            if hd == "𝔖" && args.len() == 1 && self.mode != "bin" {
                let el = &args[0];
                let mark = if self.hum() { "--" } else { "⍝" };
                let mut approx = String::new();
                if c.leq(el, &num_ty()) {
                    let x = self.m().stream_nth(v, self.n)?;
                    let re_v = self.call("ℜ", &[x.clone()])?;
                    let re = self.text_of(&self.call("decimals", &[re_v, self.lit(12)?])?)?;
                    let im = self.call("ℑ", &[x])?;
                    let eq0 = self.call("≐", &[im.clone(), self.lit(0)?])?;
                    if !self.m().to_bool(&eq0)? {
                        let imt = self.text_of(&self.call("decimals", &[im, self.lit(12)?])?)?;
                        approx = format!(
                            ", ≈ {} {} {} i",
                            re,
                            if imt.starts_with('-') { "-" } else { "+" },
                            imt.trim_start_matches('-')
                        );
                    } else {
                        approx = format!(", ≈ {}", re);
                    }
                }
                return Ok(format!("   {} element {} of the stream{}", mark, self.n, approx));
            }
        }
        Ok(String::new())
    }

    /// the language value of a small natural number, built from its digits (the reader's numeral expansion)
    fn lit(&self, k: u64) -> R<V> {
        let m = self.m();
        let digits = m.list_value(&to_digits(&(crate::bigint::Int::from_u64(k), crate::bigint::Int::zero())))?;
        let one = m.list_value(&[1])?;
        m.call_g("⊗", &[digits, one])
    }

    pub fn show_value(&self, v: &V, cls: &Ty) -> R<String> {
        let t = self.term_of(v, cls)?;
        let t2 = if self.mode == "bin" {
            let mut d = self.p.doc1.clone();
            spec_term_to_bin(&t, &mut d)?
        } else {
            t
        };
        let cm = self.comment(v, cls)?;
        Ok(format!("{}{}", t2, cm))
    }

    // ------------------------------------------------------------ the Speller: the human spelling of the code of a statement
    fn node_of(&self, v: &V) -> R<Node> {
        let not_a_code = || print_err::<Node>("a statement whose code is not a code (undetermined, or not built by the simplifier)");
        match self.m().apply_whnf(v, &self.m().code_cbs.clone()) {
            Ok(Val::CN(x)) => Ok(Node::N(x)),
            Ok(Val::CS(x)) => Ok(Node::S(x)),
            Ok(Val::CA(f, a)) => Ok(Node::A(f, a)),
            Ok(Val::CL(_)) => Ok(Node::L),
            Ok(Val::CV(_)) => Ok(Node::Var),
            Ok(_) => not_a_code(),
            Err(Err::Unknown(m)) => Err(Err::Unknown(m)),
            Err(_) => not_a_code(),
        }
    }

    fn spell(&self, v: &V) -> R<String> {
        Ok(self.go(v, true)?.0)
    }

    fn symbol_name(&self, c: &V) -> R<String> {
        let ds = trim_digits(&self.m().to_list(c)?);
        let b = format!(".{}.", numeral(&ds));
        match self.p.doc1.b2s.get(&b) {
            Some(n) => Ok(n.clone()),
            None => print_err(format!("a statement mentions the symbol code {}, which neither doc 1 nor this program names", b)),
        }
    }

    fn go(&self, v: &V, formula: bool) -> R<Piece> {
        let n = self.node_of(v)?;
        match n {
            Node::N(x) => {
                if formula {
                    match self.m().apply_whnf(&x, &[self.m().vt.clone(), self.m().vf.clone()])? {
                        Val::T => Ok(("true".to_string(), 10, "atom")),
                        Val::F => Ok(("false".to_string(), 10, "atom")),
                        _ => print_err(UNDETERMINED),
                    }
                } else {
                    self.number_piece(&x)
                }
            }
            Node::S(c) => {
                let nm = self.symbol_name(&c)?;
                self.app_piece(&nm, &[], formula)
            }
            Node::A(f, a) => {
                // the spine: head and arguments
                let mut args = vec![a];
                let mut cur = self.node_of(&f)?;
                loop {
                    match cur {
                        Node::A(f2, a2) => {
                            args.push(a2);
                            cur = self.node_of(&f2)?;
                        }
                        other => {
                            args.reverse();
                            return match other {
                                Node::S(c) => {
                                    let nm = self.symbol_name(&c)?;
                                    self.app_piece(&nm, &args, formula)
                                }
                                _ => print_err("a statement applies something that is not a symbol (a λ): it has no human spelling"),
                            };
                        }
                    }
                }
            }
            _ => print_err("a statement contains a λ or a bound variable: it has no human spelling yet"),
        }
    }

    fn number_piece(&self, q: &V) -> R<Piece> {
        let t = match self.call("showc", &[q.clone()]).and_then(|s| self.text_of(&s)) {
            Ok(t) => t,
            Err(Err::Eval(_)) => return print_err("a statement holds a value that is not a number where a number is expected"),
            Err(e) => return Err(e),
        };
        let p = if t.contains(" + ") || t.contains(" - ") {
            6
        } else if t.ends_with('i') || t.contains('/') {
            7
        } else if t.starts_with('-') {
            8
        } else {
            10
        };
        Ok((t, p, "num"))
    }

    fn app_piece(&self, name: &str, args: &[V], formula: bool) -> R<Piece> {
        let k = args.len();
        if (name == "⊤" || name == "⊥") && k == 0 {
            return Ok((if name == "⊤" { "true" } else { "false" }.to_string(), 10, "atom"));
        }
        if SPELL_TRANSPARENT.contains(&name) && k == 1 {
            return self.go(&args[0], formula && name != "⇡");
        }
        if name == "⊘" && k == 0 {
            return Ok(("[]".to_string(), 10, "atom"));
        }
        if name == "∷" && k == 2 {
            let (first, _, _) = self.go(&args[0], false)?;
            let items = self.list_loop(&args[1], vec![first])?;
            return Ok((format!("[{}]", items.join(", ")), 10, "atom"));
        }
        if (name == "∨" || name == "∨Ω") && k == 2 {
            let a = self.go(&args[0], true)?;
            let b = self.go(&args[1], true)?;
            return Ok((format!("{} or {}", par(&a, 3, &["and"]), par(&b, 2, &["and"])), 2, "or"));
        }
        if (name == "∧" || name == "∧Ω") && k == 2 {
            let a = self.go(&args[0], true)?;
            let b = self.go(&args[1], true)?;
            return Ok((format!("{} and {}", par(&a, 4, &[]), par(&b, 3, &[])), 3, "and"));
        }
        if (name == "¬" || name == "¬Ω") && k == 1 {
            let a = self.go(&args[0], true)?;
            return Ok((format!("not {}", par(&a, 4, &[])), 4, "not"));
        }
        let sub = FORMULA_ARGS.contains(&name);
        let entry = self.rev_entry(name);
        let h: String = entry.map_or(name.to_string(), |e| e.hum.clone());
        let role: &str = entry.map_or("value", |e| e.role.as_str());
        let prec = entry.and_then(|e| e.prec).unwrap_or(0);
        if matches!(role, "infixl" | "infixr" | "infix") && k == 2 {
            let a = self.go(&args[0], sub)?;
            let b = self.go(&args[1], sub)?;
            let (ln, rn) = if h == "^" {
                (10, prec)
            } else if role == "infixl" {
                (prec, if ASSOC.contains(&h.as_str()) { prec } else { prec + 1 })
            } else if role == "infixr" {
                (prec + 1, prec)
            } else {
                (prec + 1, prec + 1)
            };
            let sep = if TIGHT.contains(&h.as_str()) { h.clone() } else { format!(" {} ", h) };
            return Ok((format!("{}{}{}", par(&a, ln, &[]), sep, par(&b, rn, &[])), prec, "op"));
        }
        if role == "prefix" && k == 1 {
            let a = self.go(&args[0], sub)?;
            let x0 = par(&a, prec, &[]);
            let x = if h == "-" && x0.starts_with('-') { format!("({})", a.0) } else { x0 };
            let first_alpha = h.chars().next().map_or(false, |c| c.is_alphabetic());
            return Ok((if first_alpha { format!("{} {}", h, x) } else { format!("{}{}", h, x) }, prec, "op"));
        }
        if k == 0 && role == "value" {
            return Ok((h, 10, "atom"));
        }
        if role != "value" {
            return print_err(format!("{} applied to {} argument(s) has no human spelling", h, k));
        }
        let mut as_ = vec![];
        for a in args {
            as_.push(self.go(a, sub)?.0);
        }
        Ok((format!("{}({})", h, as_.join(", ")), 10, "atom"))
    }

    fn list_loop(&self, rest: &V, mut acc: Vec<String>) -> R<Vec<String>> {
        let bad = || print_err::<Vec<String>>("a list code that does not end in ⊘");
        let mut cur = rest.clone();
        loop {
            match self.node_of(&cur)? {
                Node::S(c) => {
                    return if self.symbol_name(&c)? == "⊘" { Ok(acc) } else { bad() };
                }
                Node::A(f, a) => match self.node_of(&f)? {
                    Node::A(f2, a2) => match self.node_of(&f2)? {
                        Node::S(c) => {
                            if self.symbol_name(&c)? == "∷" {
                                let (x, _, _) = self.go(&a2, false)?;
                                acc.push(x);
                                cur = a;
                            } else {
                                return bad();
                            }
                        }
                        _ => return bad(),
                    },
                    _ => return bad(),
                },
                _ => return bad(),
            }
        }
    }

    /// reverse doc 2: the first entry that has the spec symbol on its right
    fn rev_entry(&self, spec: &str) -> Option<&Entry> {
        self.p.doc2.entries.iter().find(|e| matches!(e.role.as_str(), "value" | "infixl" | "infixr" | "infix" | "prefix") && e.rhs.iter().any(|x| x == spec))
    }
}

enum Node {
    N(V),
    S(V),
    A(V, V),
    L,
    Var,
}

/// text, precedence, kind
type Piece = (String, i64, &'static str);

const FORMULA_ARGS: [&str; 13] = ["∧", "∨", "¬", "⇒", "⇔", "∧Ω", "∨Ω", "¬Ω", "⇒Ω", "⇔Ω", "prop", "decide", "code_rd"];
const SPELL_TRANSPARENT: [&str; 4] = ["⇡", "prop", "decide", "code_rd"];
const TIGHT: [&str; 3] = ["*", "/", "^"];
const ASSOC: [&str; 2] = ["+", "*"];

fn par(p: &Piece, need: i64, avoid: &[&str]) -> String {
    if p.1 < need || avoid.contains(&p.2) {
        format!("({})", p.0)
    } else {
        p.0.clone()
    }
}

fn strip_quotes(t: &Term) -> Term {
    match t {
        Term::Quote(e, _) => strip_quotes(e),
        Term::App(f, args) => Term::App(Box::new(strip_quotes(f)), args.iter().map(strip_quotes).collect()),
        Term::Lam(ps, b) => Term::Lam(ps.clone(), Box::new(strip_quotes(b))),
        _ => t.clone(),
    }
}

// ---------------------------------------------------------------- main
pub fn output_mode(p: &Program, override_: Option<&str>, name: &str) -> String {
    if let Some(m) = override_ {
        return m.to_string();
    }
    if let Some(m) = &p.out_mode {
        return m.clone();
    }
    p.notation_of.get(name).cloned().unwrap_or_else(|| "spec".to_string())
}

/// evaluate `main` and write its output; returns the output notation used.  An unknown whose value is needed is reported
/// (Err::Print), as an undetermined truth value is.
pub fn run_main(p: &Program, mode0: Option<&str>, n: Option<usize>, write: &mut dyn FnMut(&str)) -> R<String> {
    match run_main_inner(p, mode0, n, write) {
        Err(Err::Unknown(m)) => Err(Err::Print(m)),
        other => other,
    }
}

fn run_main_inner(p: &Program, mode0: Option<&str>, n: Option<usize>, write: &mut dyn FnMut(&str)) -> R<String> {
    let c = &p.checker;
    let cls = match c.sigs.get("main").and_then(|v| v.first()) {
        None => return print_err("this program has no main:  define  main ∶ <class>  (spec),  main in <Class> := …  (hum)"),
        Some(cls) => cls.clone(),
    };
    let mode = output_mode(p, mode0, "main");
    let v = p.val("main")?;
    let pr = Printer::new(p, &mode, n.unwrap_or(10));
    let c0 = c.norm(&cls);
    if c.leq(&cls, &kk("𝕊")) {
        let mut cell = pr.cell_of(&v)?;
        loop {
            match cell {
                Cell::Nil => return Ok(mode),
                Cell::Cons(h, t) => {
                    let ch = pr.char_of(&h)?;
                    write(&ch.to_string());
                    cell = pr.cell_of(&t)?;
                }
            }
        }
    }
    if let Ty::K(hd, el) = &c0 {
        if (hd == "𝔏" || hd == "𝔖") && el.len() == 1 && c.norm(&el[0]) == c.norm(&kk("𝕊")) {
            let mut cell = pr.cell_of(&v)?;
            let mut k = 0usize;
            loop {
                match cell {
                    Cell::Cons(h, t) if n.map_or(true, |nn| k < nn) => {
                        let s = pr.text_of(&h)?;
                        write(&format!("{}\n", s));
                        cell = pr.cell_of(&t)?;
                        k += 1;
                    }
                    _ => return Ok(mode),
                }
            }
        }
    }
    let s = pr.show_value(&v, &cls)?;
    write(&format!("{}\n", s));
    Ok(mode)
}

#[allow(dead_code)]
fn _unused(_: HashMap<String, String>) {}
