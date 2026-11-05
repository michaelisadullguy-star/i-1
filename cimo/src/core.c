/* core.c -- the lazy evaluator of i-1 (port of ocamimo/src/core.ml and rustimo/src/core.rs).
   Call by need on an explicit stack of continuations; every term is compiled once to code with flat closures; a chain of applications is one
   call, a chain of lambdas one lambda of arity n; every closed application is evaluated at most once; the decoders apply a language value to
   builder constants of the host (markers, list and pair builders, ...) and read what comes back. */
#include "cimo.h"

enum { X_VAR, X_CONST, X_LAM, X_APP, X_CALL, X_CALLVAR, X_PAP };
struct Code { int tag; int i; Th *t; LamInfo *lam; Code *f; Arg *args; int nargs; PapSpec *pap; };
enum { A_VAR, A_CONST, A_LAM, A_DELAY, A_PAP };
struct Arg { int tag; int i; Th *t; LamInfo *lam; ThunkInfo *thk; PapSpec *pap; };
struct PapSpec { Th *g; Arg *args; int nargs; };
struct LamInfo { int arity; int *caps; int ncaps; Code *body; };
struct ThunkInfo { int *caps; int ncaps; Code *body; };

typedef struct Cont { int is_update; Th *t; } Cont;
struct Machine {
  Hash *globals;      /* name -> Th* */
  Hash *arities;      /* name -> int* */
  Source **lazy_src; int nlazy;
  Cont *conts; int ntop, ccont;
  Th **frame;
  Th *vt, *vf, *vnil, *cons_cb, *pair_cb, *ints[3], *code_cbs[5];
  ThunkInfo **app_infos; int napp;
};

static Val V_T_ = { V_T, NULL, NULL, 0 }, V_F_ = { V_F, NULL, NULL, 0 }, V_NIL_ = { V_NIL, NULL, NULL, 0 };

static Th *mkth(int st) { Th *t = NEW(Th); t->st = st; return t; }
static Val *mkval(int tag, Th *a, Th *b, int k) { Val *v = NEW(Val); v->tag = tag; v->a = a; v->b = b; v->k = k; return v; }
static Th *done_th(Val *v) { Th *t = mkth(ST_DONE); t->val = v; return t; }
static Th *prim_th(int p) { Th *t = mkth(ST_PRIM); t->prim = p; return t; }
Th *th_fail(int kind, const char *msg) { Th *t = mkth(ST_FAIL); t->err = NEW(Err); t->err->kind = kind; t->err->msg = (char *)msg; return t; }

static int prim_arity(int p) { return (p == P_CONS || p == P_PAIR || p == P_CODEA) ? 2 : 1; }
static Val *run_prim(int p, Th **a) {
  switch (p) {
    case P_CONS: return mkval(V_CONS, a[0], a[1], 0);
    case P_PAIR: return mkval(V_PAIR, a[0], a[1], 0);
    case P_CODEN: return mkval(V_CN, a[0], NULL, 0);
    case P_CODES: return mkval(V_CS, a[0], NULL, 0);
    case P_CODEA: return mkval(V_CA, a[0], a[1], 0);
    case P_CODEL: return mkval(V_CL, a[0], NULL, 0);
    default: return mkval(V_CV, a[0], NULL, 0);
  }
}
static const char *describe(Val *v) {
  switch (v->tag) {
    case V_FUN: return "function"; case V_T: return "true"; case V_F: return "false"; case V_CONS: return "cons cell"; case V_NIL: return "nil";
    case V_PAIR: return "pair"; case V_INT: return xfmt("%d", v->k); case V_CN: return "number code"; case V_CS: return "symbol code";
    case V_CA: return "application code"; case V_CL: return "lambda code"; default: return "variable code";
  }
}

/* ------------------------------------------------------------------ compiling de Bruijn terms */
enum { N_V, N_G, N_L, N_A };
typedef struct Ann { int tag; int level; const char *name; int arity; struct Ann *body, *f, *x; int *fv; int nfv; } Ann;

static int fv_n(Ann *a) { return a->tag == N_V ? 1 : (a->tag == N_G ? 0 : a->nfv); }
static int *fv_arr(Ann *a) {
  if (a->tag == N_V) { int *r = NEWN(int, 1); r[0] = a->level; return r; }
  return a->fv;
}
static int closed_p(Ann *a) { return a->tag == N_G || ((a->tag == N_L || a->tag == N_A) && a->nfv == 0); }
static int *union_sorted(int *a, int na, int *b, int nb, int *nout) {
  int *r = NEWN(int, na + nb);
  int i = 0, j = 0, k = 0;
  while (i < na || j < nb) {
    if (j >= nb || (i < na && a[i] < b[j])) r[k++] = a[i++];
    else if (i >= na || b[j] < a[i]) r[k++] = b[j++];
    else { r[k++] = a[i]; i++; j++; }
  }
  *nout = k;
  return r;
}
static Ann *annotate(Core *t, int depth) {
  Ann *a = NEW(Ann);
  switch (t->tag) {
    case C_V: a->tag = N_V; a->level = depth - t->k; return a;
    case C_G: a->tag = N_G; a->name = t->g; return a;
    case C_L: {
      int n = 0; Core *cur = t;
      while (cur->tag == C_L) { n++; cur = cur->f; }
      Ann *body = annotate(cur, depth + n);
      int nb = fv_n(body); int *fb = fv_arr(body);
      int *fv = NEWN(int, nb); int k = 0;
      for (int i = 0; i < nb; i++) if (fb[i] < depth) fv[k++] = fb[i];
      a->tag = N_L; a->arity = n; a->body = body; a->fv = fv; a->nfv = k;
      return a;
    }
    default: {
      Ann *fa = annotate(t->f, depth), *xa = annotate(t->x, depth);
      int n;
      a->fv = union_sorted(fv_arr(fa), fv_n(fa), fv_arr(xa), fv_n(xa), &n);
      a->nfv = n; a->tag = N_A; a->f = fa; a->x = xa;
      return a;
    }
  }
}

typedef struct Scope { int *slots; int n; } Scope;
static Scope *scope_new(void) { return NEW(Scope); }
static void scope_set(Scope *s, int level, int slot) {
  if (s->n <= level) {
    int *ns = (int *)GC_MALLOC_ATOMIC(sizeof(int) * (size_t)(level + 1));
    for (int i = 0; i < level + 1; i++) ns[i] = i < s->n ? s->slots[i] : -1;
    s->slots = ns; s->n = level + 1;
  }
  s->slots[level] = slot;
}
static int scope_slot(Scope *s, int level) {
  int r = level < s->n ? s->slots[level] : -1;
  if (r < 0) { fprintf(stderr, "i-1: internal error: a free variable is not in the frame\n"); exit(1); }
  return r;
}

typedef struct Linker { Hash *globals, *arities; } Linker;
static Th *link_global(Linker *lk, const char *g) {
  Th *t = (Th *)hget(lk->globals, g);
  return t ? t : th_fail(E_EVAL, xfmt("i-1: %s has no compiled body", g));
}
static Code *gen(Linker *lk, Ann *a, int depth, Scope *sc, int root);
static LamInfo *gen_lam(Linker *lk, Ann *a, int depth, Scope *sc) {
  LamInfo *li = NEW(LamInfo);
  li->arity = a->arity; li->ncaps = a->nfv; li->caps = NEWN(int, a->nfv);
  Scope *inner = scope_new();
  for (int j = 0; j < a->nfv; j++) { li->caps[j] = scope_slot(sc, a->fv[j]); scope_set(inner, a->fv[j], j); }
  for (int p = 0; p < a->arity; p++) scope_set(inner, depth + p, a->nfv + p);
  li->body = gen(lk, a->body, depth + a->arity, inner, 0);
  return li;
}
static ThunkInfo *gen_thunk(Linker *lk, Ann *a, int depth, Scope *sc) {
  ThunkInfo *ti = NEW(ThunkInfo);
  int n = fv_n(a); int *fv = fv_arr(a);
  ti->ncaps = n; ti->caps = NEWN(int, n);
  Scope *inner = scope_new();
  for (int j = 0; j < n; j++) { ti->caps[j] = scope_slot(sc, fv[j]); scope_set(inner, fv[j], j); }
  ti->body = gen(lk, a, depth, inner, 1);
  return ti;
}
static Th *shared(Linker *lk, Ann *a, int depth) {
  if (a->tag == N_L) { Th *t = mkth(ST_CLO); t->info = gen_lam(lk, a, depth, scope_new()); return t; }
  Th *t = mkth(ST_DELAYED);
  ThunkInfo *ti = NEW(ThunkInfo);
  ti->body = gen(lk, a, depth, scope_new(), 1);
  t->info = ti;
  return t;
}
/* the chain of applications of an open application: head and arguments in order; a closed inner application is the head */
static Ann *spine(Ann *a, L **args) {
  L *acc = NULL; Ann *cur = a; int first = 1;
  while (cur->tag == N_A && (first || !closed_p(cur))) { acc = cons(cur->x, acc); cur = cur->f; first = 0; }
  *args = acc;
  return cur;
}
static int known_arity(Linker *lk, const char *g) { int *p = (int *)hget(lk->arities, g); return p ? *p : -1; }
static PapSpec *gen_pap(Linker *lk, const char *g, L *args, int depth, Scope *sc);
static Arg gen_arg(Linker *lk, Ann *a, int depth, Scope *sc) {
  Arg r; memset(&r, 0, sizeof r);
  if (a->tag == N_V) { r.tag = A_VAR; r.i = scope_slot(sc, a->level); return r; }
  if (a->tag == N_G) { r.tag = A_CONST; r.t = link_global(lk, a->name); return r; }
  if (closed_p(a)) { r.tag = A_CONST; r.t = shared(lk, a, depth); return r; }
  if (a->tag == N_L) { r.tag = A_LAM; r.lam = gen_lam(lk, a, depth, sc); return r; }
  L *args; Ann *head = spine(a, &args);
  if (head->tag == N_G) {
    int n = known_arity(lk, head->name);
    if (n >= 0 && llen(args) < n) { r.tag = A_PAP; r.pap = gen_pap(lk, head->name, args, depth, sc); return r; }
  }
  r.tag = A_DELAY; r.thk = gen_thunk(lk, a, depth, sc);
  return r;
}
static Arg *gen_args(Linker *lk, L *args, int depth, Scope *sc, int *n) {
  int k = llen(args);
  Arg *v = NEWN(Arg, k);
  int i = 0;
  for (L *l = args; l; l = l->t) v[i++] = gen_arg(lk, (Ann *)l->h, depth, sc);
  *n = k;
  return v;
}
static PapSpec *gen_pap(Linker *lk, const char *g, L *args, int depth, Scope *sc) {
  PapSpec *p = NEW(PapSpec);
  p->g = link_global(lk, g);
  p->args = gen_args(lk, args, depth, sc, &p->nargs);
  return p;
}
static Code *mkcode(int tag) { Code *c = NEW(Code); c->tag = tag; return c; }
static Code *gen(Linker *lk, Ann *a, int depth, Scope *sc, int root) {
  Code *c;
  switch (a->tag) {
    case N_V: c = mkcode(X_VAR); c->i = scope_slot(sc, a->level); return c;
    case N_G: c = mkcode(X_CONST); c->t = link_global(lk, a->name); return c;
    case N_L:
      if (closed_p(a)) { c = mkcode(X_CONST); c->t = shared(lk, a, depth); return c; }
      c = mkcode(X_LAM); c->lam = gen_lam(lk, a, depth, sc); return c;
    default: break;
  }
  if (!root && closed_p(a)) { c = mkcode(X_CONST); c->t = shared(lk, a, depth); return c; }
  L *args; Ann *cur = spine(a, &args);
  if (cur->tag == N_G) {
    int n = known_arity(lk, cur->name);
    if (n >= 0) {
      if (llen(args) >= n) { c = mkcode(X_CALL); c->t = link_global(lk, cur->name); c->args = gen_args(lk, args, depth, sc, &c->nargs); return c; }
      c = mkcode(X_PAP); c->pap = gen_pap(lk, cur->name, args, depth, sc); return c;
    }
  }
  if (cur->tag == N_V) { c = mkcode(X_CALLVAR); c->i = scope_slot(sc, cur->level); c->args = gen_args(lk, args, depth, sc, &c->nargs); return c; }
  c = mkcode(X_APP);
  c->f = gen(lk, cur, depth, sc, 0);
  c->args = gen_args(lk, args, depth, sc, &c->nargs);
  return c;
}
/* the state of a global definition: a closed lambda is a function value at once, anything else a delayed expression */
static void gen_def(Linker *lk, Th *t, Core *c) {
  Ann *a = annotate(c, 0);
  if (a->tag == N_L) { t->st = ST_CLO; t->info = gen_lam(lk, a, 0, scope_new()); t->caps = NULL; t->ncaps = 0; return; }
  ThunkInfo *ti = NEW(ThunkInfo);
  ti->body = gen(lk, a, 0, scope_new(), 1);
  t->st = ST_DELAYED; t->info = ti; t->caps = NULL; t->ncaps = 0;
}

/* ------------------------------------------------------------------ the machine */
static int term_lams(Term *t) {
  switch (t->tag) {
    case T_LAM: return llen(t->ps) + term_lams(t->body);
    case T_ASC: case T_QUOTE: return term_lams(t->body);
    default: return 0;
  }
}
static int core_arity(Core *c) { int n = 0; while (c->tag == C_L) { n++; c = c->f; } return n; }

Machine *machine_build(L *defs, L *extra) {
  Machine *m = NEW(Machine);
  m->globals = hnew(); m->arities = hnew();
  /* the ready values first (they win over a definition of the same name), then the placeholders */
  for (L *l = extra; l; l = l->t) { Extra *e = (Extra *)l->h; hset(m->globals, e->name, e->th); }
  Hash *last = hnew();
  int i = 0;
  for (L *l = defs; l; l = l->t, i++) { int *p = NEW(int); *p = i; hset(last, ((DefSrc *)l->h)->name, p); }   /* a later definition of the same name wins */
  m->nlazy = i; m->lazy_src = NEWN(Source *, i);
  i = 0;
  for (L *l = defs; l; l = l->t, i++) {
    DefSrc *d = (DefSrc *)l->h;
    if (*(int *)hget(last, d->name) == i && !hhas(m->globals, d->name)) {
      int ar = d->src->is_term ? llen(d->src->ps) + term_lams(d->src->term) : core_arity(d->src->core);
      if (ar > 0) { int *p = NEW(int); *p = ar; hset(m->arities, d->name, p); }
      Th *t = mkth(ST_LAZY); t->idx = i;
      hset(m->globals, d->name, t);
      m->lazy_src[i] = d->src;
    }
  }
  m->conts = NEWN(Cont, 1024); m->ccont = 1024;
  m->vt = done_th(&V_T_); m->vf = done_th(&V_F_); m->vnil = done_th(&V_NIL_);
  m->cons_cb = prim_th(P_CONS); m->pair_cb = prim_th(P_PAIR);
  for (int k = 0; k < 3; k++) m->ints[k] = done_th(mkval(V_INT, NULL, NULL, k));
  for (int k = 0; k < 5; k++) m->code_cbs[k] = prim_th(P_CODEN + k);
  return m;
}
Th *m_vt(Machine *m) { return m->vt; }
Th *m_vf(Machine *m) { return m->vf; }
Th **m_code_cbs(Machine *m) { return m->code_cbs; }

/* compile a global that has not been needed before: the thunk t becomes a closure or a delayed expression (or fails) */
static void compile_global(Machine *m, Th *t) {
  Source *src = m->lazy_src[t->idx];
  m->lazy_src[t->idx] = NULL;
  Linker lk = { m->globals, m->arities };
  if (!src) { Th *f = th_fail(E_EVAL, "i-1: internal error: a global was compiled twice"); *t = *f; return; }
  Core *c = src->core;
  if (src->is_term) {
    Handler h;
    if (TRY(h)) { c = erase_def(src->ps, src->term); ENDTRY(h); }
    else { Th *f = th_fail(cur_err.kind, cur_err.msg); *t = *f; return; }
  }
  gen_def(&lk, t, c);
}

Th *machine_global(Machine *m, const char *g) {
  Th *t = (Th *)hget(m->globals, g);
  if (!t) eval_err(xfmt("i-1: %s is not defined", g));
  return t;
}

Th *m_app(Machine *m, Th *f, Th **args, int n) {
  if (m->napp <= n) {
    ThunkInfo **ni = NEWN(ThunkInfo *, n + 1);
    for (int k = 0; k <= n; k++) {
      if (k < m->napp) { ni[k] = m->app_infos[k]; continue; }
      ThunkInfo *ti = NEW(ThunkInfo);
      ti->ncaps = k + 1; ti->caps = NEWN(int, k + 1);
      for (int i = 0; i <= k; i++) ti->caps[i] = i;
      Code *v0 = mkcode(X_VAR); v0->i = 0;
      if (k == 0) ti->body = v0;
      else {
        Code *ap = mkcode(X_APP); ap->f = v0; ap->nargs = k; ap->args = NEWN(Arg, k);
        for (int i = 0; i < k; i++) { ap->args[i].tag = A_VAR; ap->args[i].i = i + 1; }
        ti->body = ap;
      }
      ni[k] = ti;
    }
    m->app_infos = ni; m->napp = n + 1;
  }
  Th *t = mkth(ST_DELAYED);
  t->info = m->app_infos[n];
  t->ncaps = n + 1; t->caps = NEWN(Th *, n + 1);
  t->caps[0] = f;
  for (int i = 0; i < n; i++) t->caps[i + 1] = args[i];
  return t;
}
Th *m_call_g(Machine *m, const char *f, Th **args, int n) { return m_app(m, machine_global(m, f), args, n); }

static void push(Machine *m, int is_update, Th *t) {
  if (m->ntop >= m->ccont) {
    Cont *nc = NEWN(Cont, m->ccont * 2);
    memcpy(nc, m->conts, sizeof(Cont) * (size_t)m->ntop);
    m->conts = nc; m->ccont *= 2;
  }
  m->conts[m->ntop].is_update = is_update; m->conts[m->ntop].t = t; m->ntop++;
}
static Cont pop(Machine *m) { Cont k = m->conts[--m->ntop]; m->conts[m->ntop].t = NULL; return k; }
static int waiting(Machine *m, int base, int want) {
  int n = 0;
  while (n < want && m->ntop > base + n && !m->conts[m->ntop - 1 - n].is_update) n++;
  return n;
}
static Th **pick(Th **frame, int *idx, int n) {
  if (n == 0) return NULL;
  Th **r = NEWN(Th *, n);
  for (int i = 0; i < n; i++) r[i] = frame[idx[i]];
  return r;
}
static Th *make_pap(PapSpec *spec, Th **frame);
static Th *make_arg(Arg *a, Th **frame) {
  switch (a->tag) {
    case A_VAR: return frame[a->i];
    case A_CONST: return a->t;
    case A_LAM: { Th *t = mkth(ST_CLO); t->info = a->lam; t->ncaps = a->lam->ncaps; t->caps = pick(frame, a->lam->caps, a->lam->ncaps); return t; }
    case A_DELAY: { Th *t = mkth(ST_DELAYED); t->info = a->thk; t->ncaps = a->thk->ncaps; t->caps = pick(frame, a->thk->caps, a->thk->ncaps); return t; }
    default: return make_pap(a->pap, frame);
  }
}
static Th *make_pap(PapSpec *spec, Th **frame) {
  Th *t = mkth(ST_PAP);
  t->base = spec->g; t->ncaps = spec->nargs; t->caps = NEWN(Th *, spec->nargs);
  for (int i = 0; i < spec->nargs; i++) t->caps[i] = make_arg(&spec->args[i], frame);
  return t;
}
static Val *fun_val(Th *t) { return mkval(V_FUN, t, NULL, 0); }

/* apply a lambda: returns the code to evaluate in the new frame, or NULL with *res set to a value (a partial application) */
static Code *call_clo(Machine *m, int base, LamInfo *info, Th **caps, int ncaps, Th **held, int nheld, Th *clo, Th *first, Val **res) {
  int need = info->arity - nheld;
  int extra = waiting(m, base, need - 1);
  if (extra + 1 < need) {
    Th *p = mkth(ST_PAP);
    p->base = clo; p->ncaps = nheld + 1 + extra; p->caps = NEWN(Th *, p->ncaps);
    for (int i = 0; i < nheld; i++) p->caps[i] = held[i];
    p->caps[nheld] = first;
    for (int k = 1; k <= extra; k++) p->caps[nheld + k] = pop(m).t;
    *res = fun_val(p);
    return NULL;
  }
  Th **fr = NEWN(Th *, ncaps + nheld + need);
  for (int i = 0; i < ncaps; i++) fr[i] = caps[i];
  for (int i = 0; i < nheld; i++) fr[ncaps + i] = held[i];
  fr[ncaps + nheld] = first;
  for (int k = 1; k < need; k++) fr[ncaps + nheld + k] = pop(m).t;
  m->frame = fr;
  return info->body;
}
static Val *call_prim(Machine *m, int base, int p, Th **held, int nheld, Th *prim_v, Th *first) {
  int need = prim_arity(p) - nheld;
  int extra = waiting(m, base, need - 1);
  int n = nheld + 1 + extra;
  Th **args = NEWN(Th *, n);
  for (int i = 0; i < nheld; i++) args[i] = held[i];
  args[nheld] = first;
  for (int k = 1; k <= extra; k++) args[nheld + k] = pop(m).t;
  if (extra + 1 < need) { Th *pp = mkth(ST_PAP); pp->base = prim_v; pp->caps = args; pp->ncaps = n; return fun_val(pp); }
  return run_prim(p, args);
}

enum { M_FORCE, M_EVAL, M_DELIVER };
Val *m_apply_whnf(Machine *m, Th *start, Th **args, int nargs) {
  volatile int base = m->ntop;
  for (int k = nargs - 1; k >= 0; k--) push(m, 0, args[k]);
  Handler h;
  if (!TRY(h)) {
    /* an error: the thunks under evaluation keep it (evaluating them again gives the same error), the rest of the work is dropped */
    Err *e = NEW(Err); *e = cur_err;
    while (m->ntop > base) { Cont k = pop(m); if (k.is_update) { Th *f = th_fail(e->kind, e->msg); *k.t = *f; } }
    raise_err(e->kind, e->msg);
  }
  int mode = M_FORCE;
  Th *t = start;
  Code *code = NULL;
  Val *val = NULL;
  for (;;) {
    switch (mode) {
      case M_FORCE:
        switch (t->st) {
          case ST_DONE: val = t->val; mode = M_DELIVER; break;
          case ST_CLO: case ST_PAP: case ST_PRIM: val = fun_val(t); mode = M_DELIVER; break;
          case ST_RUNNING: eval_err("<<loop>>");
          case ST_FAIL: raise_err(t->err->kind, t->err->msg);
          case ST_LAZY: compile_global(m, t); break;
          default: {   /* delayed */
            ThunkInfo *info = (ThunkInfo *)t->info;
            m->frame = t->caps;
            t->st = ST_RUNNING; t->caps = NULL;
            push(m, 1, t);
            code = info->body; mode = M_EVAL;
          }
        }
        break;
      case M_EVAL:
        switch (code->tag) {
          case X_VAR: case X_CONST: {
            Th *x = code->tag == X_VAR ? m->frame[code->i] : code->t;
            if (x->st == ST_DONE) { val = x->val; mode = M_DELIVER; }
            else if (x->st == ST_CLO || x->st == ST_PAP || x->st == ST_PRIM) { val = fun_val(x); mode = M_DELIVER; }
            else { t = x; mode = M_FORCE; }
            break;
          }
          case X_LAM: {
            Th *c = mkth(ST_CLO); c->info = code->lam; c->ncaps = code->lam->ncaps; c->caps = pick(m->frame, code->lam->caps, code->lam->ncaps);
            val = fun_val(c); mode = M_DELIVER;
            break;
          }
          case X_CALL: {
            Th *g = code->t;
            if (g->st == ST_LAZY) compile_global(m, g);
            Th **fr = m->frame;
            if (g->st == ST_CLO && ((LamInfo *)g->info)->arity <= code->nargs) {
              LamInfo *info = (LamInfo *)g->info;
              int n = info->arity;
              for (int k = code->nargs - 1; k >= n; k--) push(m, 0, make_arg(&code->args[k], fr));
              Th **nf = NEWN(Th *, n);
              for (int k = 0; k < n; k++) nf[k] = make_arg(&code->args[k], fr);
              m->frame = nf; code = info->body;
            } else {
              for (int k = code->nargs - 1; k >= 0; k--) push(m, 0, make_arg(&code->args[k], fr));
              t = g; mode = M_FORCE;
            }
            break;
          }
          case X_CALLVAR: {
            Th *x = m->frame[code->i];
            Th **fr = m->frame;
            if (x->st == ST_CLO && ((LamInfo *)x->info)->arity == code->nargs) {
              LamInfo *info = (LamInfo *)x->info;
              Th **nf = NEWN(Th *, x->ncaps + code->nargs);
              for (int i = 0; i < x->ncaps; i++) nf[i] = x->caps[i];
              for (int k = 0; k < code->nargs; k++) nf[x->ncaps + k] = make_arg(&code->args[k], fr);
              m->frame = nf; code = info->body;
            } else {
              for (int k = code->nargs - 1; k >= 0; k--) push(m, 0, make_arg(&code->args[k], fr));
              if (x->st == ST_DONE) { val = x->val; mode = M_DELIVER; }
              else if (x->st == ST_CLO || x->st == ST_PAP || x->st == ST_PRIM) { val = fun_val(x); mode = M_DELIVER; }
              else { t = x; mode = M_FORCE; }
            }
            break;
          }
          case X_PAP: val = fun_val(make_pap(code->pap, m->frame)); mode = M_DELIVER; break;
          default: {   /* X_APP */
            Th **fr = m->frame;
            for (int k = code->nargs - 1; k >= 0; k--) push(m, 0, make_arg(&code->args[k], fr));
            code = code->f;
          }
        }
        break;
      default: {   /* M_DELIVER */
        if (m->ntop <= base) { ENDTRY(h); return val; }
        Cont k = pop(m);
        if (k.is_update) { k.t->st = ST_DONE; k.t->val = val; k.t->caps = NULL; k.t->info = NULL; break; }
        if (val->tag != V_FUN) eval_err(scat("a value that is not a function was applied: ", describe(val)));
        Th *f = val->a, *first = k.t;
        Val *res = NULL;
        Code *entered = NULL;
        if (f->st == ST_CLO) entered = call_clo(m, base, (LamInfo *)f->info, f->caps, f->ncaps, NULL, 0, f, first, &res);
        else if (f->st == ST_PRIM) res = call_prim(m, base, f->prim, NULL, 0, f, first);
        else {   /* a partial application of a closure or a primitive */
          Th *b = f->base;
          if (b->st == ST_LAZY) compile_global(m, b);
          if (b->st == ST_CLO) entered = call_clo(m, base, (LamInfo *)b->info, b->caps, b->ncaps, f->caps, f->ncaps, b, first, &res);
          else res = call_prim(m, base, b->prim, f->caps, f->ncaps, b, first);
        }
        if (entered) { code = entered; mode = M_EVAL; } else val = res;
      }
    }
  }
}

/* ------------------------------------------------------------------ decoding */
int m_to_bool(Machine *m, Th *v) { Th *a[2] = { m->vt, m->vf }; return m_apply_whnf(m, v, a, 2)->tag == V_T; }
Val *m_cell_or_nil(Machine *m, Th *v) { Th *a[2] = { m->cons_cb, m->vnil }; return m_apply_whnf(m, v, a, 2); }
int m_to_ord(Machine *m, Th *v) {
  Val *r = m_apply_whnf(m, v, m->ints, 3);
  if (r->tag != V_INT) eval_err("an ordering was expected");
  return r->k;
}
Digits m_to_list(Machine *m, Th *v) {
  Buf *b = bnew();
  Th *cur = v;
  for (;;) {
    Val *c = m_cell_or_nil(m, cur);
    if (c->tag == V_CONS) { baddc(b, (char)(m_to_bool(m, c->a) ? 1 : 0)); cur = c->b; }
    else if (c->tag == V_NIL) break;
    else eval_err("a list was expected");
  }
  Digits d = { b->n, (unsigned char *)b->s };
  return d;
}
void m_to_pair(Machine *m, Th *v, Th **a, Th **b) {
  Th *args[1] = { m->pair_cb };
  Val *r = m_apply_whnf(m, v, args, 1);
  if (r->tag != V_PAIR) eval_err("a pair was expected");
  *a = r->a; *b = r->b;
}
Th *m_stream_nth(Machine *m, Th *v, int n) {
  Th *cur = v; int k = n;
  for (;;) {
    Val *c = m_cell_or_nil(m, cur);
    if (c->tag != V_CONS) eval_err("a stream was expected");
    if (k == 0) return c->a;
    k--; cur = c->b;
  }
}
Th *m_list_value(Machine *m, Digits ds) {
  Th *tv = machine_global(m, "⊤"), *fv = machine_global(m, "⊥"), *cn = machine_global(m, "∷");
  Th *acc = fv;
  for (int i = ds.n - 1; i >= 0; i--) { Th *a[2] = { ds.d[i] ? tv : fv, acc }; acc = m_app(m, cn, a, 2); }
  return acc;
}
GI m_gi_of(Machine *m, Th *v) { return val_digits(m_to_list(m, v)); }
