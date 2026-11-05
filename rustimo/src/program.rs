//! program.rs -- loader / driver for i-1 programs (port of haskimo/src/I1/Program.hs and pymo/imo.py).
//!
//! A file is read in the notation chosen by its extension (x.bin.imo, x.hum.imo, x.imo = spec) or by section headers
//! (@bin  @spec  @hum on a line of their own).  Every section is translated to spec statements, the whole program is
//! checked by the class checker, and the definitions are run by the evaluator (lazy, call-by-need).
//!
//! A symbol that the program declares and never defines is an UNKNOWN: its class must be a number class, a statement about it is
//! simplified by lib/solve.imo, and evaluating it is a run-time error (Err::Unknown).
use crate::base::*;
use crate::core::*;
use crate::data;
use crate::hum::*;
use crate::layers::*;
use crate::quote::*;
use crate::syntax::*;
use crate::types::*;
use std::collections::{BTreeSet, HashMap, HashSet};

pub struct Program {
    pub doc1: Doc1,
    pub doc2: Doc2,
    pub hum: Hum,
    /// file, statement, trusted
    pub statements: Vec<(String, Stmt, bool)>,
    pub checker: Checker,
    /// aligned with `statements` (None: the statement had an error)
    pub resolved: Vec<Option<Stmt>>,
    /// file, what, message
    pub errors: Vec<(String, String, String)>,
    /// defined symbol -> the notation of the section that defines it
    pub notation_of: HashMap<String, String>,
    /// set by an  @out bin|spec|hum  line
    pub out_mode: Option<String>,
    /// the number of statements that came from the embedded prelude (they are first, and trusted)
    pub pre_count: usize,
    /// the definitions of the program itself, erased to de Bruijn terms (made by `check`)
    user_defs: Vec<(String, Core)>,
    /// every name that is defined (prelude and program), made by `check`
    defined: HashSet<String>,
    pub machine: Option<Machine>,
}

pub struct SourceFile {
    pub path: String,
    pub text: String,
}

impl Program {
    pub fn new() -> R<Program> {
        let d1 = Doc1::parse(data::DOC1)?;
        let d2 = Doc2::parse(data::DOC2)?.remap(&d1);
        let mut checker = Checker::new();
        checker.overloads = d2.overload_table();
        Ok(Program {
            doc1: d1,
            hum: mk_hum(d2.clone()),
            doc2: d2,
            statements: vec![],
            checker,
            resolved: vec![],
            errors: vec![],
            notation_of: HashMap::new(),
            out_mode: None,
            pre_count: 0,
            user_defs: vec![],
            defined: HashSet::new(),
            machine: None,
        })
    }

    /// add the text of a file (or of a string) in the given default notation
    pub fn add_text(&mut self, text: &str, name: &str, trusted: bool, notation: &str) -> R<()> {
        let mut out_mode = self.out_mode.clone();
        let mut lines: Vec<String> = vec![];
        for ln in text.split('\n') {
            let words: Vec<&str> = ln.split_whitespace().collect();
            if words.len() == 2 && words[0] == "@out" {
                let w = words[1];
                if w == "bin" || w == "spec" || w == "hum" {
                    out_mode = Some(w.to_string());
                    lines.push(String::new());
                    continue;
                }
                return parse_err(format!("{}: @out takes bin, spec or hum, not {}", name, w));
            }
            lines.push(ln.to_string());
        }
        let text2 = lines.join("\n");
        self.out_mode = out_mode;
        for (mode, chunk) in split_sections(&text2, notation) {
            let sts = match mode.as_str() {
                "spec" => parse_statements(&chunk)?,
                "bin" => parse_statements(&bin_to_spec_text(&chunk, &self.doc1)?)?,
                _ => hum_statements(&self.hum, &chunk)?,
            };
            if !trusted {
                for st in &sts {
                    if let Stmt::Def(n, _, _) = st {
                        self.notation_of.insert(n.clone(), mode.clone());
                    }
                }
            }
            for st in sts {
                self.statements.push((name.to_string(), st, trusted));
            }
        }
        Ok(())
    }

    /// add a file; a bin program brings its local symbol table (x.sbl next to x.bin.imo)
    pub fn add_file(&mut self, f: &SourceFile, trusted: bool) -> R<()> {
        let path = &f.path;
        let before = match path.rfind(".imo") {
            Some(k) => &path[..k],
            None => path.as_str(),
        };
        let local = format!("{}.sbl", before.replace(".bin", "").replace(".hum", "").replace(".spec", ""));
        let uses_bin = default_notation(path) == "bin" || format!("\n{}", f.text).contains("\n@bin");
        if uses_bin && std::path::Path::new(&local).is_file() {
            let tbl = read_utf8(&local).map_err(|e| Err::Parse(format!("{}: {}", local, e)))?;
            for line in tbl.split('\n') {
                if line.contains(" := ") && !line.starts_with('⍝') {
                    let parts: Vec<&str> = line.split(" := ").collect();
                    if parts.len() != 2 {
                        return parse_err(format!("bad line in {}", basename(&local)));
                    }
                    let a = strip(parts[0]);
                    let b = strip(parts[1]);
                    if self.doc1.s2b.contains_key(a) {
                        continue;
                    }
                    if let Some(other) = self.doc1.b2s.get(b) {
                        return parse_err(format!(
                            "{}: local code {} for {} is already doc 1's code for {} (doc 1 grew: regenerate the local table with  i1.py translate … --to bin)",
                            basename(&local),
                            b,
                            a,
                            other
                        ));
                    }
                    self.doc1.add_local(a, b);
                }
            }
        }
        self.add_text(&f.text, path, trusted, default_notation(path))
    }

    // ------------------------------------------------------------ checking
    /// check the program: class errors are collected in `errors`; the statements that mention a relation on ℝ[i] or an unknown are
    /// then written as codes (quote.rs)
    pub fn check(&mut self) -> R<()> {
        self.statements.retain(|(f, _, _)| f != "<quote>");
        Program::unknowns_of(&mut self.checker, &self.statements);
        let n = self.statements.len();
        let mut resolved: Vec<Option<Stmt>> = Vec::with_capacity(n);
        let mut errors: Vec<(String, String, String)> = vec![];
        for i in 0..n {
            let r = {
                let (_, st, trusted) = &self.statements[i];
                self.checker.check_statement(st, *trusted)?
            };
            match r {
                Ok(Some(new)) => resolved.push(Some(new)),
                Ok(None) => {
                    // as written: a statement of the prelude moves to `resolved`, the others are copied (they are small)
                    if self.statements[i].2 {
                        resolved.push(Some(std::mem::replace(&mut self.statements[i].1, Stmt::Fact(Term::Num(String::new())))));
                    } else {
                        resolved.push(Some(self.statements[i].1.clone()));
                    }
                }
                Err(e) => {
                    let st = &self.statements[i].1;
                    let what = match st {
                        Stmt::Def(n, _, _) => n.clone(),
                        Stmt::Decl(n, _) => n.clone(),
                        _ => pp_statement(st),
                    };
                    errors.push((self.statements[i].0.clone(), what, e));
                    resolved.push(None);
                }
            }
        }
        let mut defs_for_taint: Vec<(String, Vec<String>, Term)> = vec![];
        for ((_, _, t), r) in self.statements.iter().zip(resolved.iter()) {
            if let (false, Some(Stmt::Def(n, ps, b))) = (*t, r) {
                defs_for_taint.push((n.clone(), ps.clone(), b.clone()));
            }
        }
        self.checker.settle_taint(&defs_for_taint);
        self.resolved = resolved;
        self.errors = errors;
        if !self.errors.is_empty() {
            return Ok(());
        }
        self.codes_of()?;
        if self.resolved.iter().any(|r| matches!(r, Some(Stmt::Def(_, _, b)) if has_quote(b))) {
            self.quote_program()?;
        }
        // the definitions of the program, in de Bruijn form (those of the embedded prelude are erased when they are first needed)
        self.defined = HashSet::new();
        self.user_defs = vec![];
        for (i, r) in self.resolved.iter().enumerate() {
            if let Some(Stmt::Def(n, ps, b)) = r {
                self.defined.insert(n.clone());
                if i >= self.pre_count {
                    self.user_defs.push(erase_def(n, ps, b)?);
                }
            }
        }
        Ok(())
    }

    /// the unknowns (declared by the program, defined nowhere), in declaration order, and a first estimate of which program
    /// definitions need their values
    fn unknowns_of(c: &mut Checker, stmts: &[(String, Stmt, bool)]) {
        let defined: HashSet<&str> = stmts
            .iter()
            .filter_map(|(_, s, _)| match s {
                Stmt::Def(n, _, _) => Some(n.as_str()),
                _ => None,
            })
            .collect();
        let mut order: Vec<String> = vec![];
        let mut seen: HashSet<String> = HashSet::new();
        for (_, s, trusted) in stmts {
            if let (Stmt::Decl(n, ty), false) = (s, *trusted) {
                if defined.contains(n.as_str()) || is_class_or_stmt(ty) {
                    continue;
                }
                if seen.insert(n.clone()) {
                    order.push(n.clone());
                }
            }
        }
        let user: Vec<(&String, &Vec<String>, &Term)> = stmts
            .iter()
            .filter_map(|(_, s, t)| match (s, *t) {
                (Stmt::Def(n, ps, b), false) => Some((n, ps, b)),
                _ => None,
            })
            .collect();
        let mut uses: HashMap<String, HashSet<String>> = HashMap::new();
        for (n, ps, b) in &user {
            let bound: HashSet<String> = ps.iter().cloned().collect();
            uses.insert((*n).clone(), refs(b, &bound, &c.overloads));
        }
        let mut tainted: HashSet<String> = order.iter().cloned().collect();
        loop {
            let new: Vec<String> = uses.iter().filter(|(n, u)| !tainted.contains(*n) && u.iter().any(|x| tainted.contains(x))).map(|(n, _)| n.clone()).collect();
            if new.is_empty() {
                break;
            }
            tainted.extend(new);
        }
        let order_set: HashSet<&String> = order.iter().collect();
        c.unknowns = order.iter().map(|n| (n.clone(), None)).collect();
        c.user_defined = user.iter().map(|(n, _, _)| (*n).clone()).collect();
        c.raw_taint = tainted.iter().filter(|n| !order_set.contains(n)).cloned().collect();
        c.taint = HashMap::new();
    }

    /// program-local codes (doc 1 format) for the program's own symbols, assigned when the program is checked and in a fixed order
    fn codes_of(&mut self) -> R<()> {
        let mut order: Vec<String> = self.checker.unknowns.iter().map(|(n, _)| n.clone()).collect();
        for (_, s, trusted) in &self.statements {
            if let (Stmt::Decl(n, _), false) = (s, *trusted) {
                if n != ENV_NAME && self.checker.sigs.contains_key(n) {
                    order.push(n.clone());
                }
            }
        }
        for n in order {
            self.doc1.code(&n, true)?;
        }
        Ok(())
    }

    /// replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝  and add the table of definitions
    fn quote_program(&mut self) -> R<()> {
        let (qrs, tab, doc2) = {
            let sts: Vec<(bool, Option<&Stmt>)> = self.statements.iter().map(|(_, _, t)| *t).zip(self.resolved.iter().map(|r| r.as_ref())).collect();
            let (qr, d1) = mk_quoter(&self.checker, &sts, &self.doc1)?;
            let mut st = QS { doc: d1, needed: vec![] };
            let mut replaced: Vec<(usize, Stmt)> = vec![];
            for (i, r) in self.resolved.iter().enumerate() {
                if let Some(Stmt::Def(n, ps, b)) = r {
                    if has_quote(b) {
                        let b2 = qr.quote_replace(&mut st, b)?;
                        replaced.push((i, Stmt::Def(n.clone(), ps.clone(), b2)));
                    }
                }
            }
            let tab = qr.quote_table(&mut st)?;
            (replaced, tab, st.doc)
        };
        for (i, st) in qrs {
            self.resolved[i] = Some(st);
        }
        self.doc1 = doc2;
        let env_ty = Ty::K("𝔏".to_string(), vec![Ty::K("𝔓".to_string(), vec![kk("𝔇"), kk("𝔔")])]);
        if let Err(e) = self.checker.declare(ENV_NAME, &env_ty) {
            return Err(Err::Eval(format!("quote: ε⌜⌝ declaration: {}", e)));
        }
        let at = self.statements.iter().take_while(|(_, _, t)| *t).count();
        let decl_st = Stmt::Decl(ENV_NAME.to_string(), env_ty);
        let def_st = Stmt::Def(ENV_NAME.to_string(), vec![], tab);
        self.statements.insert(at, ("<quote>".to_string(), def_st.clone(), false));
        self.statements.insert(at, ("<quote>".to_string(), decl_st.clone(), false));
        self.resolved.insert(at, Some(def_st));
        self.resolved.insert(at, Some(decl_st));
        Ok(())
    }

    // ------------------------------------------------------------ building
    pub fn user_statements(&self) -> Vec<Stmt> {
        self.statements
            .iter()
            .zip(self.resolved.iter())
            .filter_map(|((_, _, t), r)| if *t { None } else { r.clone() })
            .collect()
    }

    pub fn spec_text(&self) -> String {
        self.user_statements().iter().map(|s| format!("{}\n", pp_statement(s))).collect()
    }

    pub fn bin_text(&mut self) -> R<String> {
        let sts = self.user_statements();
        spec_statements_to_bin_text(&sts, &mut self.doc1, true)
    }

    pub fn local_table(&self) -> String {
        self.doc1.render(&["program-local symbols (same format as doc 1)"])
    }

    /// the human name of a spec symbol (reverse doc 2; a symbol of the program is its own name)
    pub fn hum_name(&self, spec: &str) -> String {
        for e in &self.doc2.entries {
            if matches!(e.role.as_str(), "value" | "infixl" | "infixr" | "infix" | "prefix") && e.rhs.iter().any(|x| x == spec) {
                return e.hum.clone();
            }
        }
        spec.to_string()
    }

    /// build the evaluator: the definitions of the embedded prelude are compiled when they are first needed
    pub fn build(&mut self) -> R<()> {
        let mut defs: Vec<(String, Source)> = Vec::with_capacity(self.resolved.len());
        for r in self.resolved.iter_mut().take(self.pre_count) {
            if let Some(Stmt::Def(n, ps, b)) = r.take() {
                defs.push((n, Source::Term(ps, b)));
            }
        }
        for (n, c) in std::mem::take(&mut self.user_defs) {
            defs.push((n, Source::Core(c)));
        }
        let mut extra: Vec<(String, V)> = vec![];
        for (n, _) in &self.checker.unknowns {
            let h = self.hum_name(n);
            let msg = format!(
                "{} is an unknown (it is declared and never defined, so it has no value); use it in a statement — a relation such as {} == 1 — which is simplified, not evaluated",
                h, h
            );
            extra.push((n.clone(), Thunk::new(St::Fail(Err::Unknown(msg)))));
        }
        self.machine = Some(Machine::build(defs, extra));
        Ok(())
    }

    /// the globals that some definition of the program uses and nothing defines (checked programs only)
    pub fn missing(&mut self) -> R<Vec<String>> {
        if !self.errors.is_empty() {
            return Ok(vec![]);
        }
        let mut defined: HashSet<&str> = self.defined.iter().map(|n| n.as_str()).collect();
        for (n, _) in &self.checker.unknowns {
            defined.insert(n.as_str());
        }
        let mut missing: BTreeSet<String> = BTreeSet::new();
        for (_, c) in &self.user_defs {
            collect_missing(c, &defined, &mut missing);
        }
        Ok(missing.into_iter().collect())
    }

    pub fn machine(&self) -> &Machine {
        self.machine.as_ref().expect("the program is not built")
    }

    pub fn val(&self, n: &str) -> R<V> {
        self.machine().global(n)
    }
}

fn collect_missing(c: &Core, defined: &HashSet<&str>, out: &mut BTreeSet<String>) {
    // iterative over the spine of applications to keep the native stack shallow for long numerals
    let mut stack: Vec<&Core> = vec![c];
    while let Some(c) = stack.pop() {
        match c {
            Core::G(g) => {
                if !defined.contains(g.as_str()) {
                    out.insert(g.clone());
                }
            }
            Core::L(b) => stack.push(b),
            Core::A(f, x) => {
                stack.push(x);
                stack.push(f);
            }
            Core::V(_) => {}
        }
    }
}

fn is_class_or_stmt(ty: &Ty) -> bool {
    let mut cur = ty;
    loop {
        match cur {
            Ty::K(n, a) if n == "→" && a.len() == 2 => cur = &a[1],
            _ => break,
        }
    }
    *cur == kk("𝒦") || *cur == kk("𝒮")
}

fn refs(t: &Term, bound: &HashSet<String>, overloads: &std::collections::BTreeMap<String, Vec<String>>) -> HashSet<String> {
    match t {
        Term::Var(n) => {
            if bound.contains(n) {
                HashSet::new()
            } else {
                match overloads.get(n) {
                    Some(v) => v.iter().cloned().collect(),
                    None => std::iter::once(n.clone()).collect(),
                }
            }
        }
        Term::App(f, args) => {
            let mut s = refs(f, bound, overloads);
            for a in args {
                s.extend(refs(a, bound, overloads));
            }
            s
        }
        Term::Lam(ps, b) => {
            let mut bd = bound.clone();
            for (n, _) in ps {
                bd.insert(n.clone());
            }
            refs(b, &bd, overloads)
        }
        Term::Asc(e, _) => refs(e, bound, overloads),
        _ => HashSet::new(),
    }
}

/// load the prelude and the files and check them
pub fn load_program(files: &[SourceFile], trusted_paths: &[String], with_prelude: bool) -> R<Program> {
    let mut p = Program::new()?;
    if with_prelude {
        // I1_SKIP_LIB=a.imo,b.imo leaves the named library files out (libsrc/build.sh translates a module that is itself part of the prelude)
        let skip: Vec<String> = std::env::var("I1_SKIP_LIB").map(|v| v.split(',').map(|x| x.trim().to_string()).collect()).unwrap_or_default();
        for (path, text) in data::lib_files() {
            if skip.iter().any(|x| !x.is_empty() && path.ends_with(x.as_str())) {
                continue;
            }
            p.add_file(&SourceFile { path: path.to_string(), text: text.to_string() }, true)?;
        }
        p.pre_count = p.statements.len();
    }
    for f in files {
        let trusted = trusted_paths.contains(&f.path);
        p.add_file(f, trusted)?;
    }
    p.check()?;
    Ok(p)
}
