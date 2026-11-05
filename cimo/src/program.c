/* program.c -- loader / driver for i-1 programs (port of ocamimo/src/program.ml).
   A file is read in the notation chosen by its extension (x.bin.imo, x.hum.imo, x.imo = spec) or by section headers (@bin @spec @hum); every
   section is translated to spec statements, the whole program is checked by the class checker, and the definitions are run by the evaluator.
   A symbol that the program declares and never defines is an UNKNOWN. */
#include "cimo.h"
#include <sys/stat.h>

static Program *new_program(void) {
  Program *p = NEW(Program);
  Doc1 *d1 = doc1_parse(DOC1);
  Doc2 *d2 = doc2_remap(doc2_parse(DOC2), d1);
  p->doc1 = d1; p->doc2 = d2; p->hum = mk_hum(d2);
  p->checker = new_checker();
  Hash *ov = overload_table(d2);
  for (int i = 0; i < ov->n; i++) hset(p->checker->overloads, ov->keys[i], ov->vals[i]);
  p->notation_of = hnew(); p->defined = hnew();
  p->cstat = 1024; p->statements = NEWN(Triple, p->cstat);
  return p;
}
static void add_stmt(Program *p, const char *file, Stmt *st, int trusted) {
  if (p->nstat >= p->cstat) {
    Triple *n = NEWN(Triple, p->cstat * 2);
    memcpy(n, p->statements, sizeof(Triple) * (size_t)p->nstat);
    p->statements = n; p->cstat *= 2;
  }
  Triple *t = &p->statements[p->nstat++];
  t->file = file; t->st = st; t->trusted = trusted;
}
/* add the text of a file (or of a string) in the given default notation */
static void add_text(Program *p, const char *text, const char *name, int trusted, const char *notation) {
  const char *out_mode = p->out_mode;
  L *lines = NULL;
  for (L *l = split_on(text, "\n"); l; l = l->t) {
    const char *ln = (const char *)l->h;
    L *words = split_ws(ln);
    if (llen(words) == 2 && !strcmp((const char *)words->h, "@out")) {
      const char *w = (const char *)words->t->h;
      if (!strcmp(w, "bin") || !strcmp(w, "spec") || !strcmp(w, "hum")) { out_mode = w; lines = cons("", lines); continue; }
      parse_err(xfmt("%s: @out takes bin, spec or hum, not %s", name, w));
    }
    lines = cons((void *)ln, lines);
  }
  char *text2 = sjoin(lrev(lines), "\n");
  p->out_mode = out_mode;
  for (L *s = split_sections(text2, notation); s; s = s->t) {
    Section *sec = (Section *)s->h;
    L *sts;
    if (!strcmp(sec->mode, "spec")) sts = parse_statements(sec->text);
    else if (!strcmp(sec->mode, "bin")) sts = parse_statements(bin_to_spec_text(sec->text, p->doc1));
    else sts = hum_statements(p->hum, sec->text);
    if (!trusted) for (L *x = sts; x; x = x->t) if (((Stmt *)x->h)->kind == S_DEF) hset(p->notation_of, ((Stmt *)x->h)->name, (void *)sec->mode);
    for (L *x = sts; x; x = x->t) add_stmt(p, name, (Stmt *)x->h, trusted);
  }
}
static int is_file_p(const char *path) { struct stat sb; return stat(path, &sb) == 0 && S_ISREG(sb.st_mode); }
static char *replace_all(const char *s, const char *a, const char *b) { return sjoin(split_on(s, a), b); }
/* add a file; a bin program brings its local symbol table (x.sbl next to x.bin.imo) */
static void add_file(Program *p, SourceFile *f, int trusted) {
  const char *path = f->path;
  int k = rfind_sub(path, ".imo");
  char *before = k >= 0 ? ssub(path, 0, k) : (char *)path;
  char *local = scat(replace_all(replace_all(replace_all(before, ".bin", ""), ".hum", ""), ".spec", ""), ".sbl");
  int uses_bin = !strcmp(default_notation(path), "bin") || contains_sub(scat("\n", f->text), "\n@bin");
  if (uses_bin && is_file_p(local)) {
    extern char *read_utf8_file(const char *path, char **err);
    char *err = NULL;
    char *tbl = read_utf8_file(local, &err);
    if (!tbl) parse_err(xfmt("%s: %s", local, err));
    for (L *l = split_on(tbl, "\n"); l; l = l->t) {
      const char *line = (const char *)l->h;
      if (contains_sub(line, " := ") && !starts_with(line, "⍝")) {
        L *parts = split_on(line, " := ");
        if (llen(parts) != 2) parse_err(xfmt("bad line in %s", basename_of(local)));
        char *a = strip((const char *)parts->h), *b = strip((const char *)parts->t->h);
        if (hhas(p->doc1->s2b, a)) continue;
        const char *other = (const char *)hget(p->doc1->b2s, b);
        if (other)
          parse_err(xfmt("%s: local code %s for %s is already doc 1's code for %s (doc 1 grew: regenerate the local table with  i1.py translate … --to bin)", basename_of(local), b, a, other));
        doc1_add_local(p->doc1, a, b);
      }
    }
  }
  add_text(p, f->text, path, trusted, default_notation(path));
}

/* ------------------------------------------------------------------ checking */
static int class_or_stmt(Ty *ty) {
  Ty *cur = ty;
  while (cur->tag == TY_K && !strcmp(cur->name, "→") && llen(cur->args) == 2) cur = (Ty *)cur->args->t->h;
  return ty_eq(cur, kk("𝒦")) || ty_eq(cur, kk("𝒮"));
}
/* names referenced by a term (outside bound), with overloads expanded; added to the hash */
static void refs(Term *t, Hash *bound, Hash *overloads, Hash *out) {
  switch (t->tag) {
    case T_VAR:
      if (hhas(bound, t->s)) return;
      if (hhas(overloads, t->s)) { for (L *l = (L *)hget(overloads, t->s); l; l = l->t) hset(out, (const char *)l->h, out); }
      else hset(out, t->s, out);
      return;
    case T_APP: refs(t->f, bound, overloads, out); for (L *a = t->args; a; a = a->t) refs((Term *)a->h, bound, overloads, out); return;
    case T_LAM: {
      Hash *bd = hcopy(bound);
      for (L *p = t->ps; p; p = p->t) hset(bd, ((Param *)p->h)->name, bd);
      refs(t->body, bd, overloads, out);
      return;
    }
    case T_ASC: refs(t->body, bound, overloads, out); return;
    default: return;
  }
}
/* the unknowns (declared by the program, defined nowhere), in declaration order, and a first estimate of which program definitions need their values */
static void unknowns_of(Checker *c, Triple *stmts, int n) {
  Hash *defined = hnew(), *seen = hnew();
  for (int i = 0; i < n; i++) if (stmts[i].st->kind == S_DEF) hset(defined, stmts[i].st->name, defined);
  L *order = NULL;
  for (int i = 0; i < n; i++) {
    Stmt *s = stmts[i].st;
    if (s->kind == S_DECL && !stmts[i].trusted) {
      if (hhas(defined, s->name) || class_or_stmt(s->ty)) continue;
      if (!hhas(seen, s->name)) { hset(seen, s->name, seen); order = cons((void *)s->name, order); }
    }
  }
  order = lrev(order);
  Hash *uses = hnew();   /* name -> Hash of referenced names */
  L *user = NULL;
  for (int i = 0; i < n; i++) {
    Stmt *s = stmts[i].st;
    if (s->kind == S_DEF && !stmts[i].trusted) {
      user = cons(s, user);
      Hash *bound = hnew(), *out = hnew();
      for (L *p = s->params; p; p = p->t) hset(bound, (const char *)p->h, bound);
      refs(s->body, bound, c->overloads, out);
      hset(uses, s->name, out);
    }
  }
  Hash *tainted = hnew();
  for (L *o = order; o; o = o->t) hset(tainted, (const char *)o->h, tainted);
  for (int go = 1; go;) {
    go = 0;
    for (int i = 0; i < uses->n; i++) {
      if (hhas(tainted, uses->keys[i])) continue;
      Hash *u = (Hash *)uses->vals[i];
      int hit = 0;
      for (int j = 0; j < u->n && !hit; j++) if (hhas(tainted, u->keys[j])) hit = 1;
      if (hit) { hset(tainted, uses->keys[i], tainted); go = 1; }
    }
  }
  L *un = NULL;
  for (L *o = order; o; o = o->t) { Unknown *u = NEW(Unknown); u->name = (const char *)o->h; u->dom = -1; un = cons(u, un); }
  c->unknowns = lrev(un);
  hclear(c->user_defined);
  for (L *u = user; u; u = u->t) hset(c->user_defined, ((Stmt *)u->h)->name, c);
  hclear(c->raw_taint);
  for (int i = 0; i < tainted->n; i++) if (!lmem_str(tainted->keys[i], order)) hset(c->raw_taint, tainted->keys[i], c);
  hclear(c->taint);
}
/* program-local codes (doc 1 format) for the program's own symbols, assigned when the program is checked and in a fixed order */
static void codes_of(Program *p) {
  Checker *c = p->checker;
  for (L *u = c->unknowns; u; u = u->t) doc1_code(p->doc1, ((Unknown *)u->h)->name, 1);
  for (int i = 0; i < p->nstat; i++) {
    Stmt *s = p->statements[i].st;
    if (s->kind == S_DECL && !p->statements[i].trusted && strcmp(s->name, ENV_NAME) && hhas(c->sigs, s->name)) doc1_code(p->doc1, s->name, 1);
  }
}
static void quote_program(Program *p) {
  L *sts = NULL;
  for (int i = p->nstat - 1; i >= 0; i--) { StTrust *e = NEW(StTrust); e->trusted = p->statements[i].trusted; e->st = p->resolved[i]; sts = cons(e, sts); }
  Doc1 *d1;
  Quoter *qr = mk_quoter(p->checker, sts, p->doc1, &d1);
  QS *st = NEW(QS); st->doc = d1; st->needed = NULL;
  Stmt **repl = NEWN(Stmt *, p->nstat);
  for (int i = 0; i < p->nstat; i++) {
    Stmt *r = p->resolved[i];
    if (r && r->kind == S_DEF && has_quote(r->body)) repl[i] = s_def(r->name, r->params, quote_replace(qr, st, r->body));
  }
  Term *tab = quote_table(qr, st);
  for (int i = 0; i < p->nstat; i++) if (repl[i]) p->resolved[i] = repl[i];
  p->doc1 = st->doc;
  Ty *env_ty = ty_k("𝔏", l1(ty_k("𝔓", l2(kk("𝔇"), kk("𝔔")))));
  Handler h;
  if (TRY(h)) { declare(p->checker, ENV_NAME, env_ty); ENDTRY(h); }
  else { if (cur_err.kind == E_CLASS) eval_err(xfmt("quote: ε⌜⌝ declaration: %s", cur_err.msg)); raise_err(cur_err.kind, cur_err.msg); }
  int at = 0;
  while (at < p->nstat && p->statements[at].trusted) at++;
  Stmt *decl_st = s_decl(ENV_NAME, env_ty), *def_st = s_def(ENV_NAME, NULL, tab);
  /* insert (decl_st, def_st) at `at` in both arrays */
  Triple *ns = NEWN(Triple, p->nstat + 2 + 16);
  Stmt **nr = NEWN(Stmt *, p->nstat + 2 + 16);
  memcpy(ns, p->statements, sizeof(Triple) * (size_t)at);
  memcpy(nr, p->resolved, sizeof(Stmt *) * (size_t)at);
  ns[at].file = "<quote>"; ns[at].st = decl_st; ns[at].trusted = 0; nr[at] = decl_st;
  ns[at + 1].file = "<quote>"; ns[at + 1].st = def_st; ns[at + 1].trusted = 0; nr[at + 1] = def_st;
  memcpy(ns + at + 2, p->statements + at, sizeof(Triple) * (size_t)(p->nstat - at));
  memcpy(nr + at + 2, p->resolved + at, sizeof(Stmt *) * (size_t)(p->nstat - at));
  p->statements = ns; p->resolved = nr; p->nstat += 2; p->cstat = p->nstat + 16;
}
/* check one statement: 1 and the resolved statement (or the statement as written), or 0 and the class error */
static int check_one(Checker *c, Triple *tr, Stmt **out, Err *err) {
  Handler h;
  Stmt *nw = NULL;
  if (TRY(h)) { nw = check_statement(c, tr->st, tr->trusted); ENDTRY(h); *out = nw ? nw : tr->st; return 1; }
  if (cur_err.kind != E_CLASS) raise_err(cur_err.kind, cur_err.msg);
  *err = cur_err;
  return 0;
}
/* check the program: class errors are collected in `errors`; the statements that mention a relation on ℝ[i] or an unknown are then written as codes */
static void check(Program *p) {
  int k = 0;
  for (int i = 0; i < p->nstat; i++) if (strcmp(p->statements[i].file, "<quote>")) p->statements[k++] = p->statements[i];
  p->nstat = k;
  Checker *c = p->checker;
  unknowns_of(c, p->statements, p->nstat);
  int n = p->nstat;
  p->resolved = NEWN(Stmt *, n + 16);
  L *errors = NULL;
  for (int i = 0; i < n; i++) {
    Triple *tr = &p->statements[i];
    Stmt *out; Err e;
    if (check_one(c, tr, &out, &e)) p->resolved[i] = out;
    else {
      ErrRec *er = NEW(ErrRec);
      er->file = tr->file; er->msg = e.msg;
      er->what = tr->st->kind == S_DEF || tr->st->kind == S_DECL ? tr->st->name : pp_statement(tr->st);
      errors = cons(er, errors);
      p->resolved[i] = NULL;
    }
  }
  L *dft = NULL;
  for (int i = 0; i < n; i++) if (!p->statements[i].trusted && p->resolved[i] && p->resolved[i]->kind == S_DEF) dft = cons(p->resolved[i], dft);
  settle_taint(c, lrev(dft));
  p->errors = lrev(errors);
  if (p->errors) return;
  codes_of(p);
  int any = 0;
  for (int i = 0; i < p->nstat; i++) if (p->resolved[i] && p->resolved[i]->kind == S_DEF && has_quote(p->resolved[i]->body)) any = 1;
  if (any) quote_program(p);
  /* the definitions of the program, in de Bruijn form (those of the embedded prelude are erased when they are first needed) */
  hclear(p->defined);
  L *ud = NULL;
  for (int i = 0; i < p->nstat; i++) {
    Stmt *r = p->resolved[i];
    if (r && r->kind == S_DEF) {
      hset(p->defined, r->name, p->defined);
      if (i >= p->pre_count) { DefSrc *d = NEW(DefSrc); d->name = r->name; d->src = NEW(Source); d->src->core = erase_def(r->params, r->body); ud = cons(d, ud); }
    }
  }
  p->user_defs = lrev(ud);
}

/* ------------------------------------------------------------------ building */
L *user_statements(Program *p) {
  L *out = NULL;
  for (int i = 0; i < p->nstat; i++) if (!p->statements[i].trusted && p->resolved[i]) out = cons(p->resolved[i], out);
  return lrev(out);
}
char *spec_text(Program *p) {
  Buf *b = bnew();
  for (L *s = user_statements(p); s; s = s->t) { badd(b, pp_statement((Stmt *)s->h)); baddc(b, '\n'); }
  return bstr(b);
}
char *bin_text(Program *p) { return spec_statements_to_bin_text(user_statements(p), p->doc1, 1); }
char *local_table(Program *p) { return doc1_render(p->doc1, l1("program-local symbols (same format as doc 1)")); }
/* the human name of a spec symbol (reverse doc 2; a symbol of the program is its own name) */
static const char *hum_name(Program *p, const char *spec) {
  for (L *l = p->doc2->entries; l; l = l->t) {
    Entry *e = (Entry *)l->h;
    if (!(strcmp(e->role, "value") && strcmp(e->role, "infixl") && strcmp(e->role, "infixr") && strcmp(e->role, "infix") && strcmp(e->role, "prefix")) == 0) continue;
    if (lmem_str(spec, e->rhs)) return e->hum;
  }
  return spec;
}
/* build the evaluator: the definitions of the embedded prelude are compiled when they are first needed */
void program_build(Program *p) {
  L *defs = NULL;
  for (int i = 0; i < p->pre_count; i++) {
    Stmt *r = p->resolved[i];
    if (r && r->kind == S_DEF) {
      DefSrc *d = NEW(DefSrc); d->name = r->name; d->src = NEW(Source);
      d->src->is_term = 1; d->src->ps = r->params; d->src->term = r->body;
      defs = cons(d, defs);
    }
  }
  defs = lrev(defs);
  defs = lappend(defs, p->user_defs);
  L *extra = NULL;
  for (L *u = p->checker->unknowns; u; u = u->t) {
    const char *n = ((Unknown *)u->h)->name, *h = hum_name(p, n);
    Extra *e = NEW(Extra); e->name = n;
    e->th = th_fail(E_UNKNOWN, xfmt("%s is an unknown (it is declared and never defined, so it has no value); use it in a statement — a relation such as %s == 1 — which is simplified, not evaluated", h, h));
    extra = cons(e, extra);
  }
  p->machine = machine_build(defs, lrev(extra));
}
/* the globals that some definition of the program uses and nothing defines (checked programs only), sorted */
L *program_missing(Program *p) {
  if (p->errors) return NULL;
  Hash *out = hnew();
  for (L *d = p->user_defs; d; d = d->t) {
    L *stack = l1(((DefSrc *)d->h)->src->core);
    while (stack) {
      Core *c = (Core *)stack->h;
      stack = stack->t;
      if (c->tag == C_G) {
        int unk = 0;
        for (L *u = p->checker->unknowns; u; u = u->t) if (!strcmp(((Unknown *)u->h)->name, c->g)) unk = 1;
        if (!hhas(p->defined, c->g) && !unk) hset(out, c->g, out);
      } else if (c->tag == C_L) stack = cons(c->f, stack);
      else if (c->tag == C_A) stack = cons(c->f, cons(c->x, stack));
    }
  }
  /* sort by bytes */
  int n = out->n;
  char **ks = NEWN(char *, n);
  for (int i = 0; i < n; i++) ks[i] = out->keys[i];
  for (int i = 1; i < n; i++) { char *x = ks[i]; int j = i - 1; while (j >= 0 && strcmp(ks[j], x) > 0) { ks[j + 1] = ks[j]; j--; } ks[j + 1] = x; }
  L *r = NULL;
  for (int i = n - 1; i >= 0; i--) r = cons(ks[i], r);
  return r;
}
Th *program_val(Program *p, const char *n) { return machine_global(p->machine, n); }

/* load the prelude and the files and check them */
Program *load_program(L *files, L *trusted_paths, int with_prelude) {
  Program *p = new_program();
  if (with_prelude) {
    for (int i = 0; LIB_NAMES[i]; i++) { SourceFile f = { LIB_NAMES[i], LIB_TEXTS[i] }; SourceFile *pf = NEW(SourceFile); *pf = f; add_file(p, pf, 1); }
    p->pre_count = p->nstat;
  }
  for (L *l = files; l; l = l->t) {
    SourceFile *f = (SourceFile *)l->h;
    add_file(p, f, lmem_str(f->path, trusted_paths));
  }
  check(p);
  return p;
}
