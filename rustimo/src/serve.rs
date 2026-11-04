//! serve.rs -- "rustimo serve FILE...": a loaded program as a service, for the shared test suite (port of haskimo/src/I1/Serve.hs).
//!
//! The library suites of tests/ were written against the Python API of Pymo (load a program, take the value of a symbol, decode it).
//! To run the same suites on Rustimo, tests/core_serve.py starts  rustimo serve  and speaks this protocol: one request per line on
//! standard input, one answer per line on standard output.  Values stay inside rustimo and are named by HANDLES (small numbers);
//! only digit strings, truth values and the shape of lists and pairs cross the pipe — what the Python decoders (to_list, to_pair,
//! to_bool, stream_nth) read from a value in Pymo.
//!
//!   after the load:  OK   |   ERRORS n   followed by n lines  file TAB what TAB message
//!
//!   NAME x            -> S spec-name           the spec symbol of a human name (hum::spec_name)
//!   V s               -> H h                   the value of the global s
//!   APPLY f a ...     -> H h                   f applied to the values a ...  (lazily)
//!   MK bits           -> H h                   a digit list (least significant digit first; bits may be empty)
//!   CELL h            -> N  |  C hh ht         a list cell
//!   LIST h            -> L n h1 ... hn         all the elements of a (finite) list
//!   PAIR h            -> P ha hb
//!   BOOL h            -> B 1 | B 0 | B ?
//!   DIGITS h          -> D bits                a digit list, least significant digit first
//!   Q h               -> Q zbits|dbits         a pair of digit lists (an element of ℚ[i])
//!   ORD h             -> O k                   an ordering (0, 1 or 2: the alternative it selects)
//!   NTH h n           -> H h'                  element n of a stream
//!   CLASS s           -> T json                the declared class of the symbol s, normalised: ["K",name,[args]] ["V",name] ["F","⊥"]
//!   an error          -> ERR message           (on one line)
use crate::base::*;
use crate::core::*;
use crate::hum::spec_name;
use crate::program::Program;
use crate::syntax::*;
use std::io::{BufRead, Write};

fn bits_of(ds: &[u8]) -> String {
    ds.iter().map(|&d| if d == 1 { '1' } else { '0' }).collect()
}

fn json(t: &Ty) -> String {
    fn s(x: &str) -> String {
        let mut out = String::from("\"");
        for c in x.chars() {
            match c {
                '"' => out.push_str("\\\""),
                '\\' => out.push_str("\\\\"),
                c => out.push(c),
            }
        }
        out.push('"');
        out
    }
    match t {
        Ty::K(n, args) => format!("[\"K\",{},[{}]]", s(n), args.iter().map(json).collect::<Vec<_>>().join(",")),
        Ty::V(n) => format!("[\"V\",{}]", s(n)),
        Ty::F => "[\"F\",\"⊥\"]".to_string(),
    }
}

fn one_line(s: &str) -> String {
    s.chars().map(|c| if c == '\n' || c == '\t' { ' ' } else { c }).collect()
}

pub fn serve(p: &Program) -> R<()> {
    let m = p.machine();
    let mut table: Vec<V> = vec![];
    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    let mut out = std::io::BufWriter::new(stdout.lock());
    let new = |v: V, table: &mut Vec<V>| -> usize {
        table.push(v);
        table.len() - 1
    };
    let get = |h: &str, table: &Vec<V>| -> R<V> {
        match h.parse::<usize>() {
            Ok(i) => table.get(i).cloned().ok_or_else(|| Err::Eval(format!("no handle {}", h))),
            Err(_) => Err(Err::Eval(format!("bad handle {}", py_repr(h)))),
        }
    };
    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        let ws: Vec<&str> = line.split_whitespace().collect();
        if ws == ["QUIT"] {
            break;
        }
        let r: R<String> = (|| -> R<String> {
            match ws.as_slice() {
                ["NAME", n] => Ok(format!("S {}", spec_name(&p.hum, n))),
                ["V", n] => {
                    if m.has_global(n) {
                        let h = new(m.global(n)?, &mut table);
                        Ok(format!("H {}", h))
                    } else {
                        Err(Err::Eval(format!("{} is not defined", n)))
                    }
                }
                ["APPLY", f, as_ @ ..] => {
                    let fv = get(f, &table)?;
                    let avs = as_.iter().map(|a| get(a, &table)).collect::<R<Vec<_>>>()?;
                    let h = new(m.app(&fv, &avs), &mut table);
                    Ok(format!("H {}", h))
                }
                ["MK", rest @ ..] => {
                    let bits: String = rest.concat();
                    let ds: Vec<u8> = bits.chars().map(|c| if c == '1' { 1 } else { 0 }).collect();
                    let h = new(m.list_value(&ds)?, &mut table);
                    Ok(format!("H {}", h))
                }
                ["CELL", h] => {
                    let v = get(h, &table)?;
                    match m.cell_or_nil(&v)? {
                        Val::Cons(a, b) => {
                            let ha = new(a, &mut table);
                            let hb = new(b, &mut table);
                            Ok(format!("C {} {}", ha, hb))
                        }
                        Val::Nil => Ok("N".to_string()),
                        _ => Err(Err::Eval("a list was expected".to_string())),
                    }
                }
                ["LIST", h] => {
                    let mut cur = get(h, &table)?;
                    let mut hs = vec![];
                    loop {
                        match m.cell_or_nil(&cur)? {
                            Val::Cons(a, b) => {
                                hs.push(new(a, &mut table));
                                cur = b;
                            }
                            Val::Nil => break,
                            _ => return Err(Err::Eval("a list was expected".to_string())),
                        }
                    }
                    let mut s = format!("L {}", hs.len());
                    for h in hs {
                        s.push_str(&format!(" {}", h));
                    }
                    Ok(s)
                }
                ["PAIR", h] => {
                    let v = get(h, &table)?;
                    let (a, b) = m.to_pair(&v)?;
                    let ha = new(a, &mut table);
                    let hb = new(b, &mut table);
                    Ok(format!("P {} {}", ha, hb))
                }
                ["BOOL", h] => {
                    let v = get(h, &table)?;
                    Ok(match m.tri(&v)? {
                        Some(true) => "B 1",
                        Some(false) => "B 0",
                        None => "B ?",
                    }
                    .to_string())
                }
                ["DIGITS", h] => {
                    let v = get(h, &table)?;
                    Ok(format!("D {}", bits_of(&m.to_list(&v)?)))
                }
                ["Q", h] => {
                    let v = get(h, &table)?;
                    let (z, d) = m.to_pair(&v)?;
                    Ok(format!("Q {}|{}", bits_of(&m.to_list(&z)?), bits_of(&m.to_list(&d)?)))
                }
                ["ORD", h] => {
                    let v = get(h, &table)?;
                    Ok(format!("O {}", m.to_ord(&v)?))
                }
                ["NTH", h, n] => {
                    let v = get(h, &table)?;
                    let k: usize = n.parse().map_err(|_| Err::Eval("Prelude.read: no parse".to_string()))?;
                    let e = m.stream_nth(&v, k)?;
                    let r = new(e, &mut table);
                    Ok(format!("H {}", r))
                }
                ["CLASS", s] => match p.checker.sigs.get(*s).and_then(|v| v.first()) {
                    Some(t) => Ok(format!("T {}", json(&p.checker.norm(t)))),
                    None => Err(Err::Eval(format!("{} has no declared class", s))),
                },
                _ => Err(Err::Eval(format!("bad request {}", py_repr(&ws.join(" "))))),
            }
        })();
        let reply = match r {
            Ok(s) => s,
            Err(e) => format!("ERR {}", one_line(e.text())),
        };
        writeln!(out, "{}", reply).ok();
        out.flush().ok();
    }
    Ok(())
}
