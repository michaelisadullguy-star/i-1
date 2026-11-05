/* syntax.c -- the SPEC notation reader of i-1 (port of ocamimo/src/syntax.ml). */
#include "cimo.h"

/* ------------------------------------------------------------------ constructors */
Ty *ty_k(const char *name, L *args) { Ty *t = NEW(Ty); t->tag = TY_K; t->name = name; t->args = args; return t; }
Ty *ty_v(const char *name) { Ty *t = NEW(Ty); t->tag = TY_V; t->name = name; return t; }
Ty *ty_f(void) { static Ty *f = NULL; if (!f) { f = NEW(Ty); f->tag = TY_F; } return f; }
Ty *kk(const char *name) { return ty_k(name, NULL); }
int ty_eq(Ty *a, Ty *b) {
  if (a == b) return 1;
  if (a->tag != b->tag) return 0;
  if (a->tag == TY_F) return 1;
  if (strcmp(a->name, b->name)) return 0;
  if (a->tag == TY_V) return 1;
  L *x = a->args, *y = b->args;
  for (; x && y; x = x->t, y = y->t) if (!ty_eq((Ty *)x->h, (Ty *)y->h)) return 0;
  return !x && !y;
}
int ty_is_k(Ty *t, const char *name) { return t->tag == TY_K && !strcmp(t->name, name); }

static Term *mkterm(int tag) { Term *t = NEW(Term); t->tag = tag; return t; }
Term *t_num(const char *s) { Term *t = mkterm(T_NUM); t->s = s; return t; }
Term *t_chr(int c) { Term *t = mkterm(T_CHR); t->c = c; return t; }
Term *t_str(const char *s) { Term *t = mkterm(T_STR); t->s = s; return t; }
Term *t_var(const char *n) { Term *t = mkterm(T_VAR); t->s = n; return t; }
Term *t_app(Term *f, L *args) { Term *t = mkterm(T_APP); t->f = f; t->args = args; return t; }
Term *t_lam(L *ps, Term *body) { Term *t = mkterm(T_LAM); t->ps = ps; t->body = body; return t; }
Term *t_asc(Term *e, Ty *ty) { Term *t = mkterm(T_ASC); t->body = e; t->ty = ty; return t; }
Term *t_quote(Term *e, L *loc) { Term *t = mkterm(T_QUOTE); t->body = e; t->loc = loc; return t; }
Term *app_s(const char *f, L *args) { return t_app(t_var(f), args); }
static int terms_eq(L *a, L *b) {
  for (; a && b; a = a->t, b = b->t) if (!term_eq((Term *)a->h, (Term *)b->h)) return 0;
  return !a && !b;
}
int term_eq(Term *a, Term *b) {
  if (a == b) return 1;
  if (a->tag != b->tag) return 0;
  switch (a->tag) {
    case T_NUM: case T_STR: case T_VAR: return !strcmp(a->s, b->s);
    case T_CHR: return a->c == b->c;
    case T_APP: return term_eq(a->f, b->f) && terms_eq(a->args, b->args);
    case T_LAM: {
      L *x = a->ps, *y = b->ps;
      for (; x && y; x = x->t, y = y->t) {
        Param *p = (Param *)x->h, *q = (Param *)y->h;
        if (strcmp(p->name, q->name) || (p->ty == NULL) != (q->ty == NULL) || (p->ty && !ty_eq(p->ty, q->ty))) return 0;
      }
      return !x && !y && term_eq(a->body, b->body);
    }
    case T_ASC: return ty_eq(a->ty, b->ty) && term_eq(a->body, b->body);
    default: return term_eq(a->body, b->body);
  }
}
Stmt *s_def(const char *n, L *params, Term *body) { Stmt *s = NEW(Stmt); s->kind = S_DEF; s->name = n; s->params = params; s->body = body; return s; }
Stmt *s_decl(const char *n, Ty *ty) { Stmt *s = NEW(Stmt); s->kind = S_DECL; s->name = n; s->ty = ty; return s; }
Stmt *s_fact(Term *t) { Stmt *s = NEW(Stmt); s->kind = S_FACT; s->body = t; return s; }
Core *c_v(int k) { Core *c = NEW(Core); c->tag = C_V; c->k = k; return c; }
Core *c_l(Core *b) { Core *c = NEW(Core); c->tag = C_L; c->f = b; return c; }
Core *c_a(Core *f, Core *x) { Core *c = NEW(Core); c->tag = C_A; c->f = f; c->x = x; return c; }
Core *c_g(const char *g) { Core *c = NEW(Core); c->tag = C_G; c->g = g; return c; }

L *loc_insert(L *loc, const char *n, Ty *t) {
  int found = 0;
  for (L *l = loc; l; l = l->t) if (!strcmp(((LocEnt *)l->h)->name, n)) found = 1;
  LocEnt *e = NEW(LocEnt); e->name = n; e->ty = t;
  if (!found) return lappend(loc, l1(e));
  L *out = NULL;
  for (L *l = loc; l; l = l->t) out = cons(!strcmp(((LocEnt *)l->h)->name, n) ? e : l->h, out);
  return lrev(out);
}
Ty *loc_lookup(L *loc, const char *n) { for (; loc; loc = loc->t) if (!strcmp(((LocEnt *)loc->h)->name, n)) return ((LocEnt *)loc->h)->ty; return NULL; }
int loc_member(L *loc, const char *n) { for (; loc; loc = loc->t) if (!strcmp(((LocEnt *)loc->h)->name, n)) return 1; return 0; }
int is_class_var(const char *n) { return !strcmp(n, "α") || !strcmp(n, "β") || !strcmp(n, "γ") || !strcmp(n, "δ") || !strcmp(n, "ε"); }

#define ARROW "→"
#define MAPSTO "↦"
#define COLON "∶"
#define ASSIGN "≔"

/* ------------------------------------------------------------------ Haskell-style `show` (the messages of Haskimo quote it) */
static const char *hs_names[32] = {"NUL", "SOH", "STX", "ETX", "EOT", "ENQ", "ACK", "a", "b", "t", "n", "v", "f", "r", "SO", "SI", "DLE", "DC1", "DC2", "DC3", "DC4",
                                   "NAK", "SYN", "ETB", "CAN", "EM", "SUB", "ESC", "FS", "GS", "RS", "US"};
static char *hs_show_str(const char *s) {
  int n; int *cs = decode(s, &n);
  Buf *b = bnew();
  baddc(b, '"');
  for (int i = 0; i < n; i++) {
    int u = cs[i], next = i + 1 < n ? cs[i + 1] : -1;
    if (u == 34) badd(b, "\\\"");
    else if (u == 92) badd(b, "\\\\");
    else if (u < 32) { baddc(b, '\\'); badd(b, hs_names[u]); if (u == 14 && next == 72) badd(b, "\\&"); }
    else if (u == 127) badd(b, "\\DEL");
    else if (u > 126) { badd(b, xfmt("\\%d", u)); if (next >= 48 && next <= 57) badd(b, "\\&"); }
    else baddc(b, (char)u);
  }
  baddc(b, '"');
  return bstr(b);
}
char *hs_show_list_str(L *xs) {
  Buf *b = bnew();
  baddc(b, '[');
  for (int first = 1; xs; xs = xs->t, first = 0) { if (!first) baddc(b, ','); badd(b, hs_show_str((const char *)xs->h)); }
  baddc(b, ']');
  return bstr(b);
}
static char *hs_show_ty(Ty *t) {
  if (t->tag == TY_V) return scat("V ", hs_show_str(t->name));
  if (t->tag == TY_F) return "F";
  Buf *b = bnew();
  for (L *a = t->args; a; a = a->t) { if (a != t->args) baddc(b, ','); badd(b, hs_show_ty((Ty *)a->h)); }
  return xfmt("K %s [%s]", hs_show_str(t->name), bstr(b));
}

/* ------------------------------------------------------------------ lexer */
static Tok *mktok(int kind, const char *s, int c) { Tok *t = NEW(Tok); t->kind = kind; t->s = s; t->c = c; return t; }
static char *hs_show_tok(Tok *t) {
  switch (t->kind) {
    case K_NL: return "TNL";
    case K_OPEN: return "TOpen";
    case K_CLOSE: return "TClose";
    case K_NUM: return scat("TkNum ", hs_show_str(t->s));
    case K_CHR: return xfmt("TkChr %d", t->c);
    case K_STR: return scat("TkStr ", hs_show_str(t->s));
    default: return scat("TkName ", hs_show_str(t->s));
  }
}
static int is_delim(int c) { return c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '(' || c == ')' || c == '0' || c == '1' || c == '.' || c == '\'' || c == '"'; }

L *lex_spec(const char *text) {
  int n; int *cs = decode(text, &n);
  int i = 0, d = 0;
  L *out = NULL;
  while (i < n) {
    int c = cs[i];
    if (c == ' ' || c == '\t' || c == '\r') i++;
    else if (c == '\n') { if (d == 0) out = cons(mktok(K_NL, NULL, 0), out); i++; }
    else if (c == '(') { out = cons(mktok(K_OPEN, NULL, 0), out); d++; i++; }
    else if (c == ')') { out = cons(mktok(K_CLOSE, NULL, 0), out); d--; i++; }
    else if (c == '0' || c == '1' || c == '.') {
      int j = i, dots = 0;
      while (j < n && (cs[j] == '0' || cs[j] == '1' || cs[j] == '.')) { if (cs[j] == '.') dots++; j++; }
      char *s = encode_range(cs, i, j);
      if (dots > 1) parse_err(xfmt("bad numeral %s (spec notation allows one radix point)", py_repr(s)));
      out = cons(mktok(K_NUM, s, 0), out);
      i = j;
    } else if (c == '\'' || c == '"') {
      Buf *body = bnew();
      int blen = 0, first = 0, j = i + 1;
      for (;;) {
        if (j >= n) parse_err("unterminated literal");
        int x = cs[j];
        if (x == c) { j++; break; }
        if (x == '\\') {
          if (j + 1 >= n) parse_err("string index out of range");
          int y = cs[j + 1];
          if (y == 'n') y = '\n'; else if (y == 't') y = '\t';
          if (blen == 0) first = y;
          baddcp(body, y); blen++; j += 2;
        } else { if (blen == 0) first = x; baddcp(body, x); blen++; j++; }
      }
      if (c == '\'') {
        if (blen == 1) out = cons(mktok(K_CHR, NULL, first), out);
        else parse_err(xfmt("char literal needs exactly one character: %s", py_repr(bstr(body))));
      } else out = cons(mktok(K_STR, bstr(body), 0), out);
      i = j;
    } else {
      int j = i;
      while (j < n && !is_delim(cs[j])) j++;
      char *name = encode_range(cs, i, j);
      if (!strcmp(name, "⍝")) {
        int k = j;
        while (k < n && cs[k] != '\n') k++;
        i = k;
      } else { out = cons(mktok(K_NAME, name, 0), out); i = j; }
    }
  }
  return lrev(out);
}

/* token trees: an atom or a parenthesised group */
typedef struct TT { int grp; Tok *tok; L *items; } TT;
static TT *tt_atom(Tok *t) { TT *x = NEW(TT); x->tok = t; return x; }
static char *hs_show_tt(TT *t) {
  if (t->grp) {
    Buf *b = bnew();
    for (L *a = t->items; a; a = a->t) { if (a != t->items) baddc(b, ','); badd(b, hs_show_tt((TT *)a->h)); }
    return xfmt("Grp [%s]", bstr(b));
  }
  char *s = hs_show_tok(t->tok);
  return strchr(s, ' ') ? xfmt("Atom (%s)", s) : scat("Atom ", s);
}
static L *trees_go(Tok **v, int n, int *i) {
  L *out = NULL;
  while (*i < n) {
    Tok *t = v[*i];
    if (t->kind == K_OPEN) {
      (*i)++;
      L *inner = trees_go(v, n, i);
      if (*i < n && v[*i]->kind == K_CLOSE) { (*i)++; TT *g = NEW(TT); g->grp = 1; g->items = inner; out = cons(g, out); }
      else parse_err("missing )");
    } else if (t->kind == K_CLOSE) break;
    else { out = cons(tt_atom(t), out); (*i)++; }
  }
  return lrev(out);
}
static L *trees(L *ts) {
  int n = llen(ts), i = 0;
  Tok **v = NEWN(Tok *, n);
  int k = 0;
  for (L *l = ts; l; l = l->t) v[k++] = (Tok *)l->h;
  L *r = trees_go(v, n, &i);
  if (i < n) parse_err("unexpected )");
  return r;
}
static L *logical_lines(L *toks) {
  L *lines = NULL, *cur = NULL;
  for (L *l = toks; l; l = l->t) {
    Tok *t = (Tok *)l->h;
    if (t->kind == K_NL) { lines = cons(lrev(cur), lines); cur = NULL; } else cur = cons(t, cur);
  }
  lines = cons(lrev(cur), lines);
  lines = lrev(lines);
  L *out = NULL;
  for (L *l = lines; l; l = l->t) { L *tt = trees((L *)l->h); if (tt) out = cons(tt, out); }
  return lrev(out);
}

/* ------------------------------------------------------------------ terms */
static int is_name(TT *t, const char *n) { return !t->grp && t->tok->kind == K_NAME && !strcmp(t->tok->s, n); }
static Term *parse_seq(L *ts);
static Ty *parse_type_seq(L *inner);
static Ty *parse_type_atom(L *ts, L **rest);
static L *parse_binders(L *ts) {
  L *out = NULL;
  while (ts) {
    TT *t = (TT *)ts->h;
    if (!t->grp && t->tok->kind == K_NAME) {
      Param *p = NEW(Param); p->name = t->tok->s; p->ty = NULL;
      if (ts->t && is_name((TT *)ts->t->h, COLON)) { p->ty = parse_type_atom(ts->t->t, &ts); }
      else ts = ts->t;
      out = cons(p, out);
    } else parse_err(scat("bad binder ", hs_show_tt(t)));
  }
  return lrev(out);
}
static Term *parse_item(TT *t) {
  if (!t->grp) {
    Tok *k = t->tok;
    switch (k->kind) {
      case K_NUM: return t_num(k->s);
      case K_CHR: return t_chr(k->c);
      case K_STR: return t_str(k->s);
      case K_NAME: return t_var(k->s);
      default: parse_err(scat("unexpected ", hs_show_tok(k)));
    }
  }
  int last = -1, i = 0;
  for (L *l = t->items; l; l = l->t, i++) if (is_name((TT *)l->h, MAPSTO)) last = i;
  if (last >= 0) return t_lam(parse_binders(ltake(last, t->items)), parse_seq(ldrop(last + 1, t->items)));
  return parse_seq(t->items);
}
static Term *parse_seq(L *ts) {
  if (!ts) parse_err("empty application");
  if (!ts->t) return parse_item((TT *)ts->h);
  Term *f = parse_item((TT *)ts->h);
  L *args = NULL;
  for (L *l = ts->t; l; l = l->t) args = cons(parse_item((TT *)l->h), args);
  return t_app(f, lrev(args));
}

/* ------------------------------------------------------------------ types */
static Ty *parse_type_atom(L *ts, L **rest) {
  if (!ts) parse_err("list index out of range");
  TT *t = (TT *)ts->h;
  if (!t->grp && t->tok->kind == K_NAME) { *rest = ts->t; return is_class_var(t->tok->s) ? ty_v(t->tok->s) : kk(t->tok->s); }
  if (t->grp) { *rest = ts->t; return parse_type_seq(t->items); }
  parse_err(scat("bad type ", hs_show_tt(t)));
}
static L *type_atoms(L *ts) {
  L *out = NULL;
  while (ts) { Ty *a = parse_type_atom(ts, &ts); out = cons(a, out); }
  return lrev(out);
}
static Ty *parse_type_seq(L *inner) {
  if (!inner) parse_err("empty type");
  if (is_name((TT *)inner->h, ARROW)) {
    L *a = type_atoms(inner->t);
    if (llen(a) == 2) return ty_k(ARROW, a);
    parse_err("→ takes two classes");
  }
  int k = -1, i = 0;
  for (L *l = inner; l; l = l->t, i++) if (is_name((TT *)l->h, ARROW)) { k = i; break; }
  if (k >= 0) {
    Ty *l = parse_type_seq(ltake(k, inner));
    Ty *r = parse_type_seq(ldrop(k + 1, inner));
    return ty_k(ARROW, l2(l, r));
  }
  L *rest;
  Ty *hd = parse_type_atom(inner, &rest);
  L *args = type_atoms(rest);
  if (!args) return hd;
  if (hd->tag == TY_K && !hd->args) return ty_k(hd->name, args);
  parse_err(scat("bad class application ", hs_show_ty(hd)));
}
char *show_type(Ty *t) {
  if (t->tag == TY_V) return (char *)t->name;
  if (t->tag == TY_F) return "⊥";
  if (!strcmp(t->name, ARROW) && llen(t->args) == 2) {
    Ty *a = (Ty *)t->args->h;
    char *l = show_type(a);
    if (ty_is_k(a, ARROW)) l = xfmt("(%s)", l);
    return xfmt("%s → %s", l, show_type((Ty *)t->args->t->h));
  }
  if (!t->args) return (char *)t->name;
  Buf *b = bnew();
  for (L *a = t->args; a; a = a->t) {
    if (a != t->args) baddc(b, ' ');
    Ty *x = (Ty *)a->h;
    badd(b, ty_is_k(x, ARROW) ? xfmt("(%s)", show_type(x)) : show_type(x));
  }
  return xfmt("(%s %s)", t->name, bstr(b));
}

/* ------------------------------------------------------------------ statements */
static int has_assign(TT *t) {
  if (t->grp) { for (L *l = t->items; l; l = l->t) if (has_assign((TT *)l->h)) return 1; return 0; }
  return t->tok->kind == K_NAME && !strcmp(t->tok->s, ASSIGN);
}
static Stmt *statement(L *ln) {
  int any = 0;
  for (L *l = ln; l; l = l->t) if (has_assign((TT *)l->h)) any = 1;
  if (any) {
    int k = -1, i = 0;
    for (L *l = ln; l; l = l->t, i++) if (is_name((TT *)l->h, ASSIGN)) { k = i; break; }
    if (k < 0) parse_err("assertion failed");
    L *hd = ltake(k, ln), *body = ldrop(k + 1, ln);
    L *names = NULL;
    for (L *l = hd; l; l = l->t) { TT *t = (TT *)l->h; if (!t->grp && t->tok->kind == K_NAME) names = cons((void *)t->tok->s, names); }
    names = lrev(names);
    if (!hd || llen(names) != llen(hd)) parse_err(scat("bad definition head ", hs_show_list_str(names)));
    return s_def((const char *)names->h, names->t, parse_seq(body));
  }
  if (llen(ln) >= 3 && is_name((TT *)ln->t->h, COLON)) {
    TT *a = (TT *)ln->h;
    if (!a->grp && a->tok->kind == K_NAME) return s_decl(a->tok->s, parse_type_seq(ln->t->t));
    parse_err("assertion failed");
  }
  return s_fact(parse_seq(ln));
}
L *parse_statements(const char *text) {
  L *toks = lex_spec(text);
  L *lines = logical_lines(toks);
  L *out = NULL;
  for (L *l = lines; l; l = l->t) out = cons(statement((L *)l->h), out);
  return lrev(out);
}

/* ------------------------------------------------------------------ erasure to the runtime (de Bruijn) term */
static Core *int_ast(const char *s) {
  Core *r = c_g("⊥");
  for (; *s; s++) r = c_a(c_a(c_g("∷"), c_g(*s == '1' ? "⊤" : "⊥")), r);
  return r;
}
static Core *num_ast(const char *s) {
  const char *dot = strchr(s, '.');
  if (!dot) return c_a(c_a(c_g("⊗"), int_ast(s)), int_ast("1"));
  char *x = ssub(s, 0, (int)(dot - s)), *y = (char *)dot + 1;
  char *bits = scat(x, y);
  if (!*bits) parse_err("empty numeral");
  Buf *b = bnew(); baddc(b, '1');
  for (int i = 0; i < (int)strlen(y); i++) baddc(b, '0');
  return c_a(c_a(c_g("⊗"), int_ast(bits)), int_ast(bstr(b)));
}
Core *erase(L *scope, Term *t) {
  switch (t->tag) {
    case T_NUM: return num_ast(t->s);
    case T_CHR: return num_ast(int_numeral_text(t->c));
    case T_STR: {
      int n; int *cs = decode(t->s, &n);
      Core *r = c_g("⊘");
      for (int i = n - 1; i >= 0; i--) r = c_a(c_a(c_g("∷"), num_ast(int_numeral_text(cs[i]))), r);
      return r;
    }
    case T_VAR: {
      int idx = 0;
      for (L *l = scope; l; l = l->t, idx++) if (!strcmp((const char *)l->h, t->s)) return c_v(idx + 1);
      return c_g(t->s);
    }
    case T_APP: {
      Core *acc = erase(scope, t->f);
      for (L *a = t->args; a; a = a->t) acc = c_a(acc, erase(scope, (Term *)a->h));
      return acc;
    }
    case T_LAM: {
      L *sc = scope;
      for (L *p = t->ps; p; p = p->t) sc = cons((void *)((Param *)p->h)->name, sc);
      Core *body = erase(sc, t->body);
      for (L *p = t->ps; p; p = p->t) body = c_l(body);
      return body;
    }
    default: return erase(scope, t->body);   /* Asc, Quote */
  }
}
Core *erase_def(L *params, Term *body) {
  L *scope = NULL;
  for (L *p = params; p; p = p->t) scope = cons(p->h, scope);
  Core *c = erase(scope, body);
  for (L *p = params; p; p = p->t) c = c_l(c);
  return c;
}

/* ------------------------------------------------------------------ pretty printer (spec text) */
char *pp_type(Ty *t) {
  if (t->tag == TY_V) return (char *)t->name;
  if (t->tag == TY_F) return "⊥";
  if (!strcmp(t->name, ARROW) && llen(t->args) == 2) return xfmt("(→ %s %s)", pp_type((Ty *)t->args->h), pp_type((Ty *)t->args->t->h));
  if (!t->args) return (char *)t->name;
  Buf *b = bnew();
  for (L *a = t->args; a; a = a->t) { if (a != t->args) baddc(b, ' '); badd(b, pp_type((Ty *)a->h)); }
  return xfmt("(%s %s)", t->name, bstr(b));
}
static char *esc_with(const char *s, int q) {
  int n; int *cs = decode(s, &n);
  Buf *b = bnew();
  for (int i = 0; i < n; i++) {
    int c = cs[i];
    if (c == '\\') badd(b, "\\\\");
    else if (c == '\n') badd(b, "\\n");
    else if (c == q) { baddc(b, '\\'); baddcp(b, c); }
    else baddcp(b, c);
  }
  return bstr(b);
}
char *pp_term(Term *t) {
  switch (t->tag) {
    case T_NUM: case T_VAR: return (char *)t->s;
    case T_CHR: return xfmt("'%s'", esc_with(cp_string(t->c), '\''));
    case T_STR: return xfmt("\"%s\"", esc_with(t->s, '"'));
    case T_APP: {
      Buf *b = bnew();
      baddc(b, '('); badd(b, pp_term(t->f));
      for (L *a = t->args; a; a = a->t) { baddc(b, ' '); badd(b, pp_term((Term *)a->h)); }
      baddc(b, ')');
      return bstr(b);
    }
    case T_LAM: {
      Buf *b = bnew();
      baddc(b, '(');
      for (L *p = t->ps; p; p = p->t) {
        Param *q = (Param *)p->h;
        if (p != t->ps) baddc(b, ' ');
        badd(b, q->name);
        if (q->ty) { badd(b, " ∶ "); badd(b, pp_type(q->ty)); }
      }
      badd(b, " ↦ "); badd(b, pp_term(t->body)); baddc(b, ')');
      return bstr(b);
    }
    default: return pp_term(t->body);
  }
}
char *pp_statement(Stmt *s) {
  if (s->kind == S_DEF) {
    Buf *b = bnew();
    badd(b, s->name);
    for (L *p = s->params; p; p = p->t) { baddc(b, ' '); badd(b, (const char *)p->h); }
    badd(b, " ≔ "); badd(b, pp_term(s->body));
    return bstr(b);
  }
  if (s->kind == S_DECL) return xfmt("%s ∶ %s", s->name, pp_type(s->ty));
  return pp_term(s->body);
}

/* ------------------------------------------------------------------ Python repr of the tuple form of a term (for error messages) */
static char *tuple_of(L *xs) {
  if (!xs) return "()";
  if (!xs->t) return xfmt("(%s,)", (char *)xs->h);
  return xfmt("(%s)", sjoin(xs, ", "));
}
static char *repr_ty(Ty *t) {
  if (t->tag == TY_V) return xfmt("('V', %s)", py_repr(t->name));
  if (t->tag == TY_F) return "('F', '⊥')";
  L *a = NULL;
  for (L *x = t->args; x; x = x->t) a = cons(repr_ty((Ty *)x->h), a);
  return xfmt("('K', %s, %s)", py_repr(t->name), tuple_of(lrev(a)));
}
char *repr_term(Term *t) {
  switch (t->tag) {
    case T_NUM: return xfmt("('num', %s)", py_repr(t->s));
    case T_CHR: return xfmt("('chr', %d)", t->c);
    case T_STR: return xfmt("('str', %s)", py_repr(t->s));
    case T_VAR: return xfmt("('var', %s)", py_repr(t->s));
    case T_APP: {
      L *a = NULL;
      for (L *x = t->args; x; x = x->t) a = cons(repr_term((Term *)x->h), a);
      return xfmt("('app', %s, [%s])", repr_term(t->f), sjoin(lrev(a), ", "));
    }
    case T_LAM: {
      L *a = NULL;
      for (L *x = t->ps; x; x = x->t) {
        Param *p = (Param *)x->h;
        a = cons(xfmt("(%s, %s)", py_repr(p->name), p->ty ? repr_ty(p->ty) : "None"), a);
      }
      return xfmt("('lam', [%s], %s)", sjoin(lrev(a), ", "), repr_term(t->body));
    }
    case T_ASC: return xfmt("('asc', %s, %s)", repr_term(t->body), repr_ty(t->ty));
    default: return xfmt("('quote', %s)", repr_term(t->body));
  }
}
