/* imo_rt.c -- the run-time system of Compimo (see imo_rt.h): objects, laziness, application, errors, and the interface to the host. */
#include "imo_rt.h"
#include <stdio.h>
#include <stdarg.h>
#include <setjmp.h>
#include <alloca.h>
#ifndef IMO_NOGC
#define GC_THREADS
#include <gc.h>
#endif

/* ------------------------------------------------------------------------------------------------- memory */
#ifdef IMO_NOGC
static char *bump_p, *bump_end;
void *rt_alloc(size_t bytes) {
  bytes = (bytes + 15) & ~(size_t)15;
  if ((size_t)(bump_end - bump_p) < bytes) {
    size_t chunk = bytes > (64u << 20) ? bytes : (64u << 20);
    bump_p = calloc(1, chunk); if (!bump_p) { fputs("i-1: out of memory\n", stderr); exit(2); }
    bump_end = bump_p + chunk;
  }
  void *r = bump_p; bump_p += bytes; return r;
}
#else
void *rt_alloc(size_t bytes) { return GC_malloc(bytes); }
#endif

#ifdef IMO_NOGC
void *rt_alloc_atomic(size_t b) { return rt_alloc(b); }
#else
void *rt_alloc_atomic(size_t b) { return GC_malloc_atomic(b); }
#endif
V RT_T, RT_F;
static V VT, VF, VNIL, VINT[3];
static const Desc D_T = {0, 2, 0}, D_F = {0, 2, 1};

/* ------------------------------------------------------------------------------------------------- errors */
typedef struct { int kind; char msg[512]; } ErrInfo;
static jmp_buf *cur_jmp;
static ErrInfo cur_err;
static V *bh; static size_t bh_top, bh_cap;                    /* the thunks under evaluation (to be marked failed when an error unwinds) */

void rt_error(int kind, const char *fmt, ...) {
  va_list ap; va_start(ap, fmt); vsnprintf(cur_err.msg, sizeof cur_err.msg, fmt, ap); va_end(ap);
  cur_err.kind = kind;
  if (!cur_jmp) { fprintf(stderr, "%s\n", cur_err.msg); exit(1); }
  longjmp(*cur_jmp, 1);
}

/* ------------------------------------------------------------------------------------------------- objects */
V rt_mkclo(Fn fn, uint32_t arity, uint32_t nfv, V *fv) {
  Clo *c = rt_alloc(sizeof(Clo) + nfv * sizeof(V));
  c->h.tag = T_CLO; c->h.n = nfv; c->arity = arity; c->fn = fn;
  for (uint32_t i = 0; i < nfv; i++) c->fv[i] = fv[i];
  return (V)c;
}
V rt_mkthunk(Th fn, uint32_t nfv, V *fv) {
  Thk *t = rt_alloc(sizeof(Thk) + (nfv ? nfv : 1) * sizeof(V));
  t->h.tag = T_THUNK; t->h.n = nfv ? nfv : 1; t->fn = fn;
  for (uint32_t i = 0; i < nfv; i++) t->fv[i] = fv[i];
  return (V)t;
}
V rt_mkdata(const Desc *d, uint32_t nf, V *f) {
  Data *o = rt_alloc(sizeof(Data) + nf * sizeof(V));
  o->h.tag = T_DATA; o->h.n = nf; o->d = d;
  for (uint32_t i = 0; i < nf; i++) o->f[i] = f[i];
  return (V)o;
}
V rt_data0(const Desc *d) { return rt_mkdata(d, 0, NULL); }
V rt_pap(V f, int n, V *a) {
  int held = 0; V fun = f; V *old = NULL;
  if (f->h.tag == T_PAP) { Pap *p = (Pap *)f; held = p->h.n; fun = p->fun; old = p->args; }
  Pap *p = rt_alloc(sizeof(Pap) + (held + n) * sizeof(V));
  p->h.tag = T_PAP; p->h.n = held + n; p->fun = fun;
  for (int i = 0; i < held; i++) p->args[i] = old[i];
  for (int i = 0; i < n; i++) p->args[held + i] = a[i];
  return (V)p;
}
static V mkval(uint32_t kind, int32_t k, V a, V b) {
  Val *v = rt_alloc(sizeof(Val)); v->h.tag = T_VAL; v->h.n = 2; v->kind = kind; v->k = k; v->f[0] = a; v->f[1] = b; return (V)v;
}
static V mkprim(uint32_t kind, uint32_t arity) {
  Prim *p = rt_alloc(sizeof(Prim)); p->h.tag = T_PRIM; p->kind = kind; p->arity = arity; return (V)p;
}

/* ------------------------------------------------------------------------------------------------- evaluation */
V rt_force(V t) {
  for (;;) {
    switch (t->h.tag) {
      case T_IND: t = ((Thk *)t)->fv[0]; continue;
      case T_THUNK: {
        Thk *k = (Thk *)t; Th fn = k->fn;
        k->h.tag = T_BLACK;
        if (bh_top == bh_cap) { bh_cap = bh_cap ? bh_cap * 2 : 1024; V *nb = rt_alloc(bh_cap * sizeof(V)); if (bh_top) memcpy(nb, bh, bh_top * sizeof(V)); bh = nb; }
        bh[bh_top++] = t;
        V r = fn(k->fv);
        bh_top--;
        for (uint32_t i = 1; i < k->h.n; i++) k->fv[i] = NULL;       /* the captured variables are no longer needed */
        k->fv[0] = r; k->h.tag = T_IND;
        return r;
      }
      case T_BLACK: rt_error(0, "i-1: a value that depends on itself (<<loop>>)");
      case T_FAIL: { ErrInfo *e = (ErrInfo *)((Thk *)t)->fv[0]; rt_error(e->kind, "%s", e->msg); }
      default: return t;
    }
  }
}

V rt_apply(V f, int n, V *a) {
  for (;;) {
    if (n == 0) return EVAL(f);
    f = EVAL(f);
    switch (f->h.tag) {
      case T_CLO: {
        Clo *c = (Clo *)f; int ar = (int)c->arity;
        if (n == ar) return c->fn(c->fv, a);
        if (n < ar) return rt_pap(f, n, a);
        V r = c->fn(c->fv, a); a += ar; n -= ar; f = r; continue;
      }
      case T_PAP: {
        Pap *p = (Pap *)f; int h = (int)p->h.n, total = h + n;
        V *tmp = total <= 64 ? alloca(total * sizeof(V)) : rt_alloc(total * sizeof(V));
        for (int i = 0; i < h; i++) tmp[i] = p->args[i];
        for (int i = 0; i < n; i++) tmp[h + i] = a[i];
        f = p->fun; a = tmp; n = total; continue;
      }
      case T_DATA: {
        Data *d = (Data *)f; const Desc *ds = d->d; int m = (int)ds->m;
        if (n < m) return rt_pap(f, n, a);
        V alt = a[ds->j];
        if (n == m) return rt_apply(alt, (int)ds->nf, d->f);
        V r = rt_apply(alt, (int)ds->nf, d->f); a += m; n -= m; f = r; continue;
      }
      case T_PACK: {
        Pack *p = (Pack *)f;
        if (n < 2) return rt_pap(f, n, a);
        V r;
        if (p->len == 0) r = EVAL(a[1]);
        else {
          V t = RT_F;
          if (p->len > 1) { Pack *q = rt_alloc(sizeof(Pack)); q->h.tag = T_PACK; q->h.n = 1; q->len = p->len - 1; q->p = p->p + 1; q->owner = p->owner ? p->owner : (V)p; t = (V)q; }
          r = rt_apply(a[0], 2, (V[]){p->p[0] ? RT_T : RT_F, t});
        }
        if (n == 2) return r;
        f = r; a += 2; n -= 2; continue;
      }
      case T_PRIM: {
        Prim *p = (Prim *)f; int ar = (int)p->arity;
        if (n < ar) return rt_pap(f, n, a);
        if (n > ar) rt_error(0, "i-1: a value that is not a function is applied");
        static const uint32_t vk[] = {VK_CONS, VK_PAIR, VK_CN, VK_CS, VK_CA, VK_CL, VK_CV};
        return mkval(vk[p->kind], 0, a[0], ar > 1 ? a[1] : NULL);
      }
      default: rt_error(0, "i-1: a value that is not a function is applied");
    }
  }
}


/* ------------------------------------------------------------------------------------------------- natives: digit strings
 * A digit string is a list of Booleans, least significant digit first, of a Gaussian integer in base b = -1 + i.  The prelude computes with the lists (a serial
 * adder with a carry numeral, a sign automaton, …); here the same functions are computed on arrays of digits.  They return the same LISTS as the definitions,
 * digit for digit (the sum has a digit for each position of the longer string, and then the digits of the carry that is left): the adder and the subtractor are
 * the same transducers (lib/number.imo: ⊞ᶜ′ and ⊟ᶜ′), their carry tables ⌕′ ⌕⁺ ⌕⁻ are generated from the definitions (src/gen.rs).  The tests compare every native with the
 * definition on random strings (tests/compimo/). */
static int no_native = -1;
static V ORD[3];
static const Desc DCONS = {2, 2, 0}, DORD0 = {0, 3, 0}, DORD1 = {0, 3, 1}, DORD2 = {0, 3, 2};
extern int imo_carry_p(const uint8_t *t, int n, uint8_t *out);
extern int imo_carry_sp(const uint8_t *t, int n, uint8_t *out);
extern int imo_carry_sm(const uint8_t *t, int n, uint8_t *out);

static void nat_init(void) {
  no_native = getenv("IMO_NONAT") != NULL;
  ORD[0] = rt_data0(&DORD0); ORD[1] = rt_data0(&DORD1); ORD[2] = rt_data0(&DORD2);
}
static int native_ok(void) { if (no_native < 0) nat_init(); return !no_native; }

/* one step through a list: 1 = a cell (head, tail), 0 = the end, -1 = not a list (a native then gives up and the compiled definition decides) */
static int list_step(V l, V *h, V *t) {
  V v = EVAL(l);
  if (v->h.tag == T_PACK) {
    Pack *p = (Pack *)v;
    if (p->len == 0) return 0;
    *h = p->p[0] ? RT_T : RT_F;
    if (p->len == 1) *t = RT_F;
    else { Pack *q = rt_alloc(sizeof(Pack)); q->h.tag = T_PACK; q->h.n = 1; q->len = p->len - 1; q->p = p->p + 1; q->owner = p->owner ? p->owner : (V)p; *t = (V)q; }
    return 1;
  }
  if (v->h.tag == T_DATA) {
    Data *d = (Data *)v; const Desc *ds = d->d;
    if (ds->m == 2) {
      if (ds->j == 0 && ds->nf == 2) { *h = d->f[0]; *t = d->f[1]; return 1; }
      if (ds->j == 1 && ds->nf == 0) return 0;
    }
  }
  return -1;      /* anything else (a list made by a lambda, an undetermined value, …): the compiled definition of the prelude decides */
}
static int bool_of(V b) {
  V v = EVAL(b);
  if (v->h.tag == T_DATA) { Data *d = (Data *)v; if (d->d->m == 2 && d->d->nf == 0) return d->d->j == 0; }
  return -1;
}

typedef struct { uint8_t *p; int n, cap; uint8_t small[512]; } Buf;
static void buf_init(Buf *b) { b->p = b->small; b->n = 0; b->cap = (int)sizeof b->small; }
static void buf_push(Buf *b, int d) {
  if (b->n == b->cap) {
    int nc = b->cap * 2; uint8_t *np = malloc(nc); if (!np) { fputs("i-1: out of memory\n", stderr); exit(2); }
    memcpy(np, b->p, b->n); if (b->p != b->small) free(b->p); b->p = np; b->cap = nc;
  }
  b->p[b->n++] = (uint8_t)d;
}
static void buf_free(Buf *b) { if (b->p != b->small) free(b->p); b->p = b->small; b->n = 0; b->cap = (int)sizeof b->small; }
static void buf_append(Buf *b, const uint8_t *s, int n) { while (b->n + n > b->cap) { int nc = b->cap * 2; uint8_t *np = malloc(nc); memcpy(np, b->p, b->n); if (b->p != b->small) free(b->p); b->p = np; b->cap = nc; } memcpy(b->p + b->n, s, n); b->n += n; }
static int read_digits(V l, Buf *b) {
  V h, t; int s;
  { V v = EVAL(l); if (v->h.tag == T_PACK) { Pack *p = (Pack *)v; buf_append(b, p->p, (int)p->len); return 1; } }
  while ((s = list_step(l, &h, &t)) > 0) { int d = bool_of(h); if (d < 0) return 0; buf_push(b, d); l = t; }
  return s == 0;
}
V rt_mkpack(const uint8_t *d, int n) {
  if (n == 0) return RT_F;
  uint8_t *arr = rt_alloc_atomic(n); memcpy(arr, d, n);
  Pack *p = rt_alloc(sizeof(Pack)); p->h.tag = T_PACK; p->h.n = 1; p->len = (uint32_t)n; p->p = arr; p->owner = NULL;
  return (V)p;
}
static V list_of(const uint8_t *d, int n) { return rt_mkpack(d, n); }

/* x + y: the transducer ⊞ᶜ with its carry numeral */
static void add_digits(const uint8_t *x, int nx, const uint8_t *y, int ny, Buf *out) {
  uint8_t z[64]; int zn = 0;
  for (int i = 0; i < nx || i < ny; i++) {
    int th = i < nx ? x[i] : 0, io = i < ny ? y[i] : 0;
    if (zn > 0) {
      int dl = z[0];
      buf_push(out, th ^ io ^ dl);
      int maj = (th & io) | (th & dl) | (io & dl);
      if (maj) { uint8_t nz[64]; int nn = imo_carry_p(z + 1, zn - 1, nz); memcpy(z, nz, nn); zn = nn; }
      else { memmove(z, z + 1, zn - 1); zn--; }
    } else {
      buf_push(out, th ^ io);
      if (th & io) { z[0] = 0; z[1] = 1; z[2] = 1; zn = 3; } else zn = 0;
    }
  }
  for (int k = 0; k < zn; k++) buf_push(out, z[k]);
}
/* x - y: the transducer ⊟ᶜ */
static void sub_digits(const uint8_t *x, int nx, const uint8_t *y, int ny, Buf *out) {
  uint8_t z[64]; int zn = 0;
  for (int i = 0; i < nx || i < ny; i++) {
    int th = i < nx ? x[i] : 0, io = i < ny ? y[i] : 0;
    if (zn > 0) {
      int dl = z[0];
      buf_push(out, th ^ io ^ dl);
      uint8_t nz[64]; int nn;
      if (th) {
        if (io) { nn = zn - 1; memcpy(nz, z + 1, nn); }
        else if (dl) nn = imo_carry_sp(z + 1, zn - 1, nz);
        else { nn = zn - 1; memcpy(nz, z + 1, nn); }
      } else {
        if (io) { if (dl) { nn = zn - 1; memcpy(nz, z + 1, nn); } else nn = imo_carry_sm(z + 1, zn - 1, nz); }
        else { nn = zn - 1; memcpy(nz, z + 1, nn); }
      }
      memcpy(z, nz, nn); zn = nn;
    } else {
      buf_push(out, th ^ io);
      if (!th && io) { z[0] = 0; z[1] = 1; z[2] = 1; z[3] = 1; zn = 4; } else zn = 0;
    }
  }
  for (int k = 0; k < zn; k++) buf_push(out, z[k]);
}
V nat_addz(V x, V y) {
  if (!native_ok()) return NULL;
  Buf bx, by, o; buf_init(&bx); buf_init(&by); buf_init(&o);
  if (!read_digits(x, &bx) || !read_digits(y, &by)) { buf_free(&bx); buf_free(&by); return NULL; }
  add_digits(bx.p, bx.n, by.p, by.n, &o);
  V r = list_of(o.p, o.n); buf_free(&bx); buf_free(&by); buf_free(&o); return r;
}
V nat_subz(V x, V y) {
  if (!native_ok()) return NULL;
  Buf bx, by, o; buf_init(&bx); buf_init(&by); buf_init(&o);
  if (!read_digits(x, &bx) || !read_digits(y, &by)) { buf_free(&bx); buf_free(&by); return NULL; }
  sub_digits(bx.p, bx.n, by.p, by.n, &o);
  V r = list_of(o.p, o.n); buf_free(&bx); buf_free(&by); buf_free(&o); return r;
}
V nat_negz(V x) {
  if (!native_ok()) return NULL;
  Buf bx, o; buf_init(&bx); buf_init(&o);
  if (!read_digits(x, &bx)) { buf_free(&bx); return NULL; }
  sub_digits(NULL, 0, bx.p, bx.n, &o);
  V r = list_of(o.p, o.n); buf_free(&bx); buf_free(&o); return r;
}
/* x * y: ⊠ᶻ ξ η = η (ζ ω ↦ ζ (⊞ᶻ ξ (𝕓 (⊠ᶻ ξ ω))) (𝕓 (⊠ᶻ ξ ω))) ⊥ — from the most significant digit of η down */
V nat_mulz(V x, V y) {
  if (!native_ok()) return NULL;
  Buf bx, by, r; buf_init(&bx); buf_init(&by); buf_init(&r);
  if (!read_digits(x, &bx) || !read_digits(y, &by)) { buf_free(&bx); buf_free(&by); return NULL; }
  for (int k = by.n - 1; k >= 0; k--) {
    Buf s; buf_init(&s);
    buf_push(&s, 0);
    for (int i = 0; i < r.n; i++) buf_push(&s, r.p[i]);          /* 𝕓 r */
    buf_free(&r);                                                  /* r is rebuilt below (a Buf may point into itself: it is never copied as a struct) */
    if (by.p[k]) add_digits(bx.p, bx.n, s.p, s.n, &r);
    else buf_append(&r, s.p, s.n);
    buf_free(&s);
  }
  V res = list_of(r.p, r.n); buf_free(&bx); buf_free(&by); buf_free(&r); return res;
}
V nat_eqv(V x, V y) {
  if (!native_ok()) return NULL;
  { V ex = EVAL(x), ey = EVAL(y);
    if (ex->h.tag == T_PACK && ey->h.tag == T_PACK) {                    /* two digit strings: equal as numbers, whatever zeros they have at the high end */
      Pack *px = (Pack *)ex, *py = (Pack *)ey; uint32_t m = px->len < py->len ? px->len : py->len;
      if (memcmp(px->p, py->p, m)) return RT_F;
      const Pack *l = px->len > py->len ? px : py;
      for (uint32_t i = m; i < l->len; i++) if (l->p[i]) return RT_F;
      return RT_T;
    } }
  V hx, tx, hy, ty;
  for (;;) {
    int a = list_step(x, &hx, &tx), b = list_step(y, &hy, &ty);
    if (a < 0 || b < 0) return NULL;
    if (!a && !b) return RT_T;
    int dx = a ? bool_of(hx) : 0, dy = b ? bool_of(hy) : 0;
    if (dx < 0 || dy < 0) return NULL;
    if (dx != dy) return RT_F;
    x = a ? tx : RT_F; y = b ? ty : RT_F;
  }
}
V nat_canon(V x) {
  if (!native_ok()) return NULL;
  Buf b; buf_init(&b); if (!read_digits(x, &b)) { buf_free(&b); return NULL; }
  while (b.n > 0 && !b.p[b.n - 1]) b.n--;
  V r = list_of(b.p, b.n); buf_free(&b); return r;
}
V nat_isz(V x) {
  if (!native_ok()) return NULL;
  V h, t; int s;
  while ((s = list_step(x, &h, &t)) > 0) { int d = bool_of(h); if (d < 0) return NULL; if (d) return RT_F; x = t; }
  return s == 0 ? RT_T : NULL;
}
/* the sign automata ⋚ʳ′ (real part) and ⋚ⁱ′ (imaginary part): blocks of four digits, least significant first */
static V cmp_part(V x, int imag) {
  Buf b; buf_init(&b); if (!read_digits(x, &b)) { buf_free(&b); return NULL; }
  int sg = 1, nu = 0;
  for (int i = 0; i < b.n; i += 4) {
    int d0 = i < b.n ? b.p[i] : 0, d1 = i + 1 < b.n ? b.p[i + 1] : 0, d2 = i + 2 < b.n ? b.p[i + 2] : 0, d3 = i + 3 < b.n ? b.p[i + 3] : 0;
    int c1, c2;
    if (!imag) { c1 = d3 || (d0 && !d1); c2 = !d3 && !d0 && d1; }
    else { c1 = (d3 && !d2) || (d1 && !(d2 ^ d3)); c2 = d2 && !d3; }
    if (c1) sg = nu ? 0 : 2; else if (c2) sg = nu ? 2 : 0;
    nu = !nu;
  }
  buf_free(&b);
  return ORD[sg];
}
V nat_cmpr(V x) { if (!native_ok()) return NULL; return cmp_part(x, 0); }
V nat_cmpi(V x) { if (!native_ok()) return NULL; return cmp_part(x, 1); }

/* ------------------------------------------------------------------------------------------------- the host interface: handles, applications, markers */
typedef struct { int kind; uint32_t a, b; int32_t k; } RtVal;
static V *HT; static uint32_t h_n = 1, h_cap, *h_free, h_nfree, h_freecap;

#ifndef IMO_NOGC
static void *uncollectable(size_t b) { return GC_malloc_uncollectable(b); }
#else
static void *uncollectable(size_t b) { return calloc(1, b); }
#endif

static uint32_t hnew(V v) {
  uint32_t h;
  if (h_nfree) h = h_free[--h_nfree];
  else {
    if (h_n >= h_cap) {
      uint32_t nc = h_cap ? h_cap * 2 : 4096; V *nt = uncollectable(nc * sizeof(V));
      if (HT && h_n > 1) memcpy(nt, HT, h_n * sizeof(V));
      /* the old table stays allocated (uncollectable) but is no longer used */
      HT = nt; h_cap = nc;
    }
    h = h_n++;
  }
  HT[h] = v; return h;
}
uint32_t rt_dup(uint32_t h) { return hnew(HT[h]); }
void rt_drop(uint32_t h) {
  if (!h) return;
  HT[h] = NULL;
  if (h_nfree == h_freecap) { h_freecap = h_freecap ? h_freecap * 2 : 1024; uint32_t *nf = calloc(h_freecap, sizeof(uint32_t)); if (h_nfree) memcpy(nf, h_free, h_nfree * sizeof(uint32_t)); free(h_free); h_free = nf; }
  h_free[h_nfree++] = h;
}

/* the registry of the globals: name -> the slot that holds the object (the last registration of a name wins: a program may define what a prelude file given on the command line replaces) */
typedef struct { const char *name; V *slot; } RegEnt;
static RegEnt *reg; static size_t reg_n, reg_cap; static uint32_t *reg_tab; static size_t reg_tcap;
static uint64_t hash_str(const char *s) { uint64_t h = 1469598103934665603ULL; while (*s) { h ^= (unsigned char)*s++; h *= 1099511628211ULL; } return h; }
static void reg_rehash(void) {
  size_t nc = reg_tcap ? reg_tcap * 2 : 16384;
  uint32_t *nt = calloc(nc, sizeof(uint32_t));
  for (size_t i = 0; i < reg_n; i++) { size_t k = hash_str(reg[i].name) & (nc - 1); while (nt[k]) k = (k + 1) & (nc - 1); nt[k] = (uint32_t)i + 1; }
  free(reg_tab); reg_tab = nt; reg_tcap = nc;
}
void rt_register(const char *name, V *slot) {
  if (reg_n * 2 >= reg_tcap) reg_rehash();
  size_t k = hash_str(name) & (reg_tcap - 1);
  while (reg_tab[k]) { if (strcmp(reg[reg_tab[k] - 1].name, name) == 0) { reg[reg_tab[k] - 1].slot = slot; return; } k = (k + 1) & (reg_tcap - 1); }
  if (reg_n == reg_cap) { reg_cap = reg_cap ? reg_cap * 2 : 16384; reg = realloc(reg, reg_cap * sizeof(RegEnt)); }
  reg[reg_n].name = name; reg[reg_n].slot = slot; reg_tab[k] = (uint32_t)++reg_n;
}
static V *lookup_slot(const char *name) {
  if (!reg_tcap) return NULL;
  size_t k = hash_str(name) & (reg_tcap - 1);
  while (reg_tab[k]) { if (strcmp(reg[reg_tab[k] - 1].name, name) == 0) return reg[reg_tab[k] - 1].slot; k = (k + 1) & (reg_tcap - 1); }
  return NULL;
}
extern void imo_init_pre(void);

#ifdef IMO_PROF
void rt_prof_dump(void);
#endif
void rt_init(void) {
#ifdef IMO_PROF
  atexit(rt_prof_dump);
#endif
#ifndef IMO_NOGC
  GC_INIT();
  GC_set_free_space_divisor(2);
  GC_expand_hp(256u << 20);
  GC_allow_register_threads();
#endif
  RT_T = rt_data0(&D_T); RT_F = rt_data0(&D_F);
  VT = mkval(VK_T, 0, NULL, NULL); VF = mkval(VK_F, 0, NULL, NULL); VNIL = mkval(VK_NIL, 0, NULL, NULL);
  for (int i = 0; i < 3; i++) VINT[i] = mkval(VK_INT, i, NULL, NULL);
  HT = NULL; h_n = 1; h_cap = 0;
  /* the markers must stay reachable: handles 1..N are never dropped */
  hnew(RT_T); hnew(RT_F); hnew(VT); hnew(VF); hnew(VNIL);
  for (int i = 0; i < 3; i++) hnew(VINT[i]);
  hnew(mkprim(PK_CONS, 2)); hnew(mkprim(PK_PAIR, 2));
  hnew(mkprim(PK_CN, 1)); hnew(mkprim(PK_CS, 1)); hnew(mkprim(PK_CA, 2)); hnew(mkprim(PK_CL, 1)); hnew(mkprim(PK_CV, 1));
  imo_init_pre();
}
void rt_thread_register(void) {
#ifndef IMO_NOGC
  struct GC_stack_base sb; GC_get_stack_base(&sb); GC_register_my_thread(&sb);
#endif
}
/* marker handles: 1 true 2 false (the data), 3 vt 4 vf 5 vnil 6..8 ints 9 cons 10 pair 11..15 code builders */
uint32_t rt_marker(int w) { return rt_dup((uint32_t)w); }

uint32_t rt_lookup(const char *name) { V *s = lookup_slot(name); return s && *s ? hnew(*s) : 0; }

/* the lazy application of f to the arguments */
static V th_app0(V *fv) { return EVAL(fv[0]); }
static V th_app1(V *fv) { return rt_apply(fv[0], 1, fv + 1); }
static V th_app2(V *fv) { return rt_apply(fv[0], 2, fv + 1); }
static V th_app3(V *fv) { return rt_apply(fv[0], 3, fv + 1); }
static V th_app4(V *fv) { return rt_apply(fv[0], 4, fv + 1); }
static V th_appn(V *fv) { return rt_apply(fv[0], (int)(uintptr_t)fv[1], fv + 2); }
uint32_t rt_app(uint32_t f, int n, const uint32_t *args) {
  V a[16]; V fv[20];
  if (n > 4) {                            /* n, then the arguments */
    V *big = rt_alloc((n + 2) * sizeof(V)); big[0] = HT[f]; big[1] = (V)(uintptr_t)n;
    for (int i = 0; i < n; i++) big[2 + i] = HT[args[i]];
    Thk *t = rt_alloc(sizeof(Thk) + (n + 2) * sizeof(V)); t->h.tag = T_THUNK; t->h.n = n + 2; t->fn = th_appn;
    for (int i = 0; i < n + 2; i++) t->fv[i] = big[i];
    return hnew((V)t);
  }
  fv[0] = HT[f]; for (int i = 0; i < n; i++) a[i] = HT[args[i]], fv[1 + i] = a[i];
  Th fn = n == 0 ? th_app0 : n == 1 ? th_app1 : n == 2 ? th_app2 : n == 3 ? th_app3 : th_app4;
  return hnew(rt_mkthunk(fn, (uint32_t)n + 1, fv));
}

const char *rt_error_msg(void) { return cur_err.msg; }
int rt_error_kind(void) { return cur_err.kind; }

/* evaluate f args to weak head normal form: 0 = ok (out filled), 1 = error */
int rt_apply_whnf(uint32_t f, int n, const uint32_t *args, RtVal *out) {
  jmp_buf jb; jmp_buf *saved = cur_jmp; size_t saved_bh = bh_top;
  V a[32];
  if (n > 32) { rt_error(0, "i-1: too many arguments"); }
  if (setjmp(jb)) {
    ErrInfo *e = rt_alloc(sizeof(ErrInfo)); *e = cur_err;
    for (size_t i = saved_bh; i < bh_top; i++) {          /* the thunks that were under evaluation fail with the same error */
      Thk *t = (Thk *)bh[i]; t->h.tag = T_FAIL; t->fv[0] = (V)e;
    }
    bh_top = saved_bh; cur_jmp = saved;
    return 1;
  }
  cur_jmp = &jb;
  for (int i = 0; i < n; i++) a[i] = HT[args[i]];
  V r = rt_apply(HT[f], n, a);
  cur_jmp = saved;
  if (r->h.tag == T_VAL) {
    Val *v = (Val *)r; out->kind = (int)v->kind; out->k = v->k;
    out->a = v->f[0] ? hnew(v->f[0]) : 0; out->b = v->f[1] ? hnew(v->f[1]) : 0;
  } else { out->kind = VK_FUN; out->k = 0; out->a = hnew(r); out->b = 0; }
  return 0;
}

/* a thunk that fails with this error when it is evaluated (kind 0: evaluation error, 1: an unknown) */
V rt_failobj(int kind, const char *msg);
uint32_t rt_fail_thunk(int kind, const char *msg) { return hnew(rt_failobj(kind, msg)); }
/* install a handle as the value of a global (the unknowns of the program) */
void rt_set_global(const char *name, uint32_t h) { V *s = lookup_slot(name); if (s) *s = HT[h]; }
/* a value that fails when it is evaluated */
V rt_failobj(int kind, const char *msg) {
  ErrInfo *e = rt_alloc(sizeof(ErrInfo)); e->kind = kind; snprintf(e->msg, sizeof e->msg, "%s", msg);
  Thk *t = rt_alloc(sizeof(Thk) + sizeof(V)); t->h.tag = T_FAIL; t->h.n = 1; t->fn = NULL; t->fv[0] = (V)e;
  return (V)t;
}

#ifdef IMO_PROF
#include <stdlib.h>
uint64_t rt_prof[100000];
extern const char *const imo_pnames[];
extern const int imo_npre;
static int cmp_prof(const void *a, const void *b) { uint64_t x = rt_prof[*(const int *)a], y = rt_prof[*(const int *)b]; return x < y ? 1 : x > y ? -1 : 0; }
void rt_prof_dump(void) {
  int n = imo_npre; int *ix = malloc(n * sizeof(int)); uint64_t tot = 0;
  for (int i = 0; i < n; i++) { ix[i] = i; tot += rt_prof[i]; }
  qsort(ix, n, sizeof(int), cmp_prof);
  fprintf(stderr, "calls of prelude functions: %llu in all\n", (unsigned long long)tot);
  for (int i = 0; i < 45 && i < n; i++) fprintf(stderr, "%12llu  %s\n", (unsigned long long)rt_prof[ix[i]], imo_pnames[ix[i]]);
}
#endif
