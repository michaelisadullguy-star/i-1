//! layers.rs -- the three notation systems of i-1 and the system documents that connect them (port of haskimo/src/I1/Layers.hs).
//!
//!   bin   only  1 0 .  space ( ) newline
//!         numeral      1011  1.01                (<= 1 radix point)
//!         symbol       .B.                       B = a bit string (the code of the symbol, see doc 1)
//!         markers      .  =  ↦      ..  =  ≔      ...  =  ∶
//!   spec  unicode glyphs; the notation of the prelude (lib/*.imo); `⍝` starts a comment
//!   hum   ASCII/TeX-like notation (hum.rs)
//!
//!   doc 1   [spec sbl] := [bin sbl]            one line per symbol
//!   doc 2   [hum sbl]  := [spec sbl] or [bin sbl] ...
use crate::base::*;
use crate::syntax::*;
use std::collections::BTreeMap;

// ---------------------------------------------------------------- doc 1
#[derive(Clone)]
pub struct Doc1 {
    pub s2b: BTreeMap<String, String>,
    pub b2s: BTreeMap<String, String>,
    /// program-local symbols, in the order their codes were given
    pub local: Vec<(String, String)>,
}

/// .B. with B a non-empty bit string
pub fn is_bin_sym(s: &str) -> bool {
    let cs: Vec<char> = s.chars().collect();
    cs.len() >= 3 && cs[0] == '.' && cs[cs.len() - 1] == '.' && cs[1..cs.len() - 1].iter().all(|&c| c == '0' || c == '1')
}

impl Doc1 {
    pub fn empty() -> Doc1 {
        Doc1 { s2b: BTreeMap::new(), b2s: BTreeMap::new(), local: vec![] }
    }

    pub fn parse(text: &str) -> R<Doc1> {
        let mut d = Doc1::empty();
        for ln0 in text.split('\n') {
            let ln = strip(ln0);
            if ln.is_empty() || ln.starts_with('⍝') {
                continue;
            }
            let parts: Vec<&str> = ln.split(" := ").collect();
            if parts.len() != 2 {
                return parse_err(format!("doc1: bad line {}", py_repr(ln)));
            }
            let a = strip(parts[0]);
            let b = strip(parts[1]);
            if !is_bin_sym(b) {
                return parse_err(format!("doc1: bad binary symbol {}", py_repr(b)));
            }
            if d.s2b.contains_key(a) || d.b2s.contains_key(b) {
                return parse_err(format!("doc1: duplicate {} / {}", a, b));
            }
            d.s2b.insert(a.to_string(), b.to_string());
            d.b2s.insert(b.to_string(), a.to_string());
        }
        Ok(d)
    }


    /// the next free code:  .<max + 1 in binary>.
    fn next_code(&self) -> String {
        let mut n: u128 = 0;
        for b in self.b2s.keys() {
            let bits = &b[1..b.len() - 1];
            let mut v: u128 = 0;
            for c in bits.chars() {
                v = v * 2 + if c == '1' { 1 } else { 0 };
            }
            n = n.max(v);
        }
        let k = n + 1;
        format!(".{:b}.", k)
    }

    /// the code of a symbol; a new local code is given when allowed
    pub fn code(&mut self, name: &str, allow_new: bool) -> R<String> {
        if let Some(b) = self.s2b.get(name) {
            return Ok(b.clone());
        }
        if !allow_new {
            return parse_err(format!("{} has no binary symbol in doc 1", py_repr(name)));
        }
        let b = self.next_code();
        self.s2b.insert(name.to_string(), b.clone());
        self.b2s.insert(b.clone(), name.to_string());
        self.local.push((name.to_string(), b.clone()));
        Ok(b)
    }

    /// add a symbol of a program-local table (not counted as a symbol the program created)
    pub fn add_local(&mut self, a: &str, b: &str) {
        self.s2b.insert(a.to_string(), b.to_string());
        self.b2s.insert(b.to_string(), a.to_string());
    }

    /// the local table as text, in the format of doc 1
    pub fn render(&self, header: &[&str]) -> String {
        let mut out = String::new();
        for h in header {
            out.push_str(&format!("⍝ {}\n", h));
        }
        for (a, b) in &self.local {
            out.push_str(&format!("{} := {}\n", a, b));
        }
        out
    }
}

// ---------------------------------------------------------------- bin lexer / translators
enum BTok {
    Nl,
    Open,
    Close,
    Num(String),
    Mark(String),
    Sym(String),
}

fn reserved_spec(s: &str) -> Option<&'static str> {
    match s {
        "." => Some("↦"),
        ".." => Some("≔"),
        "..." => Some("∶"),
        _ => None,
    }
}

fn reserved_bin(s: &str) -> Option<&'static str> {
    match s {
        "↦" => Some("."),
        "≔" => Some(".."),
        "∶" => Some("..."),
        _ => None,
    }
}

fn lex_bin(text: &str) -> R<Vec<BTok>> {
    let cs: Vec<char> = text.chars().collect();
    let mut i = 0;
    let mut d: i64 = 0;
    let mut out = vec![];
    while i < cs.len() {
        let c = cs[i];
        if c == ' ' || c == '\t' || c == '\r' {
            i += 1;
        } else if c == '\n' {
            if d == 0 {
                out.push(BTok::Nl);
            }
            i += 1;
        } else if c == '(' {
            out.push(BTok::Open);
            d += 1;
            i += 1;
        } else if c == ')' {
            out.push(BTok::Close);
            d -= 1;
            i += 1;
        } else if c == '0' || c == '1' || c == '.' {
            let mut j = i;
            while j < cs.len() && (cs[j] == '0' || cs[j] == '1' || cs[j] == '.') {
                j += 1;
            }
            let s: String = cs[i..j].iter().collect();
            let pts = s.chars().filter(|&x| x == '.').count();
            if reserved_spec(&s).is_some() {
                out.push(BTok::Mark(s));
            } else if pts <= 1 {
                out.push(BTok::Num(s));
            } else if is_bin_sym(&s) {
                out.push(BTok::Sym(s));
            } else {
                return parse_err(format!("bad binary token {}", py_repr(&s)));
            }
            i = j;
        } else {
            return parse_err(format!("character {} is not part of the binary notation", py_repr(&c.to_string())));
        }
    }
    Ok(out)
}

/// tokens to text (spaces only between atoms; newlines kept).  None stands for a newline.
fn render_toks(toks: &[Option<String>]) -> String {
    let mut out = String::new();
    let mut first = true;
    for t in toks {
        match t {
            None => {
                out.push('\n');
                first = true;
            }
            Some(t) => {
                if !(t == ")" || first) {
                    out.push(' ');
                }
                out.push_str(t);
                first = t == "(";
            }
        }
    }
    out
}

/// bin text -> spec text, through doc 1 (and the program's local table)
pub fn bin_to_spec_text(text: &str, d: &Doc1) -> R<String> {
    let mut toks: Vec<Option<String>> = vec![];
    for t in lex_bin(text)? {
        toks.push(match t {
            BTok::Nl => None,
            BTok::Open => Some("(".to_string()),
            BTok::Close => Some(")".to_string()),
            BTok::Num(s) => Some(s),
            BTok::Mark(s) => reserved_spec(&s).map(|r| r.to_string()),
            BTok::Sym(s) => match d.b2s.get(&s) {
                Some(n) => Some(n.clone()),
                None => return parse_err(format!("binary symbol {} is not defined in doc 1 (or the local table)", s)),
            },
        });
    }
    Ok(render_toks(&toks))
}

/// the statements re-spelled in bin notation; new program-local symbols get codes in order of first use
pub fn spec_statements_to_bin_text(sts: &[Stmt], d: &mut Doc1, allow_new: bool) -> R<String> {
    let mut toks: Vec<Option<String>> = vec![];
    for st in sts {
        for t in lex_spec(&pp_statement(st))? {
            match t {
                Tok::Open => toks.push(Some("(".to_string())),
                Tok::Close => toks.push(Some(")".to_string())),
                Tok::Num(s) => toks.push(Some(s)),
                Tok::Name(n) => match reserved_bin(&n) {
                    Some(r) => toks.push(Some(r.to_string())),
                    None => toks.push(Some(d.code(&n, allow_new)?)),
                },
                Tok::Chr(c) => {
                    let bc = d.code("𝕔", allow_new)?;
                    toks.extend([Some("(".to_string()), Some(bc), Some(int_numeral_text(c as u64)), Some(")".to_string())]);
                }
                Tok::Str(s) => {
                    let bcons = d.code("∷", allow_new)?;
                    let bchr = d.code("𝕔", allow_new)?;
                    let bnil = d.code("⊘", allow_new)?;
                    for ch in s.chars() {
                        toks.extend([
                            Some("(".to_string()),
                            Some(bcons.clone()),
                            Some("(".to_string()),
                            Some(bchr.clone()),
                            Some(int_numeral_text(ch as u64)),
                            Some(")".to_string()),
                        ]);
                    }
                    toks.push(Some(bnil));
                    for _ in s.chars() {
                        toks.push(Some(")".to_string()));
                    }
                }
                Tok::Nl => {}
            }
        }
        toks.push(None);
    }
    Ok(render_toks(&toks))
}

/// one spec term (as text) -> the same term in bin notation, through doc 1 (literals are expanded as the reader expands them)
pub fn spec_term_to_bin(text: &str, d: &mut Doc1) -> R<String> {
    let mut toks: Vec<Option<String>> = vec![];
    for t in lex_spec(text)? {
        match t {
            Tok::Open => toks.push(Some("(".to_string())),
            Tok::Close => toks.push(Some(")".to_string())),
            Tok::Num(s) => toks.push(Some(s)),
            Tok::Name(n) => match reserved_bin(&n) {
                Some(r) => toks.push(Some(r.to_string())),
                None => toks.push(Some(d.code(&n, false)?)),
            },
            Tok::Chr(c) => {
                let bc = d.code("𝕔", false)?;
                toks.extend([Some("(".to_string()), Some(bc), Some(int_numeral_text(c as u64)), Some(")".to_string())]);
            }
            Tok::Str(s) => {
                for ch in s.chars() {
                    let bcons = d.code("∷", false)?;
                    let bchr = d.code("𝕔", false)?;
                    toks.extend([
                        Some("(".to_string()),
                        Some(bcons),
                        Some("(".to_string()),
                        Some(bchr),
                        Some(int_numeral_text(ch as u64)),
                        Some(")".to_string()),
                    ]);
                }
                toks.push(Some(d.code("⊘", false)?));
                for _ in s.chars() {
                    toks.push(Some(")".to_string()));
                }
            }
            Tok::Nl => {}
        }
    }
    Ok(render_toks(&toks))
}

// ---------------------------------------------------------------- files: default notation by extension, `@bin` `@spec` `@hum` section headers
pub fn split_sections(text: &str, def: &str) -> Vec<(String, String)> {
    let mut mode = def.to_string();
    let mut cur: Vec<&str> = vec![];
    let mut acc: Vec<(String, String)> = vec![];
    for ln in text.split('\n') {
        let s = strip(ln);
        if s == "@bin" || s == "@spec" || s == "@hum" {
            if !cur.is_empty() {
                acc.push((mode.clone(), cur.join("\n")));
            }
            cur.clear();
            mode = s[1..].to_string();
        } else {
            cur.push(ln);
        }
    }
    if !cur.is_empty() {
        acc.push((mode, cur.join("\n")));
    }
    acc
}

pub fn default_notation(path: &str) -> &'static str {
    if path.ends_with(".bin.imo") {
        "bin"
    } else if path.ends_with(".hum.imo") {
        "hum"
    } else {
        "spec"
    }
}
