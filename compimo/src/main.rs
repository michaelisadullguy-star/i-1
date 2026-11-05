//! main.rs -- command line of Compimo, the compiler of i-1: the front end is the one of Rustimo (the files in rustimo/src), the evaluator is C that is generated (gen.rs), compiled and loaded (core.rs).
//!
//!   compimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  compimo FILE...)
//!   compimo check   FILE...                                load the prelude and FILE(s), run the class checker
//!   compimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table
//!   compimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class
//! The commands, options and output are those of  python3 pymo/i1.py  (Pymo) and of  haskimo  (Haskimo): the three cores are parallel.
#[path = "../../rustimo/src/base.rs"]
mod base;
#[path = "../../rustimo/src/bigint.rs"]
mod bigint;
#[path = "../../rustimo/src/data.rs"]
mod data;
#[path = "../../rustimo/src/hum.rs"]
mod hum;
#[path = "../../rustimo/src/layers.rs"]
mod layers;
#[path = "../../rustimo/src/output.rs"]
mod output;
#[path = "../../rustimo/src/quote.rs"]
mod quote;
#[path = "../../rustimo/src/syntax.rs"]
mod syntax;
#[path = "../../rustimo/src/types.rs"]
mod types;
mod core;
mod gen;
mod program;
mod selftest;

use crate::base::*;
use crate::bigint::{Int, Rat};
use crate::core::*;
use crate::hum::spec_name;
use crate::output::*;
use crate::program::*;
use crate::syntax::*;
use std::io::{IsTerminal, Write};
use std::path::Path;

const USAGE: &str = "compimo -- Compimo, the compiler of i-1: the program is translated to C and compiled (same commands and output as Pymo, Haskimo and Rustimo)

  compimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  compimo FILE...)
  compimo check   FILE...                                load the prelude and FILE(s), run the class checker
  compimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table
  compimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class (value, stream element N, tree, string, Bool)
  compimo text    FILE... NAME                           evaluate NAME as a String and print it
  compimo prelude                                        compile the prelude into the cache now (a few minutes, once)
  compimo selftest [N] [SEED] [--against EXE]            the native arithmetic against the definitions (and against another core)

`run` prints main ∶ 𝕊 as text, a list or stream of strings line by line, and any other value as a normal-form term in the output
notation: --out, else an `@out bin|spec|hum` line in the program, else the notation main is written in.  --n N picks the stream
element shown for a stream (default 10), or the number of lines of a stream of strings.

FILE notation follows the extension:  x.imo / x.spec.imo = spec,  x.hum.imo = human,  x.bin.imo = binary (prelude.bin.imo is trusted).
";

/// standard output: a terminal sees the output as it is produced, a pipe gets blocks
struct Out {
    w: std::io::BufWriter<std::io::Stdout>,
    tty: bool,
}

impl Out {
    fn new() -> Out {
        let so = std::io::stdout();
        let tty = so.is_terminal();
        Out { w: std::io::BufWriter::with_capacity(1 << 16, so), tty }
    }
    fn put(&mut self, s: &str) {
        let _ = self.w.write_all(s.as_bytes());
        if self.tty {
            let _ = self.w.flush();
        }
    }
    fn line(&mut self, s: &str) {
        self.put(s);
        self.put("\n");
    }
    fn flush(&mut self) {
        let _ = self.w.flush();
    }
}

fn load_files(files: &[String], build: bool) -> R<Program> {
    let mut srcs = vec![];
    for f in files {
        let text = read_utf8(f).map_err(|e| match e.kind() {
            std::io::ErrorKind::InvalidData => Err::Parse(format!("{}: hGetContents: invalid argument ({})", f, e)),
            _ => Err::Parse(format!("{}: openFile: {}", f, io_reason(&e))),
        })?;
        srcs.push(SourceFile { path: f.clone(), text });
    }
    let prelude: Vec<String> = files.iter().filter(|f| f.ends_with("prelude.bin.imo")).cloned().collect();
    let mut p = load_program(&srcs, &prelude, prelude.is_empty())?;
    let missing = p.missing()?;
    if !missing.is_empty() {
        return parse_err(format!("these symbols are used and not defined: {}", missing.join(" ")));
    }
    let _ = build;
    Ok(p)
}

fn io_reason(e: &std::io::Error) -> String {
    match e.kind() {
        std::io::ErrorKind::NotFound => "does not exist (No such file or directory)".to_string(),
        _ => e.to_string(),
    }
}

fn report_errors(out: &mut Out, p: &Program) {
    for (f, w, m) in &p.errors {
        let text = if m.starts_with(w.as_str()) { m.clone() } else { format!("{}: {}", w, m) };
        out.line(&format!("error in {}: {}", basename(f), text));
    }
}

// ---------------------------------------------------------------- values of ℚ[i], as Pymo shows them
struct Q {
    re: Rat,
    im: Rat,
}

fn qval(m: &Machine, v: &V) -> R<Q> {
    let (p, d) = m.to_pair(v)?;
    let (a0, a1) = m.gi_of(&p)?;
    let (b0, b1) = m.gi_of(&d)?;
    let n = b0.mul(&b0).add(&b1.mul(&b1));
    if n.is_zero() {
        return Err(Err::Eval("Ratio has zero denominator".to_string()));
    }
    Ok(Q { re: Rat::new(a0.mul(&b0).add(&a1.mul(&b1)), n.clone()), im: Rat::new(a1.mul(&b0).sub(&a0.mul(&b1)), n) })
}

fn show_frac(r: &Rat) -> String {
    if r.is_int() {
        r.num.to_dec()
    } else {
        format!("{}/{}", r.num.to_dec(), r.den.to_dec())
    }
}

fn qfmt(m: &Machine, v: &V) -> R<String> {
    let q = qval(m, v)?;
    let s = if q.im.is_zero() { show_frac(&q.re) } else { format!("{} + {} i", show_frac(&q.re), show_frac(&q.im)) };
    let tail = if q.im.is_zero() { String::new() } else { format!(" + {} i", fmt_g(12, q.im.to_f64())) };
    Ok(format!("{}   (≈ {}{})", s, fmt_g(12, q.re.to_f64()), tail))
}

fn sfmt(m: &Machine, v: &V) -> R<String> {
    let mut out = String::new();
    let mut cur = v.clone();
    loop {
        match m.cell_or_nil(&cur)? {
            Val::Cons(h, t) => {
                let q = qval(m, &h)?;
                let k = q.re.truncate().to_i64().unwrap_or(0xfffd);
                out.push(u32::try_from(k).ok().and_then(char::from_u32).unwrap_or('\u{fffd}'));
                cur = t;
            }
            _ => return Ok(out),
        }
    }
}

fn tfmt(p: &Program, v: &V, n: Option<usize>) -> R<String> {
    let m = p.machine();
    let left_f = p.val("◀")?;
    let right_f = p.val("▶")?;
    let is_left = m.app(&left_f, &[v.clone()]);
    if m.to_bool(&is_left)? {
        let r = m.app(&right_f, &[v.clone()]);
        let (a, b) = m.to_pair(&r)?;
        Ok(format!("⟨{}, {}⟩", tfmt(p, &a, n)?, tfmt(p, &b, n)?))
    } else {
        let leaf0 = m.app(&right_f, &[v.clone()]);
        let leaf = match n {
            Some(k) => m.stream_nth(&leaf0, k)?,
            None => leaf0,
        };
        let q = qval(m, &leaf)?;
        Ok(match n {
            Some(_) => format!("{}{}", fmt_g(10, q.re.to_f64()), if q.im.is_zero() { String::new() } else { format!(" + {} i", fmt_g(10, q.im.to_f64())) }),
            None => {
                if q.im.is_zero() {
                    show_frac(&q.re)
                } else {
                    format!("({} + {} i)", show_frac(&q.re), show_frac(&q.im))
                }
            }
        })
    }
}

/// evaluate NAME and print it according to its declared class
fn show_name(p: &Program, name: &str, n: Option<usize>) -> R<String> {
    let c = &p.checker;
    let m = p.machine();
    let cls = match c.sigs.get(name).and_then(|v| v.first()) {
        Some(t) => c.norm(t),
        None => return Err(Err::Eval("Prelude.head: empty list".to_string())),
    };
    let v = p.val(name)?;
    let hd = match &cls {
        Ty::K(h, _) => h.as_str(),
        _ => "",
    };
    match &cls {
        Ty::K(h, _) if h == "𝔖" || h == "ℝ" => {
            let k = n.unwrap_or(10);
            return Ok(format!("element {} of the stream:  {}", k, qfmt(m, &m.stream_nth(&v, k)?)?));
        }
        Ty::K(h, a) if h == "𝔏" && a.len() == 1 && matches!(&a[0], Ty::K(x, _) if x == "𝕮") => return sfmt(m, &v),
        Ty::K(h, a) if h == "𝔗" && a.len() == 1 => {
            let streams = matches!(&a[0], Ty::K(x, _) if x == "𝔖");
            let k = n.unwrap_or(10);
            let body = tfmt(p, &v, if streams { Some(k) } else { None })?;
            return Ok(format!("{}{}", if streams { format!("element {} of each leaf:  ", k) } else { String::new() }, body));
        }
        _ => {}
    }
    if hd == "𝔹" {
        return Ok(if m.to_bool(&v)? { "true" } else { "false" }.to_string());
    }
    if show_type(&cls).contains('Ω') {
        return Printer::new(p, "hum", 10).show_value(&v, &cls);
    }
    qfmt(m, &v)
}

// ---------------------------------------------------------------- commands
/// remove  OPT value  from an argument list
fn take_opt(opt: &str, args: &[String]) -> (Option<String>, Vec<String>) {
    if let Some(i) = args.iter().position(|a| a == opt) {
        if i + 1 < args.len() {
            let mut rest: Vec<String> = args[..i].to_vec();
            rest.extend_from_slice(&args[i + 2..]);
            return (Some(args[i + 1].clone()), rest);
        }
    }
    (None, args.to_vec())
}

fn read_int(s: &str) -> R<usize> {
    s.trim().parse::<usize>().map_err(|_| Err::Eval("Prelude.read: no parse".to_string()))
}

fn run_cmd(out: &mut Out, args0: &[String]) -> R<i32> {
    let (o, r1) = take_opt("--out", args0);
    let (n_opt, rest) = take_opt("--n", &r1);
    if let Some(o) = &o {
        if !MODES.contains(&o.as_str()) {
            out.line(&format!("--out takes one of {}", MODES.join(", ")));
            return Ok(2);
        }
    }
    let mut p = load_files(&rest, true)?;
    if !p.errors.is_empty() {
        report_errors(out, &p);
        return Ok(1);
    }
    p.build(&[])?;
    let n = match &n_opt {
        Some(s) => Some(read_int(s)?),
        None => None,
    };
    let r = run_main(&p, o.as_deref(), n, &mut |s| out.put(s));
    match r {
        Ok(_) => Ok(0),
        Err(Err::Print(e)) => {
            out.line(&format!("error: {}", e));
            Ok(1)
        }
        Err(e) => Err(e),
    }
}

fn translate_cmd(out: &mut Out, rest: &[String]) -> R<i32> {
    let to = match rest.iter().position(|a| a == "--to") {
        Some(i) if i + 1 < rest.len() => rest[i + 1].clone(),
        _ => return Err(Err::Eval("--to is missing".to_string())),
    };
    let files: Vec<String> = rest.iter().filter(|x| *x != "--to" && **x != to).cloned().collect();
    let mut p = load_files(&files, false)?;
    if !p.errors.is_empty() {
        report_errors(out, &p);
        return Ok(1);
    }
    if to == "spec" {
        out.put(&p.spec_text());
    } else {
        let t = p.bin_text()?;
        out.put(&t);
        if !p.doc1.local.is_empty() {
            out.put(&format!("\n{}", p.local_table()));
        }
    }
    Ok(0)
}

fn query_cmd(out: &mut Out, cmd: &str, rest: &[String]) -> R<i32> {
    let (files, name, n): (Vec<String>, Option<String>, Option<usize>) = if cmd == "check" {
        (rest.to_vec(), None, None)
    } else {
        let fs: Vec<String> = rest.iter().filter(|x| Path::new(x.as_str()).is_file()).cloned().collect();
        let tl: Vec<&String> = rest.iter().filter(|x| !Path::new(x.as_str()).is_file()).collect();
        if tl.is_empty() {
            return parse_err("a name is expected");
        }
        let n = match tl.get(1) {
            Some(k) => Some(read_int(k)?),
            None => None,
        };
        (fs, Some(tl[0].clone()), n)
    };
    let mut p = load_files(&files, cmd != "check")?;
    if !p.errors.is_empty() {
        report_errors(out, &p);
        return Ok(1);
    }
    if cmd == "check" {
        out.line(&format!("ok: {} statements checked", p.user_statements().len()));
        return Ok(0);
    }
    let nm = spec_name(&p.hum, name.as_deref().unwrap_or(""));
    p.build(&[nm.clone()])?;
    let r: R<String> = if cmd == "text" { p.val(&nm).and_then(|v| sfmt(p.machine(), &v)) } else { show_name(&p, &nm, n) };
    match r {
        Ok(s) => {
            out.line(&s);
            Ok(0)
        }
        Err(Err::Unknown(m)) | Err(Err::Print(m)) => {
            out.line(&format!("error: {}", m));
            Ok(1)
        }
        Err(e) => Err(e),
    }
}

fn dispatch(out: &mut Out, args: &[String]) -> R<i32> {
    if args.is_empty() {
        out.put(USAGE);
        return Ok(0);
    }
    if args[0] == "-h" || args[0] == "--help" {
        out.put(USAGE);
        return Ok(0);
    }
    let cmd = args[0].as_str();
    let known = ["run", "check", "eval", "text", "translate", "selftest", "prelude"];
    let (cmd2, rest): (&str, &[String]) = if !known.contains(&cmd) && Path::new(cmd).is_file() { ("run", args) } else { (cmd, &args[1..]) };
    match cmd2 {
        "run" => run_cmd(out, rest),
        "selftest" => Ok(selftest::selftest(rest)),
        "prelude" => {
            // compile the prelude into the cache now (the first run of every program otherwise does it)
            let mut p = load_files(&[], true)?;
            p.build(&[])?;
            out.line("the prelude is compiled and cached");
            Ok(0)
        }
        "translate" => translate_cmd(out, rest),
        "check" | "eval" | "text" => query_cmd(out, cmd2, rest),
        _ => {
            out.put(USAGE);
            Ok(2)
        }
    }
}

fn real_main(args: Vec<String>) -> i32 {
    let mut out = Out::new();
    let code = match dispatch(&mut out, &args) {
        Ok(c) => c,
        Err(e) => {
            out.flush();
            eprintln!("compimo: {}", e.text());
            1
        }
    };
    out.flush();
    code
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    // the evaluator keeps its stack on the heap; the host recursion (reading, checking, printing nested terms) gets a large stack,
    // the largest the system gives (the memory is only used as deep as the recursion goes)
    for mb in [16384usize, 4096, 1024, 256, 64, 16] {
        let a = args.clone();
        if let Ok(child) = std::thread::Builder::new().stack_size(mb << 20).spawn(move || real_main(a)) {
            // a panic (a bug of the interpreter, not an error of a program) is an exit with status 1, as the crash of the host is in the other cores
            let code = child.join().unwrap_or(1);
            std::process::exit(code);
        }
    }
    eprintln!("compimo: cannot start the interpreter thread");
    std::process::exit(1);
}

#[allow(dead_code)]
fn _unused(_: &Int) {}
