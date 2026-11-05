/* layers.c -- doc 1 and the bin notation, and the translators between the notations (port of ocamimo/src/layers.ml). */
#include "cimo.h"

int is_bin_sym(const char *s) {
  int n = (int)strlen(s);
  if (n < 3 || s[0] != '.' || s[n - 1] != '.') return 0;
  for (int i = 1; i < n - 1; i++) if (s[i] != '0' && s[i] != '1') return 0;
  return 1;
}
static Doc1 *doc1_empty(void) { Doc1 *d = NEW(Doc1); d->s2b = hnew(); d->b2s = hnew(); d->local = NULL; return d; }
Doc1 *doc1_copy(Doc1 *d) { Doc1 *c = NEW(Doc1); c->s2b = hcopy(d->s2b); c->b2s = hcopy(d->b2s); c->local = d->local; return c; }
Doc1 *doc1_parse(const char *text) {
  Doc1 *d = doc1_empty();
  for (L *l = split_on(text, "\n"); l; l = l->t) {
    char *ln = strip((const char *)l->h);
    if (!*ln || starts_with(ln, "⍝")) continue;
    L *parts = split_on(ln, " := ");
    if (llen(parts) != 2) parse_err(xfmt("doc1: bad line %s", py_repr(ln)));
    char *a = strip((const char *)parts->h), *b = strip((const char *)parts->t->h);
    if (!is_bin_sym(b)) parse_err(xfmt("doc1: bad binary symbol %s", py_repr(b)));
    if (hhas(d->s2b, a) || hhas(d->b2s, b)) parse_err(xfmt("doc1: duplicate %s / %s", a, b));
    hset(d->s2b, a, b);
    hset(d->b2s, b, a);
  }
  return d;
}
static const char *bin_strip(const char *s) { while (*s == '0') s++; return s; }
static int bin_less(const char *a, const char *b) {
  a = bin_strip(a); b = bin_strip(b);
  size_t la = strlen(a), lb = strlen(b);
  if (la != lb) return la < lb;
  return strcmp(a, b) < 0;
}
static char *bin_succ(const char *s) {
  char *b = xfmt("%s", bin_strip(s));
  int i = (int)strlen(b) - 1;
  while (i >= 0 && b[i] == '1') { b[i] = '0'; i--; }
  if (i >= 0) { b[i] = '1'; return b; }
  return scat("1", b);
}
static char *next_code(Doc1 *d) {
  const char *m = "";
  for (int i = 0; i < d->b2s->n; i++) {
    const char *k = d->b2s->keys[i];
    char *bits = ssub(k, 1, (int)strlen(k) - 2);
    if (bin_less(m, bits)) m = bits;
  }
  return xfmt(".%s.", bin_succ(m));
}
const char *doc1_code(Doc1 *d, const char *name, int allow_new) {
  const char *b = (const char *)hget(d->s2b, name);
  if (b) return b;
  if (!allow_new) parse_err(xfmt("%s has no binary symbol in doc 1", py_repr(name)));
  char *nb = next_code(d);
  hset(d->s2b, name, nb);
  hset(d->b2s, nb, (void *)name);
  d->local = cons(l2((void *)name, nb), d->local);
  return nb;
}
void doc1_add_local(Doc1 *d, const char *a, const char *b) { hset(d->s2b, a, (void *)b); hset(d->b2s, b, (void *)a); }
char *doc1_render(Doc1 *d, L *header) {
  Buf *b = bnew();
  for (L *h = header; h; h = h->t) badd(b, xfmt("⍝ %s\n", (char *)h->h));
  for (L *l = lrev(d->local); l; l = l->t) { L *e = (L *)l->h; badd(b, xfmt("%s := %s\n", (char *)e->h, (char *)e->t->h)); }
  return bstr(b);
}

/* ------------------------------------------------------------------ bin lexer / translators */
enum { B_NL, B_OPEN, B_CLOSE, B_NUM, B_MARK, B_SYM };
typedef struct BTok { int kind; char *s; } BTok;
static const char *reserved_spec(const char *s) { return !strcmp(s, ".") ? "↦" : !strcmp(s, "..") ? "≔" : !strcmp(s, "...") ? "∶" : NULL; }
static const char *reserved_bin(const char *s) { return !strcmp(s, "↦") ? "." : !strcmp(s, "≔") ? ".." : !strcmp(s, "∶") ? "..." : NULL; }
static BTok *mkb(int kind, char *s) { BTok *t = NEW(BTok); t->kind = kind; t->s = s; return t; }
static L *lex_bin(const char *text) {
  int n; int *cs = decode(text, &n);
  int i = 0, d = 0;
  L *out = NULL;
  while (i < n) {
    int c = cs[i];
    if (c == ' ' || c == '\t' || c == '\r') i++;
    else if (c == '\n') { if (d == 0) out = cons(mkb(B_NL, NULL), out); i++; }
    else if (c == '(') { out = cons(mkb(B_OPEN, NULL), out); d++; i++; }
    else if (c == ')') { out = cons(mkb(B_CLOSE, NULL), out); d--; i++; }
    else if (c == '0' || c == '1' || c == '.') {
      int j = i, pts = 0;
      while (j < n && (cs[j] == '0' || cs[j] == '1' || cs[j] == '.')) { if (cs[j] == '.') pts++; j++; }
      char *s = encode_range(cs, i, j);
      if (reserved_spec(s)) out = cons(mkb(B_MARK, s), out);
      else if (pts <= 1) out = cons(mkb(B_NUM, s), out);
      else if (is_bin_sym(s)) out = cons(mkb(B_SYM, s), out);
      else parse_err(xfmt("bad binary token %s", py_repr(s)));
      i = j;
    } else parse_err(xfmt("character %s is not part of the binary notation", py_repr(cp_string(c))));
  }
  return lrev(out);
}
/* tokens to text (spaces only between atoms; newlines kept).  A NULL element stands for a newline. */
static char *render_toks(L *toks) {
  Buf *b = bnew();
  int first = 1;
  for (L *l = toks; l; l = l->t) {
    const char *t = (const char *)l->h;
    if (!t) { baddc(b, '\n'); first = 1; }
    else {
      if (!(!strcmp(t, ")") || first)) baddc(b, ' ');
      badd(b, t);
      first = !strcmp(t, "(");
    }
  }
  return bstr(b);
}
char *bin_to_spec_text(const char *text, Doc1 *d) {
  L *toks = NULL;
  for (L *l = lex_bin(text); l; l = l->t) {
    BTok *t = (BTok *)l->h;
    const char *x = NULL;
    switch (t->kind) {
      case B_NL: x = NULL; break;
      case B_OPEN: x = "("; break;
      case B_CLOSE: x = ")"; break;
      case B_NUM: x = t->s; break;
      case B_MARK: x = reserved_spec(t->s); break;
      default: {
        x = (const char *)hget(d->b2s, t->s);
        if (!x) parse_err(xfmt("binary symbol %s is not defined in doc 1 (or the local table)", t->s));
      }
    }
    toks = cons((void *)x, toks);
  }
  return render_toks(lrev(toks));
}
/* the tokens of spec text re-spelled in bin notation (the shared part of the two translators); appended to *out (reversed) */
static L *bin_of_spec_toks(L *toks, Doc1 *d, int allow_new, int strings_in_order, L *acc) {
#define PUSH(s) (acc = cons((void *)(s), acc))
  for (L *l = toks; l; l = l->t) {
    Tok *t = (Tok *)l->h;
    switch (t->kind) {
      case K_OPEN: PUSH("("); break;
      case K_CLOSE: PUSH(")"); break;
      case K_NUM: PUSH(t->s); break;
      case K_NAME: { const char *r = reserved_bin(t->s); if (r) PUSH(r); else PUSH(doc1_code(d, t->s, allow_new)); break; }
      case K_CHR: { const char *bc = doc1_code(d, "𝕔", allow_new); PUSH("("); PUSH(bc); PUSH(int_numeral_text(t->c)); PUSH(")"); break; }
      case K_STR: {
        int n; int *cs = decode(t->s, &n);
        if (strings_in_order) {
          const char *bcons = doc1_code(d, "∷", allow_new), *bchr = doc1_code(d, "𝕔", allow_new), *bnil = doc1_code(d, "⊘", allow_new);
          for (int i = 0; i < n; i++) { PUSH("("); PUSH(bcons); PUSH("("); PUSH(bchr); PUSH(int_numeral_text(cs[i])); PUSH(")"); }
          PUSH(bnil);
          for (int i = 0; i < n; i++) PUSH(")");
        } else {
          for (int i = 0; i < n; i++) {
            const char *bcons = doc1_code(d, "∷", allow_new), *bchr = doc1_code(d, "𝕔", allow_new);
            PUSH("("); PUSH(bcons); PUSH("("); PUSH(bchr); PUSH(int_numeral_text(cs[i])); PUSH(")");
          }
          PUSH(doc1_code(d, "⊘", allow_new));
          for (int i = 0; i < n; i++) PUSH(")");
        }
        break;
      }
      default: break;
    }
  }
#undef PUSH
  return acc;
}
char *spec_statements_to_bin_text(L *sts, Doc1 *d, int allow_new) {
  L *acc = NULL;
  for (L *l = sts; l; l = l->t) {
    acc = bin_of_spec_toks(lex_spec(pp_statement((Stmt *)l->h)), d, allow_new, 1, acc);
    acc = cons(NULL, acc);
  }
  return render_toks(lrev(acc));
}
char *spec_term_to_bin(const char *text, Doc1 *d) { return render_toks(lrev(bin_of_spec_toks(lex_spec(text), d, 0, 0, NULL))); }

/* ------------------------------------------------------------------ files: default notation by extension, `@bin` `@spec` `@hum` section headers */
L *split_sections(const char *text, const char *def) {
  const char *mode = def;
  L *cur = NULL, *acc = NULL;
  for (L *l = split_on(text, "\n"); l; l = l->t) {
    const char *ln = (const char *)l->h;
    char *s = strip(ln);
    if (!strcmp(s, "@bin") || !strcmp(s, "@spec") || !strcmp(s, "@hum")) {
      if (cur) { Section *sec = NEW(Section); sec->mode = mode; sec->text = sjoin(lrev(cur), "\n"); acc = cons(sec, acc); }
      cur = NULL;
      mode = s + 1;
    } else cur = cons((void *)ln, cur);
  }
  if (cur) { Section *sec = NEW(Section); sec->mode = mode; sec->text = sjoin(lrev(cur), "\n"); acc = cons(sec, acc); }
  return lrev(acc);
}
const char *default_notation(const char *path) {
  if (ends_with(path, ".bin.imo")) return "bin";
  if (ends_with(path, ".hum.imo")) return "hum";
  return "spec";
}
