/* types.c -- the class checker of i-1 (port of ocamimo/src/types.ml).
   Rules: every symbol must be DECLARED before it is defined or used; classes are terms; a symbol may carry several declarations (overloads);
   facts (⊆ A B) subclass, (≣ A B) class equation, (↪ f) coercion; lambda binders must be annotated; numerals get the smallest class containing
   their value; 'trusted' files (the prelude) have their signatures recorded but their bodies are NOT checked.  A class error is raised with
   class_err (E_CLASS); the exceptions of the host are the other kinds. */
#include "cimo.h"

const char *rel_r[] = { "≐ᴿ", "≠ᴿ", "≺ᴿ", "⩽ᴿ", "≻ᴿ", "⩾ᴿ", NULL };
static const char *conn_o[][2] = { { "∧Ω", "∧" }, { "∨Ω", "∨" }, { "¬Ω", "¬" }, { "⇒Ω", "⇒" }, { "⇔Ω", "⇔" } };
int is_conn_o(const char *n) { for (int i = 0; i < 5; i++) if (!strcmp(conn_o[i][0], n)) return 1; return 0; }
const char *conn_o_real(const char *n) { for (int i = 0; i < 5; i++) if (!strcmp(conn_o[i][0], n)) return conn_o[i][1]; return n; }
static int coercion_cost(const char *name) { return !strcmp(name, "decide") ? 2 : 1; }
static const struct { const char *name; int code; } domains[] = { { "ℕ", 6 }, { "ℤ", 5 }, { "ℚ", 3 }, { "ℤ[i]", 4 }, { "ℚ[i]", 2 }, { "ℝ", 1 }, { "ℝ[i]", 0 }, { NULL, 0 } };
Ty *prop_ty, *bool_ty, *num_ty;
#define ARROW "→"
enum { M_POS, M_NEG, M_EQ };
static int flip(int m) { return m == M_POS ? M_NEG : m == M_NEG ? M_POS : M_EQ; }

/* class variable -> class, small and persistent (a non-NULL pointer is a substitution; NULL is "no match") */
typedef struct SEnt { const char *name; Ty *ty; } SEnt;
typedef struct Subst { L *ents; } Subst;
static Ty *subst_get(Subst *s, const char *n) { for (L *l = s->ents; l; l = l->t) if (!strcmp(((SEnt *)l->h)->name, n)) return ((SEnt *)l->h)->ty; return NULL; }
static Subst *subst_insert(Subst *s, const char *n, Ty *t) {
  Subst *r = NEW(Subst);
  SEnt *e = NEW(SEnt); e->name = n; e->ty = t;
  int found = 0;
  for (L *l = s->ents; l; l = l->t) if (!strcmp(((SEnt *)l->h)->name, n)) found = 1;
  if (!found) { r->ents = lappend(s->ents, l1(e)); return r; }
  L *out = NULL;
  for (L *l = s->ents; l; l = l->t) out = cons(!strcmp(((SEnt *)l->h)->name, n) ? e : l->h, out);
  r->ents = lrev(out);
  return r;
}
static Subst *subst_empty(void) { return NEW(Subst); }

void ty_chain(Ty *t, L **ps, Ty **r) {
  L *acc = NULL;
  while (t->tag == TY_K && !strcmp(t->name, ARROW) && llen(t->args) == 2) { acc = cons(t->args->h, acc); t = (Ty *)t->args->t->h; }
  *ps = lrev(acc); *r = t;
}
static Ty *mk_chain(L *ps, Ty *r) {
  L *rev = lrev(ps);
  for (; rev; rev = rev->t) r = ty_k(ARROW, l2(rev->h, r));
  return r;
}
static int flex_eq(Ty *x, Ty *y) {
  if (ty_eq(x, y) || x->tag == TY_F || y->tag == TY_F) return 1;
  if (x->tag == TY_K && y->tag == TY_K) {
    if (strcmp(x->name, y->name) || llen(x->args) != llen(y->args)) return 0;
    for (L *a = x->args, *b = y->args; a; a = a->t, b = b->t) if (!flex_eq((Ty *)a->h, (Ty *)b->h)) return 0;
    return 1;
  }
  return 0;
}
static int has_var(Ty *t) {
  if (t->tag == TY_V) return 1;
  if (t->tag == TY_F) return 0;
  for (L *a = t->args; a; a = a->t) if (has_var((Ty *)a->h)) return 1;
  return 0;
}
static Ty *apply_subst(Ty *t, Subst *s, int flex) {
  if (t->tag == TY_V) { Ty *r = subst_get(s, t->name); return r ? r : (flex ? ty_f() : t); }
  if (t->tag == TY_F) return t;
  L *a = NULL;
  for (L *x = t->args; x; x = x->t) a = cons(apply_subst((Ty *)x->h, s, flex), a);
  return ty_k(t->name, lrev(a));
}

/* the smallest class containing the value of a numeral written in base i-1 */
static Ty *num_class(const char *text) {
  const char *dot = strchr(text, '.');
  char *bits = dot ? scat(ssub(text, 0, (int)(dot - text)), dot + 1) : (char *)text;
  int k = dot ? (int)strlen(dot + 1) : 0;
  int n = (int)strlen(bits);
  Digits ds; ds.n = n; ds.d = (unsigned char *)GC_MALLOC_ATOMIC((size_t)n + 1);
  for (int i = 0; i < n; i++) ds.d[i] = bits[n - 1 - i] == '1';
  GI z = val_digits(ds);
  Big *d0 = big_one(), *d1 = big_zero();
  for (int i = 0; i < k; i++) { Big *nd0 = big_neg(big_add(d0, d1)), *nd1 = big_sub(d0, d1); d0 = nd0; d1 = nd1; }
  Big *nn = big_add(big_mul(d0, d0), big_mul(d1, d1));
  Big *re_num = big_add(big_mul(z.re, d0), big_mul(z.im, d1));
  Big *im_num = big_sub(big_mul(z.im, d0), big_mul(z.re, d1));
  Big *q, *r1, *r2;
  big_divrem(re_num, nn, &q, &r1);
  big_divrem(im_num, nn, &q, &r2);
  int re_div = big_is_zero(r1), im_div = big_is_zero(r2);
  if (big_is_zero(im_num)) return re_div ? (!big_is_neg(re_num) ? kk("ℕ") : kk("ℤ")) : kk("ℚ");
  if (re_div && im_div) return kk("ℤ[i]");
  return kk("ℚ[i]");
}

/* ------------------------------------------------------------------ the checker */
Checker *new_checker(void) {
  Checker *c = NEW(Checker);
  c->classes = hnew(); c->formers = hnew(); c->sigs = hnew(); c->eqs = hnew(); c->cov = hnew(); c->defined = hnew(); c->overloads = hnew();
  c->user_defined = hnew(); c->raw_taint = hnew(); c->taint = hnew();
  int *two = NEW(int); *two = 2; int *zero = NEW(int);
  hset(c->classes, "→", two); hset(c->classes, "𝒦", zero); hset(c->classes, "𝒮", zero);
  hset(c->cov, "𝔏", c); hset(c->cov, "𝔖", c); hset(c->cov, "𝔗", c); hset(c->cov, "𝔓", c);
  if (!prop_ty) { prop_ty = kk("Ω"); bool_ty = kk("𝔹"); num_ty = kk("ℚ[i]"); }
  return c;
}

static Ty *term_to_type(Term *t) {
  if (t->tag == T_VAR) return is_class_var(t->s) ? ty_v(t->s) : kk(t->s);
  if (t->tag == T_APP && t->f->tag == T_VAR) {
    L *a = NULL;
    for (L *x = t->args; x; x = x->t) a = cons(term_to_type((Term *)x->h), a);
    return ty_k(t->f->s, lrev(a));
  }
  class_err(scat("not a class expression: ", repr_term(t)));
}

Ty *norm(Checker *c, Ty *t) {
  if (t->tag != TY_K) return t;
  if (!t->args) { Ty *e = (Ty *)hget(c->eqs, t->name); return e ? norm(c, e) : t; }
  L *a = NULL;
  for (L *x = t->args; x; x = x->t) a = cons(norm(c, (Ty *)x->h), a);
  return ty_k(t->name, lrev(a));
}
static void wf(Checker *c, Ty *t) {
  if (t->tag != TY_K) return;
  int *k = (int *)hget(c->classes, t->name);
  if (!k) class_err(scat("undeclared class ", t->name));
  if (*k != llen(t->args)) class_err(xfmt("class %s takes %d argument(s), got %d", t->name, *k, llen(t->args)));
  for (L *a = t->args; a; a = a->t) wf(c, (Ty *)a->h);
}
typedef struct IdxEnt { Ty *k; L *supers; } IdxEnt;
static L *supers_of(Checker *c, Ty *a) {
  for (L *l = c->fact_idx; l; l = l->t) { IdxEnt *e = (IdxEnt *)l->h; if (ty_eq(e->k, a)) return e->supers; }
  return NULL;
}
typedef struct Seen { Ty *a, *b; struct Seen *next; } Seen;
static int leq_s(Checker *c, Seen *seen, Ty *a0, Ty *b0) {
  Ty *a = norm(c, a0), *b = norm(c, b0);
  if (ty_eq(a, b) || a->tag == TY_F) return 1;
  int s = 0;
  if (a->tag == TY_K && b->tag == TY_K && !strcmp(a->name, b->name) && a->args && llen(a->args) == llen(b->args)) {
    if (!strcmp(a->name, ARROW)) s = leq_s(c, seen, (Ty *)b->args->h, (Ty *)a->args->h) && leq_s(c, seen, (Ty *)a->args->t->h, (Ty *)b->args->t->h);
    else if (hhas(c->cov, a->name)) {
      s = 1;
      for (L *x = a->args, *y = b->args; x && s; x = x->t, y = y->t) s = leq_s(c, seen, (Ty *)x->h, (Ty *)y->h);
    } else s = flex_eq(a, b);
  }
  if (s) return 1;
  for (L *l = supers_of(c, a); l; l = l->t) {
    Ty *y = (Ty *)l->h;
    int dup = 0;
    for (Seen *q = seen; q; q = q->next) if (ty_eq(q->a, a) && ty_eq(q->b, y)) dup = 1;
    if (dup) continue;
    Seen sn = { a, y, seen };
    if (leq_s(c, &sn, y, b)) return 1;
  }
  return 0;
}
int leq(Checker *c, Ty *a, Ty *b) { return leq_s(c, NULL, a, b); }
static int ty_mem(Ty *x, L *l) { for (; l; l = l->t) if (ty_eq(x, (Ty *)l->h)) return 1; return 0; }
static L *ups(Checker *c, Ty *a) {
  L *todo = l1(norm(c, a)), *out = NULL;
  while (todo) {
    Ty *x = (Ty *)todo->h;
    todo = todo->t;
    if (ty_mem(x, out)) continue;
    for (L *y = supers_of(c, x); y; y = y->t) todo = cons(norm(c, (Ty *)y->h), todo);
    out = lappend(out, l1(x));
  }
  return out;
}
/* the least class containing both a and b; NULL if there is none or it is not unique */
static Ty *join(Checker *c, Ty *a0, Ty *b0) {
  Ty *a = norm(c, a0), *b = norm(c, b0);
  if (a->tag == TY_K && b->tag == TY_K && !strcmp(a->name, b->name) && hhas(c->cov, a->name) && a->args && llen(a->args) == llen(b->args)) {
    L *js = NULL;
    for (L *x = a->args, *y = b->args; x; x = x->t, y = y->t) {
      Ty *j = leq(c, (Ty *)y->h, (Ty *)x->h) ? (Ty *)x->h : leq(c, (Ty *)x->h, (Ty *)y->h) ? (Ty *)y->h : join(c, (Ty *)x->h, (Ty *)y->h);
      if (!j) return NULL;
      js = cons(j, js);
    }
    return ty_k(a->name, lrev(js));
  }
  L *ub = ups(c, b), *common = NULL;
  for (L *x = ups(c, a); x; x = x->t) if (ty_mem((Ty *)x->h, ub)) common = cons(x->h, common);
  common = lrev(common);
  Ty *least = NULL; int nleast = 0;
  for (L *x = common; x; x = x->t) {
    int dom = 0;
    for (L *d = common; d; d = d->t) if (!ty_eq((Ty *)d->h, (Ty *)x->h) && leq(c, (Ty *)d->h, (Ty *)x->h)) dom = 1;
    if (!dom) { least = (Ty *)x->h; nleast++; }
  }
  return nleast == 1 ? least : NULL;
}

/* ------------------------------------------------------------------ matching a pattern against an actual class */
static Subst *do_match(Checker *c, Ty *p0, Ty *a0, Subst *s, int mode) {
  Ty *p = norm(c, p0), *a = norm(c, a0);
  if (p->tag == TY_V) {
    Ty *b = subst_get(s, p->name);
    if (!b) return subst_insert(s, p->name, a);
    if (a->tag == TY_F) return s;
    if (b->tag == TY_F) return subst_insert(s, p->name, a);
    if (mode == M_EQ) return flex_eq(b, a) ? s : NULL;
    if (leq(c, a, b)) return s;
    if (leq(c, b, a)) return mode == M_POS ? subst_insert(s, p->name, a) : s;
    if (mode == M_POS) { Ty *j = join(c, a, b); return j ? subst_insert(s, p->name, j) : NULL; }
    return NULL;
  }
  if (!has_var(p)) {
    if (a->tag == TY_F) return s;
    int ok = mode == M_POS ? leq(c, a, p) : mode == M_NEG ? leq(c, p, a) : flex_eq(p, a);
    return ok ? s : NULL;
  }
  if (a->tag == TY_F) return s;
  Subst *structural = NULL;
  if (p->tag == TY_K && a->tag == TY_K && !strcmp(p->name, a->name) && llen(p->args) == llen(a->args)) {
    Subst *cur = s; int i = 0;
    for (L *pp = p->args, *aa = a->args; pp && cur; pp = pp->t, aa = aa->t, i++) {
      int m = !strcmp(p->name, ARROW) ? (i == 0 ? flip(mode) : mode) : hhas(c->cov, p->name) ? mode : M_EQ;
      cur = do_match(c, (Ty *)pp->h, (Ty *)aa->h, cur, m);
    }
    structural = cur;
  }
  if (structural) return structural;
  if (mode == M_POS)
    for (L *y = supers_of(c, a); y; y = y->t) { Subst *r = do_match(c, p, (Ty *)y->h, s, mode); if (r) return r; }
  return NULL;
}

/* the domain code of an unknown of class t: the first number class, in the order ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i], that contains t; -1 if none */
static int domain(Checker *c, Ty *t0) {
  Ty *t = norm(c, t0);
  if (t->tag != TY_K || has_var(t)) return -1;
  for (int i = 0; domains[i].name; i++) if (hhas(c->classes, domains[i].name) && leq(c, t, kk(domains[i].name))) return domains[i].code;
  return -1;
}
int unknownish(Checker *c, const char *name) {
  for (L *l = c->unknowns; l; l = l->t) if (!strcmp(((Unknown *)l->h)->name, name)) return 1;
  int *b = (int *)hget(c->taint, name);
  if (b) return *b;
  return hhas(c->raw_taint, name);
}
/* does the (checked) term t mention an unknown (or a symbol that needs one) — outside quoted statements?  bound: a hash of names */
int mentions(Checker *c, Term *t, Hash *bound) {
  switch (t->tag) {
    case T_VAR: return !hhas(bound, t->s) && unknownish(c, t->s);
    case T_APP:
      if (mentions(c, t->f, bound)) return 1;
      for (L *a = t->args; a; a = a->t) if (mentions(c, (Term *)a->h, bound)) return 1;
      return 0;
    case T_LAM: {
      Hash *bd = hcopy(bound);
      for (L *p = t->ps; p; p = p->t) hset(bd, ((Param *)p->h)->name, bd);
      return mentions(c, t->body, bd);
    }
    default: return 0;
  }
}
int is_prop(Checker *c, Ty *t) { return ty_eq(norm(c, t), prop_ty); }
L *sigs_of(Checker *c, const char *n) { return (L *)hget(c->sigs, n); }

/* ------------------------------------------------------------------ declarations and facts */
void declare(Checker *c, const char *name, Ty *t) {
  L *ps; Ty *r;
  ty_chain(t, &ps, &r);
  if (ty_eq(r, kk("𝒦"))) {
    for (L *p = ps; p; p = p->t) if (!ty_eq((Ty *)p->h, kk("𝒦"))) class_err(scat(name, ": a class constructor takes classes only"));
    int *n = NEW(int); *n = llen(ps);
    hset(c->classes, name, n);
  } else if (ty_eq(r, kk("𝒮"))) hset(c->formers, name, c);
  else {
    wf(c, t);
    L *old = (L *)hget(c->sigs, name);
    int dup = 0;
    for (L *o = old; o; o = o->t) if (ty_eq((Ty *)o->h, t)) dup = 1;
    hset(c->sigs, name, dup ? old : lappend(old, l1(t)));
  }
}
static void reindex(Checker *c) {
  L *idx = NULL;
  for (L *f = c->facts; f; f = f->t) {
    L *pr = (L *)f->h;
    Ty *k = norm(c, (Ty *)pr->h);
    IdxEnt *found = NULL;
    for (L *l = idx; l; l = l->t) if (ty_eq(((IdxEnt *)l->h)->k, k)) found = (IdxEnt *)l->h;
    if (found) found->supers = lappend(found->supers, l1(pr->t->h));
    else { IdxEnt *e = NEW(IdxEnt); e->k = k; e->supers = l1(pr->t->h); idx = lappend(idx, l1(e)); }
  }
  c->fact_idx = idx;
}
static void fact(Checker *c, Term *term) {
  if (term->tag == T_APP && term->f->tag == T_VAR && hhas(c->formers, term->f->s)) {
    const char *h = term->f->s;
    L *args = term->args;
#define ARG(i) (lnth(args, i) && llen(args) > (i) ? (Term *)lnth(args, i) : (parse_err("Prelude.!!: index too large"), (Term *)NULL))
    if (!strcmp(h, "⊆") || !strcmp(h, "≣")) {
      Term *a0 = ARG(0), *b0 = ARG(1);
      Ty *a = term_to_type(a0), *b = term_to_type(b0);
      wf(c, a); wf(c, b);
      if (!strcmp(h, "⊆")) { c->facts = lappend(c->facts, l1(l2(a, b))); reindex(c); }
      else {
        if (a->tag == TY_K && !a->args) { hset(c->eqs, a->name, b); reindex(c); }
        else parse_err("class equation: left side must be an atomic class");
      }
      return;
    }
    if (!strcmp(h, "↗")) {
      if (args && ((Term *)args->h)->tag == T_VAR) {
        const char *n = ((Term *)args->h)->s;
        int *k = (int *)hget(c->classes, n);
        if ((k ? *k : 0) >= 1) hset(c->cov, n, c); else class_err(xfmt("covariant: %s is not a class constructor", n));
      } else class_err("covariant:  is not a class constructor");
      return;
    }
    if (!strcmp(h, "↪")) {
      if (args && ((Term *)args->h)->tag == T_VAR) {
        const char *f = ((Term *)args->h)->s;
        if (hhas(c->sigs, f)) c->coercions = lappend(c->coercions, l1((void *)f)); else class_err(xfmt("coercion %s is not declared", f));
      } else class_err("coercion  is not declared");
      return;
    }
    class_err(scat("unknown statement ", h));
#undef ARG
  }
  class_err(scat("not a declared statement: ", repr_term(term)));
}

/* ------------------------------------------------------------------ terms */
typedef struct NameTy { const char *name; Ty *ty; } NameTy;
static L *entries_for(Checker *c, const char *hd) {
  L *names = (L *)hget(c->overloads, hd);
  if (!names) names = l1((void *)hd);
  L *out = NULL;
  for (L *n = names; n; n = n->t) {
    if (!hhas(c->sigs, (const char *)n->h)) class_err(scat("undeclared symbol ", (const char *)n->h));
    for (L *e = sigs_of(c, (const char *)n->h); e; e = e->t) { NameTy *nt = NEW(NameTy); nt->name = (const char *)n->h; nt->ty = (Ty *)e->h; out = cons(nt, out); }
  }
  return lrev(out);
}
static const char *best_coercion(Checker *c, Ty *p, Ty *a_ty, Subst *s, Subst **s_out) {
  const char *bn = NULL; Ty *bcr = NULL; Subst *bs = NULL;
  for (L *cn = c->coercions; cn; cn = cn->t) {
    for (L *ce = sigs_of(c, (const char *)cn->h); ce; ce = ce->t) {
      L *cps; Ty *cr;
      ty_chain((Ty *)ce->h, &cps, &cr);
      if (llen(cps) != 1 || !leq(c, a_ty, (Ty *)cps->h)) continue;
      Subst *s1 = do_match(c, p, apply_subst(cr, subst_empty(), 0), s, M_POS);
      if (s1) {
        if (!bn || leq(c, cr, bcr)) { bn = (const char *)cn->h; bcr = cr; bs = s1; }
      }
    }
  }
  if (!bn) return NULL;
  *s_out = bs;
  return bn;
}
typedef struct TryRes { Ty *ty; L *args; int cost; } TryRes;
/* apply a class `entry` to args (TyTerm*): the result class, the new args and the cost, or NULL */
static TryRes *try_apply(Checker *c, Ty *entry, L *args) {
  Ty *t = entry; Subst *s = subst_empty(); int cost = 0; L *nw = NULL;
  for (L *a = args; a; a = a->t) {
    TyTerm *tt = (TyTerm *)a->h;
    Ty *nt = norm(c, t);
    if (!(nt->tag == TY_K && !strcmp(nt->name, ARROW) && llen(nt->args) == 2)) return NULL;
    Ty *p = (Ty *)nt->args->h, *r = (Ty *)nt->args->t->h;
    Subst *s2 = do_match(c, p, tt->ty, s, M_POS);
    if (s2) { s = s2; nw = cons(tt->term, nw); }
    else {
      Subst *s1;
      const char *cname = best_coercion(c, p, tt->ty, s, &s1);
      if (!cname) return NULL;
      s = s1; cost += coercion_cost(cname);
      nw = cons(app_s(cname, l1(tt->term)), nw);
    }
    t = r;
  }
  TryRes *res = NEW(TryRes);
  res->ty = apply_subst(t, s, 1); res->args = lrev(nw); res->cost = cost;
  return res;
}
typedef struct Cand { const char *name; Ty *entry; TryRes *res; } Cand;
typedef struct Resolved { const char *name; Ty *ty; L *args; } Resolved;
static Resolved resolve_app(Checker *c, const char *hd, L *args, const char *label) {
  L *ents = entries_for(c, hd), *cands = NULL;
  for (L *e = ents; e; e = e->t) {
    NameTy *nt = (NameTy *)e->h;
    TryRes *r = try_apply(c, nt->ty, args);
    if (r) { Cand *cd = NEW(Cand); cd->name = nt->name; cd->entry = nt->ty; cd->res = r; cands = cons(cd, cands); }
  }
  cands = lrev(cands);
  if (!cands) {
    L *as = NULL, *es = NULL;
    for (L *a = args; a; a = a->t) as = cons(show_type(((TyTerm *)a->h)->ty), as);
    for (L *e = ents; e; e = e->t) es = cons(xfmt("%s ∶ %s", ((NameTy *)e->h)->name, show_type(((NameTy *)e->h)->ty)), es);
    class_err(xfmt("no declaration of %s accepts (%s);  candidates: %s", label, sjoin(lrev(as), ", "), sjoin(lrev(es), ", ")));
  }
  int mn = ((Cand *)cands->h)->res->cost;
  for (L *l = cands; l; l = l->t) if (((Cand *)l->h)->res->cost < mn) mn = ((Cand *)l->h)->res->cost;
  L *cands2 = NULL;
  for (L *l = cands; l; l = l->t) if (((Cand *)l->h)->res->cost == mn) cands2 = cons(l->h, cands2);
  cands2 = lrev(cands2);
  L *best = NULL;
  int nargs = llen(args);
  for (L *x = cands2; x; x = x->t) {
    int all = 1;
    for (L *y = cands2; y && all; y = y->t) {
      L *p1, *p2; Ty *r1, *r2;
      ty_chain(((Cand *)x->h)->entry, &p1, &r1);
      ty_chain(((Cand *)y->h)->entry, &p2, &r2);
      int n = nargs; if (llen(p1) < n) n = llen(p1); if (llen(p2) < n) n = llen(p2);
      L *a = p1, *b = p2;
      for (int i = 0; i < n && all; i++, a = a->t, b = b->t) if (!leq(c, (Ty *)a->h, (Ty *)b->h)) all = 0;
    }
    if (all) best = cons(x->h, best);
  }
  best = lrev(best);
  L *pool = best ? best : cands2;
  if (llen(best) != 1) {
    L *sigs = NULL;
    for (L *l = pool; l; l = l->t) {
      Cand *cd = (Cand *)l->h;
      int dup = 0;
      for (L *s = sigs; s; s = s->t) { Cand *o = (Cand *)s->h; if (!strcmp(o->name, cd->name) && ty_eq(o->res->ty, cd->res->ty)) dup = 1; }
      if (!dup) sigs = lappend(sigs, l1(cd));
    }
    if (llen(sigs) != 1) {
      L *ms = NULL;
      for (L *l = cands2; l; l = l->t) ms = cons(xfmt("%s ∶ %s", ((Cand *)l->h)->name, show_type(((Cand *)l->h)->entry)), ms);
      class_err(xfmt("ambiguous use of %s: %s", label, sjoin(lrev(ms), "; ")));
    }
  }
  Cand *cd = (Cand *)pool->h;
  Resolved r = { cd->name, cd->res->ty, cd->res->args };
  return r;
}
/* the checked application (name new…) of class rt — marked as a quoted statement (class Ω) when it is one */
static TyTerm statement_of(Checker *c, L *loc, const char *name, Ty *rt, L *nw) {
  Term *app_t = app_s(name, nw);
  Hash *bound = hnew();
  for (L *l = loc; l; l = l->t) hset(bound, ((LocEnt *)l->h)->name, bound);
  Ty *r = norm(c, rt);
  TyTerm res;
  int is_rel = 0;
  for (int i = 0; rel_r[i]; i++) if (!strcmp(rel_r[i], name)) is_rel = 1;
  int ment = 0;
  for (L *a = nw; a; a = a->t) if (mentions(c, (Term *)a->h, bound)) ment = 1;
  if ((is_rel && llen(nw) == 2) || (is_conn_o(name) && is_prop(c, rt)) || ((ty_eq(r, prop_ty) || ty_eq(r, bool_ty)) && ment)) {
    res.ty = prop_ty; res.term = t_quote(app_t, loc);
  } else { res.ty = rt; res.term = app_t; }
  return res;
}
static int join_list(Checker *c, L *loc, Term *t, TyTerm *out);

TyTerm synth(Checker *c, L *loc, Term *t) {
  TyTerm res;
  switch (t->tag) {
    case T_NUM: res.ty = num_class(t->s); res.term = t; return res;
    case T_CHR: res.ty = kk("𝕮"); res.term = t; return res;
    case T_STR: res.ty = kk("𝕊"); res.term = t; return res;
    case T_VAR: {
      Ty *ty = loc_lookup(loc, t->s);
      if (ty) { res.ty = ty; res.term = t; return res; }
      L *ents = entries_for(c, t->s);
      if (llen(ents) == 1) { NameTy *nt = (NameTy *)ents->h; res.ty = apply_subst(nt->ty, subst_empty(), 1); res.term = t_var(nt->name); return res; }
      class_err(xfmt("%s is overloaded (%d declarations): use it applied to arguments", t->s, llen(ents)));
    }
    case T_ASC: {
      wf(c, t->ty);
      TyTerm r = synth(c, loc, t->body);
      Term *fixed = fit(c, r.term, r.ty, t->ty);
      if (!fixed) class_err(xfmt("ascription: a term of class %s is not in %s", show_type(r.ty), show_type(t->ty)));
      res.ty = t->ty; res.term = fixed; return res;
    }
    case T_LAM: {
      L *loc2 = loc, *ptys = NULL;
      for (L *p = t->ps; p; p = p->t) {
        Param *q = (Param *)p->h;
        if (!q->ty) class_err(xfmt("binder %s has no class: write (%s ∶ class ↦ …)", q->name, q->name));
        wf(c, q->ty);
        loc2 = loc_insert(loc2, q->name, q->ty);
        ptys = cons(q->ty, ptys);
      }
      TyTerm r = synth(c, loc2, t->body);
      res.ty = mk_chain(lrev(ptys), r.ty); res.term = t_lam(t->ps, r.term);
      return res;
    }
    case T_QUOTE: res.ty = prop_ty; res.term = t; return res;
    default: break;
  }
  /* T_APP */
  L *args = NULL;
  for (L *a = t->args; a; a = a->t) { TyTerm *x = NEW(TyTerm); *x = synth(c, loc, (Term *)a->h); args = cons(x, args); }
  args = lrev(args);
  if (t->f->tag == T_VAR && !loc_member(loc, t->f->s)) {
    const char *h = t->f->s;
    Handler hd;
    Resolved r;
    volatile int ok = 0;
    char *emsg = NULL;
    if (TRY(hd)) { r = resolve_app(c, h, args, h); ENDTRY(hd); ok = 1; }
    else {
      if (cur_err.kind != E_CLASS) raise_err(cur_err.kind, cur_err.msg);
      emsg = cur_err.msg;
    }
    if (ok) return statement_of(c, loc, r.name, r.ty, r.args);
    TyTerm j;
    if (join_list(c, loc, t, &j)) return j;
    class_err(emsg);
  }
  TyTerm ft = synth(c, loc, t->f);
  TryRes *r = try_apply(c, ft.ty, args);
  if (!r) {
    L *as = NULL;
    for (L *a = args; a; a = a->t) as = cons(show_type(((TyTerm *)a->h)->ty), as);
    class_err(xfmt("cannot apply a function of class %s to (%s)", show_type(ft.ty), sjoin(lrev(as), ", ")));
  }
  res.ty = r->ty; res.term = t_app(ft.term, r->args);
  return res;
}
/* a cons chain (a list literal) whose elements are truth values and statements is a list of statements: the truth values are made statements
   (prop).  0 when that is not the case. */
static int join_list(Checker *c, L *loc, Term *t, TyTerm *out) {
  L *items = NULL; Term *tl = t;
  for (;;) {
    if (tl->tag == T_APP && llen(tl->args) == 2 && tl->f->tag == T_VAR && (!strcmp(tl->f->s, "∷") || !strcmp(tl->f->s, "hum:cons")) && !loc_member(loc, tl->f->s)) {
      items = cons(tl->args->h, items);
      tl = (Term *)tl->args->t->h;
    } else break;
  }
  items = lrev(items);
  if (!items || !hhas(c->sigs, "∷")) return 0;
  L *el = NULL;
  for (L *x = items; x; x = x->t) { TyTerm *e = NEW(TyTerm); *e = synth(c, loc, (Term *)x->h); el = cons(e, el); }
  el = lrev(el);
  TyTerm tt = synth(c, loc, tl);
  Ty *list_prop = ty_k("𝔏", l1(prop_ty));
  int any = 0;
  for (L *e = el; e; e = e->t) if (is_prop(c, ((TyTerm *)e->h)->ty)) any = 1;
  if (!(any || ty_eq(norm(c, tt.ty), list_prop)) || !leq(c, tt.ty, list_prop)) return 0;
  Term *o = tt.term;
  for (L *e = lrev(el); e; e = e->t) {
    TyTerm *x = (TyTerm *)e->h;
    if (is_prop(c, x->ty)) o = app_s("∷", l2(x->term, o));
    else if (leq(c, x->ty, bool_ty)) o = app_s("∷", l2(app_s("prop", l1(x->term)), o));
    else return 0;
  }
  out->ty = list_prop; out->term = o;
  return 1;
}

/* term (of class got) made to fit the class want: as it is, through one coercion, element by element for a list or pair literal, or — for a λ — by
   fitting its body.  NULL when it does not fit. */
Term *fit(Checker *c, Term *term, Ty *got, Ty *want) {
  if (leq(c, got, want)) return term;
  Ty *g = norm(c, got), *w = norm(c, want);
  Term *via = NULL;
  for (L *cn = c->coercions; cn; cn = cn->t)
    for (L *ce = sigs_of(c, (const char *)cn->h); ce; ce = ce->t) {
      L *cps; Ty *cr;
      ty_chain((Ty *)ce->h, &cps, &cr);
      if (llen(cps) == 1 && leq(c, got, (Ty *)cps->h) && leq(c, cr, want)) via = app_s((const char *)cn->h, l1(term));
    }
  if (via) return via;
  if (term->tag == T_VAR && !strcmp(term->s, "⊘") && w->tag == TY_K && !strcmp(w->name, "𝔏")) return term;
  if (term->tag == T_APP && term->f->tag == T_VAR && llen(term->args) == 2 && g->tag == TY_K && w->tag == TY_K && !strcmp(g->name, w->name)) {
    const char *h = term->f->s;
    Term *a0 = (Term *)term->args->h, *a1 = (Term *)term->args->t->h;
    if (!strcmp(h, "∷") && !strcmp(g->name, "𝔏")) {
      Term *h2 = fit(c, a0, (Ty *)g->args->h, (Ty *)w->args->h);
      if (h2) { Term *t2 = fit(c, a1, got, want); if (t2) return app_s("∷", l2(h2, t2)); }
    }
    if (!strcmp(h, "⊗") && !strcmp(g->name, "𝔓")) {
      Term *x = fit(c, a0, (Ty *)g->args->h, (Ty *)w->args->h);
      if (x) { Term *y = fit(c, a1, (Ty *)g->args->t->h, (Ty *)w->args->t->h); if (y) return app_s("⊗", l2(x, y)); }
    }
  }
  if (term->tag == T_LAM) {
    int n = llen(term->ps);
    L *pg, *pw; Ty *rg, *rw;
    ty_chain(g, &pg, &rg); ty_chain(w, &pw, &rw);
    if (llen(pg) >= n && llen(pw) >= n) {
      int ok = 1;
      L *x = pg, *y = pw;
      for (int i = 0; i < n && ok; i++, x = x->t, y = y->t) if (!leq(c, (Ty *)y->h, (Ty *)x->h)) ok = 0;
      if (ok) {
        Term *nb = fit(c, term->body, mk_chain(ldrop(n, pg), rg), mk_chain(ldrop(n, pw), rw));
        return nb ? t_lam(term->ps, nb) : NULL;
      }
    }
  }
  return NULL;
}

/* after checking: which program symbols need the value of an unknown (the least fixed point over their checked bodies) */
void settle_taint(Checker *c, L *defs) {
  hclear(c->taint);
  for (L *d = defs; d; d = d->t) { int *f = NEW(int); *f = 0; hset(c->taint, ((Stmt *)d->h)->name, f); }
  int changed = 1;
  while (changed) {
    changed = 0;
    for (L *d = defs; d; d = d->t) {
      Stmt *s = (Stmt *)d->h;
      int *cur = (int *)hget(c->taint, s->name);
      if (!*cur) {
        Hash *bound = hnew();
        for (L *p = s->params; p; p = p->t) hset(bound, (const char *)p->h, bound);
        if (mentions(c, s->body, bound)) { *cur = 1; changed = 1; }
      }
    }
  }
}
static Term *check_entry(Checker *c, const char *name, L *params, Term *body, Ty *entry) {
  L *ps; Ty *r;
  ty_chain(entry, &ps, &r);
  if (llen(params) > llen(ps)) class_err(xfmt("%s has %d parameters but its class %s has only %d", name, llen(params), show_type(entry), llen(ps)));
  L *loc = NULL; int i = 0;
  for (L *p = params; p; p = p->t, i++) loc = loc_insert(loc, (const char *)p->h, (Ty *)lnth(ps, i));
  Ty *want = mk_chain(ldrop(llen(params), ps), r);
  TyTerm got = synth(c, loc, body);
  Term *fixed = fit(c, got.term, got.ty, want);
  if (!fixed) class_err(xfmt("%s: the body has class %s but %s was declared", name, show_type(got.ty), show_type(want)));
  return fixed;
}

/* ------------------------------------------------------------------ statements */
Stmt *check_statement(Checker *c, Stmt *st, int trusted) {
  if (st->kind == S_DECL) {
    declare(c, st->name, st->ty);
    int unk = 0;
    for (L *u = c->unknowns; u; u = u->t) if (!strcmp(((Unknown *)u->h)->name, st->name)) unk = 1;
    if (!trusted && unk) {
      if (llen(sigs_of(c, st->name)) > 1) class_err(xfmt("%s is declared but never defined, so it is an unknown, and an unknown has one class", st->name));
      int k = domain(c, st->ty);
      if (k < 0)
        class_err(xfmt("%s is declared but never defined, so it is an unknown; an unknown must be a number (a class below ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i] — human \\NN \\ZZ \\QQ \\Z \\Q \\RR \\CC), not %s",
                       st->name, show_type(st->ty)));
      for (L *u = c->unknowns; u; u = u->t) if (!strcmp(((Unknown *)u->h)->name, st->name)) ((Unknown *)u->h)->dom = k;
    }
    return NULL;
  }
  if (st->kind == S_FACT) { fact(c, st->body); return NULL; }
  if (hhas(c->defined, st->name)) class_err(xfmt("%s is defined twice", st->name));
  if (!hhas(c->sigs, st->name)) class_err(xfmt("%s is defined before it is declared:  write  %s ∶ <class>  first", st->name, st->name));
  hset(c->defined, st->name, c);
  if (trusted) return NULL;
  Stmt *out = NULL;
  for (L *e = sigs_of(c, st->name); e; e = e->t) {
    Term *nb = check_entry(c, st->name, st->params, st->body, (Ty *)e->h);
    if (!out) {
      Hash *bound = hnew();
      for (L *p = st->params; p; p = p->t) hset(bound, (const char *)p->h, bound);
      int *t = NEW(int); *t = mentions(c, nb, bound);
      hset(c->taint, st->name, t);
      out = s_def(st->name, st->params, nb);
    }
  }
  if (!out) class_err("no declaration");
  return out;
}
