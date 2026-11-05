/* main.c -- command line of Cimo, the C interpreter of i-1 (port of ocamimo/src/main.ml and rustimo/src/main.rs).
     cimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  cimo FILE...)
     cimo check   FILE...                                load the prelude and FILE(s), run the class checker
     cimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table
     cimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class (value, stream element N, tree, string, Bool)
     cimo text    FILE... NAME                           evaluate NAME as a String and print it */
#include "cimo.h"
#include <sys/stat.h>
#include <unistd.h>

static const char *USAGE =
  "cimo -- Cimo, the C interpreter of i-1 (same commands and output as Pymo, Haskimo, Rustimo, OCamimo and Schimo)\n\n"
  "  cimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  cimo FILE...)\n"
  "  cimo check   FILE...                                load the prelude and FILE(s), run the class checker\n"
  "  cimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table\n"
  "  cimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class (value, stream element N, tree, string, Bool)\n"
  "  cimo text    FILE... NAME                           evaluate NAME as a String and print it\n\n"
  "`run` prints main ∶ 𝕊 as text, a list or stream of strings line by line, and any other value as a normal-form term in the output\n"
  "notation: --out, else an `@out bin|spec|hum` line in the program, else the notation main is written in.  --n N picks the stream\n"
  "element shown for a stream (default 10), or the number of lines of a stream of strings.\n\n"
  "FILE notation follows the extension:  x.imo / x.spec.imo = spec,  x.hum.imo = human,  x.bin.imo = binary (prelude.bin.imo is trusted).\n";

static void put(const char *s) { fputs(s, stdout); }
static void line(const char *s) { fputs(s, stdout); fputc('\n', stdout); }
static int is_file(const char *p) { struct stat sb; return stat(p, &sb) == 0 && S_ISREG(sb.st_mode); }

#include <errno.h>
/* read a file; NULL and a message in *err when it cannot be read or is not valid UTF-8 */
char *read_utf8_file(const char *path, char **err) {
  FILE *f = fopen(path, "rb");
  if (!f) { *err = strerror(errno); return NULL; }
  size_t cap = 1 << 16, n = 0;
  char *buf = (char *)GC_MALLOC_ATOMIC(cap);
  for (;;) {
    size_t r = fread(buf + n, 1, cap - n - 1, f);
    n += r;
    if (r == 0) break;
    if (n + 1 >= cap) { char *nb = (char *)GC_MALLOC_ATOMIC(cap * 2); memcpy(nb, buf, n); buf = nb; cap *= 2; }
  }
  fclose(f);
  buf[n] = 0;
  int at = utf8_error_at(buf, (int)n);
  if (at >= 0) { *err = xfmt("cannot decode byte sequence starting from %d (position %d)", (unsigned char)buf[at], at); return NULL; }
  return buf;
}

static Program *load_files(L *files, int build) {
  L *srcs = NULL;
  for (L *f = files; f; f = f->t) {
    const char *path = (const char *)f->h;
    char *err = NULL;
    char *text = read_utf8_file(path, &err);
    if (!text) {
      if (!is_file(path) && access(path, F_OK) != 0) parse_err(xfmt("%s: openFile: does not exist (No such file or directory)", path));
      if (strstr(err, "cannot decode")) parse_err(xfmt("%s: hGetContents: invalid argument (%s)", path, err));
      parse_err(xfmt("%s: openFile: %s", path, err));
    }
    SourceFile *sf = NEW(SourceFile); sf->path = path; sf->text = text;
    srcs = cons(sf, srcs);
  }
  srcs = lrev(srcs);
  L *prelude = NULL;
  for (L *f = files; f; f = f->t) if (ends_with((const char *)f->h, "prelude.bin.imo")) prelude = cons(f->h, prelude);
  Program *p = load_program(srcs, prelude, prelude == NULL);
  L *missing = program_missing(p);
  if (missing) parse_err(scat("these symbols are used and not defined: ", sjoin(missing, " ")));
  if (build && !p->errors) program_build(p);
  return p;
}
static void report_errors(Program *p) {
  for (L *l = p->errors; l; l = l->t) {
    ErrRec *e = (ErrRec *)l->h;
    line(xfmt("error in %s: %s", basename_of(e->file), starts_with(e->msg, e->what) ? e->msg : xfmt("%s: %s", e->what, e->msg)));
  }
}

/* ------------------------------------------------------------------ values of ℚ[i], as Pymo shows them: a pair of exact rationals */
typedef struct Rat { Big *num, *den; } Rat;
static Rat rat_new(Big *num, Big *den) {
  if (big_is_neg(den)) { num = big_neg(num); den = big_neg(den); }
  Big *g = big_gcd(num, den);
  if (!big_is_zero(g) && big_cmp(g, big_one()) != 0) { Big *q, *r; big_divrem(num, g, &q, &r); num = q; big_divrem(den, g, &q, &r); den = q; }
  Rat r = { num, den };
  return r;
}
typedef struct Q { Rat re, im; } Q;
static Q qval(Machine *m, Th *v) {
  Th *p, *d;
  m_to_pair(m, v, &p, &d);
  GI a = m_gi_of(m, p), b = m_gi_of(m, d);
  Big *n = big_add(big_mul(b.re, b.re), big_mul(b.im, b.im));
  if (big_is_zero(n)) eval_err("Ratio has zero denominator");
  Q q;
  q.re = rat_new(big_add(big_mul(a.re, b.re), big_mul(a.im, b.im)), n);
  q.im = rat_new(big_sub(big_mul(a.im, b.re), big_mul(a.re, b.im)), n);
  return q;
}
static int rat_is_int(Rat r) { return big_cmp(r.den, big_one()) == 0; }
static char *show_frac(Rat r) { return rat_is_int(r) ? big_to_dec(r.num) : xfmt("%s/%s", big_to_dec(r.num), big_to_dec(r.den)); }
static char *qfmt(Machine *m, Th *v) {
  Q q = qval(m, v);
  int im_zero = big_is_zero(q.im.num);
  char *s = im_zero ? show_frac(q.re) : xfmt("%s + %s i", show_frac(q.re), show_frac(q.im));
  char *tail = im_zero ? "" : xfmt(" + %s i", fmt_g(12, big_ratio_to_double(q.im.num, q.im.den)));
  return xfmt("%s   (≈ %s%s)", s, fmt_g(12, big_ratio_to_double(q.re.num, q.re.den)), tail);
}
static char *sfmt(Machine *m, Th *v) {
  Buf *b = bnew();
  Th *cur = v;
  for (;;) {
    Val *c = m_cell_or_nil(m, cur);
    if (c->tag != V_CONS) break;
    Q q = qval(m, c->a);
    Big *t, *r;
    big_divrem(q.re.num, q.re.den, &t, &r);
    int64_t k;
    if (!big_to_i64(t, &k)) k = 0xfffd;
    baddcp(b, (k < 0 || k > 0x10FFFF) ? 0xFFFD : (int)k);
    cur = c->b;
  }
  return bstr(b);
}
static char *tfmt(Program *p, Th *v, int n) {
  Machine *m = p->machine;
  Th *left_f = program_val(p, "◀"), *right_f = program_val(p, "▶");
  Th *is_left = m_app(m, left_f, &v, 1);
  if (m_to_bool(m, is_left)) {
    Th *r = m_app(m, right_f, &v, 1), *a, *b;
    m_to_pair(m, r, &a, &b);
    char *sa = tfmt(p, a, n), *sb = tfmt(p, b, n);
    return xfmt("⟨%s, %s⟩", sa, sb);
  }
  Th *leaf0 = m_app(m, right_f, &v, 1);
  Th *leaf = n >= 0 ? m_stream_nth(m, leaf0, n) : leaf0;
  Q q = qval(m, leaf);
  if (n >= 0) {
    char *re = fmt_g(10, big_ratio_to_double(q.re.num, q.re.den));
    return big_is_zero(q.im.num) ? re : xfmt("%s + %s i", re, fmt_g(10, big_ratio_to_double(q.im.num, q.im.den)));
  }
  return big_is_zero(q.im.num) ? show_frac(q.re) : xfmt("(%s + %s i)", show_frac(q.re), show_frac(q.im));
}
/* evaluate NAME and print it according to its declared class */
static char *show_name(Program *p, const char *name, int n) {
  Checker *c = p->checker;
  Machine *m = p->machine;
  L *sg = sigs_of(c, name);
  if (!sg) eval_err("Prelude.head: empty list");
  Ty *cls = norm(c, (Ty *)sg->h);
  Th *v = program_val(p, name);
  const char *hd = cls->tag == TY_K ? cls->name : "";
  if (cls->tag == TY_K && (!strcmp(hd, "𝔖") || !strcmp(hd, "ℝ"))) {
    int k = n >= 0 ? n : 10;
    return xfmt("element %d of the stream:  %s", k, qfmt(m, m_stream_nth(m, v, k)));
  }
  if (cls->tag == TY_K && !strcmp(hd, "𝔏") && llen(cls->args) == 1 && ty_is_k((Ty *)cls->args->h, "𝕮")) return sfmt(m, v);
  if (cls->tag == TY_K && !strcmp(hd, "𝔗") && llen(cls->args) == 1) {
    int streams = ty_is_k((Ty *)cls->args->h, "𝔖");
    int k = n >= 0 ? n : 10;
    char *body = tfmt(p, v, streams ? k : -1);
    return scat(streams ? xfmt("element %d of each leaf:  ", k) : "", body);
  }
  if (!strcmp(hd, "𝔹")) return m_to_bool(m, v) ? "true" : "false";
  if (contains_sub(show_type(cls), "Ω")) { Printer pr = { p, "hum", 10 }; return show_value(&pr, v, cls); }
  return qfmt(m, v);
}

/* ------------------------------------------------------------------ commands */
/* remove  OPT value  from an argument list */
static L *take_opt(const char *opt, L *args, const char **val) {
  int i = 0, n = llen(args);
  for (L *a = args; a; a = a->t, i++) {
    if (!strcmp((const char *)a->h, opt) && i + 1 < n) { *val = (const char *)lnth(args, i + 1); return lappend(ltake(i, args), ldrop(i + 2, args)); }
  }
  *val = NULL;
  return args;
}
static int read_int(const char *s) {
  char *t = strip(s);
  if (!*t) eval_err("Prelude.read: no parse");
  for (char *c = t; *c; c++) if (*c < '0' || *c > '9') eval_err("Prelude.read: no parse");
  return atoi(t);
}
static int run_cmd(L *args0) {
  const char *o, *nopt;
  L *r1 = take_opt("--out", args0, &o);
  L *rest = take_opt("--n", r1, &nopt);
  if (o) {
    int ok = 0;
    for (int i = 0; MODES[i]; i++) if (!strcmp(MODES[i], o)) ok = 1;
    if (!ok) { line("--out takes one of bin, spec, hum"); return 2; }
  }
  Program *p = load_files(rest, 1);
  if (p->errors) { report_errors(p); return 1; }
  int n = nopt ? read_int(nopt) : -1;
  Handler h;
  if (TRY(h)) { run_main(p, o, n, put); ENDTRY(h); return 0; }
  if (cur_err.kind == E_PRINT) { line(scat("error: ", cur_err.msg)); return 1; }
  raise_err(cur_err.kind, cur_err.msg);
}
static int translate_cmd(L *rest) {
  const char *to = NULL;
  int i = 0, n = llen(rest);
  for (L *a = rest; a; a = a->t, i++) if (!strcmp((const char *)a->h, "--to") && i + 1 < n) { to = (const char *)lnth(rest, i + 1); break; }
  if (!to) eval_err("--to is missing");
  L *files = NULL;
  for (L *a = rest; a; a = a->t) if (strcmp((const char *)a->h, "--to") && strcmp((const char *)a->h, to)) files = cons(a->h, files);
  Program *p = load_files(lrev(files), 0);
  if (p->errors) { report_errors(p); return 1; }
  if (!strcmp(to, "spec")) put(spec_text(p));
  else {
    put(bin_text(p));
    if (p->doc1->local) put(scat("\n", local_table(p)));
  }
  return 0;
}
static int query_cmd(const char *cmd, L *rest) {
  L *files = NULL; const char *name = NULL; int n = -1;
  if (!strcmp(cmd, "check")) files = rest;
  else {
    L *fs = NULL, *tl = NULL;
    for (L *a = rest; a; a = a->t) { if (is_file((const char *)a->h)) fs = cons(a->h, fs); else tl = cons(a->h, tl); }
    files = lrev(fs); tl = lrev(tl);
    if (!tl) parse_err("a name is expected");
    if (tl->t) n = read_int((const char *)tl->t->h);
    name = (const char *)tl->h;
  }
  Program *p = load_files(files, strcmp(cmd, "check"));
  if (p->errors) { report_errors(p); return 1; }
  if (!strcmp(cmd, "check")) { line(xfmt("ok: %d statements checked", llen(user_statements(p)))); return 0; }
  const char *nm = spec_name(p->hum, name ? name : "");
  Handler h;
  char *r = NULL;
  if (TRY(h)) { r = !strcmp(cmd, "text") ? sfmt(p->machine, program_val(p, nm)) : show_name(p, nm, n); ENDTRY(h); line(r); return 0; }
  if (cur_err.kind == E_UNKNOWN || cur_err.kind == E_PRINT) { line(scat("error: ", cur_err.msg)); return 1; }
  raise_err(cur_err.kind, cur_err.msg);
}
static int dispatch(L *args) {
  if (!args) { put(USAGE); return 0; }
  const char *cmd = (const char *)args->h;
  if (!strcmp(cmd, "-h") || !strcmp(cmd, "--help")) { put(USAGE); return 0; }
  int known = !strcmp(cmd, "run") || !strcmp(cmd, "check") || !strcmp(cmd, "eval") || !strcmp(cmd, "text") || !strcmp(cmd, "translate");
  const char *cmd2 = cmd; L *rest = args->t;
  if (!known && is_file(cmd)) { cmd2 = "run"; rest = args; }
  if (!strcmp(cmd2, "run")) return run_cmd(rest);
  if (!strcmp(cmd2, "translate")) return translate_cmd(rest);
  if (!strcmp(cmd2, "check") || !strcmp(cmd2, "eval") || !strcmp(cmd2, "text")) return query_cmd(cmd2, rest);
  put(USAGE);
  return 2;
}
int main(int argc, char **argv) {
  /* the host recursion (reading, checking, printing nested terms) gets the largest stack the system gives: the program starts itself again
     under  ulimit -s unlimited  (the evaluator keeps its own stack on the heap) */
  if (!getenv("CIMO_STACK")) {
    setenv("CIMO_STACK", "1", 1);
    char **nargv = (char **)malloc(sizeof(char *) * (size_t)(argc + 6));
    int k = 0;
    nargv[k++] = (char *)"sh"; nargv[k++] = (char *)"-c";
    nargv[k++] = (char *)"ulimit -s unlimited 2>/dev/null || ulimit -s $(ulimit -H -s) 2>/dev/null; exec \"$0\" \"$@\"";
    nargv[k++] = argv[0];
    for (int i = 1; i < argc; i++) nargv[k++] = argv[i];
    nargv[k] = NULL;
    execv("/bin/sh", nargv);
  }
  GC_INIT();
  GC_set_free_space_divisor(2);
  L *args = NULL;
  for (int i = argc - 1; i >= 1; i--) args = cons(argv[i], args);
  Handler h;
  int code;
  if (TRY(h)) { code = dispatch(args); ENDTRY(h); }
  else { fflush(stdout); fprintf(stderr, "cimo: %s\n", cur_err.msg); code = 1; }
  fflush(stdout);
  return code;
}
