/* imo_rt.h -- the run-time system of Compimo, the compiler of i-1.
 *
 * A value of i-1 is an untyped lambda term evaluated lazily (call by need).  Here it is a pointer to a heap object:
 *   T_CLO    a function: code, arity, captured variables
 *   T_THUNK  a delayed computation: code, captured variables; when it has been evaluated it is overwritten by T_IND (the value)
 *   T_PAP    a partial application: the function and the arguments held so far (never a PAP of a PAP)
 *   T_DATA   a Scott-encoded constructor applied to its fields: λ k1 … km. kj f1 … fn  (the booleans, the cells of lists, pairs, …)
 *   T_PRIM   a builder of the host (what the decoders apply a language value to);  T_VAL  what such a builder makes
 *   T_PACK   a digit string (a list of Booleans) kept as an array of bytes: what the native arithmetic makes; applied to the two alternatives of a list it behaves as the cells it stands for
 * A value that is evaluated (weak head normal form) is a T_CLO, T_PAP, T_DATA, T_PRIM or T_VAL.
 * Memory: the Boehm collector (libgc); a program that is linked without it (-DIMO_NOGC) never frees.
 */
#ifndef IMO_RT_H
#define IMO_RT_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>

typedef struct Obj Obj;
typedef Obj *V;
typedef V (*Fn)(V *fv, V *a);   /* code of a function: captured variables, arguments */
typedef V (*Th)(V *fv);         /* code of a thunk: captured variables; returns the value (evaluated) */

enum { T_CLO = 1, T_THUNK, T_BLACK, T_IND, T_FAIL, T_PAP, T_DATA, T_PRIM, T_VAL, T_PACK };

typedef struct { uint32_t tag, n; } Hdr;                      /* n: the number of V slots at the end */
typedef struct { uint32_t nf, m, j; } Desc;                   /* a constructor: fields, alternatives, the alternative it selects */
struct Obj { Hdr h; };
typedef struct { Hdr h; uint32_t arity, pad; Fn fn; V fv[]; } Clo;
typedef struct { Hdr h; Th fn; V fv[]; } Thk;                  /* fv[0] is the value after evaluation, so n >= 1 */
typedef struct { Hdr h; V fun; V args[]; } Pap;
typedef struct { Hdr h; const Desc *d; V f[]; } Data;
typedef struct { Hdr h; uint32_t kind, arity; } Prim;
typedef struct { Hdr h; uint32_t kind; int32_t k; V f[2]; } Val;
typedef struct { Hdr h; uint32_t len, pad; const uint8_t *p; V owner; } Pack;   /* a list of Booleans (digits) as bytes: behaves as the list of its digits, least significant first */

/* kinds of host builders and of what they make */
enum { PK_CONS, PK_PAIR, PK_CN, PK_CS, PK_CA, PK_CL, PK_CV };
enum { VK_FUN = 0, VK_T, VK_F, VK_NIL, VK_CONS, VK_PAIR, VK_INT, VK_CN, VK_CS, VK_CA, VK_CL, VK_CV };

void *rt_alloc(size_t bytes);                                  /* zeroed, scanned by the collector */
V rt_force(V t);
static inline V EVAL(V v) {
  for (;;) {
    switch (v->h.tag) {
      case T_IND: v = ((Thk *)v)->fv[0]; continue;
      case T_THUNK: case T_BLACK: case T_FAIL: return rt_force(v);
      default: return v;
    }
  }
}
V rt_apply(V f, int n, V *a);
V rt_pap(V f, int n, V *a);
V rt_mkclo(Fn fn, uint32_t arity, uint32_t nfv, V *fv);
V rt_failobj(int kind, const char *msg);
void rt_register(const char *name, V *slot);
V rt_mkthunk(Th fn, uint32_t nfv, V *fv);
V rt_mkdata(const Desc *d, uint32_t nf, V *f);
V rt_data0(const Desc *d);
void rt_error(int kind, const char *fmt, ...) __attribute__((noreturn));
extern V RT_T, RT_F;

#ifdef IMO_PROF
extern uint64_t rt_prof[];
#define PROF(i) (rt_prof[i]++)
#else
#define PROF(i) ((void)0)
#endif
/* natives: the arithmetic on digit strings of the prelude (lib/number.imo, lib/arith.imo) computed in machine words; each returns NULL when it cannot
   (a number of more than 200 digits, a product that overflows): the compiled definition of the prelude is then used */
V rt_mkpack(const uint8_t *d, int n);
V nat_addz(V x, V y); V nat_subz(V x, V y); V nat_mulz(V x, V y); V nat_negz(V x); V nat_eqv(V x, V y); V nat_canon(V x); V nat_isz(V x);
V nat_cmpr(V x); V nat_cmpi(V x);
#define A1(f, x) rt_apply((f), 1, (V[]){(x)})
#define A2(f, x, y) rt_apply((f), 2, (V[]){(x), (y)})
#define A3(f, x, y, z) rt_apply((f), 3, (V[]){(x), (y), (z)})

#endif
