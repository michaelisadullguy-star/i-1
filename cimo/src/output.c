/* output.c -- printing values: the output side of the three notations, and the `main` entry point (port of ocamimo/src/output.ml).
   A value is printed as a NORMAL-FORM TERM in the chosen notation.  Nothing is computed on the host: the normal forms are computed IN THE LANGUAGE
   (⊜, showq / showc, decimals); the host walks the value as its declared class describes it, reads digit strings and turns code points into
   characters.  main ∶ 𝕊: its text is the output; main ∶ 𝔏 𝕊 / 𝔖 𝕊: one line per element; any other class: the value as a term. */
#include "cimo.h"

const char *MODES[] = { "bin", "spec", "hum", NULL };
static const char *UNDETERMINED =
  "undetermined: this truth value is neither proved nor refuted — a statement that depends on its unknowns, or a relation on ℝ[i] that no rule decides (declare it Prop to print its simplest form instead of a Bool)";

static Machine *mach(Printer *pr) { return pr->p->machine; }
static Checker *chk(Printer *pr) { return pr->p->checker; }
static int is_hum(Printer *pr) { return !strcmp(pr->mode, "hum"); }
static char *esc(int q, const char *s) {
  int n; int *cs = decode(s, &n);
  Buf *b = bnew();
  for (int i = 0; i < n; i++) {
    int c = cs[i];
    if (c == '\\') badd(b, "\\\\");
    else if (c == '\n') badd(b, "\\n");
    else if (c == '\t') badd(b, "\\t");
    else if (c == q) { baddc(b, '\\'); baddcp(b, c); }
    else baddcp(b, c);
  }
  return bstr(b);
}
/* a list / string cell: a V_CONS or V_NIL value; ⍰ (an undetermined Boolean inside the text) is reported, never printed as text */
static Val *cell_of(Printer *pr, Th *v) {
  Val *c = m_cell_or_nil(mach(pr), v);
  if (c->tag != V_CONS && c->tag != V_NIL) print_err(UNDETERMINED);
  return c;
}
static int boolean_of(Printer *pr, Th *v) {
  Machine *m = mach(pr);
  Th *a[2] = { m_vt(m), m_vf(m) };
  Val *r = m_apply_whnf(m, v, a, 2);
  if (r->tag == V_T) return 1;
  if (r->tag == V_F) return 0;
  print_err(UNDETERMINED);
}
static Th *call(Printer *pr, const char *f, Th **args, int n) { return m_call_g(mach(pr), f, args, n); }
/* a 𝕮 value (a natural numeral, as a ℚ[i] pair) -> code point; its canonical form is a pair (n, 1) */
static int char_of(Printer *pr, Th *v) {
  Machine *m = mach(pr);
  Th *canon = call(pr, "⊜", &v, 1);
  Th *z, *mm;
  m_to_pair(m, canon, &z, &mm);
  Digits zd = m_to_list(m, z), md = m_to_list(m, mm);
  int ok_den = md.n == 1 && md.d[0] == 1;
  int64_t re, im;
  if (val_digits_small(zd, &re, &im) && im == 0 && re >= 0 && re <= 0x10FFFF && ok_den) return (re >= 0xD800 && re <= 0xDFFF) ? 0xFFFD : (int)re;
  return 0xFFFD;
}
char *text_of(Printer *pr, Th *v) {
  Buf *b = bnew();
  Val *cell = cell_of(pr, v);
  while (cell->tag == V_CONS) { baddcp(b, char_of(pr, cell->a)); cell = cell_of(pr, cell->b); }
  return bstr(b);
}
static char *digits_str(Printer *pr, Th *v) { return numeral(m_to_list(mach(pr), v)); }
static int is_class(Printer *pr, Ty *cls, const char *name) { return leq(chk(pr), cls, kk(name)) && leq(chk(pr), kk(name), cls); }
static Term *strip_quotes(Term *t) {
  switch (t->tag) {
    case T_QUOTE: return strip_quotes(t->body);
    case T_APP: { L *a = NULL; for (L *x = t->args; x; x = x->t) a = cons(strip_quotes((Term *)x->h), a); return t_app(strip_quotes(t->f), lrev(a)); }
    case T_LAM: return t_lam(t->ps, strip_quotes(t->body));
    default: return t;
  }
}

/* ------------------------------------------------------------------ the Speller: the human spelling of the code of a statement */
enum { ND_N, ND_S, ND_A, ND_L, ND_V };
typedef struct Node { int tag; Th *a, *b; } Node;
typedef struct Piece { char *text; int prec; const char *kind; } Piece;
static const char *formula_args[] = { "∧", "∨", "¬", "⇒", "⇔", "∧Ω", "∨Ω", "¬Ω", "⇒Ω", "⇔Ω", "prop", "decide", "code_rd", NULL };
static const char *spell_transparent[] = { "⇡", "prop", "decide", "code_rd", NULL };
static int in_arr(const char *s, const char **a) { for (; *a; a++) if (!strcmp(s, *a)) return 1; return 0; }
static char *par(Piece p, int need, const char *avoid) {
  if (p.prec < need || (avoid && !strcmp(p.kind, avoid))) return xfmt("(%s)", p.text);
  return p.text;
}
static Node node_of(Printer *pr, Th *v) {
  Machine *m = mach(pr);
  Handler h;
  Val *r = NULL;
  Node nd = { 0, NULL, NULL };
  if (TRY(h)) { r = m_apply_whnf(m, v, m_code_cbs(m), 5); ENDTRY(h); }
  else {
    if (cur_err.kind == E_UNKNOWN) raise_err(cur_err.kind, cur_err.msg);
    print_err("a statement whose code is not a code (undetermined, or not built by the simplifier)");
  }
  switch (r->tag) {
    case V_CN: nd.tag = ND_N; nd.a = r->a; break;
    case V_CS: nd.tag = ND_S; nd.a = r->a; break;
    case V_CA: nd.tag = ND_A; nd.a = r->a; nd.b = r->b; break;
    case V_CL: nd.tag = ND_L; break;
    case V_CV: nd.tag = ND_V; break;
    default: print_err("a statement whose code is not a code (undetermined, or not built by the simplifier)");
  }
  return nd;
}
static const char *symbol_name(Printer *pr, Th *c) {
  Digits ds = trim_digits(m_to_list(mach(pr), c));
  char *b = xfmt(".%s.", numeral(ds));
  const char *n = (const char *)hget(pr->p->doc1->b2s, b);
  if (!n) print_err(xfmt("a statement mentions the symbol code %s, which neither doc 1 nor this program names", b));
  return n;
}
/* reverse doc 2: the first entry that has the spec symbol on its right */
static Entry *rev_entry(Printer *pr, const char *spec) {
  for (L *l = pr->p->doc2->entries; l; l = l->t) {
    Entry *e = (Entry *)l->h;
    if ((!strcmp(e->role, "value") || !strcmp(e->role, "infixl") || !strcmp(e->role, "infixr") || !strcmp(e->role, "infix") || !strcmp(e->role, "prefix")) && lmem_str(spec, e->rhs)) return e;
  }
  return NULL;
}
static Piece mkpiece(char *text, int prec, const char *kind) { Piece p = { text, prec, kind }; return p; }
static Piece number_piece(Printer *pr, Th *q) {
  Handler h;
  char *t = NULL;
  if (TRY(h)) { t = text_of(pr, call(pr, "showc", &q, 1)); ENDTRY(h); }
  else {
    if (cur_err.kind == E_EVAL) print_err("a statement holds a value that is not a number where a number is expected");
    raise_err(cur_err.kind, cur_err.msg);
  }
  int p = (contains_sub(t, " + ") || contains_sub(t, " - ")) ? 6 : (ends_with(t, "i") || strchr(t, '/')) ? 7 : starts_with(t, "-") ? 8 : 10;
  return mkpiece(t, p, "num");
}
static Piece go(Printer *pr, Th *v, int formula);
static L *list_loop(Printer *pr, Th *rest, L *acc) {
  Th *cur = rest;
  for (;;) {
    Node n = node_of(pr, cur);
    if (n.tag == ND_S) { if (!strcmp(symbol_name(pr, n.a), "⊘")) return acc; print_err("a list code that does not end in ⊘"); }
    if (n.tag != ND_A) print_err("a list code that does not end in ⊘");
    Node n2 = node_of(pr, n.a);
    if (n2.tag != ND_A) print_err("a list code that does not end in ⊘");
    Node n3 = node_of(pr, n2.a);
    if (n3.tag != ND_S || strcmp(symbol_name(pr, n3.a), "∷")) print_err("a list code that does not end in ⊘");
    acc = lappend(acc, l1(go(pr, n2.b, 0).text));
    cur = n.b;
  }
}
static Piece app_piece(Printer *pr, const char *name, Th **args, int k, int formula) {
  if ((!strcmp(name, "⊤") || !strcmp(name, "⊥")) && k == 0) return mkpiece(!strcmp(name, "⊤") ? "true" : "false", 10, "atom");
  if (in_arr(name, spell_transparent) && k == 1) return go(pr, args[0], formula && strcmp(name, "⇡"));
  if (!strcmp(name, "⊘") && k == 0) return mkpiece("[]", 10, "atom");
  if (!strcmp(name, "∷") && k == 2) {
    char *first = go(pr, args[0], 0).text;
    L *items = list_loop(pr, args[1], l1(first));
    return mkpiece(xfmt("[%s]", sjoin(items, ", ")), 10, "atom");
  }
  if ((!strcmp(name, "∨") || !strcmp(name, "∨Ω")) && k == 2) {
    Piece a = go(pr, args[0], 1), b = go(pr, args[1], 1);
    return mkpiece(xfmt("%s or %s", par(a, 3, "and"), par(b, 2, "and")), 2, "or");
  }
  if ((!strcmp(name, "∧") || !strcmp(name, "∧Ω")) && k == 2) {
    Piece a = go(pr, args[0], 1), b = go(pr, args[1], 1);
    return mkpiece(xfmt("%s and %s", par(a, 4, NULL), par(b, 3, NULL)), 3, "and");
  }
  if ((!strcmp(name, "¬") || !strcmp(name, "¬Ω")) && k == 1) {
    Piece a = go(pr, args[0], 1);
    return mkpiece(xfmt("not %s", par(a, 4, NULL)), 4, "not");
  }
  int sub = in_arr(name, formula_args);
  Entry *entry = rev_entry(pr, name);
  const char *h = entry ? entry->hum : name, *role = entry ? entry->role : "value";
  int prec = entry && entry->has_prec ? entry->prec : 0;
  if ((!strcmp(role, "infixl") || !strcmp(role, "infixr") || !strcmp(role, "infix")) && k == 2) {
    Piece a = go(pr, args[0], sub), b = go(pr, args[1], sub);
    int ln, rn;
    if (!strcmp(h, "^")) { ln = 10; rn = prec; }
    else if (!strcmp(role, "infixl")) { ln = prec; rn = (!strcmp(h, "+") || !strcmp(h, "*")) ? prec : prec + 1; }
    else if (!strcmp(role, "infixr")) { ln = prec + 1; rn = prec; }
    else { ln = prec + 1; rn = prec + 1; }
    const char *sep = (!strcmp(h, "*") || !strcmp(h, "/") || !strcmp(h, "^")) ? h : xfmt(" %s ", h);
    return mkpiece(xfmt("%s%s%s", par(a, ln, NULL), sep, par(b, rn, NULL)), prec, "op");
  }
  if (!strcmp(role, "prefix") && k == 1) {
    Piece a = go(pr, args[0], sub);
    char *x0 = par(a, prec, NULL);
    char *x = (!strcmp(h, "-") && starts_with(x0, "-")) ? xfmt("(%s)", a.text) : x0;
    int fa; { int n; int *cs = decode(h, &n); fa = n > 0 && ((cs[0] >= 'a' && cs[0] <= 'z') || (cs[0] >= 'A' && cs[0] <= 'Z') || cs[0] > 127); }
    return mkpiece(fa ? xfmt("%s %s", h, x) : xfmt("%s%s", h, x), prec, "op");
  }
  if (k == 0 && !strcmp(role, "value")) return mkpiece((char *)h, 10, "atom");
  if (strcmp(role, "value")) print_err(xfmt("%s applied to %d argument(s) has no human spelling", h, k));
  L *as = NULL;
  for (int i = 0; i < k; i++) as = cons(go(pr, args[i], sub).text, as);
  return mkpiece(xfmt("%s(%s)", h, sjoin(lrev(as), ", ")), 10, "atom");
}
static Piece go(Printer *pr, Th *v, int formula) {
  Node n = node_of(pr, v);
  if (n.tag == ND_N) {
    if (formula) {
      Machine *m = mach(pr);
      Th *a[2] = { m_vt(m), m_vf(m) };
      Val *r = m_apply_whnf(m, n.a, a, 2);
      if (r->tag == V_T) return mkpiece("true", 10, "atom");
      if (r->tag == V_F) return mkpiece("false", 10, "atom");
      print_err(UNDETERMINED);
    }
    return number_piece(pr, n.a);
  }
  if (n.tag == ND_S) return app_piece(pr, symbol_name(pr, n.a), NULL, 0, formula);
  if (n.tag == ND_A) {
    L *args = l1(n.b);   /* collected from the outside in: the last argument first */
    Node cur = node_of(pr, n.a);
    for (;;) {
      if (cur.tag == ND_A) { args = cons(cur.b, args); cur = node_of(pr, cur.a); }
      else if (cur.tag == ND_S) {
        const char *nm = symbol_name(pr, cur.a);
        int k = llen(args);
        Th **av = NEWN(Th *, k);
        int i = 0;
        for (L *l = args; l; l = l->t) av[i++] = (Th *)l->h;
        return app_piece(pr, nm, av, k, formula);
      } else print_err("a statement applies something that is not a symbol (a λ): it has no human spelling");
    }
  }
  print_err("a statement contains a λ or a bound variable: it has no human spelling yet");
}
static char *spell(Printer *pr, Th *v) { return go(pr, v, 1).text; }

/* the spec term of a human statement, read in the program's context (unknowns declared): the checker chooses ≐ or ≐ᴿ, inserts ⇡ and prop, and
   marks statements — the marks are dropped, the term is what a reader of the output reads back */
static char *reread(Printer *pr, const char *text) {
  Checker *c = chk(pr);
  Handler h;
  Term *term = NULL;
  if (TRY(h)) {
    L *ts = lex_hum(text), *rest;
    term = hum_expr_top(pr->p->hum, ts, &rest);
    if (rest) parse_err(scat("unexpected ", show_htok((HTok *)rest->h)));
    ENDTRY(h);
  } else {
    if (cur_err.kind == E_PARSE) print_err(xfmt("the statement %s cannot be read in the human notation (%s)", py_repr(text), cur_err.msg));
    raise_err(cur_err.kind, cur_err.msg);
  }
  TyTerm r;
  Handler h2;
  char *emsg = NULL;
  volatile int ok = 0;
  if (TRY(h2)) { r = synth(c, NULL, term); ENDTRY(h2); ok = 1; }
  else { if (cur_err.kind != E_CLASS) raise_err(cur_err.kind, cur_err.msg); emsg = cur_err.msg; }
  if (!ok) print_err(xfmt("the statement %s does not read back in this program: %s", py_repr(text), emsg));
  Term *fitted = fit(c, r.term, r.ty, prop_ty);
  if (!fitted) print_err(xfmt("%s reads back as a %s, not as a statement", py_repr(text), show_type(r.ty)));
  return pp_term(strip_quotes(fitted));
}
static char *statement_text(Printer *pr, Th *v) {
  char *text = spell(pr, v);
  return is_hum(pr) ? text : reread(pr, text);
}
static char *number_text(Printer *pr, Th *v, Ty *cls) {
  Machine *m = mach(pr);
  if (is_hum(pr)) return text_of(pr, call(pr, leq(chk(pr), cls, kk("ℚ")) ? "showq" : "showc", &v, 1));
  Th *canon = call(pr, "⊜", &v, 1), *z, *mm;
  m_to_pair(m, canon, &z, &mm);
  char *zt = digits_str(pr, z), *mt = digits_str(pr, mm);
  return !strcmp(mt, "1") ? zt : xfmt("(÷ %s %s)", zt, mt);
}
/* the normal-form term of v (of class cls) in spec or hum notation (bin is spelled from spec) */
static char *term_of(Printer *pr, Th *v, Ty *raw) {
  Checker *c = chk(pr);
  Machine *m = mach(pr);
  int hum = is_hum(pr);
  Ty *cls = norm(c, raw);
  if (cls->tag != TY_K) print_err(xfmt("cannot print a value whose class is not known (%s)", show_type(raw)));
  const char *hd = cls->name;
  L *args = cls->args;
  if (ty_eq(cls, prop_ty)) return statement_text(pr, v);
  if (is_class(pr, raw, "𝕊") || (!strcmp(hd, "𝔏") && args && ty_eq(norm(c, (Ty *)args->h), kk("𝕮")))) return xfmt("\"%s\"", esc('"', text_of(pr, v)));
  if (leq(c, raw, kk("𝕮"))) return xfmt("'%s'", esc('\'', cp_string(char_of(pr, v))));
  if (leq(c, raw, num_ty)) return number_text(pr, v, raw);
  if (!strcmp(hd, "𝔹")) { int b = boolean_of(pr, v); return hum ? (b ? "true" : "false") : (b ? "⊤" : "⊥"); }
  if (!strcmp(hd, "𝔒")) {
    int k = m_to_ord(m, v);
    static const char *hn[] = { "less", "same", "greater" }, *sn[] = { "⋖", "≖", "⋗" };
    return (char *)(hum ? hn : sn)[k < 2 ? k : 2];
  }
  if (!strcmp(hd, "𝔏")) {
    Ty *el = (Ty *)args->h;
    cell_of(pr, v);
    if (ty_eq(norm(c, el), bool_ty) && !hum) return xfmt("(◀ %s)", digits_str(pr, v));
    L *items = NULL;
    Val *cell = cell_of(pr, v);
    while (cell->tag == V_CONS) { items = cons(term_of(pr, cell->a, el), items); cell = cell_of(pr, cell->b); }
    if (hum) return xfmt("[%s]", sjoin(lrev(items), ", "));
    char *out = "⊘";
    for (L *x = items; x; x = x->t) out = xfmt("(∷ %s %s)", (char *)x->h, out);
    return out;
  }
  if (!strcmp(hd, "𝔓")) {
    Th *a, *b;
    m_to_pair(m, v, &a, &b);
    char *x = term_of(pr, a, (Ty *)args->h), *y = term_of(pr, b, (Ty *)args->t->h);
    return hum ? xfmt("pair(%s, %s)", x, y) : xfmt("(⊗ %s %s)", x, y);
  }
  if (!strcmp(hd, "𝔗")) {
    Th *tag, *body;
    m_to_pair(m, v, &tag, &body);
    if (m_to_bool(m, tag)) {
      Th *a, *b;
      m_to_pair(m, body, &a, &b);
      char *x = term_of(pr, a, cls), *y = term_of(pr, b, cls);
      return hum ? xfmt("node(%s, %s)", x, y) : xfmt("(❁ %s %s)", x, y);
    }
    char *x = term_of(pr, body, (Ty *)args->h);
    return hum ? xfmt("leaf(%s)", x) : xfmt("(❀ %s)", x);
  }
  if (!strcmp(hd, "𝔖")) return term_of(pr, m_stream_nth(m, v, pr->n), (Ty *)args->h);
  if (!strcmp(hd, "→") || !strcmp(hd, "𝔄")) print_err(xfmt("a value of class %s has no normal form to print (it is a function)", show_type(raw)));
  print_err(xfmt("cannot print a value of class %s", show_type(raw)));
}
/* the language value of a small natural number, built from its digits (the reader's numeral expansion) */
static Th *lit(Printer *pr, int k) {
  Machine *m = mach(pr);
  Digits one = { 1, (unsigned char *)"\1" };
  Th *a[2] = { m_list_value(m, to_digits_i64(k, 0)), m_list_value(m, one) };
  return m_call_g(m, "⊗", a, 2);
}
/* the remark printed after a stream element (none in bin: the binary notation has no comments) */
static char *comment(Printer *pr, Th *v, Ty *cls0) {
  Checker *c = chk(pr);
  Machine *m = mach(pr);
  Ty *cls = norm(c, cls0);
  if (cls->tag == TY_K && !strcmp(cls->name, "𝔖") && llen(cls->args) == 1 && strcmp(pr->mode, "bin")) {
    Ty *el = (Ty *)cls->args->h;
    const char *mark = is_hum(pr) ? "--" : "⍝";
    char *approx = "";
    if (leq(c, el, num_ty)) {
      Th *x = m_stream_nth(m, v, pr->n);
      Th *re_v = call(pr, "ℜ", &x, 1);
      Th *a1[2] = { re_v, lit(pr, 12) };
      char *re = text_of(pr, call(pr, "decimals", a1, 2));
      Th *im = call(pr, "ℑ", &x, 1);
      Th *a2[2] = { im, lit(pr, 0) };
      Th *eq0 = call(pr, "≐", a2, 2);
      if (!m_to_bool(m, eq0)) {
        Th *a3[2] = { im, lit(pr, 12) };
        char *imt = text_of(pr, call(pr, "decimals", a3, 2));
        const char *stripped = imt; while (*stripped == '-') stripped++;
        approx = xfmt(", ≈ %s %s %s i", re, starts_with(imt, "-") ? "-" : "+", stripped);
      } else approx = xfmt(", ≈ %s", re);
    }
    return xfmt("   %s element %d of the stream%s", mark, pr->n, approx);
  }
  return "";
}
char *show_value(Printer *pr, Th *v, Ty *cls) {
  char *t = term_of(pr, v, cls);
  char *t2 = !strcmp(pr->mode, "bin") ? spec_term_to_bin(t, doc1_copy(pr->p->doc1)) : t;
  return scat(t2, comment(pr, v, cls));
}

/* ------------------------------------------------------------------ main */
static const char *output_mode(Program *p, const char *override_, const char *name) {
  if (override_) return override_;
  if (p->out_mode) return p->out_mode;
  const char *m = (const char *)hget(p->notation_of, name);
  return m ? m : "spec";
}
static const char *run_main_inner(Program *p, const char *mode0, int n, void (*write)(const char *)) {
  Checker *c = p->checker;
  L *sg = sigs_of(c, "main");
  if (!sg) print_err("this program has no main:  define  main ∶ <class>  (spec),  main in <Class> := …  (hum)");
  Ty *cls = (Ty *)sg->h;
  const char *mode = output_mode(p, mode0, "main");
  Th *v = program_val(p, "main");
  Printer pr = { p, mode, n >= 0 ? n : 10 };
  Ty *c0 = norm(c, cls);
  if (leq(c, cls, kk("𝕊"))) {
    Val *cell = cell_of(&pr, v);
    while (cell->tag == V_CONS) { write(cp_string(char_of(&pr, cell->a))); cell = cell_of(&pr, cell->b); }
    return mode;
  }
  if (c0->tag == TY_K && (!strcmp(c0->name, "𝔏") || !strcmp(c0->name, "𝔖")) && llen(c0->args) == 1 && ty_eq(norm(c, (Ty *)c0->args->h), norm(c, kk("𝕊")))) {
    Val *cell = cell_of(&pr, v);
    int k = 0;
    while (cell->tag == V_CONS && (n < 0 || k < n)) {
      char *s = text_of(&pr, cell->a);
      write(scat(s, "\n"));
      cell = cell_of(&pr, cell->b);
      k++;
    }
    return mode;
  }
  write(scat(show_value(&pr, v, cls), "\n"));
  return mode;
}
/* evaluate `main` and write its output; returns the output notation used.  An unknown whose value is needed is reported (E_PRINT), as an
   undetermined truth value is. */
const char *run_main(Program *p, const char *mode0, int n, void (*write)(const char *)) {
  Handler h;
  const char *r = NULL;
  if (TRY(h)) { r = run_main_inner(p, mode0, n, write); ENDTRY(h); return r; }
  if (cur_err.kind == E_UNKNOWN) print_err(cur_err.msg);
  raise_err(cur_err.kind, cur_err.msg);
}
