//! syntax.rs -- the SPEC notation reader of i-1 (port of haskimo/src/I1/Syntax.hs and pymo/syntax.py).
//!
//! spec text  ->  statements:
//!   Def name params body        name x y ≔ term
//!   Decl name type              name ∶ type
//!   Fact term                   (⊆ A B)   (≣ A B)   (↪ f)
//! Named term AST: Num Chr Str Var App Lam (Asc and Quote are made by the human reader and the class checker).
//! Types:  K name args  class constructor application;  V name  class variable;  '→' is the constructor of functions.
//! Comment: everything after the name ⍝ up to the end of the line.
use crate::base::*;
use crate::bigint::Int;

// ---------------------------------------------------------------- the data
/// a class: constructor application, class variable, or the flexible class ⊥ of an unconstrained polymorphic constant
#[derive(Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub enum Ty {
    K(String, Vec<Ty>),
    V(String),
    F,
}

/// an insertion-ordered map from names to classes (a Python dict)
pub type Loc = Vec<(String, Ty)>;

#[derive(Clone, PartialEq, Debug)]
pub enum Term {
    Num(String),
    Chr(u32),
    Str(String),
    Var(String),
    App(Box<Term>, Vec<Term>),
    Lam(Vec<(String, Option<Ty>)>, Box<Term>),
    Asc(Box<Term>, Ty),
    /// a statement (class Ω) with the classes of the variables bound outside it
    Quote(Box<Term>, Loc),
}

#[derive(Clone, PartialEq, Debug)]
pub enum Stmt {
    Def(String, Vec<String>, Term),
    Decl(String, Ty),
    Fact(Term),
}

/// the runtime term in de Bruijn form
#[derive(Clone, PartialEq, Debug)]
pub enum Core {
    V(usize),
    L(Box<Core>),
    A(Box<Core>, Box<Core>),
    G(String),
}

pub fn kk(n: &str) -> Ty {
    Ty::K(n.to_string(), vec![])
}

pub fn app(f: &str, xs: Vec<Term>) -> Term {
    Term::App(Box::new(Term::Var(f.to_string())), xs)
}

pub fn var(n: &str) -> Term {
    Term::Var(n.to_string())
}

pub fn loc_insert(loc: &mut Loc, n: &str, t: Ty) {
    for e in loc.iter_mut() {
        if e.0 == n {
            e.1 = t;
            return;
        }
    }
    loc.push((n.to_string(), t));
}

pub fn loc_lookup<'a>(loc: &'a Loc, n: &str) -> Option<&'a Ty> {
    loc.iter().find(|e| e.0 == n).map(|e| &e.1)
}

pub fn loc_member(loc: &Loc, n: &str) -> bool {
    loc.iter().any(|e| e.0 == n)
}

pub fn loc_names(loc: &Loc) -> Vec<String> {
    loc.iter().map(|e| e.0.clone()).collect()
}

pub const CLASS_VARS: [&str; 5] = ["α", "β", "γ", "δ", "ε"];

pub fn is_class_var(n: &str) -> bool {
    CLASS_VARS.contains(&n)
}

// ---------------------------------------------------------------- Haskell-style `show` (the messages of Haskimo quote it)
fn hs_show_str(s: &str) -> String {
    const NAMES: [&str; 32] = [
        "NUL", "SOH", "STX", "ETX", "EOT", "ENQ", "ACK", "a", "b", "t", "n", "v", "f", "r", "SO", "SI", "DLE", "DC1", "DC2", "DC3", "DC4",
        "NAK", "SYN", "ETB", "CAN", "EM", "SUB", "ESC", "FS", "GS", "RS", "US",
    ];
    let cs: Vec<char> = s.chars().collect();
    let mut out = String::from("\"");
    for (i, &c) in cs.iter().enumerate() {
        let next = cs.get(i + 1).copied();
        let u = c as u32;
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            _ if u < 32 => {
                out.push('\\');
                out.push_str(NAMES[u as usize]);
                if u == 14 && next == Some('H') {
                    out.push_str("\\&");
                }
            }
            '\u{7f}' => out.push_str("\\DEL"),
            _ if u > 126 => {
                out.push_str(&format!("\\{}", u));
                if next.map_or(false, |n| n.is_ascii_digit()) {
                    out.push_str("\\&");
                }
            }
            _ => out.push(c),
        }
    }
    out.push('"');
    out
}

pub fn hs_show_list_str(xs: &[String]) -> String {
    format!("[{}]", xs.iter().map(|x| hs_show_str(x)).collect::<Vec<_>>().join(","))
}

fn hs_show_ty(t: &Ty) -> String {
    match t {
        Ty::V(n) => format!("V {}", hs_show_str(n)),
        Ty::F => "F".to_string(),
        Ty::K(n, args) => format!("K {} [{}]", hs_show_str(n), args.iter().map(hs_show_ty_arg).collect::<Vec<_>>().join(",")),
    }
}

fn hs_show_ty_arg(t: &Ty) -> String {
    // inside a list: showsPrec 0
    hs_show_ty(t)
}

// ---------------------------------------------------------------- lexer
#[derive(Clone, PartialEq, Debug)]
pub enum Tok {
    Nl,
    Open,
    Close,
    Num(String),
    Chr(u32),
    Str(String),
    Name(String),
}

fn hs_show_tok(t: &Tok) -> String {
    match t {
        Tok::Nl => "TNL".to_string(),
        Tok::Open => "TOpen".to_string(),
        Tok::Close => "TClose".to_string(),
        Tok::Num(s) => format!("TkNum {}", hs_show_str(s)),
        Tok::Chr(c) => format!("TkChr {}", c),
        Tok::Str(s) => format!("TkStr {}", hs_show_str(s)),
        Tok::Name(s) => format!("TkName {}", hs_show_str(s)),
    }
}

pub fn lex_spec(text: &str) -> R<Vec<Tok>> {
    let cs: Vec<char> = text.chars().collect();
    let mut i = 0;
    let mut d: i64 = 0;
    let mut out = vec![];
    const DELIM: &str = " \t\r\n()01.'\"";
    while i < cs.len() {
        let c = cs[i];
        if c == ' ' || c == '\t' || c == '\r' {
            i += 1;
        } else if c == '\n' {
            if d == 0 {
                out.push(Tok::Nl);
            }
            i += 1;
        } else if c == '(' {
            out.push(Tok::Open);
            d += 1;
            i += 1;
        } else if c == ')' {
            out.push(Tok::Close);
            d -= 1;
            i += 1;
        } else if c == '0' || c == '1' || c == '.' {
            let mut j = i;
            while j < cs.len() && (cs[j] == '0' || cs[j] == '1' || cs[j] == '.') {
                j += 1;
            }
            let s: String = cs[i..j].iter().collect();
            if s.chars().filter(|&x| x == '.').count() > 1 {
                return parse_err(format!("bad numeral {} (spec notation allows one radix point)", py_repr(&s)));
            }
            out.push(Tok::Num(s));
            i = j;
        } else if c == '\'' || c == '"' {
            // literal: up to the closing quote; a backslash escapes the next character (n, t as in Python)
            let mut body: Vec<char> = vec![];
            let mut j = i + 1;
            loop {
                if j >= cs.len() {
                    return parse_err("unterminated literal");
                }
                let x = cs[j];
                if x == c {
                    j += 1;
                    break;
                } else if x == '\\' {
                    if j + 1 >= cs.len() {
                        return parse_err("string index out of range");
                    }
                    let y = cs[j + 1];
                    body.push(match y {
                        'n' => '\n',
                        't' => '\t',
                        _ => y,
                    });
                    j += 2;
                } else {
                    body.push(x);
                    j += 1;
                }
            }
            if c == '\'' {
                if body.len() == 1 {
                    out.push(Tok::Chr(body[0] as u32));
                } else {
                    let s: String = body.iter().collect();
                    return parse_err(format!("char literal needs exactly one character: {}", py_repr(&s)));
                }
            } else {
                out.push(Tok::Str(body.iter().collect()));
            }
            i = j;
        } else {
            let mut j = i;
            while j < cs.len() && !DELIM.contains(cs[j]) {
                j += 1;
            }
            let name: String = cs[i..j].iter().collect();
            if name == "⍝" {
                let mut k = j;
                while k < cs.len() && cs[k] != '\n' {
                    k += 1;
                }
                i = k;
            } else {
                out.push(Tok::Name(name));
                i = j;
            }
        }
    }
    Ok(out)
}

/// token trees: an atom or a parenthesised group
#[derive(Clone, PartialEq, Debug)]
pub enum TT {
    Atom(Tok),
    Grp(Vec<TT>),
}

fn hs_show_tt(t: &TT) -> String {
    match t {
        TT::Atom(k) => {
            let s = hs_show_tok(k);
            if s.contains(' ') {
                format!("Atom ({})", s)
            } else {
                format!("Atom {}", s)
            }
        }
        TT::Grp(xs) => format!("Grp [{}]", xs.iter().map(hs_show_tt).collect::<Vec<_>>().join(",")),
    }
}

fn trees_go(ts: &[Tok], i: &mut usize) -> R<Vec<TT>> {
    let mut out = vec![];
    while *i < ts.len() {
        match &ts[*i] {
            Tok::Open => {
                *i += 1;
                let inner = trees_go(ts, i)?;
                if *i < ts.len() && ts[*i] == Tok::Close {
                    *i += 1;
                    out.push(TT::Grp(inner));
                } else {
                    return parse_err("missing )");
                }
            }
            Tok::Close => break,
            t => {
                out.push(TT::Atom(t.clone()));
                *i += 1;
            }
        }
    }
    Ok(out)
}

/// token list (one line, no Nl) -> token trees
fn trees(ts: &[Tok]) -> R<Vec<TT>> {
    let mut i = 0;
    let r = trees_go(ts, &mut i)?;
    if i < ts.len() {
        return parse_err("unexpected )");
    }
    Ok(r)
}

/// the logical lines (split at top-level newlines) of a token stream, each as a list of token trees
fn logical_lines(toks: &[Tok]) -> R<Vec<Vec<TT>>> {
    let mut out = vec![];
    for line in toks.split(|t| *t == Tok::Nl) {
        let tt = trees(line)?;
        if !tt.is_empty() {
            out.push(tt);
        }
    }
    Ok(out)
}

// ---------------------------------------------------------------- terms
fn is_name(t: &TT, n: &str) -> bool {
    matches!(t, TT::Atom(Tok::Name(m)) if m == n)
}

fn parse_item(t: &TT) -> R<Term> {
    match t {
        TT::Atom(Tok::Num(s)) => Ok(Term::Num(s.clone())),
        TT::Atom(Tok::Chr(c)) => Ok(Term::Chr(*c)),
        TT::Atom(Tok::Str(s)) => Ok(Term::Str(s.clone())),
        TT::Atom(Tok::Name(n)) => Ok(Term::Var(n.clone())),
        TT::Atom(k) => parse_err(format!("unexpected {}", hs_show_tok(k))),
        TT::Grp(inner) => {
            let last_arrow = inner.iter().rposition(|x| is_name(x, "↦"));
            match last_arrow {
                Some(k) => Ok(Term::Lam(parse_binders(&inner[..k])?, Box::new(parse_seq(&inner[k + 1..])?))),
                None => parse_seq(inner),
            }
        }
    }
}

fn parse_binders(ts: &[TT]) -> R<Vec<(String, Option<Ty>)>> {
    let mut out = vec![];
    let mut r = ts;
    while !r.is_empty() {
        match &r[0] {
            TT::Atom(Tok::Name(name)) => {
                if r.len() >= 2 && is_name(&r[1], "∶") {
                    let (ty, rest) = parse_type_atom(&r[2..])?;
                    out.push((name.clone(), Some(ty)));
                    r = rest;
                } else {
                    out.push((name.clone(), None));
                    r = &r[1..];
                }
            }
            t => return parse_err(format!("bad binder {}", hs_show_tt(t))),
        }
    }
    Ok(out)
}

fn parse_seq(ts: &[TT]) -> R<Term> {
    match ts {
        [] => parse_err("empty application"),
        [x] => parse_item(x),
        [x, xs @ ..] => {
            let f = parse_item(x)?;
            let args = xs.iter().map(parse_item).collect::<R<Vec<_>>>()?;
            Ok(Term::App(Box::new(f), args))
        }
    }
}

// ---------------------------------------------------------------- types
fn parse_type_atom(ts: &[TT]) -> R<(Ty, &[TT])> {
    match ts.first() {
        Some(TT::Atom(Tok::Name(n))) => Ok((if is_class_var(n) { Ty::V(n.clone()) } else { Ty::K(n.clone(), vec![]) }, &ts[1..])),
        Some(TT::Grp(inner)) => Ok((parse_type_seq(inner)?, &ts[1..])),
        Some(t) => parse_err(format!("bad type {}", hs_show_tt(t))),
        None => parse_err("list index out of range"),
    }
}

fn type_atoms(mut ts: &[TT]) -> R<Vec<Ty>> {
    let mut out = vec![];
    while !ts.is_empty() {
        let (a, r) = parse_type_atom(ts)?;
        out.push(a);
        ts = r;
    }
    Ok(out)
}

pub fn parse_type_seq(inner: &[TT]) -> R<Ty> {
    if inner.is_empty() {
        return parse_err("empty type");
    }
    if is_name(&inner[0], "→") {
        let mut a = type_atoms(&inner[1..])?;
        if a.len() == 2 {
            let b = a.pop().unwrap();
            let x = a.pop().unwrap();
            return Ok(Ty::K("→".to_string(), vec![x, b]));
        }
        return parse_err("→ takes two classes");
    }
    if let Some(k) = inner.iter().position(|x| is_name(x, "→")) {
        let l = parse_type_seq(&inner[..k])?;
        let r = parse_type_seq(&inner[k + 1..])?;
        return Ok(Ty::K("→".to_string(), vec![l, r]));
    }
    let (hd, r) = parse_type_atom(inner)?;
    let args = type_atoms(r)?;
    if args.is_empty() {
        return Ok(hd);
    }
    match hd {
        Ty::K(n, a) if a.is_empty() => Ok(Ty::K(n, args)),
        other => parse_err(format!("bad class application {}", hs_show_ty(&other))),
    }
}

pub fn show_type(t: &Ty) -> String {
    match t {
        Ty::V(n) => n.clone(),
        Ty::F => "⊥".to_string(),
        Ty::K(n, args) if n == "→" && args.len() == 2 => {
            let l = show_type(&args[0]);
            let l = if matches!(&args[0], Ty::K(m, _) if m == "→") { format!("({})", l) } else { l };
            format!("{} → {}", l, show_type(&args[1]))
        }
        Ty::K(n, args) if args.is_empty() => n.clone(),
        Ty::K(n, args) => {
            let a: Vec<String> = args
                .iter()
                .map(|a| if matches!(a, Ty::K(m, _) if m == "→") { format!("({})", show_type(a)) } else { show_type(a) })
                .collect();
            format!("({} {})", n, a.join(" "))
        }
    }
}

// ---------------------------------------------------------------- statements
fn has_assign(t: &TT) -> bool {
    match t {
        TT::Atom(Tok::Name(n)) => n == "≔",
        TT::Grp(xs) => xs.iter().any(has_assign),
        _ => false,
    }
}

fn statement(ln: &[TT]) -> R<Stmt> {
    if ln.iter().any(has_assign) {
        return match ln.iter().position(|t| is_name(t, "≔")) {
            Some(k) => {
                let hd = &ln[..k];
                let body = &ln[k + 1..];
                let names: Vec<String> = hd
                    .iter()
                    .filter_map(|t| match t {
                        TT::Atom(Tok::Name(n)) => Some(n.clone()),
                        _ => None,
                    })
                    .collect();
                if hd.is_empty() || names.len() != hd.len() {
                    return parse_err(format!("bad definition head {}", hs_show_list_str(&names)));
                }
                Ok(Stmt::Def(names[0].clone(), names[1..].to_vec(), parse_seq(body)?))
            }
            None => parse_err("assertion failed"),
        };
    }
    if ln.len() >= 3 {
        if let (TT::Atom(Tok::Name(n)), true) = (&ln[0], is_name(&ln[1], "∶")) {
            return Ok(Stmt::Decl(n.clone(), parse_type_seq(&ln[2..])?));
        }
        if is_name(&ln[1], "∶") {
            return parse_err("assertion failed");
        }
    }
    Ok(Stmt::Fact(parse_seq(ln)?))
}

pub fn parse_statements(text: &str) -> R<Vec<Stmt>> {
    let toks = lex_spec(text)?;
    logical_lines(&toks)?.iter().map(|l| statement(l)).collect()
}

// ---------------------------------------------------------------- erasure to the runtime (de Bruijn) term
/// the reader's expansion of a numeral: the pair (digits, denominator) of Gaussian integers, digits LSB first
pub fn num_ast(s: &str) -> R<Core> {
    let g = |n: &str| Core::G(n.to_string());
    let a = |f: Core, x: Core| Core::A(Box::new(f), Box::new(x));
    match s.split_once('.') {
        None => Ok(a(a(g("⊗"), int_ast(s)), int_ast("1"))),
        Some((x, y)) => {
            let bits = format!("{}{}", x, y);
            if bits.is_empty() {
                return parse_err("empty numeral");
            }
            let den = format!("1{}", "0".repeat(y.chars().count()));
            Ok(a(a(g("⊗"), int_ast(&bits)), int_ast(&den)))
        }
    }
}

fn int_ast(s: &str) -> Core {
    let mut r = Core::G("⊥".to_string());
    for ch in s.chars() {
        let d = Core::G(if ch == '1' { "⊤" } else { "⊥" }.to_string());
        r = Core::A(Box::new(Core::A(Box::new(Core::G("∷".to_string())), Box::new(d))), Box::new(r));
    }
    r
}

/// scope: the binders in scope, innermost LAST
pub fn erase(scope: &mut Vec<String>, t: &Term) -> R<Core> {
    Ok(match t {
        Term::Num(s) => num_ast(s)?,
        Term::Chr(c) => num_ast(&int_numeral_text(*c as u64))?,
        Term::Str(s) => {
            let mut r = Core::G("⊘".to_string());
            for ch in s.chars().rev() {
                let c = num_ast(&int_numeral_text(ch as u64))?;
                r = Core::A(Box::new(Core::A(Box::new(Core::G("∷".to_string())), Box::new(c))), Box::new(r));
            }
            r
        }
        Term::Var(nm) => match scope.iter().rposition(|x| x == nm) {
            Some(idx) => Core::V(scope.len() - idx),
            None => Core::G(nm.clone()),
        },
        Term::App(f, args) => {
            let mut acc = erase(scope, f)?;
            for a in args {
                let x = erase(scope, a)?;
                acc = Core::A(Box::new(acc), Box::new(x));
            }
            acc
        }
        Term::Lam(ps, b) => {
            for (n, _) in ps {
                scope.push(n.clone());
            }
            let body = erase(scope, b);
            for _ in ps {
                scope.pop();
            }
            let mut body = body?;
            for _ in ps {
                body = Core::L(Box::new(body));
            }
            body
        }
        Term::Asc(e, _) => erase(scope, e)?,
        Term::Quote(e, _) => erase(scope, e)?,
    })
}

pub fn erase_def(name: &str, params: &[String], body: &Term) -> R<(String, Core)> {
    let mut scope: Vec<String> = params.to_vec();
    let mut c = erase(&mut scope, body)?;
    for _ in params {
        c = Core::L(Box::new(c));
    }
    Ok((name.to_string(), c))
}

// ---------------------------------------------------------------- pretty printer (spec text)
pub fn pp_type(t: &Ty) -> String {
    match t {
        Ty::V(n) => n.clone(),
        Ty::F => "⊥".to_string(),
        Ty::K(n, args) if n == "→" && args.len() == 2 => format!("(→ {} {})", pp_type(&args[0]), pp_type(&args[1])),
        Ty::K(n, args) if args.is_empty() => n.clone(),
        Ty::K(n, args) => format!("({} {})", n, args.iter().map(pp_type).collect::<Vec<_>>().join(" ")),
    }
}

fn esc_with(s: &str, q: char) -> String {
    let mut out = String::new();
    for ch in s.chars() {
        match ch {
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            c if c == q => {
                out.push('\\');
                out.push(c);
            }
            c => out.push(c),
        }
    }
    out
}

pub fn pp_term(t: &Term) -> String {
    match t {
        Term::Num(s) => s.clone(),
        Term::Chr(c) => format!("'{}'", esc_with(&char::from_u32(*c).unwrap_or('\u{fffd}').to_string(), '\'')),
        Term::Str(s) => format!("\"{}\"", esc_with(s, '"')),
        Term::Var(n) => n.clone(),
        Term::App(f, args) => {
            let mut parts = vec![pp_term(f)];
            parts.extend(args.iter().map(pp_term));
            format!("({})", parts.join(" "))
        }
        Term::Lam(ps, b) => {
            let p: Vec<String> = ps
                .iter()
                .map(|(n, ty)| match ty {
                    None => n.clone(),
                    Some(ty) => format!("{} ∶ {}", n, pp_type(ty)),
                })
                .collect();
            format!("({} ↦ {})", p.join(" "), pp_term(b))
        }
        Term::Asc(e, _) => pp_term(e),
        Term::Quote(e, _) => pp_term(e),
    }
}

pub fn pp_statement(s: &Stmt) -> String {
    match s {
        Stmt::Def(n, ps, b) => {
            let mut parts = vec![n.clone()];
            parts.extend(ps.iter().cloned());
            format!("{} ≔ {}", parts.join(" "), pp_term(b))
        }
        Stmt::Decl(n, ty) => format!("{} ∶ {}", n, pp_type(ty)),
        Stmt::Fact(t) => pp_term(t),
    }
}

// ---------------------------------------------------------------- Python repr of the tuple form of a term (for error messages)
fn tuple_of(xs: &[String]) -> String {
    match xs.len() {
        0 => "()".to_string(),
        1 => format!("({},)", xs[0]),
        _ => format!("({})", xs.join(", ")),
    }
}

fn repr_ty(t: &Ty) -> String {
    match t {
        Ty::V(n) => format!("('V', {})", py_repr(n)),
        Ty::F => "('F', '⊥')".to_string(),
        Ty::K(n, args) => format!("('K', {}, {})", py_repr(n), tuple_of(&args.iter().map(repr_ty).collect::<Vec<_>>())),
    }
}

pub fn repr_term(t: &Term) -> String {
    let tup = |xs: Vec<String>| format!("({})", xs.join(", "));
    match t {
        Term::Num(s) => tup(vec!["'num'".into(), py_repr(s)]),
        Term::Chr(c) => tup(vec!["'chr'".into(), c.to_string()]),
        Term::Str(s) => tup(vec!["'str'".into(), py_repr(s)]),
        Term::Var(n) => tup(vec!["'var'".into(), py_repr(n)]),
        Term::App(f, args) => tup(vec!["'app'".into(), repr_term(f), format!("[{}]", args.iter().map(repr_term).collect::<Vec<_>>().join(", "))]),
        Term::Lam(ps, b) => tup(vec![
            "'lam'".into(),
            format!(
                "[{}]",
                ps.iter()
                    .map(|(n, ty)| tup(vec![py_repr(n), ty.as_ref().map_or("None".to_string(), repr_ty)]))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            repr_term(b),
        ]),
        Term::Asc(e, ty) => tup(vec!["'asc'".into(), repr_term(e), repr_ty(ty)]),
        Term::Quote(e, _) => tup(vec!["'quote'".into(), repr_term(e)]),
    }
}

#[allow(dead_code)]
fn _unused(_: &Int) {}
