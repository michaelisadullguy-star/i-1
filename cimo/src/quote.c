/* quote.c -- the compiler side of statements (port of ocamimo/src/quote.ml).  A statement — a relation on ℝ[i], a relation or predicate about an
   unknown, a connective with a statement operand (types.c marks them T_QUOTE) — is simplified from DEFINITIONS whenever it is evaluated or
   output, so its checked term φ is replaced by a term that builds φ's CODE at run time; the statement becomes (simplify′ ε⌜⌝ ⌜φ⌝) where ε⌜⌝ is
   one table, for the whole program, of (code, ⌜definition⌝). */
#include "cimo.h"

const char *ENV_NAME = "ε⌜⌝";
static const char *unfold[] = { "exp", "sin", "cos", "sinh", "cosh", "log", "atan", NULL };
static const char *transparent[] = { "prop", "decide", "code_rd", NULL };
typedef struct DefEnt { L *params; Term *body; Ty *cls; } DefEnt;
struct Quoter { Checker *c; Hash *defs, *prelude, *stmt; L *unknowns; };   /* defs: name -> DefEnt*; prelude: name -> DefEnt* (cls unused); unknowns: Unknown* with dom >= 0 */

static Term *digits(const char *text) { return app_s("↓ᶻ", l1(t_num(text))); }
static Term *nat(int k) { return digits(numeral(to_digits_i64(k, 0))); }
static int in_list(const char *s, const char **l) { for (; *l; l++) if (!strcmp(s, *l)) return 1; return 0; }
int has_quote(Term *t) {
  switch (t->tag) {
    case T_QUOTE: return 1;
    case T_APP: if (has_quote(t->f)) return 1; for (L *a = t->args; a; a = a->t) if (has_quote((Term *)a->h)) return 1; return 0;
    case T_LAM: return has_quote(t->body);
    default: return 0;
  }
}
/* statements of the program, resolved: a list of StTrust* */
Quoter *mk_quoter(Checker *c, L *sts, Doc1 *d0, Doc1 **d1out) {
  Quoter *q = NEW(Quoter);
  q->c = c; q->defs = hnew(); q->prelude = hnew(); q->stmt = hnew();
  for (L *l = sts; l; l = l->t) {
    StTrust *e = (StTrust *)l->h;
    if (e->st && e->st->kind == S_DEF) {
      DefEnt *d = NEW(DefEnt); d->params = e->st->params; d->body = e->st->body;
      if (!e->trusted) {
        L *sg = sigs_of(c, e->st->name);
        d->cls = sg ? (Ty *)sg->h : kk("?");
        hset(q->defs, e->st->name, d);
      } else if (in_list(e->st->name, unfold)) hset(q->prelude, e->st->name, d);
    }
  }
  L *un = NULL;
  for (L *u = c->unknowns; u; u = u->t) if (((Unknown *)u->h)->dom >= 0) un = cons(u->h, un);
  q->unknowns = lrev(un);
  Doc1 *d1 = doc1_copy(d0);
  for (L *u = q->unknowns; u; u = u->t) doc1_code(d1, ((Unknown *)u->h)->name, 1);
  for (int i = 0; i < q->defs->n; i++) if (has_quote(((DefEnt *)q->defs->vals[i])->body)) hset(q->stmt, q->defs->keys[i], q);
  *d1out = d1;
  return q;
}
static Term *q_code(QS *st, const char *name) {
  const char *real = conn_o_real(name);
  const char *b = doc1_code(st->doc, real, 1);
  return digits(ssub(b, 1, (int)strlen(b) - 2));
}
static int is_unknown(Quoter *q, const char *n) { for (L *u = q->unknowns; u; u = u->t) if (!strcmp(((Unknown *)u->h)->name, n)) return 1; return 0; }
static void need(Quoter *q, QS *st, const char *name) {
  if ((hhas(q->defs, name) || hhas(q->prelude, name) || is_unknown(q, name)) && !lmem_str(name, st->needed)) st->needed = lappend(st->needed, l1((void *)name));
}
static int is_value_class(Quoter *q, Ty *c0) {
  if (!c0) return 0;
  Ty *c = norm(q->c, c0);
  return c->tag == TY_K && (ty_eq(c, bool_ty) || leq(q->c, c, num_ty));
}
static int has_rel(Quoter *q, Term *t) {
  switch (t->tag) {
    case T_QUOTE: return 1;
    case T_VAR: {
      for (int i = 0; rel_r[i]; i++) if (!strcmp(rel_r[i], t->s)) return 1;
      return is_conn_o(t->s) || hhas(q->stmt, t->s);
    }
    case T_APP: if (has_rel(q, t->f)) return 1; for (L *a = t->args; a; a = a->t) if (has_rel(q, (Term *)a->h)) return 1; return 0;
    case T_LAM: return has_rel(q, t->body);
    default: return 0;
  }
}
static int free_in(Term *t, Hash *names) {
  switch (t->tag) {
    case T_VAR: return hhas(names, t->s);
    case T_APP: if (free_in(t->f, names)) return 1; for (L *a = t->args; a; a = a->t) if (free_in((Term *)a->h, names)) return 1; return 0;
    case T_LAM: {
      Hash *rest = hnew();
      for (int i = 0; i < names->n; i++) {
        int bound = 0;
        for (L *p = t->ps; p; p = p->t) if (!strcmp(((Param *)p->h)->name, names->keys[i])) bound = 1;
        if (!bound) hset(rest, names->keys[i], names);
      }
      return free_in(t->body, rest);
    }
    case T_QUOTE: return free_in(t->body, names);
    default: return 0;
  }
}
/* the code of a term.  ib: binders inside the quote (innermost last: Param*) with their classes; outer: classes of variables bound outside (LocEnt*) */
static Term *q_term(Quoter *q, QS *st, Term *t, L *ib, L *outer, int typed) {
  int nnames = llen(ib);
  switch (t->tag) {
    case T_QUOTE: return q_term(q, st, t->body, ib, outer, typed);
    case T_NUM: case T_CHR: case T_STR: return app_s("𝔮ⁿ", l1(t));
    case T_VAR: {
      const char *n = t->s;
      int idx = -1, i = 0;
      for (L *l = ib; l; l = l->t, i++) if (!strcmp(((Param *)l->h)->name, n)) idx = i;
      if (idx >= 0) return app_s("𝔮ᵛ", l1(nat(nnames - idx)));
      Ty *oc = loc_lookup(outer, n);
      if (oc) {
        if (is_value_class(q, oc)) return app_s("𝔮ⁿ", l1(t));
        if (is_prop(q->c, oc)) return app_s("code_rd", l1(t));
        int pos = 0, j = 0;
        for (L *l = outer; l; l = l->t, j++) if (!strcmp(((LocEnt *)l->h)->name, n)) { pos = j; break; }
        return app_s("𝔮ᵛ", l1(nat(nnames + 1 + pos)));
      }
      if (is_unknown(q, n)) { need(q, st, n); return app_s("𝔮ˢ", l1(q_code(st, n))); }
      if (typed && !hhas(q->defs, n) && hhas(q->c->sigs, n)) {
        int all = 1;
        for (L *s = sigs_of(q->c, n); s; s = s->t) if (!is_value_class(q, (Ty *)s->h)) all = 0;
        if (all) return app_s("𝔮ⁿ", l1(t));
      }
      DefEnt *d = (DefEnt *)hget(q->defs, n);
      if (d && is_value_class(q, d->cls) && !hhas(q->stmt, n) && !unknownish(q->c, n)) return app_s("𝔮ⁿ", l1(t));
      need(q, st, n);
      return app_s("𝔮ˢ", l1(q_code(st, n)));
    }
    case T_APP: {
      if (typed && t->f->tag == T_VAR && in_list(t->f->s, transparent) && llen(t->args) == 1) {
        int bound = 0;
        for (L *l = ib; l; l = l->t) if (!strcmp(((Param *)l->h)->name, t->f->s)) bound = 1;
        if (!bound && !loc_member(outer, t->f->s)) return q_term(q, st, (Term *)t->args->h, ib, outer, typed);
      }
      if (typed && !has_rel(q, t)) {
        Hash *nameset = hnew();
        for (L *l = ib; l; l = l->t) hset(nameset, ((Param *)l->h)->name, nameset);
        if (!free_in(t, nameset)) {
          Hash *both = hnew();
          for (L *l = outer; l; l = l->t) hset(both, ((LocEnt *)l->h)->name, both);
          for (int i = 0; i < nameset->n; i++) hset(both, nameset->keys[i], both);
          if (!mentions(q->c, t, both)) {
            L *loc = outer;
            for (L *l = ib; l; l = l->t) { Param *p = (Param *)l->h; loc = loc_insert(loc, p->name, p->ty ? p->ty : ty_f()); }
            Ty *volatile klass = NULL;
            Handler h;
            if (TRY(h)) { klass = synth(q->c, loc, t).ty; ENDTRY(h); }
            else if (cur_err.kind != E_CLASS) raise_err(cur_err.kind, cur_err.msg);
            if (is_value_class(q, klass)) return app_s("𝔮ⁿ", l1(t));
          }
        }
      }
      Term *out = q_term(q, st, t->f, ib, outer, typed);
      for (L *a = t->args; a; a = a->t) { Term *qa = q_term(q, st, (Term *)a->h, ib, outer, typed); out = app_s("𝔮ᵃ", l2(out, qa)); }
      return out;
    }
    case T_LAM: {
      L *inner = lappend(ib, t->ps);
      Term *o = q_term(q, st, t->body, inner, outer, typed);
      for (L *p = t->ps; p; p = p->t) o = app_s("𝔮ˡ", l1(o));
      return o;
    }
    default: parse_err("a statement cannot be written as a code: asc");
  }
}
static Term *definition_code(Quoter *q, QS *st, const char *name) {
  for (L *u = q->unknowns; u; u = u->t) {
    Unknown *un = (Unknown *)u->h;
    if (!strcmp(un->name, name)) {
      Term *cd = q_code(st, "𝔲");
      char *kn = numeral(to_digits_i64(un->dom, 0));
      return app_s("𝔮ᵃ", l2(app_s("𝔮ˢ", l1(cd)), app_s("𝔮ⁿ", l1(t_num(kn)))));
    }
  }
  DefEnt *d = (DefEnt *)hget(q->defs, name);
  if (d) {
    L *ps = NULL; Ty *cl = d->cls;
    for (L *p = d->params; p; p = p->t) {
      Ty *n = norm(q->c, cl);
      Param *pp = NEW(Param); pp->name = (const char *)p->h;
      if (n->tag == TY_K && llen(n->args) == 2) { pp->ty = (Ty *)n->args->h; cl = (Ty *)n->args->t->h; }
      else { pp->ty = NULL; cl = ty_f(); }
      ps = lappend(ps, l1(pp));
    }
    Term *out = q_term(q, st, d->body, ps, NULL, 1);
    for (L *p = d->params; p; p = p->t) out = app_s("𝔮ˡ", l1(out));
    return out;
  }
  d = (DefEnt *)hget(q->prelude, name);
  if (d) {
    L *ps = NULL;
    for (L *p = d->params; p; p = p->t) { Param *pp = NEW(Param); pp->name = (const char *)p->h; pp->ty = NULL; ps = lappend(ps, l1(pp)); }
    Term *out = q_term(q, st, d->body, ps, NULL, 0);
    for (L *p = d->params; p; p = p->t) out = app_s("𝔮ˡ", l1(out));
    return out;
  }
  parse_err(xfmt("no definition for %s to write as a code", name));
}
/* replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝ */
Term *quote_replace(Quoter *q, QS *st, Term *t) {
  switch (t->tag) {
    case T_QUOTE: { Term *cd = q_term(q, st, t->body, NULL, t->loc, 1); return app_s("simplify′", l2(t_var(ENV_NAME), cd)); }
    case T_APP: {
      Term *f2 = quote_replace(q, st, t->f);
      L *as = NULL;
      for (L *a = t->args; a; a = a->t) as = cons(quote_replace(q, st, (Term *)a->h), as);
      return t_app(f2, lrev(as));
    }
    case T_LAM: return t_lam(t->ps, quote_replace(q, st, t->body));
    default: return t;
  }
}
/* the one table of definitions for the whole program */
Term *quote_table(Quoter *q, QS *st) {
  L *entries = NULL;   /* (name, term) pairs */
  for (int k = 0; k < llen(st->needed); k++) {
    const char *name = (const char *)lnth(st->needed, k);
    Term *cd = q_code(st, name);
    Term *dc = definition_code(q, st, name);
    entries = cons(l2((void *)name, app_s("⊗", l2(cd, dc))), entries);
  }
  entries = lrev(entries);
  L *first = NULL, *rest = NULL;
  int nun = llen(q->unknowns);
  for (int u = 0; u < nun; u++)
    for (L *e = entries; e; e = e->t) if (!strcmp((const char *)((L *)e->h)->h, ((Unknown *)lnth(q->unknowns, u))->name)) first = cons(((L *)e->h)->t->h, first);
  first = lrev(first);
  for (L *e = entries; e; e = e->t) if (!is_unknown(q, (const char *)((L *)e->h)->h)) rest = cons(((L *)e->h)->t->h, rest);
  L *all = lappend(first, lrev(rest));
  Term *out = t_var("⊘");
  for (L *e = lrev(all); e; e = e->t) out = app_s("∷", l2(e->h, out));
  return out;
}
