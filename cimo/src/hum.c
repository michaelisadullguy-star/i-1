/* hum.c -- the HUMAN notation of i-1 and doc 2 (port of ocamimo/src/hum.ml). */
#include "cimo.h"

/* ------------------------------------------------------------------ doc 2 */
static Doc2 *doc2_make(L *entries) {
  Doc2 *d = NEW(Doc2);
  d->entries = entries; d->by_hum = hnew();
  for (L *l = entries; l; l = l->t) {
    Entry *e = (Entry *)l->h;
    hset(d->by_hum, e->hum, cons(e, (L *)hget(d->by_hum, e->hum)));
  }
  for (int i = 0; i < d->by_hum->n; i++) d->by_hum->vals[i] = lrev((L *)d->by_hum->vals[i]);
  return d;
}
Doc2 *doc2_parse(const char *text) {
  L *es = NULL;
  for (L *l = split_on(text, "\n"); l; l = l->t) {
    char *ln1 = strip((const char *)l->h);
    if (!*ln1 || starts_with(ln1, "⍝")) continue;
    int c = find_sub(ln1, " ⍝ ", 0);
    char *ln = c >= 0 ? ssub(ln1, 0, c) : ln1;
    int k = find_sub(ln, " := ", 0);
    if (k < 0) parse_err(xfmt("doc2: bad line %s", py_repr(ln)));
    char *hd = ssub(ln, 0, k), *rest = ln + k + 4;
    int j = rfind_sub(rest, " ; ");
    char *rhs = j >= 0 ? ssub(rest, 0, j) : "";
    L *role = split_ws(j >= 0 ? rest + j + 3 : rest);
    if (!role) parse_err("Prelude.head: empty list");
    Entry *e = NEW(Entry);
    e->hum = strip(hd);
    L *rl = NULL;
    for (L *x = split_on(rhs, " | "); x; x = x->t) rl = cons(strip((const char *)x->h), rl);
    e->rhs = lrev(rl);
    e->role = (const char *)role->h;
    if (role->t) {
      char *endp; const char *ps = (const char *)role->t->h;
      long v = strtol(ps, &endp, 10);
      if (*ps && !*endp) { e->has_prec = 1; e->prec = (int)v; }
    }
    es = cons(e, es);
  }
  return doc2_make(lrev(es));
}
Entry *doc2_find(Doc2 *d, const char *hum, const char **roles) {
  for (L *l = (L *)hget(d->by_hum, hum); l; l = l->t) {
    Entry *e = (Entry *)l->h;
    for (const char **r = roles; *r; r++) if (!strcmp(*r, e->role)) return e;
  }
  return NULL;
}
int all_bin_chars(const char *s) { for (; *s; s++) if (*s != '0' && *s != '1' && *s != '.') return 0; return 1; }
Hash *overload_table(Doc2 *d) {
  Hash *m = hnew();
  for (L *l = d->entries; l; l = l->t) {
    Entry *e = (Entry *)l->h;
    if (!strcmp(e->role, "class") || !strcmp(e->role, "literal") || !strcmp(e->role, "syntax")) continue;
    char *key = !strcmp(e->role, "prefix") ? scat("hum:prefix ", e->hum) : scat("hum:", e->hum);
    L *v = NULL;
    for (L *x = e->rhs; x; x = x->t) { const char *s = (const char *)x->h; if (!(*s && all_bin_chars(s))) v = cons((void *)s, v); }
    hset(m, key, lrev(v));
  }
  return m;
}
Doc2 *doc2_remap(Doc2 *d, Doc1 *d1) {
  L *es = NULL;
  for (L *l = d->entries; l; l = l->t) {
    Entry *e = (Entry *)l->h, *n = NEW(Entry);
    *n = *e;
    L *r = NULL;
    for (L *x = e->rhs; x; x = x->t) {
      const char *s = (const char *)x->h;
      const char *m = is_bin_sym(s) ? (const char *)hget(d1->b2s, s) : NULL;
      r = cons((void *)(m ? m : s), r);
    }
    n->rhs = lrev(r);
    es = cons(n, es);
  }
  return doc2_make(lrev(es));
}

/* ------------------------------------------------------------------ lexer */
enum { H_NUM = 1, H_STR, H_CHR, H_ID, H_OP };
static HTok *mkh(int kind, const char *s, int c) { HTok *t = NEW(HTok); t->kind = kind; t->s = s; t->c = c; return t; }
char *show_htok(HTok *t) {
  switch (t->kind) {
    case H_NUM: return xfmt("('NUM', %s)", py_repr(t->s));
    case H_STR: return xfmt("('STR', %s)", py_repr(t->s));
    case H_CHR: return xfmt("('CHR', %d)", t->c);
    case H_ID: return xfmt("('ID', %s)", py_repr(t->s));
    default: return xfmt("('OP', %s)", py_repr(t->s));
  }
}
static int is_digit(int c) { return c >= '0' && c <= '9'; }
static int is_letter(int c) { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'); }
/* the body of a quoted literal; returns the body with its backslashes (NULL if unterminated) and sets *next */
static char *quoted(int *cs, int n, int start, int q, int *next) {
  Buf *b = bnew();
  int i = start;
  while (i < n) {
    int x = cs[i];
    if (x == q) { *next = i + 1; return bstr(b); }
    if (x == '\\') {
      if (i + 1 < n && cs[i + 1] != '\n') { baddc(b, '\\'); baddcp(b, cs[i + 1]); i += 2; } else return NULL;
    } else { baddcp(b, x); i++; }
  }
  return NULL;
}
static int *unescape(const char *s, int *np) {
  int n; int *cs = decode(s, &n);
  int *out = NEWN(int, n); int k = 0, i = 0;
  while (i < n) {
    if (cs[i] == '\\' && i + 1 < n) { int y = cs[i + 1]; out[k++] = y == 'n' ? '\n' : y == 't' ? '\t' : y; i += 2; }
    else out[k++] = cs[i++];
  }
  *np = k;
  return out;
}
L *lex_hum(const char *line0) {
  int n0; int *cs = decode(line0, &n0);
  int n = n0;
  while (n > 0 && cp_is_ws(cs[n - 1])) n--;
  int i = 0;
  L *out = NULL;
  for (;;) {
    while (i < n && cp_is_ws(cs[i])) i++;
    if (i >= n) return lrev(out);
    int c = cs[i];
    if (is_digit(c)) {
      int j = i;
      while (j < n && is_digit(cs[j])) j++;
      char *ip = encode_range(cs, i, j);
      if (j + 1 < n && cs[j] == '.' && is_digit(cs[j + 1])) {
        int k = j + 1;
        while (k < n && is_digit(cs[k])) k++;
        out = cons(mkh(H_NUM, xfmt("%s.%s", ip, encode_range(cs, j + 1, k)), 0), out);
        i = k;
      } else { out = cons(mkh(H_NUM, ip, 0), out); i = j; }
      continue;
    }
    if (c == '"') {
      int next; char *body = quoted(cs, n, i + 1, '"', &next);
      if (body) { int un; int *u = unescape(body, &un); out = cons(mkh(H_STR, encode_range(u, 0, un), 0), out); i = next; continue; }
    }
    if (c == '\'') {
      int next; char *body = quoted(cs, n, i + 1, '\'', &next);
      if (body) {
        int un; int *u = unescape(body, &un);
        if (un == 1) { out = cons(mkh(H_CHR, NULL, u[0]), out); i = next; continue; }
      }
    }
    if (c == '\\') {
      int j = i + 1;
      while (j < n && is_letter(cs[j])) j++;
      if (j > i + 1) { out = cons(mkh(H_ID, scat("\\", encode_range(cs, i + 1, j)), 0), out); i = j; continue; }
    }
    if (is_letter(c) || c == '_') {
      int j = i;
      while (j < n && (is_letter(cs[j]) || cs[j] == '_' || is_digit(cs[j]))) j++;
      out = cons(mkh(H_ID, encode_range(cs, i, j), 0), out);
      i = j;
      continue;
    }
    char *rest = encode_range(cs, i, i + 3 < n ? i + 3 : n);
    static const char *ops[] = { ":=", "|->", "->", "==", "!=", "++", NULL };
    const char *found = NULL;
    for (int k = 0; ops[k]; k++) if (starts_with(rest, ops[k])) { found = ops[k]; break; }
    if (found) { out = cons(mkh(H_OP, found, 0), out); i += (int)strlen(found); continue; }
    if (c < 128 && strchr("-+*/^(),[]", c)) { out = cons(mkh(H_OP, xfmt("%c", c), 0), out); i++; continue; }
    parse_err(xfmt("human notation: cannot read %s", py_repr(encode_range(cs, i, i + 12 < n ? i + 12 : n))));
  }
}
/* a logical line ends at a newline outside parentheses; `--` starts a comment */
static int count_ch(const char *s, char ch) { int k = 0; for (; *s; s++) if (*s == ch) k++; return k; }
static L *hum_logical_lines(const char *text) {
  L *out = NULL;
  Buf *cur = bnew();
  int depth = 0;
  for (L *l = split_on(text, "\n"); l; l = l->t) {
    const char *ln0 = (const char *)l->h;
    const char *ln = ln0;
    if (contains_sub(ln0, "--") && !strchr(ln0, '"')) ln = ssub(ln0, 0, find_sub(ln0, "--", 0));
    baddc(cur, ' '); badd(cur, ln);
    depth += count_ch(ln, '(') - count_ch(ln, ')') + count_ch(ln, '[') - count_ch(ln, ']');
    if (depth <= 0) {
      char *s = strip(bstr(cur));
      if (*s) out = cons(s, out);
      cur = bnew(); depth = 0;
    }
  }
  char *s = strip(bstr(cur));
  if (*s) out = cons(s, out);
  return lrev(out);
}

/* ------------------------------------------------------------------ parser */
Hum *mk_hum(Doc2 *d) {
  Hum *h = NEW(Hum);
  h->doc = d; h->infix = hnew(); h->prefix = hnew();
  for (L *l = d->entries; l; l = l->t) {
    Entry *e = (Entry *)l->h;
    if (!strcmp(e->role, "infixl") || !strcmp(e->role, "infixr") || !strcmp(e->role, "infix")) hset(h->infix, e->hum, e);
    if (!strcmp(e->role, "prefix")) hset(h->prefix, e->hum, e);
  }
  return h;
}
static void oob(void) { parse_err("list index out of range"); }
static int is_op(HTok *t, const char *o) { return t->kind == H_OP && !strcmp(t->s, o); }
static int is_id_s(HTok *t, const char *o) { return t->kind == H_ID && !strcmp(t->s, o); }
static const char *CLASS_ROLE[] = { "class", NULL }, *LITERAL_ROLE[] = { "literal", NULL }, *VALUE_ROLE[] = { "value", NULL };

static Ty *class_expr(Hum *h, L *ts, L **rest);
static Ty *class_atom(Hum *h, L *ts, L **rest) {
  if (!ts) oob();
  HTok *t = (HTok *)ts->h;
  if (is_op(t, "(")) {
    L *r; Ty *c = class_expr(h, ts->t, &r);
    if (r && is_op((HTok *)r->h, ")")) { *rest = r->t; return c; }
    parse_err("missing )");
  }
  if (t->kind == H_ID) {
    Entry *e = doc2_find(h->doc, t->s, CLASS_ROLE);
    if (!e) parse_err(xfmt("%s is not a class in doc 2", t->s));
    const char *name = (const char *)e->rhs->h;
    if (is_class_var(name)) { *rest = ts->t; return ty_v(name); }
    if (ts->t && is_op((HTok *)ts->t->h, "(")) {
      L *args = NULL, *r = ts->t->t;
      for (;;) {
        L *r1; Ty *a = class_expr(h, r, &r1);
        args = cons(a, args);
        if (!r1) oob();
        HTok *x = (HTok *)r1->h;
        if (is_op(x, ",")) r = r1->t;
        else if (is_op(x, ")")) { *rest = r1->t; return ty_k(name, lrev(args)); }
        else parse_err("missing ) in class");
      }
    }
    *rest = ts->t;
    return ty_k(name, NULL);
  }
  parse_err(scat("class expected, found ", show_htok(t)));
}
static Ty *class_expr(Hum *h, L *ts, L **rest) {
  L *r; Ty *l = class_atom(h, ts, &r);
  if (r && is_op((HTok *)r->h, "->")) {
    L *r2; Ty *rt = class_expr(h, r->t, &r2);
    *rest = r2;
    return ty_k("→", l2(l, rt));
  }
  *rest = r;
  return l;
}
static Term *number(const char *text) {
  const char *dot = strchr(text, '.');
  if (!dot) return t_num(big_numeral_text(big_parse_dec(text)));
  char *a = ssub(text, 0, (int)(dot - text)); const char *b = dot + 1;
  Big *den = big_pow10((int)strlen(b));
  return app_s("hum:/", l2(t_num(big_numeral_text(big_parse_dec(scat(a, b)))), t_num(big_numeral_text(den))));
}
static const char *op_key(HTok *t) { return (t->kind == H_OP || t->kind == H_ID) ? t->s : NULL; }
static Term *hum_expr(Hum *h, L *ts, int minprec, L *scope, L **rest);
static L *call_args(Hum *h, L *ts, L *scope, L **rest) {
  L *out = NULL, *r = ts;
  for (;;) {
    L *r1; Term *a = hum_expr(h, r, 0, scope, &r1);
    out = cons(a, out);
    if (!r1) oob();
    HTok *x = (HTok *)r1->h;
    if (is_op(x, ",")) r = r1->t;
    else if (is_op(x, ")")) { *rest = r1->t; return lrev(out); }
    else parse_err("missing ) in call");
  }
}
static Term *atom(Hum *h, L *ts, L *scope, L **rest) {
  if (!ts) oob();
  HTok *t = (HTok *)ts->h;
  switch (t->kind) {
    case H_NUM: *rest = ts->t; return number(t->s);
    case H_STR: *rest = ts->t; return t_str(t->s);
    case H_CHR: *rest = ts->t; return t_chr(t->c);
    case H_OP:
      if (!strcmp(t->s, "[")) {
        L *r0 = ts->t, *items = NULL, *r1;
        if (r0 && is_op((HTok *)r0->h, "]")) r1 = r0;
        else {
          L *r = r0;
          for (;;) {
            L *rr; Term *a = hum_expr(h, r, 0, scope, &rr);
            items = cons(a, items);
            if (rr && is_op((HTok *)rr->h, ",")) r = rr->t; else { r1 = rr; break; }
          }
          items = lrev(items);
        }
        if (!r1) oob();
        if (is_op((HTok *)r1->h, "]")) {
          Term *e = t_var("hum:nil");
          for (L *a = lrev(items); a; a = a->t) e = app_s("hum:cons", l2(a->h, e));
          *rest = r1->t;
          return e;
        }
        parse_err("missing ] in list");
      }
      if (!strcmp(t->s, "(")) {
        L *r1; Term *e = hum_expr(h, ts->t, 0, scope, &r1);
        if (!r1) oob();
        HTok *x = (HTok *)r1->h;
        if (is_id_s(x, "in")) {
          L *r3; Ty *c = class_expr(h, r1->t, &r3);
          if (!r3) oob();
          if (is_op((HTok *)r3->h, ")")) { *rest = r3->t; return t_asc(e, c); }
          parse_err("missing )");
        }
        if (is_op(x, ")")) { *rest = r1->t; return e; }
        parse_err("missing )");
      }
      parse_err(scat("unexpected ", show_htok(t)));
    default: {   /* H_ID */
      const char *name = t->s;
      L *r = ts->t;
      int starts_paren = r && is_op((HTok *)r->h, "(");
      if (!lmem_str(name, scope) && !starts_paren) {
        Entry *lit = doc2_find(h->doc, name, LITERAL_ROLE);
        if (lit) { *rest = r; return t_num((const char *)lit->rhs->h); }
      }
      Term *hd = (lmem_str(name, scope) || !doc2_find(h->doc, name, VALUE_ROLE)) ? t_var(name) : t_var(scat("hum:", name));
      if (r && is_op((HTok *)r->h, "(")) {
        if (r->t && is_op((HTok *)r->t->h, ")")) { *rest = r->t->t; return t_app(hd, NULL); }
        L *r2; L *args = call_args(h, r->t, scope, &r2);
        *rest = r2;
        return t_app(hd, args);
      }
      *rest = r;
      return hd;
    }
  }
}
static Term *hum_expr(Hum *h, L *ts, int minprec, L *scope, L **rest) {
  if (!ts) oob();
  /* lambda:  x in Class |-> body */
  HTok *t0 = (HTok *)ts->h;
  if (t0->kind == H_ID && ts->t && is_id_s((HTok *)ts->t->h, "in")) {
    L *r1; Ty *c = class_expr(h, ts->t->t, &r1);
    if (r1 && is_op((HTok *)r1->h, "|->")) {
      L *r3; Term *body = hum_expr(h, r1->t, 0, cons((void *)t0->s, scope), &r3);
      *rest = r3;
      Param *p = NEW(Param); p->name = t0->s; p->ty = c;
      return t_lam(l1(p), body);
    }
  }
  const char *key = op_key(t0);
  Term *left; L *r;
  if (key && hget(h->prefix, key) && !(t0->kind == H_ID && lmem_str(key, scope))) {
    Entry *pe = (Entry *)hget(h->prefix, key);
    L *r1; Term *arg = hum_expr(h, ts->t, pe->has_prec ? pe->prec : 0, scope, &r1);
    left = app_s(scat("hum:prefix ", key), l1(arg)); r = r1;
  } else left = atom(h, ts, scope, &r);
  for (;;) {
    const char *op = r ? op_key((HTok *)r->h) : NULL;
    Entry *ie = op ? (Entry *)hget(h->infix, op) : NULL;
    int prec = ie ? (ie->has_prec ? ie->prec : 0) : 0;
    if (ie && prec >= minprec) {
      L *r1; Term *right = hum_expr(h, r->t, strcmp(ie->role, "infixr") ? prec + 1 : prec, scope, &r1);
      left = app_s(scat("hum:", op), l2(left, right));
      r = r1;
    } else { *rest = r; return left; }
  }
}
Term *hum_expr_top(Hum *h, L *ts, L **rest) { return hum_expr(h, ts, 0, NULL, rest); }

/* statements */
const char *spec_name(Hum *h, const char *name) {
  Entry *e = doc2_find(h->doc, name, VALUE_ROLE);
  if (e && llen(e->rhs) == 1 && !all_bin_chars((const char *)e->rhs->h)) return (const char *)e->rhs->h;
  return name;
}
Term *type_to_term(Ty *t) {
  if (t->tag == TY_V) return t_var(t->name);
  if (t->tag == TY_F) return t_var("⊥");
  if (!t->args) return t_var(t->name);
  L *a = NULL;
  for (L *x = t->args; x; x = x->t) a = cons(type_to_term((Ty *)x->h), a);
  return t_app(t_var(t->name), lrev(a));
}
static const char *tok_text(HTok *t) { return t->kind == H_CHR ? cp_string(t->c) : t->s; }
static L *hum_statement(Hum *h, const char *line) {
  L *ts = lex_hum(line);
  int k = -1, i = 0;
  for (L *l = ts; l; l = l->t, i++) if (is_id_s((HTok *)l->h, "subseteq")) { k = i; break; }
  if (k >= 0) {
    L *ra, *rb;
    Ty *a = class_expr(h, ltake(k, ts), &ra);
    Ty *b = class_expr(h, ldrop(k + 1, ts), &rb);
    if (ra || rb) parse_err("assertion failed");
    return l1(s_fact(app_s("⊆", l2(type_to_term(a), type_to_term(b)))));
  }
  if (ts && ((HTok *)ts->h)->kind == H_ID) {
    const char *name = ((HTok *)ts->h)->s;
    L *r0 = ts->t, *params = NULL, *r1 = r0;
    if (r0 && is_op((HTok *)r0->h, "(")) {
      L *r = r0->t;
      for (;;) {
        if (!r) oob();
        if (is_op((HTok *)r->h, ")")) { r1 = r->t; break; }
        params = cons((void *)tok_text((HTok *)r->h), params);
        r = r->t;
        if (r && is_op((HTok *)r->h, ",")) r = r->t;
      }
      params = lrev(params);
    }
    if (r1 && is_id_s((HTok *)r1->h, "in")) {
      L *r3; Ty *cls = class_expr(h, r1->t, &r3);
      if (!r3) {
        if (params) parse_err(xfmt("%s: a declaration without := takes no parameters (an unknown is a number)", name));
        return l1(s_decl(spec_name(h, name), cls));
      }
      if (is_op((HTok *)r3->h, ":=")) {
        L *r5; Term *body = hum_expr(h, r3->t, 0, params, &r5);
        const char *sp = spec_name(h, name);
        if (r5) parse_err(scat("unexpected ", show_htok((HTok *)r5->h)));
        return l2(s_decl(sp, cls), s_def(sp, params, body));
      }
      parse_err("missing :=");
    }
    parse_err(xfmt("declare the class first:  %s in <Class> := …", name));
  }
  parse_err(xfmt("statement must start with a name: %s", py_repr(line)));
}
L *hum_statements(Hum *h, const char *text) {
  L *out = NULL;
  for (L *l = hum_logical_lines(text); l; l = l->t)
    for (L *s = hum_statement(h, (const char *)l->h); s; s = s->t) out = cons(s->h, out);
  return lrev(out);
}
