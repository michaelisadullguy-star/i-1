/* util.c -- lists, strings, UTF-8, hash tables, errors, big integers, the digits of the base i-1 (port of ocamimo/src/{bigint,base}.ml). */
#include "cimo.h"
#include <math.h>
#include <ctype.h>

/* ------------------------------------------------------------------ lists */
L *cons(void *h, L *t) { L *l = NEW(L); l->h = h; l->t = t; return l; }
int llen(L *l) { int n = 0; for (; l; l = l->t) n++; return n; }
L *lrev(L *l) { L *r = NULL; for (; l; l = l->t) r = cons(l->h, r); return r; }
L *lappend(L *a, L *b) {
  if (!a) return b;
  L *r = lrev(a);
  L *out = b;
  for (; r; r = r->t) out = cons(r->h, out);
  return out;
}
void *lnth(L *l, int i) { while (i-- > 0 && l) l = l->t; return l ? l->h : NULL; }
L *ltake(int n, L *l) { L *r = NULL; for (; n > 0 && l; n--, l = l->t) r = cons(l->h, r); return lrev(r); }
L *ldrop(int n, L *l) { for (; n > 0 && l; n--) l = l->t; return l; }
L *l1(void *x) { return cons(x, NULL); }
L *l2(void *x, void *y) { return cons(x, l1(y)); }
L *l3(void *x, void *y, void *z) { return cons(x, l2(y, z)); }
int lmem_str(const char *s, L *l) { for (; l; l = l->t) if (!strcmp((const char *)l->h, s)) return 1; return 0; }

/* ------------------------------------------------------------------ buffers and strings */
Buf *bnew(void) { Buf *b = NEW(Buf); b->cap = 64; b->s = (char *)GC_MALLOC_ATOMIC(64); b->s[0] = 0; return b; }
static void bgrow(Buf *b, int need) {
  if (b->n + need + 1 <= b->cap) return;
  int nc = b->cap * 2;
  while (nc < b->n + need + 1) nc *= 2;
  char *ns = (char *)GC_MALLOC_ATOMIC((size_t)nc);
  memcpy(ns, b->s, (size_t)b->n);
  b->s = ns; b->cap = nc;
}
void baddn(Buf *b, const char *s, int n) { bgrow(b, n); memcpy(b->s + b->n, s, (size_t)n); b->n += n; b->s[b->n] = 0; }
void badd(Buf *b, const char *s) { baddn(b, s, (int)strlen(s)); }
void baddc(Buf *b, char c) { bgrow(b, 1); b->s[b->n++] = c; b->s[b->n] = 0; }
void baddcp(Buf *b, int c) {
  if (c < 0 || c > 0x10FFFF || (c >= 0xD800 && c <= 0xDFFF)) c = 0xFFFD;
  if (c < 0x80) baddc(b, (char)c);
  else if (c < 0x800) { baddc(b, (char)(0xC0 | (c >> 6))); baddc(b, (char)(0x80 | (c & 0x3F))); }
  else if (c < 0x10000) { baddc(b, (char)(0xE0 | (c >> 12))); baddc(b, (char)(0x80 | ((c >> 6) & 0x3F))); baddc(b, (char)(0x80 | (c & 0x3F))); }
  else { baddc(b, (char)(0xF0 | (c >> 18))); baddc(b, (char)(0x80 | ((c >> 12) & 0x3F))); baddc(b, (char)(0x80 | ((c >> 6) & 0x3F))); baddc(b, (char)(0x80 | (c & 0x3F))); }
}
char *bstr(Buf *b) { return b->s; }

char *xfmt(const char *fmt, ...) {
  va_list ap, ap2;
  va_start(ap, fmt);
  va_copy(ap2, ap);
  int n = vsnprintf(NULL, 0, fmt, ap);
  va_end(ap);
  char *s = (char *)GC_MALLOC_ATOMIC((size_t)n + 1);
  vsnprintf(s, (size_t)n + 1, fmt, ap2);
  va_end(ap2);
  return s;
}
char *scat(const char *a, const char *b) {
  size_t la = strlen(a), lb = strlen(b);
  char *s = (char *)GC_MALLOC_ATOMIC(la + lb + 1);
  memcpy(s, a, la); memcpy(s + la, b, lb); s[la + lb] = 0;
  return s;
}
char *scat3(const char *a, const char *b, const char *c) { return scat(scat(a, b), c); }
char *ssub(const char *s, int from, int len) {
  char *r = (char *)GC_MALLOC_ATOMIC((size_t)len + 1);
  memcpy(r, s + from, (size_t)len); r[len] = 0;
  return r;
}
char *sjoin(L *parts, const char *sep) {
  Buf *b = bnew();
  for (int first = 1; parts; parts = parts->t, first = 0) { if (!first) badd(b, sep); badd(b, (const char *)parts->h); }
  return bstr(b);
}
int starts_with(const char *s, const char *p) { return strncmp(s, p, strlen(p)) == 0; }
int ends_with(const char *s, const char *p) { size_t ls = strlen(s), lp = strlen(p); return ls >= lp && !strcmp(s + ls - lp, p); }
int find_sub(const char *s, const char *p, int start) {
  const char *r = strstr(s + start, p);
  return r ? (int)(r - s) : -1;
}
int rfind_sub(const char *s, const char *p) {
  int ls = (int)strlen(s), lp = (int)strlen(p);
  for (int i = ls - lp; i >= 0; i--) if (!strncmp(s + i, p, (size_t)lp)) return i;
  return -1;
}
int contains_sub(const char *s, const char *p) { return strstr(s, p) != NULL; }
L *split_on(const char *s, const char *sep) {
  int lp = (int)strlen(sep);
  L *out = NULL;
  int start = 0;
  for (;;) {
    int k = find_sub(s, sep, start);
    if (k < 0) { out = cons(ssub(s, start, (int)strlen(s) - start), out); break; }
    out = cons(ssub(s, start, k - start), out);
    start = k + lp;
  }
  return lrev(out);
}
int cp_is_ws(int c) {
  return (c >= 9 && c <= 13) || c == 0x20 || c == 0x85 || c == 0xA0 || c == 0x1680 || (c >= 0x2000 && c <= 0x200A) || c == 0x2028 || c == 0x2029 ||
         c == 0x202F || c == 0x205F || c == 0x3000;
}
L *split_ws(const char *s) {
  int n; int *cs = decode(s, &n);
  L *out = NULL; int start = -1;
  for (int i = 0; i < n; i++) {
    if (cp_is_ws(cs[i])) { if (start >= 0) { out = cons(encode_range(cs, start, i), out); start = -1; } }
    else if (start < 0) start = i;
  }
  if (start >= 0) out = cons(encode_range(cs, start, n), out);
  return lrev(out);
}
char *strip(const char *s) {
  int n; int *cs = decode(s, &n);
  int lo = 0, hi = n;
  while (lo < hi && cp_is_ws(cs[lo])) lo++;
  while (hi > lo && cp_is_ws(cs[hi - 1])) hi--;
  return encode_range(cs, lo, hi);
}
const char *basename_of(const char *p) { const char *r = strrchr(p, '/'); return r ? r + 1 : p; }

int *decode(const char *s, int *np) {
  int len = (int)strlen(s);
  int *out = (int *)GC_MALLOC_ATOMIC(sizeof(int) * (size_t)(len + 1));
  int k = 0, i = 0;
  while (i < len) {
    unsigned c = (unsigned char)s[i];
    int l, v;
    if (c < 0x80) { l = 1; v = (int)c; }
    else if (c < 0xE0) { l = 2; v = (int)(c & 0x1F); }
    else if (c < 0xF0) { l = 3; v = (int)(c & 0x0F); }
    else { l = 4; v = (int)(c & 0x07); }
    for (int j = 1; j < l; j++) if (i + j < len) v = (v << 6) | ((unsigned char)s[i + j] & 0x3F);
    out[k++] = v;
    i += l;
  }
  *np = k;
  return out;
}
char *encode_range(const int *cs, int lo, int hi) {
  Buf *b = bnew();
  for (int i = lo; i < hi; i++) baddcp(b, cs[i]);
  return bstr(b);
}
char *cp_string(int c) { Buf *b = bnew(); baddcp(b, c); return bstr(b); }
int utf8_error_at(const char *s, int n) {
  int i = 0;
  while (i < n) {
    unsigned c = (unsigned char)s[i];
#define CONT(k) (i + (k) < n && (((unsigned char)s[i + (k)]) & 0xC0) == 0x80)
    if (c < 0x80) i++;
    else if (c >= 0xC2 && c < 0xE0 && CONT(1)) i += 2;
    else if (c >= 0xE0 && c < 0xF0 && CONT(1) && CONT(2)) {
      unsigned c1 = (unsigned char)s[i + 1];
      if ((c == 0xE0 && c1 < 0xA0) || (c == 0xED && c1 >= 0xA0)) return i;
      i += 3;
    } else if (c >= 0xF0 && c < 0xF5 && CONT(1) && CONT(2) && CONT(3)) {
      unsigned c1 = (unsigned char)s[i + 1];
      if ((c == 0xF0 && c1 < 0x90) || (c == 0xF4 && c1 >= 0x90)) return i;
      i += 4;
    } else return i;
#undef CONT
  }
  return -1;
}

/* ------------------------------------------------------------------ hash tables */
static uint64_t hash_str(const char *s) { uint64_t h = 1469598103934665603ULL; for (; *s; s++) { h ^= (unsigned char)*s; h *= 1099511628211ULL; } return h; }
Hash *hnew(void) {
  Hash *h = NEW(Hash);
  h->cap = 16; h->keys = NEWN(char *, 16); h->vals = NEWN(void *, 16);
  h->nslots = 32; h->slots = (int *)GC_MALLOC_ATOMIC(sizeof(int) * 32);
  for (int i = 0; i < 32; i++) h->slots[i] = -1;
  return h;
}
static int hfind(Hash *h, const char *k) {
  uint64_t x = hash_str(k);
  int i = (int)(x & (uint64_t)(h->nslots - 1));
  while (h->slots[i] >= 0) {
    if (!strcmp(h->keys[h->slots[i]], k)) return h->slots[i];
    i = (i + 1) & (h->nslots - 1);
  }
  return -1;
}
void *hget(Hash *h, const char *k) { int i = hfind(h, k); return i < 0 ? NULL : h->vals[i]; }
int hhas(Hash *h, const char *k) { return hfind(h, k) >= 0; }
static void hrehash(Hash *h, int nslots) {
  h->nslots = nslots;
  h->slots = (int *)GC_MALLOC_ATOMIC(sizeof(int) * (size_t)nslots);
  for (int i = 0; i < nslots; i++) h->slots[i] = -1;
  for (int j = 0; j < h->n; j++) {
    int i = (int)(hash_str(h->keys[j]) & (uint64_t)(nslots - 1));
    while (h->slots[i] >= 0) i = (i + 1) & (nslots - 1);
    h->slots[i] = j;
  }
}
void hset(Hash *h, const char *k, void *v) {
  int i = hfind(h, k);
  if (i >= 0) { h->vals[i] = v; return; }
  if (h->n == h->cap) {
    h->cap *= 2;
    char **nk = NEWN(char *, h->cap); void **nv = NEWN(void *, h->cap);
    memcpy(nk, h->keys, sizeof(char *) * (size_t)h->n); memcpy(nv, h->vals, sizeof(void *) * (size_t)h->n);
    h->keys = nk; h->vals = nv;
  }
  h->keys[h->n] = (char *)k; h->vals[h->n] = v; h->n++;
  if (h->n * 2 > h->nslots) hrehash(h, h->nslots * 2);
  else {
    int s = (int)(hash_str(k) & (uint64_t)(h->nslots - 1));
    while (h->slots[s] >= 0) s = (s + 1) & (h->nslots - 1);
    h->slots[s] = h->n - 1;
  }
}
Hash *hcopy(Hash *h) {
  Hash *c = NEW(Hash);
  *c = *h;
  c->keys = NEWN(char *, h->cap); c->vals = NEWN(void *, h->cap);
  memcpy(c->keys, h->keys, sizeof(char *) * (size_t)h->n); memcpy(c->vals, h->vals, sizeof(void *) * (size_t)h->n);
  c->slots = (int *)GC_MALLOC_ATOMIC(sizeof(int) * (size_t)h->nslots);
  memcpy(c->slots, h->slots, sizeof(int) * (size_t)h->nslots);
  return c;
}
void hclear(Hash *h) {
  h->n = 0;
  for (int i = 0; i < h->nslots; i++) h->slots[i] = -1;
}

/* ------------------------------------------------------------------ errors */
Handler *hstack = NULL;
Err cur_err;
void raise_err(int kind, const char *msg) {
  if (!hstack) { fprintf(stderr, "cimo: %s\n", msg); exit(1); }
  Handler *h = hstack;
  hstack = h->prev;
  cur_err.kind = kind; cur_err.msg = (char *)msg;
  longjmp(h->jb, 1);
}
void parse_err(const char *msg) { raise_err(E_PARSE, msg); }
void print_err(const char *msg) { raise_err(E_PRINT, msg); }
void eval_err(const char *msg) { raise_err(E_EVAL, msg); }
void class_err(const char *msg) { raise_err(E_CLASS, msg); }

/* ------------------------------------------------------------------ big integers */
static Big *mkbig(int neg, uint32_t *d, int n) {
  while (n > 0 && d[n - 1] == 0) n--;
  Big *b = NEW(Big);
  b->n = n; b->d = d; b->neg = neg && n > 0;
  return b;
}
static uint32_t *newlimbs(int n) { return (uint32_t *)GC_MALLOC_ATOMIC(sizeof(uint32_t) * (size_t)(n > 0 ? n : 1)); }
Big *big_zero(void) { return mkbig(0, newlimbs(1), 0); }
Big *big_one(void) { uint32_t *d = newlimbs(1); d[0] = 1; return mkbig(0, d, 1); }
Big *big_of_i64(int64_t v) {
  uint64_t m = v < 0 ? (uint64_t)0 - (uint64_t)v : (uint64_t)v;
  uint32_t *d = newlimbs(2);
  d[0] = (uint32_t)m; d[1] = (uint32_t)(m >> 32);
  return mkbig(v < 0, d, 2);
}
static int cmp_mag(uint32_t *a, int na, uint32_t *b, int nb) {
  if (na != nb) return na < nb ? -1 : 1;
  for (int i = na - 1; i >= 0; i--) if (a[i] != b[i]) return a[i] < b[i] ? -1 : 1;
  return 0;
}
static Big *add_mag(Big *a, Big *b, int neg) {
  Big *l = a->n >= b->n ? a : b, *s = a->n >= b->n ? b : a;
  uint32_t *d = newlimbs(l->n + 1);
  uint64_t carry = 0;
  for (int i = 0; i < l->n; i++) {
    uint64_t t = (uint64_t)l->d[i] + (i < s->n ? s->d[i] : 0) + carry;
    d[i] = (uint32_t)t; carry = t >> 32;
  }
  d[l->n] = (uint32_t)carry;
  return mkbig(neg, d, l->n + 1);
}
static Big *sub_mag(Big *a, Big *b, int neg) {   /* |a| >= |b| */
  uint32_t *d = newlimbs(a->n);
  int64_t borrow = 0;
  for (int i = 0; i < a->n; i++) {
    int64_t t = (int64_t)a->d[i] - borrow - (i < b->n ? (int64_t)b->d[i] : 0);
    if (t < 0) { t += ((int64_t)1 << 32); borrow = 1; } else borrow = 0;
    d[i] = (uint32_t)t;
  }
  return mkbig(neg, d, a->n);
}
Big *big_neg(Big *a) { return mkbig(!a->neg, a->d, a->n); }
Big *big_add(Big *a, Big *b) {
  if (a->neg == b->neg) return add_mag(a, b, a->neg);
  int c = cmp_mag(a->d, a->n, b->d, b->n);
  if (c == 0) return big_zero();
  return c > 0 ? sub_mag(a, b, a->neg) : sub_mag(b, a, b->neg);
}
Big *big_sub(Big *a, Big *b) { return big_add(a, big_neg(b)); }
Big *big_mul(Big *a, Big *b) {
  if (a->n == 0 || b->n == 0) return big_zero();
  uint32_t *d = newlimbs(a->n + b->n);
  memset(d, 0, sizeof(uint32_t) * (size_t)(a->n + b->n));
  for (int i = 0; i < a->n; i++) {
    uint64_t carry = 0;
    for (int j = 0; j < b->n; j++) {
      uint64_t t = (uint64_t)a->d[i] * b->d[j] + d[i + j] + carry;
      d[i + j] = (uint32_t)t; carry = t >> 32;
    }
    d[i + b->n] = (uint32_t)carry;
  }
  return mkbig(a->neg != b->neg, d, a->n + b->n);
}
int big_is_zero(Big *a) { return a->n == 0; }
int big_is_neg(Big *a) { return a->neg; }
int big_is_odd(Big *a) { return a->n > 0 && (a->d[0] & 1); }
static Big *shr_mag(Big *a, int n, int neg) {
  int limbs = n / 32, bits = n % 32;
  if (limbs >= a->n) return big_zero();
  int m = a->n - limbs;
  uint32_t *d = newlimbs(m);
  for (int i = 0; i < m; i++) {
    uint32_t lo = a->d[limbs + i] >> bits;
    uint32_t hi = (bits && i + 1 < m) ? a->d[limbs + i + 1] << (32 - bits) : 0;
    d[i] = lo | hi;
  }
  return mkbig(neg, d, m);
}
static Big *shl_mag(Big *a, int n, int neg) {
  if (a->n == 0) return big_zero();
  int limbs = n / 32, bits = n % 32;
  uint32_t *d = newlimbs(a->n + limbs + 1);
  memset(d, 0, sizeof(uint32_t) * (size_t)(a->n + limbs + 1));
  for (int i = 0; i < a->n; i++) {
    uint64_t v = (uint64_t)a->d[i] << bits;
    d[limbs + i] |= (uint32_t)v;
    d[limbs + i + 1] |= (uint32_t)(v >> 32);
  }
  return mkbig(neg, d, a->n + limbs + 1);
}
Big *big_half(Big *a) { return shr_mag(a, 1, a->neg); }
int big_cmp(Big *a, Big *b) {
  int sa = a->n == 0 ? 0 : (a->neg ? -1 : 1), sb = b->n == 0 ? 0 : (b->neg ? -1 : 1);
  if (sa != sb) return sa < sb ? -1 : 1;
  if (sa == 0) return 0;
  int c = cmp_mag(a->d, a->n, b->d, b->n);
  return sa > 0 ? c : -c;
}
static int bit_len(Big *a) {
  if (a->n == 0) return 0;
  uint32_t top = a->d[a->n - 1];
  int l = 32 - __builtin_clz(top);
  return (a->n - 1) * 32 + l;
}
static int bit_at(Big *a, int i) { int l = i / 32; return l < a->n && ((a->d[l] >> (i % 32)) & 1); }
static uint32_t divmod_small(Big *a, uint32_t dv, Big **q) {
  uint32_t *d = newlimbs(a->n);
  uint64_t rem = 0;
  for (int i = a->n - 1; i >= 0; i--) {
    uint64_t cur = (rem << 32) | a->d[i];
    d[i] = (uint32_t)(cur / dv); rem = cur % dv;
  }
  *q = mkbig(0, d, a->n);
  return (uint32_t)rem;
}
void big_divrem(Big *a, Big *b, Big **q, Big **r) {
  if (b->n == 0) eval_err("division by zero");
  if (cmp_mag(a->d, a->n, b->d, b->n) < 0) { *q = big_zero(); *r = a; return; }
  if (b->n == 1) {
    Big *qq; uint32_t rm = divmod_small(a, b->d[0], &qq);
    uint32_t *rd = newlimbs(1); rd[0] = rm;
    *q = mkbig(a->neg != b->neg, qq->d, qq->n);
    *r = mkbig(a->neg, rd, 1);
    return;
  }
  int nbits = bit_len(a);
  uint32_t *qd = newlimbs(a->n);
  memset(qd, 0, sizeof(uint32_t) * (size_t)a->n);
  Big *rem = big_zero(), *bb = mkbig(0, b->d, b->n);
  for (int i = nbits - 1; i >= 0; i--) {
    rem = shl_mag(rem, 1, 0);
    if (bit_at(a, i)) {
      if (rem->n == 0) { uint32_t *d = newlimbs(1); d[0] = 1; rem = mkbig(0, d, 1); }
      else { uint32_t *d = newlimbs(rem->n); memcpy(d, rem->d, sizeof(uint32_t) * (size_t)rem->n); d[0] |= 1; rem = mkbig(0, d, rem->n); }
    }
    if (cmp_mag(rem->d, rem->n, bb->d, bb->n) >= 0) { rem = sub_mag(rem, bb, 0); qd[i / 32] |= (uint32_t)1 << (i % 32); }
  }
  *q = mkbig(a->neg != b->neg, qd, a->n);
  *r = mkbig(a->neg, rem->d, rem->n);
}
Big *big_gcd(Big *a, Big *b) {
  a = mkbig(0, a->d, a->n); b = mkbig(0, b->d, b->n);
  while (b->n) { Big *q, *r; big_divrem(a, b, &q, &r); a = b; b = r; }
  return a;
}
Big *big_parse_dec(const char *s) {
  Big *r = big_zero();
  int n = (int)strlen(s), i = 0;
  while (i < n) {
    int len = 0; uint32_t k = 0, p = 1;
    while (i + len < n && len < 9 && s[i + len] >= '0' && s[i + len] <= '9') { k = k * 10 + (uint32_t)(s[i + len] - '0'); p *= 10; len++; }
    if (len == 0) { i++; continue; }
    Big *pb = big_of_i64(p), *kb = big_of_i64(k);
    r = big_add(big_mul(r, pb), kb);
    i += len;
  }
  return r;
}
Big *big_pow10(int k) { Big *r = big_one(), *ten = big_of_i64(10); for (int i = 0; i < k; i++) r = big_mul(r, ten); return r; }
char *big_to_dec(Big *a) {
  if (a->n == 0) return "0";
  L *chunks = NULL;
  Big *cur = mkbig(0, a->d, a->n);
  while (cur->n) {
    Big *q; uint32_t r = divmod_small(cur, 1000000000u, &q);
    chunks = cons((void *)(uintptr_t)r, chunks);
    cur = q;
  }
  Buf *b = bnew();
  if (a->neg) baddc(b, '-');
  badd(b, xfmt("%u", (unsigned)(uintptr_t)chunks->h));
  for (L *c = chunks->t; c; c = c->t) badd(b, xfmt("%09u", (unsigned)(uintptr_t)c->h));
  return bstr(b);
}
int big_to_i64(Big *a, int64_t *out) {
  if (a->n > 2) return 0;
  uint64_t m = (a->n > 0 ? a->d[0] : 0) | ((uint64_t)(a->n > 1 ? a->d[1] : 0) << 32);
  if (a->neg) { if (m > (uint64_t)INT64_MAX + 1) return 0; *out = (int64_t)(0 - m); return 1; }
  if (m > (uint64_t)INT64_MAX) return 0;
  *out = (int64_t)m;
  return 1;
}
static int low_bits_nonzero(Big *a, int n) {
  int full = n / 32;
  for (int i = 0; i < full && i < a->n; i++) if (a->d[i]) return 1;
  int rem = n % 32;
  return rem > 0 && full < a->n && (a->d[full] & (((uint32_t)1 << rem) - 1)) != 0;
}
/* the nearest double (ties to even) to num/den (den > 0) */
double big_ratio_to_double(Big *num, Big *den) {
  if (num->n == 0) return 0.0;
  int neg = num->neg;
  Big *a = mkbig(0, num->d, num->n);
  int shift = 55 - (bit_len(a) - bit_len(den));
  Big *n, *d;
  if (shift >= 0) { n = shl_mag(a, shift, 0); d = den; } else { n = a; d = shl_mag(den, -shift, 0); }
  Big *q, *rm;
  big_divrem(n, d, &q, &rm);
  int qbits = bit_len(q);
  int sticky = rm->n != 0;
  int exp2 = qbits - 1 - shift;
  int keep = exp2 >= -1022 ? 53 : 53 - (-1022 - exp2);
  if (keep <= 0) return neg ? -0.0 : 0.0;
  int drop = qbits - keep;
  int qb = qbits;
  if (drop > 0) {
    int half_bit = bit_at(q, drop - 1);
    int below = low_bits_nonzero(q, drop - 1) || sticky;
    Big *m = shr_mag(q, drop, 0);
    if (half_bit && (below || big_is_odd(m))) m = big_add(m, big_one());
    if (bit_len(m) > keep) { m = shr_mag(m, 1, 0); exp2++; }
    q = m; qb = keep;
  }
  int64_t mant = 0;
  big_to_i64(q, &mant);
  double x = ldexp((double)mant, exp2 - (qb - 1));
  return neg ? -x : x;
}

/* ------------------------------------------------------------------ the base i-1 */
GI val_digits(Digits ds) {
  Big *sa = big_zero(), *sb = big_zero(), *pa = big_one(), *pb = big_zero();
  for (int i = 0; i < ds.n; i++) {
    if (ds.d[i]) { sa = big_add(sa, pa); sb = big_add(sb, pb); }
    Big *na = big_neg(big_add(pa, pb)), *nb = big_sub(pa, pb);
    pa = na; pb = nb;
  }
  GI g = { sa, sb };
  return g;
}
int val_digits_small(Digits ds, int64_t *re, int64_t *im) {
  int e = ds.n;
  while (e > 0 && ds.d[e - 1] == 0) e--;
  if (e > 100) return 0;
  int64_t sa = 0, sb = 0, pa = 1, pb = 0;
  for (int i = 0; i < e; i++) {
    if (ds.d[i]) { sa += pa; sb += pb; }
    int64_t na = -pa - pb, nb = pa - pb;
    pa = na; pb = nb;
  }
  *re = sa; *im = sb;
  return 1;
}
Digits to_digits(GI g) {
  Big *x = g.re, *y = g.im;
  Buf *out = bnew();
  while (!(big_is_zero(x) && big_is_zero(y))) {
    int d = big_is_odd(big_add(x, y));
    Big *x1 = d ? big_sub(x, big_one()) : x;
    Big *nx = big_half(big_add(big_neg(x1), y));
    Big *ny = big_half(big_sub(big_neg(x1), y));
    baddc(out, (char)d);
    x = nx; y = ny;
  }
  Digits r = { out->n, (unsigned char *)out->s };
  return r;
}
Digits to_digits_i64(int64_t x, int64_t y) {
  Buf *out = bnew();
  while (!(x == 0 && y == 0)) {
    int d = ((x + y) & 1) != 0;
    int64_t x1 = d ? x - 1 : x;
    int64_t nx = (-x1 + y) / 2, ny = (-x1 - y) / 2;
    baddc(out, (char)d);
    x = nx; y = ny;
  }
  Digits r = { out->n, (unsigned char *)out->s };
  return r;
}
char *numeral(Digits ds) {
  if (ds.n == 0) return "0";
  char *s = (char *)GC_MALLOC_ATOMIC((size_t)ds.n + 1);
  for (int i = 0; i < ds.n; i++) s[i] = ds.d[ds.n - 1 - i] ? '1' : '0';
  s[ds.n] = 0;
  return s;
}
char *int_numeral_text(int64_t n) { return numeral(to_digits_i64(n, 0)); }
char *big_numeral_text(Big *n) { GI g = { n, big_zero() }; return numeral(to_digits(g)); }
Digits trim_digits(Digits ds) { int e = ds.n; while (e > 0 && ds.d[e - 1] == 0) e--; Digits r = { e, ds.d }; return r; }

static int py_printable(int c) {
  if (c == ' ') return 1;
  if (c < 0x20 || (c >= 0x7F && c <= 0x9F) || cp_is_ws(c)) return 0;
  return !(c == 0xAD || (c >= 0x600 && c <= 0x605) || c == 0x61C || c == 0x6DD || c == 0x70F || c == 0x180E || (c >= 0x200B && c <= 0x200F) ||
           (c >= 0x202A && c <= 0x202E) || (c >= 0x2060 && c <= 0x2064) || (c >= 0x2066 && c <= 0x206F) || c == 0xFEFF || (c >= 0xFFF9 && c <= 0xFFFB) ||
           (c >= 0xE000 && c <= 0xF8FF) || (c >= 0xF0000 && c <= 0x10FFFF));
}
char *py_repr(const char *s) {
  int n; int *cs = decode(s, &n);
  int sq = 0, dq = 0;
  for (int i = 0; i < n; i++) { if (cs[i] == '\'') sq = 1; if (cs[i] == '"') dq = 1; }
  int q = (sq && !dq) ? '"' : '\'';
  Buf *b = bnew();
  baddc(b, (char)q);
  for (int i = 0; i < n; i++) {
    int c = cs[i];
    if (c == q) { baddc(b, '\\'); baddc(b, (char)c); }
    else if (c == '\\') badd(b, "\\\\");
    else if (c == '\n') badd(b, "\\n");
    else if (c == '\r') badd(b, "\\r");
    else if (c == '\t') badd(b, "\\t");
    else if (py_printable(c)) baddcp(b, c);
    else if (c < 0x100) badd(b, xfmt("\\x%02x", c));
    else if (c < 0x10000) badd(b, xfmt("\\u%04x", c));
    else badd(b, xfmt("\\U%08x", c));
  }
  baddc(b, (char)q);
  return bstr(b);
}
char *fmt_g(int p, double x) {
  if (x == 0.0) return signbit(x) ? "-0" : "0";
  if (isinf(x)) return x < 0 ? "-inf" : "inf";
  if (isnan(x)) return "nan";
  return xfmt("%.*g", p, x);
}
