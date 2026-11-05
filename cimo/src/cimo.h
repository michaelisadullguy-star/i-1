/* cimo.h -- Cimo, the C interpreter of i-1: common types and declarations.  (A port of ocamimo/src; the memory is managed by the Boehm collector.) */
#ifndef CIMO_H
#define CIMO_H
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <setjmp.h>
#include <gc.h>

#define NEW(T) ((T *)GC_MALLOC(sizeof(T)))
#define NEWN(T, n) ((T *)GC_MALLOC(sizeof(T) * (size_t)((n) > 0 ? (n) : 1)))

/* ------------------------------------------------------------------ lists (immutable singly linked) and strings */
typedef struct L { void *h; struct L *t; } L;
L *cons(void *h, L *t);
int llen(L *l);
L *lrev(L *l);
L *lappend(L *a, L *b);
void *lnth(L *l, int i);
L *ltake(int n, L *l);
L *ldrop(int n, L *l);
L *l1(void *x);
L *l2(void *x, void *y);
L *l3(void *x, void *y, void *z);
int lmem_str(const char *s, L *l);

typedef struct Buf { char *s; int n, cap; } Buf;
Buf *bnew(void);
void badd(Buf *b, const char *s);
void baddn(Buf *b, const char *s, int n);
void baddc(Buf *b, char c);
void baddcp(Buf *b, int cp);
char *bstr(Buf *b);

char *xfmt(const char *fmt, ...);
char *scat(const char *a, const char *b);
char *scat3(const char *a, const char *b, const char *c);
char *ssub(const char *s, int from, int len);
char *sjoin(L *parts, const char *sep);
int starts_with(const char *s, const char *p);
int ends_with(const char *s, const char *p);
int find_sub(const char *s, const char *p, int start);   /* -1 if none (byte offset) */
int rfind_sub(const char *s, const char *p);
int contains_sub(const char *s, const char *p);
L *split_on(const char *s, const char *sep);
L *split_ws(const char *s);
char *strip(const char *s);
const char *basename_of(const char *p);
int cp_is_ws(int c);

int *decode(const char *s, int *n);      /* the code points of a UTF-8 string */
char *encode_range(const int *cs, int lo, int hi);
char *cp_string(int c);
int utf8_error_at(const char *s, int n);   /* byte offset of the first invalid sequence, or -1 */

/* hash tables with string keys; iteration in insertion order */
typedef struct Hash { char **keys; void **vals; int n, cap; int *slots; int nslots; } Hash;
Hash *hnew(void);
void *hget(Hash *h, const char *k);
int hhas(Hash *h, const char *k);
void hset(Hash *h, const char *k, void *v);
Hash *hcopy(Hash *h);
void hclear(Hash *h);

/* ------------------------------------------------------------------ errors of the host (try/catch with setjmp) */
enum { E_PARSE = 1, E_UNKNOWN, E_PRINT, E_EVAL, E_CLASS, E_UTF8 };
typedef struct Err { int kind; char *msg; } Err;
typedef struct Handler { jmp_buf jb; struct Handler *prev; } Handler;
extern Handler *hstack;
extern Err cur_err;
void raise_err(int kind, const char *msg) __attribute__((noreturn));
void parse_err(const char *msg) __attribute__((noreturn));
void print_err(const char *msg) __attribute__((noreturn));
void eval_err(const char *msg) __attribute__((noreturn));
void class_err(const char *msg) __attribute__((noreturn));
#define TRY(h) (((h).prev = hstack), (hstack = &(h)), setjmp((h).jb) == 0)
#define ENDTRY(h) (hstack = (h).prev)

/* ------------------------------------------------------------------ big integers */
typedef struct Big { int neg; int n; uint32_t *d; } Big;   /* magnitude little endian, no high zero limbs; zero: n = 0, neg = 0 */
Big *big_zero(void);
Big *big_one(void);
Big *big_of_i64(int64_t v);
Big *big_add(Big *a, Big *b);
Big *big_sub(Big *a, Big *b);
Big *big_mul(Big *a, Big *b);
Big *big_neg(Big *a);
int big_is_zero(Big *a);
int big_is_neg(Big *a);
int big_is_odd(Big *a);
Big *big_half(Big *a);                       /* exact half of an even number */
int big_cmp(Big *a, Big *b);
void big_divrem(Big *a, Big *b, Big **q, Big **r);
Big *big_gcd(Big *a, Big *b);
Big *big_parse_dec(const char *s);
Big *big_pow10(int k);
char *big_to_dec(Big *a);
int big_to_i64(Big *a, int64_t *out);        /* 1 if it fits */
double big_ratio_to_double(Big *num, Big *den);

/* ------------------------------------------------------------------ the base i-1 */
typedef struct GI { Big *re, *im; } GI;
typedef struct Digits { int n; unsigned char *d; } Digits;   /* least significant digit first */
GI val_digits(Digits ds);
int val_digits_small(Digits ds, int64_t *re, int64_t *im);   /* 1 when it fits (at most 100 significant digits) */
Digits to_digits(GI g);
Digits to_digits_i64(int64_t x, int64_t y);
char *numeral(Digits ds);
char *int_numeral_text(int64_t n);
char *big_numeral_text(Big *n);
Digits trim_digits(Digits ds);
char *py_repr(const char *s);
char *fmt_g(int p, double x);

/* ------------------------------------------------------------------ syntax: classes, terms, statements, de Bruijn terms */
enum { TY_K, TY_V, TY_F };
typedef struct Ty { int tag; const char *name; L *args; } Ty;
Ty *ty_k(const char *name, L *args);
Ty *ty_v(const char *name);
Ty *ty_f(void);
Ty *kk(const char *name);
int ty_eq(Ty *a, Ty *b);
int ty_is_k(Ty *t, const char *name);

enum { T_NUM, T_CHR, T_STR, T_VAR, T_APP, T_LAM, T_ASC, T_QUOTE };
typedef struct Param { const char *name; Ty *ty; } Param;     /* ty may be NULL */
typedef struct LocEnt { const char *name; Ty *ty; } LocEnt;
typedef struct Term {
  int tag; const char *s; int c;
  struct Term *f; L *args;      /* App: f applied to args (Term*) */
  L *ps; struct Term *body;     /* Lam: params (Param*), body; Asc/Quote: body = the term */
  Ty *ty; L *loc;               /* Asc: class; Quote: LocEnt* list */
} Term;
Term *t_num(const char *s);
Term *t_chr(int c);
Term *t_str(const char *s);
Term *t_var(const char *n);
Term *t_app(Term *f, L *args);
Term *t_lam(L *ps, Term *body);
Term *t_asc(Term *e, Ty *ty);
Term *t_quote(Term *e, L *loc);
Term *app_s(const char *f, L *args);       /* (f args) with f a variable */
int term_eq(Term *a, Term *b);

enum { S_DEF, S_DECL, S_FACT };
typedef struct Stmt { int kind; const char *name; L *params; Term *body; Ty *ty; } Stmt;   /* Def name params body | Decl name ty | Fact body */
Stmt *s_def(const char *n, L *params, Term *body);
Stmt *s_decl(const char *n, Ty *ty);
Stmt *s_fact(Term *t);

enum { C_V, C_L, C_A, C_G };
typedef struct Core { int tag; int k; struct Core *f, *x; const char *g; } Core;
Core *c_v(int k);
Core *c_l(Core *b);
Core *c_a(Core *f, Core *x);
Core *c_g(const char *g);

L *loc_insert(L *loc, const char *n, Ty *t);
Ty *loc_lookup(L *loc, const char *n);
int loc_member(L *loc, const char *n);
int is_class_var(const char *n);
char *show_type(Ty *t);
char *pp_type(Ty *t);
char *pp_term(Term *t);
char *pp_statement(Stmt *s);
char *repr_term(Term *t);
char *hs_show_list_str(L *xs);
L *parse_statements(const char *text);
Core *erase(L *scope, Term *t);          /* scope: names, innermost first */
Core *erase_def(L *params, Term *body);

/* tokens of the spec notation */
enum { K_NL, K_OPEN, K_CLOSE, K_NUM, K_CHR, K_STR, K_NAME };
typedef struct Tok { int kind; const char *s; int c; } Tok;
L *lex_spec(const char *text);

/* ------------------------------------------------------------------ layers: doc 1, bin notation */
typedef struct Doc1 { Hash *s2b, *b2s; L *local; } Doc1;     /* local: (name, code) pairs, newest first */
Doc1 *doc1_parse(const char *text);
Doc1 *doc1_copy(Doc1 *d);
const char *doc1_code(Doc1 *d, const char *name, int allow_new);
void doc1_add_local(Doc1 *d, const char *a, const char *b);
char *doc1_render(Doc1 *d, L *header);
int is_bin_sym(const char *s);
char *bin_to_spec_text(const char *text, Doc1 *d);
char *spec_statements_to_bin_text(L *sts, Doc1 *d, int allow_new);
char *spec_term_to_bin(const char *text, Doc1 *d);
typedef struct Section { const char *mode; char *text; } Section;
L *split_sections(const char *text, const char *def);
const char *default_notation(const char *path);

/* ------------------------------------------------------------------ hum: doc 2 and the human notation */
typedef struct Entry { const char *hum; L *rhs; const char *role; int has_prec; int prec; } Entry;
typedef struct Doc2 { L *entries; Hash *by_hum; } Doc2;
typedef struct Hum { Doc2 *doc; Hash *infix; Hash *prefix; } Hum;     /* infix: hum -> Entry*; prefix: hum -> Entry* */
Doc2 *doc2_parse(const char *text);
Entry *doc2_find(Doc2 *d, const char *hum, const char **roles);       /* roles: NULL terminated */
Hash *overload_table(Doc2 *d);
Doc2 *doc2_remap(Doc2 *d, Doc1 *d1);
Hum *mk_hum(Doc2 *d);
typedef struct HTok { int kind; const char *s; int c; } HTok;          /* kinds: 1 num 2 str 3 chr 4 id 5 op */
L *lex_hum(const char *line);
char *show_htok(HTok *t);
Term *hum_expr_top(Hum *h, L *ts, L **rest);                           /* hum_expr at minprec 0 with an empty scope */
L *hum_statements(Hum *h, const char *text);
const char *spec_name(Hum *h, const char *name);
int all_bin_chars(const char *s);
Term *type_to_term(Ty *t);

/* ------------------------------------------------------------------ types: the class checker */
typedef struct Checker {
  Hash *classes;    /* name -> int* arity */
  Hash *formers;
  Hash *sigs;       /* name -> L of Ty* */
  L *facts;         /* (Ty*, Ty*) pairs in order */
  L *fact_idx;      /* (normalised sub, L of supers) pairs */
  Hash *eqs;        /* atom -> Ty* */
  L *coercions;     /* names, in order */
  Hash *cov;
  Hash *defined;
  Hash *overloads;  /* key -> L of names */
  L *unknowns;      /* (name, int domain or -1) pairs */
  Hash *user_defined, *raw_taint, *taint;
} Checker;
typedef struct Unknown { const char *name; int dom; } Unknown;
Checker *new_checker(void);
Checker *checker_copy(Checker *c);
Ty *norm(Checker *c, Ty *t);
int leq(Checker *c, Ty *a, Ty *b);
int is_prop(Checker *c, Ty *t);
extern Ty *prop_ty, *bool_ty, *num_ty;
void declare(Checker *c, const char *name, Ty *t);
Stmt *check_statement(Checker *c, Stmt *st, int trusted);     /* NULL: as written; raises on a class error */
void settle_taint(Checker *c, L *defs);
typedef struct TyTerm { Ty *ty; Term *term; } TyTerm;
TyTerm synth(Checker *c, L *loc, Term *t);
Term *fit(Checker *c, Term *term, Ty *got, Ty *want);         /* NULL when it does not fit */
int unknownish(Checker *c, const char *name);
int mentions(Checker *c, Term *t, Hash *bound);
extern const char *rel_r[];
int is_conn_o(const char *n);
const char *conn_o_real(const char *n);
L *sigs_of(Checker *c, const char *n);
Ty *class_domain_check(Checker *c, Ty *t);
void ty_chain(Ty *t, L **ps, Ty **r);

/* ------------------------------------------------------------------ quote */
typedef struct QS { Doc1 *doc; L *needed; } QS;
typedef struct Quoter Quoter;
extern const char *ENV_NAME;
int has_quote(Term *t);
typedef struct StTrust { int trusted; Stmt *st; } StTrust;
Quoter *mk_quoter(Checker *c, L *sts, Doc1 *d0, Doc1 **d1);
Term *quote_replace(Quoter *q, QS *st, Term *t);
Term *quote_table(Quoter *q, QS *st);

/* ------------------------------------------------------------------ core: the evaluator */
typedef struct Th Th;
typedef struct Val Val;
typedef struct Code Code;
typedef struct Arg Arg;
typedef struct LamInfo LamInfo;
typedef struct ThunkInfo ThunkInfo;
typedef struct PapSpec PapSpec;
typedef struct Machine Machine;
enum { P_CONS, P_PAIR, P_CODEN, P_CODES, P_CODEA, P_CODEL, P_CODEV };
enum { V_FUN, V_T, V_F, V_CONS, V_NIL, V_PAIR, V_INT, V_CN, V_CS, V_CA, V_CL, V_CV };
struct Val { int tag; Th *a, *b; int k; };
enum { ST_DONE, ST_DELAYED, ST_CLO, ST_PAP, ST_LAZY, ST_PRIM, ST_RUNNING, ST_FAIL };
struct Th { int st; Val *val; void *info; Th **caps; int ncaps; Th *base; int idx; int prim; Err *err; };
typedef struct Source { int is_term; Core *core; L *ps; Term *term; } Source;   /* Source: a core term, or a checked definition to erase when first needed */
typedef struct DefSrc { const char *name; Source *src; } DefSrc;
typedef struct Extra { const char *name; Th *th; } Extra;
Machine *machine_build(L *defs, L *extra);
Th *machine_global(Machine *m, const char *g);               /* raises when undefined */
Th *th_fail(int kind, const char *msg);
Val *m_apply_whnf(Machine *m, Th *f, Th **args, int n);
Th *m_app(Machine *m, Th *f, Th **args, int n);
Th *m_call_g(Machine *m, const char *f, Th **args, int n);
int m_to_bool(Machine *m, Th *v);
Val *m_cell_or_nil(Machine *m, Th *v);
int m_to_ord(Machine *m, Th *v);
Digits m_to_list(Machine *m, Th *v);
void m_to_pair(Machine *m, Th *v, Th **a, Th **b);
Th *m_stream_nth(Machine *m, Th *v, int n);
Th *m_list_value(Machine *m, Digits ds);
GI m_gi_of(Machine *m, Th *v);
Th *m_vt(Machine *m);
Th *m_vf(Machine *m);
Th **m_code_cbs(Machine *m);

/* ------------------------------------------------------------------ program */
typedef struct Triple { const char *file; Stmt *st; int trusted; } Triple;
typedef struct ErrRec { const char *file; const char *what; const char *msg; } ErrRec;
typedef struct Program {
  Doc1 *doc1; Doc2 *doc2; Hum *hum;
  Triple *statements; int nstat, cstat;
  Checker *checker;
  Stmt **resolved;
  L *errors;                  /* ErrRec*, in order */
  Hash *notation_of;
  const char *out_mode;
  int pre_count;
  L *user_defs;               /* Core* with names: DefSrc* */
  Hash *defined;
  Machine *machine;
} Program;
typedef struct SourceFile { const char *path; const char *text; } SourceFile;
Program *load_program(L *files, L *trusted_paths, int with_prelude);
void program_build(Program *p);
L *program_missing(Program *p);
L *user_statements(Program *p);
char *spec_text(Program *p);
char *bin_text(Program *p);
char *local_table(Program *p);
Th *program_val(Program *p, const char *n);

/* ------------------------------------------------------------------ output */
typedef struct Printer { Program *p; const char *mode; int n; } Printer;
extern const char *MODES[];
char *show_value(Printer *pr, Th *v, Ty *cls);
const char *run_main(Program *p, const char *mode0, int n, void (*write)(const char *));   /* n < 0: not given */
char *text_of(Printer *pr, Th *v);

/* data_gen.c */
extern const char *DOC1, *DOC2;
extern const char *LIB_NAMES[];
extern const char *LIB_TEXTS[];
#endif
