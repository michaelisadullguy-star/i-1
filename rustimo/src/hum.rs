//! hum.rs -- the HUMAN notation of i-1 and doc 2 (port of haskimo/src/I1/Hum.hs and pymo/hum.py).
//!
//! doc 2 line   <hum symbol> := <rhs> | <rhs> | ...  ; <role>          (⍝ starts a comment)
//!     rhs   a spec symbol, or a bin symbol (a numeral such as 11, or .B.)
//!     role  class | value | literal | infixl P | infixr P | infix P | prefix P
//!     several rhs  = an overload set; the checker picks one by the classes of the arguments.
//!
//! human statements (one per logical line)
//!     name in Class := expr                      declaration + definition
//!     name in Class                              declaration only: an UNKNOWN of a number class
//!     name(x, y) in A -> B -> C := expr          parameters take their classes from the declaration
//!     A subseteq B                               fact (⊆ A B)
//! human terms
//!     1, 12, 3.25   "text"  'c'   f(a, b)   a + b   a - b   -a   a * b   a / b   a == b   a geq b   (e in Class)
//!     x in Class |-> body                        lambda (binder classes are mandatory)
use crate::base::*;
use crate::bigint::Int;
use crate::layers::{is_bin_sym, Doc1};
use crate::syntax::*;
use std::collections::{BTreeMap, HashMap, HashSet};

// ---------------------------------------------------------------- doc 2
#[derive(Clone, Debug)]
pub struct Entry {
    pub hum: String,
    pub rhs: Vec<String>,
    pub role: String,
    pub prec: Option<i64>,
}

#[derive(Clone)]
pub struct Doc2 {
    pub entries: Vec<Entry>,
    by_hum: HashMap<String, Vec<usize>>,
}

impl Doc2 {
    fn make(entries: Vec<Entry>) -> Doc2 {
        let mut by_hum: HashMap<String, Vec<usize>> = HashMap::new();
        for (i, e) in entries.iter().enumerate() {
            by_hum.entry(e.hum.clone()).or_default().push(i);
        }
        Doc2 { entries, by_hum }
    }

    pub fn parse(text: &str) -> R<Doc2> {
        let mut es = vec![];
        for ln0 in text.split('\n') {
            let ln1 = strip(ln0);
            if ln1.is_empty() || ln1.starts_with('⍝') {
                continue;
            }
            let ln = ln1.split(" ⍝ ").next().unwrap_or("");
            let (hd, rest) = match ln.split_once(" := ") {
                Some(p) => p,
                None => return parse_err(format!("doc2: bad line {}", py_repr(ln))),
            };
            let (rhs, role): (&str, Vec<&str>) = match rest.rsplit_once(" ; ") {
                Some((a, b)) => (a, b.split_whitespace().collect()),
                None => ("", rest.split_whitespace().collect()),
            };
            if role.is_empty() {
                return parse_err("Prelude.head: empty list");
            }
            es.push(Entry {
                hum: strip(hd).to_string(),
                rhs: rhs.split(" | ").map(|x| strip(x).to_string()).collect(),
                role: role[0].to_string(),
                prec: role.get(1).and_then(|p| p.parse::<i64>().ok()),
            });
        }
        Ok(Doc2::make(es))
    }

    /// the first entry for a human symbol that has one of the roles
    pub fn find(&self, hum: &str, roles: &[&str]) -> Option<&Entry> {
        self.by_hum.get(hum)?.iter().map(|&i| &self.entries[i]).find(|e| roles.contains(&e.role.as_str()))
    }

    /// key -> [spec symbols]  (bin-literal right-hand sides are handled by the reader, not listed here)
    pub fn overload_table(&self) -> BTreeMap<String, Vec<String>> {
        let mut m = BTreeMap::new();
        for e in &self.entries {
            if matches!(e.role.as_str(), "class" | "literal" | "syntax") {
                continue;
            }
            let key = if e.role == "prefix" { format!("hum:prefix {}", e.hum) } else { format!("hum:{}", e.hum) };
            let v: Vec<String> = e.rhs.iter().filter(|x| !(!x.is_empty() && x.chars().all(|c| c == '0' || c == '1' || c == '.'))).cloned().collect();
            m.insert(key, v);
        }
        m
    }

    /// a bin symbol on the right of doc 2 means the spec symbol that doc 1 gives that code to
    pub fn remap(&self, d1: &Doc1) -> Doc2 {
        let es = self
            .entries
            .iter()
            .map(|e| {
                let mut e = e.clone();
                e.rhs = e.rhs.iter().map(|x| if is_bin_sym(x) { d1.b2s.get(x).cloned().unwrap_or_else(|| x.clone()) } else { x.clone() }).collect();
                e
            })
            .collect();
        Doc2::make(es)
    }
}

// ---------------------------------------------------------------- lexer
#[derive(Clone, PartialEq, Debug)]
pub enum HTok {
    Num(String),
    Str(String),
    Chr(u32),
    Id(String),
    Op(String),
}

pub fn show_tok(t: &HTok) -> String {
    match t {
        HTok::Num(s) => format!("('NUM', {})", py_repr(s)),
        HTok::Str(s) => format!("('STR', {})", py_repr(s)),
        HTok::Chr(c) => format!("('CHR', {})", c),
        HTok::Id(s) => format!("('ID', {})", py_repr(s)),
        HTok::Op(s) => format!("('OP', {})", py_repr(s)),
    }
}

fn is_ascii_letter(c: char) -> bool {
    c.is_ascii_alphabetic()
}

/// the body of a quoted literal: any character but the quote and the backslash, or a backslash and any character but a newline;
/// returns (body with its backslashes, index after the closing quote)
fn quoted(cs: &[char], start: usize, q: char) -> Option<(String, usize)> {
    let mut body = String::new();
    let mut i = start;
    while i < cs.len() {
        let x = cs[i];
        if x == q {
            return Some((body, i + 1));
        } else if x == '\\' {
            match cs.get(i + 1) {
                Some(&y) if y != '\n' => {
                    body.push('\\');
                    body.push(y);
                    i += 2;
                }
                _ => return None,
            }
        } else {
            body.push(x);
            i += 1;
        }
    }
    None
}

fn unescape(s: &str) -> Vec<char> {
    let cs: Vec<char> = s.chars().collect();
    let mut out = vec![];
    let mut i = 0;
    while i < cs.len() {
        if cs[i] == '\\' && i + 1 < cs.len() {
            out.push(match cs[i + 1] {
                'n' => '\n',
                't' => '\t',
                y => y,
            });
            i += 2;
        } else {
            out.push(cs[i]);
            i += 1;
        }
    }
    out
}

pub fn lex_hum(line0: &str) -> R<Vec<HTok>> {
    let cs: Vec<char> = line0.trim_end_matches(|c: char| c.is_whitespace()).chars().collect();
    let mut i = 0;
    let mut out = vec![];
    loop {
        while i < cs.len() && cs[i].is_whitespace() {
            i += 1;
        }
        if i >= cs.len() {
            return Ok(out);
        }
        let c = cs[i];
        if c.is_ascii_digit() {
            let mut j = i;
            while j < cs.len() && cs[j].is_ascii_digit() {
                j += 1;
            }
            let ip: String = cs[i..j].iter().collect();
            if j + 1 < cs.len() && cs[j] == '.' && cs[j + 1].is_ascii_digit() {
                let mut k = j + 1;
                while k < cs.len() && cs[k].is_ascii_digit() {
                    k += 1;
                }
                let fp: String = cs[j + 1..k].iter().collect();
                out.push(HTok::Num(format!("{}.{}", ip, fp)));
                i = k;
            } else {
                out.push(HTok::Num(ip));
                i = j;
            }
            continue;
        }
        if c == '"' {
            if let Some((body, next)) = quoted(&cs, i + 1, '"') {
                out.push(HTok::Str(unescape(&body).into_iter().collect()));
                i = next;
                continue;
            }
        }
        if c == '\'' {
            if let Some((body, next)) = quoted(&cs, i + 1, '\'') {
                let u = unescape(&body);
                if u.len() == 1 {
                    out.push(HTok::Chr(u[0] as u32));
                    i = next;
                    continue;
                }
            }
        }
        if c == '\\' {
            let mut j = i + 1;
            while j < cs.len() && is_ascii_letter(cs[j]) {
                j += 1;
            }
            if j > i + 1 {
                let nm: String = cs[i + 1..j].iter().collect();
                out.push(HTok::Id(format!("\\{}", nm)));
                i = j;
                continue;
            }
        }
        if is_ascii_letter(c) || c == '_' {
            let mut j = i;
            while j < cs.len() && (is_ascii_letter(cs[j]) || cs[j] == '_' || cs[j].is_ascii_digit()) {
                j += 1;
            }
            out.push(HTok::Id(cs[i..j].iter().collect()));
            i = j;
            continue;
        }
        let rest: String = cs[i..cs.len().min(i + 3)].iter().collect();
        if let Some(op) = [":=", "|->", "->", "==", "!=", "++"].iter().find(|op| rest.starts_with(**op)) {
            out.push(HTok::Op(op.to_string()));
            i += op.chars().count();
            continue;
        }
        if "-+*/^(),[]".contains(c) {
            out.push(HTok::Op(c.to_string()));
            i += 1;
            continue;
        }
        let take: String = cs[i..cs.len().min(i + 12)].iter().collect();
        return parse_err(format!("human notation: cannot read {}", py_repr(&take)));
    }
}

/// a logical line ends at a newline outside parentheses; `--` starts a comment
pub fn hum_logical_lines(text: &str) -> Vec<String> {
    let mut out = vec![];
    let mut cur = String::new();
    let mut depth: i64 = 0;
    for ln0 in text.split('\n') {
        let ln: &str = if ln0.contains("--") && !ln0.contains('"') { ln0.split("--").next().unwrap_or("") } else { ln0 };
        cur.push(' ');
        cur.push_str(ln);
        let count = |c: char| ln.chars().filter(|&x| x == c).count() as i64;
        depth = depth + count('(') - count(')') + count('[') - count(']');
        if depth <= 0 {
            let s = strip(&cur).to_string();
            if !s.is_empty() {
                out.push(s);
            }
            cur.clear();
            depth = 0;
        }
    }
    let s = strip(&cur).to_string();
    if !s.is_empty() {
        out.push(s);
    }
    out
}

// ---------------------------------------------------------------- parser
#[derive(Clone)]
pub struct Hum {
    pub doc: Doc2,
    infix: HashMap<String, (i64, String)>,
    prefix: HashMap<String, i64>,
}

pub fn mk_hum(d: Doc2) -> Hum {
    let mut infix = HashMap::new();
    let mut prefix = HashMap::new();
    for e in &d.entries {
        if matches!(e.role.as_str(), "infixl" | "infixr" | "infix") {
            infix.insert(e.hum.clone(), (e.prec.unwrap_or(0), e.role.clone()));
        }
        if e.role == "prefix" {
            prefix.insert(e.hum.clone(), e.prec.unwrap_or(0));
        }
    }
    Hum { doc: d, infix, prefix }
}

fn oob<T>() -> R<T> {
    parse_err("list index out of range")
}

type Scope = HashSet<String>;

// classes
fn class_atom<'a>(h: &Hum, ts: &'a [HTok]) -> R<(Ty, &'a [HTok])> {
    match ts.first() {
        Some(HTok::Op(o)) if o == "(" => {
            let (c, r) = class_expr(h, &ts[1..])?;
            match r.first() {
                Some(HTok::Op(o)) if o == ")" => Ok((c, &r[1..])),
                _ => parse_err("missing )"),
            }
        }
        Some(HTok::Id(n)) => match h.doc.find(n, &["class"]) {
            None => parse_err(format!("{} is not a class in doc 2", n)),
            Some(e) => {
                let name = e.rhs[0].clone();
                if is_class_var(&name) {
                    return Ok((Ty::V(name), &ts[1..]));
                }
                match ts.get(1) {
                    Some(HTok::Op(o)) if o == "(" => {
                        let (args, rest) = class_args(h, &ts[2..])?;
                        Ok((Ty::K(name, args), rest))
                    }
                    _ => Ok((Ty::K(name, vec![]), &ts[1..])),
                }
            }
        },
        Some(t) => parse_err(format!("class expected, found {}", show_tok(t))),
        None => oob(),
    }
}

fn class_args<'a>(h: &Hum, ts: &'a [HTok]) -> R<(Vec<Ty>, &'a [HTok])> {
    let mut out = vec![];
    let mut r = ts;
    loop {
        let (a, r1) = class_expr(h, r)?;
        out.push(a);
        match r1.first() {
            Some(HTok::Op(o)) if o == "," => r = &r1[1..],
            Some(HTok::Op(o)) if o == ")" => return Ok((out, &r1[1..])),
            None => return oob(),
            _ => return parse_err("missing ) in class"),
        }
    }
}

pub fn class_expr<'a>(h: &Hum, ts: &'a [HTok]) -> R<(Ty, &'a [HTok])> {
    let (l, r) = class_atom(h, ts)?;
    match r.first() {
        Some(HTok::Op(o)) if o == "->" => {
            let (rt, r2) = class_expr(h, &r[1..])?;
            Ok((Ty::K("→".to_string(), vec![l, rt]), r2))
        }
        _ => Ok((l, r)),
    }
}

// terms
fn number(text: &str) -> Term {
    match text.split_once('.') {
        None => Term::Num(big_numeral_text(&Int::parse_dec(text))),
        Some((a, b)) => {
            let digits = format!("{}{}", a, b);
            let den = Int::pow_small(10, b.chars().count() as u32);
            app(
                "hum:/",
                vec![Term::Num(big_numeral_text(&Int::parse_dec(&digits))), Term::Num(big_numeral_text(&den))],
            )
        }
    }
}

fn is_op(t: &HTok, o: &str) -> bool {
    matches!(t, HTok::Op(x) if x == o)
}

fn atom<'a>(h: &Hum, ts: &'a [HTok], scope: &Scope) -> R<(Term, &'a [HTok])> {
    let starts_paren = |r: &[HTok]| r.first().map_or(false, |t| is_op(t, "("));
    match ts.first() {
        None => oob(),
        Some(HTok::Num(s)) => Ok((number(s), &ts[1..])),
        Some(HTok::Str(s)) => Ok((Term::Str(s.clone()), &ts[1..])),
        Some(HTok::Chr(c)) => Ok((Term::Chr(*c), &ts[1..])),
        Some(HTok::Op(o)) if o == "[" => {
            let r0 = &ts[1..];
            let (items, r1) = if r0.first().map_or(false, |t| is_op(t, "]")) {
                (vec![], r0)
            } else {
                list_items(h, r0, scope)?
            };
            match r1.first() {
                Some(t) if is_op(t, "]") => {
                    let mut e = var("hum:nil");
                    for a in items.into_iter().rev() {
                        e = app("hum:cons", vec![a, e]);
                    }
                    Ok((e, &r1[1..]))
                }
                None => oob(),
                _ => parse_err("missing ] in list"),
            }
        }
        Some(HTok::Op(o)) if o == "(" => {
            let (e, r1) = hum_expr(h, &ts[1..], 0, scope)?;
            match r1.first() {
                Some(HTok::Id(w)) if w == "in" => {
                    let (c, r3) = class_expr(h, &r1[1..])?;
                    match r3.first() {
                        Some(t) if is_op(t, ")") => Ok((Term::Asc(Box::new(e), c), &r3[1..])),
                        None => oob(),
                        _ => parse_err("missing )"),
                    }
                }
                Some(t) if is_op(t, ")") => Ok((e, &r1[1..])),
                None => oob(),
                _ => parse_err("missing )"),
            }
        }
        Some(HTok::Id(name)) => {
            let r = &ts[1..];
            if !scope.contains(name) && !starts_paren(r) {
                if let Some(lit) = h.doc.find(name, &["literal"]) {
                    return Ok((Term::Num(lit.rhs[0].clone()), r));
                }
            }
            let hd = if scope.contains(name) || h.doc.find(name, &["value"]).is_none() { var(name) } else { var(&format!("hum:{}", name)) };
            match r.first() {
                Some(t) if is_op(t, "(") => {
                    if r.get(1).map_or(false, |t| is_op(t, ")")) {
                        return Ok((Term::App(Box::new(hd), vec![]), &r[2..]));
                    }
                    let (args, r2) = call_args(h, &r[1..], scope)?;
                    Ok((Term::App(Box::new(hd), args), r2))
                }
                _ => Ok((hd, r)),
            }
        }
        Some(t) => parse_err(format!("unexpected {}", show_tok(t))),
    }
}

fn list_items<'a>(h: &Hum, ts: &'a [HTok], scope: &Scope) -> R<(Vec<Term>, &'a [HTok])> {
    let mut out = vec![];
    let mut r = ts;
    loop {
        let (a, r1) = hum_expr(h, r, 0, scope)?;
        out.push(a);
        match r1.first() {
            Some(t) if is_op(t, ",") => r = &r1[1..],
            _ => return Ok((out, r1)),
        }
    }
}

fn call_args<'a>(h: &Hum, ts: &'a [HTok], scope: &Scope) -> R<(Vec<Term>, &'a [HTok])> {
    let mut out = vec![];
    let mut r = ts;
    loop {
        let (a, r1) = hum_expr(h, r, 0, scope)?;
        out.push(a);
        match r1.first() {
            Some(t) if is_op(t, ",") => r = &r1[1..],
            Some(t) if is_op(t, ")") => return Ok((out, &r1[1..])),
            None => return oob(),
            _ => return parse_err("missing ) in call"),
        }
    }
}

fn op_key(t: &HTok) -> Option<&str> {
    match t {
        HTok::Op(o) | HTok::Id(o) => Some(o),
        _ => None,
    }
}

pub fn hum_expr<'a>(h: &Hum, ts: &'a [HTok], minprec: i64, scope: &Scope) -> R<(Term, &'a [HTok])> {
    if ts.is_empty() {
        return oob();
    }
    // lambda:  x in Class |-> body
    if let (HTok::Id(name), Some(HTok::Id(w))) = (&ts[0], ts.get(1)) {
        if w == "in" {
            let (c, r1) = class_expr(h, &ts[2..])?;
            if r1.first().map_or(false, |t| is_op(t, "|->")) {
                let mut sc = scope.clone();
                sc.insert(name.clone());
                let (body, r3) = hum_expr(h, &r1[1..], 0, &sc)?;
                return Ok((Term::Lam(vec![(name.clone(), Some(c))], Box::new(body)), r3));
            }
        }
    }
    let t0 = &ts[0];
    let (left, r) = match op_key(t0) {
        Some(key) if h.prefix.contains_key(key) && !(matches!(t0, HTok::Id(_)) && scope.contains(key)) => {
            let (arg, r1) = hum_expr(h, &ts[1..], h.prefix[key], scope)?;
            (app(&format!("hum:prefix {}", key), vec![arg]), r1)
        }
        _ => atom(h, ts, scope)?,
    };
    let mut left = left;
    let mut r = r;
    loop {
        let step = match r.first().and_then(op_key) {
            Some(op) => match h.infix.get(op) {
                Some((prec, kind)) if *prec >= minprec => Some((op.to_string(), *prec, kind.clone())),
                _ => None,
            },
            None => None,
        };
        match step {
            Some((op, prec, kind)) => {
                let (right, r1) = hum_expr(h, &r[1..], if kind != "infixr" { prec + 1 } else { prec }, scope)?;
                left = app(&format!("hum:{}", op), vec![left, right]);
                r = r1;
            }
            None => return Ok((left, r)),
        }
    }
}

// statements
pub fn spec_name(h: &Hum, name: &str) -> String {
    match h.doc.find(name, &["value"]) {
        Some(e) if e.rhs.len() == 1 && !e.rhs[0].chars().all(|c| c == '0' || c == '1' || c == '.') => e.rhs[0].clone(),
        _ => name.to_string(),
    }
}

pub fn type_to_term(t: &Ty) -> Term {
    match t {
        Ty::V(n) => var(n),
        Ty::K(n, a) if a.is_empty() => var(n),
        Ty::K(n, a) => Term::App(Box::new(var(n)), a.iter().map(type_to_term).collect()),
        Ty::F => var("⊥"),
    }
}

fn tok_text(t: &HTok) -> String {
    match t {
        HTok::Num(s) | HTok::Str(s) | HTok::Id(s) | HTok::Op(s) => s.clone(),
        HTok::Chr(c) => char::from_u32(*c).unwrap_or('\u{fffd}').to_string(),
    }
}

fn param_list(ts: &[HTok]) -> R<(Vec<String>, &[HTok])> {
    let mut out = vec![];
    let mut r = ts;
    loop {
        match r.first() {
            Some(t) if is_op(t, ")") => return Ok((out, &r[1..])),
            Some(t) => {
                out.push(tok_text(t));
                r = &r[1..];
                if r.first().map_or(false, |x| is_op(x, ",")) {
                    r = &r[1..];
                }
            }
            None => return oob(),
        }
    }
}

pub fn hum_statement(h: &Hum, line: &str) -> R<Vec<Stmt>> {
    let ts = lex_hum(line)?;
    if let Some(k) = ts.iter().position(|t| matches!(t, HTok::Id(w) if w == "subseteq")) {
        let (a, ra) = class_expr(h, &ts[..k])?;
        let (b, rb) = class_expr(h, &ts[k + 1..])?;
        if !ra.is_empty() || !rb.is_empty() {
            return parse_err("assertion failed");
        }
        return Ok(vec![Stmt::Fact(app("⊆", vec![type_to_term(&a), type_to_term(&b)]))]);
    }
    match ts.first() {
        Some(HTok::Id(name)) => {
            let r0 = &ts[1..];
            let (params, r1) = if r0.first().map_or(false, |t| is_op(t, "(")) { param_list(&r0[1..])? } else { (vec![], r0) };
            match r1.first() {
                Some(HTok::Id(w)) if w == "in" => {
                    let (cls, r3) = class_expr(h, &r1[1..])?;
                    if r3.is_empty() {
                        if !params.is_empty() {
                            return parse_err(format!("{}: a declaration without := takes no parameters (an unknown is a number)", name));
                        }
                        return Ok(vec![Stmt::Decl(spec_name(h, name), cls)]);
                    }
                    if is_op(&r3[0], ":=") {
                        let sc: Scope = params.iter().cloned().collect();
                        let (body, r5) = hum_expr(h, &r3[1..], 0, &sc)?;
                        let sp = spec_name(h, name);
                        if let Some(t) = r5.first() {
                            return parse_err(format!("unexpected {}", show_tok(t)));
                        }
                        return Ok(vec![Stmt::Decl(sp.clone(), cls), Stmt::Def(sp, params, body)]);
                    }
                    parse_err("missing :=")
                }
                _ => parse_err(format!("declare the class first:  {} in <Class> := …", name)),
            }
        }
        _ => parse_err(format!("statement must start with a name: {}", py_repr(line))),
    }
}

pub fn hum_statements(h: &Hum, text: &str) -> R<Vec<Stmt>> {
    let mut out = vec![];
    for l in hum_logical_lines(text) {
        out.extend(hum_statement(h, &l)?);
    }
    Ok(out)
}
