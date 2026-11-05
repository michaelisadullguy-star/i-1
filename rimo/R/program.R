# program.R -- loader / driver for i-1 programs (port of schimo/src/program.rkt).
# A file is read in the notation chosen by its extension (x.bin.imo, x.hum.imo, x.imo = spec) or by section headers (@bin @spec @hum on a line of their own).  Every section is translated
# to spec statements, the whole program is checked by the class checker, and the definitions are run by the evaluator (lazy, call-by-need).  A symbol that the program declares and
# never defines is an UNKNOWN: its class must be a number class.
# The program is an environment: doc1, doc2, hum, statements (a list of list(file, statement, trusted)), checker, resolved (a list aligned with statements; NULL: the statement had an error),
# errors (list of list(file, what, message)), notation_of (env), out_mode, pre_count, pre_checked, user_defs (list of list(name, core)), defined (env), machine.

# ---------------------------------------------------------------- the prelude: read from the repository, parsed and checked once, kept in a cache file
rimo_root <- function() get("RIMO_ROOT", envir = globalenv())
prelude_files <- function(root) {
  man <- split_on(read_utf8(file.path(root, "lib", "MANIFEST")), "\n")
  man <- man[nchar(man) > 0L & !startsWith(man, "⍝")]
  file.path(root, "lib", man)
}
new_program_bare <- function(d1, d2, hum, checker) {
  p <- new.env(hash = FALSE, parent = emptyenv())
  p$doc1 <- d1; p$doc2 <- d2; p$hum <- hum; p$statements <- list(); p$checker <- checker; p$resolved <- list(); p$errors <- list()
  p$notation_of <- new.env(hash = TRUE, parent = emptyenv()); p$out_mode <- NULL; p$pre_count <- 0L; p$pre_checked <- 0L; p$user_defs <- list()
  p$defined <- new.env(hash = TRUE, parent = emptyenv()); p$machine <- NULL
  p
}
new_program <- function(root = rimo_root()) {
  d1 <- doc1_parse(read_utf8(file.path(root, "docs", "doc1.sbl")))
  d2 <- doc2_remap(doc2_parse(read_utf8(file.path(root, "docs", "doc2.sbl"))), d1)
  checker <- new_checker()
  ov <- overload_table(d2)
  for (k in ls(ov, all.names = TRUE)) assign(k, get(k, envir = ov), envir = checker$overloads)
  new_program_bare(d1, d2, mk_hum(d2), checker)
}
cache_dir <- function() { d <- Sys.getenv("RIMO_CACHE", file.path(path.expand("~"), ".cache", "rimo")); dir.create(d, recursive = TRUE, showWarnings = FALSE); d }
prelude_key <- function(root) {
  fs <- c(prelude_files(root), file.path(root, "docs", "doc1.sbl"), file.path(root, "docs", "doc2.sbl"), file.path(root, "lib", "MANIFEST"),
          file.path(rimo_src, c("base.R", "syntax.R", "layers.R", "hum.R", "types.R")))
  tf <- tempfile(); writeLines(paste(unname(tools::md5sum(fs)), collapse = ""), tf)
  k <- unname(tools::md5sum(tf)); unlink(tf); k
}
# a program with the prelude loaded and its statements checked (from the cache when there is one)
prelude_program <- function(root) {
  key <- prelude_key(root)
  file <- file.path(cache_dir(), paste0("prelude-", key, ".rds"))
  if (file.exists(file)) {
    st <- tryCatch(readRDS(file), error = function(e) NULL)
    if (!is.null(st)) {
      p <- new_program_bare(st$doc1, st$doc2, st$hum, st$checker)
      p$statements <- st$statements; p$pre_count <- st$pre_count; p$pre_checked <- st$pre_count
      return(p)
    }
  }
  p <- new_program(root)
  for (f in prelude_files(root)) add_file(p, f, read_utf8(f), TRUE)
  p$pre_count <- length(p$statements)
  for (e in p$statements) check_statement(p$checker, e[[2L]], TRUE)
  p$pre_checked <- p$pre_count
  tmp <- paste0(file, ".", Sys.getpid())
  saveRDS(list(doc1 = p$doc1, doc2 = p$doc2, hum = p$hum, checker = p$checker, statements = p$statements, pre_count = p$pre_count), tmp, compress = FALSE)
  file.rename(tmp, file)
  p
}

# add the text of a file (or of a string) in the given default notation
add_text <- function(p, text, name, trusted, notation) {
  out_mode <- p$out_mode
  lines <- split_on(text, "\n")
  for (i in seq_along(lines)) {
    words <- split_ws(lines[i])
    if (length(words) == 2L && words[1L] == "@out") {
      w <- words[2L]
      if (w %in% c("bin", "spec", "hum")) { out_mode <- w; lines[i] <- "" } else parse_err(sprintf("%s: @out takes bin, spec or hum, not %s", name, w))
    }
  }
  text2 <- paste(lines, collapse = "\n")
  p$out_mode <- out_mode
  for (sec in split_sections(text2, notation)) {
    mode <- sec[[1L]]; chunk <- sec[[2L]]
    sts <- if (mode == "spec") parse_statements(chunk) else if (mode == "bin") parse_statements(bin_to_spec_text(chunk, p$doc1)) else hum_statements(p$hum, chunk)
    if (!trusted) for (st in sts) if (st[[1L]] == "SDef") assign(st[[2L]], mode, envir = p$notation_of)
    for (st in sts) p$statements[[length(p$statements) + 1L]] <- list(name, st, trusted)
  }
}

# add a file; a bin program brings its local symbol table (x.sbl next to x.bin.imo)
add_file <- function(p, path, text, trusted) {
  k <- rfind_sub(path, ".imo")
  before <- if (!is.null(k)) substr(path, 1L, k - 1L) else path
  replace_all <- function(s, a, b) paste(split_on(s, a), collapse = b)
  local <- paste0(replace_all(replace_all(replace_all(before, ".bin", ""), ".hum", ""), ".spec", ""), ".sbl")
  uses_bin <- default_notation(path) == "bin" || contains_sub(paste0("\n", text), "\n@bin")
  if (uses_bin && file.exists(local) && !dir.exists(local)) {
    tbl <- tryCatch(read_utf8(local), bad_utf8 = function(e) stop(host_err("parse", sprintf("%s: %s", local, conditionMessage(e)))))
    for (line in split_on(tbl, "\n")) {
      if (contains_sub(line, " := ") && !starts_with(line, "⍝")) {
        parts <- split_on(line, " := ")
        if (length(parts) != 2L) parse_err(sprintf("bad line in %s", basename_of(local)))
        a <- strip(parts[1L]); b <- strip(parts[2L])
        if (!has_key(p$doc1$s2b, a)) {
          other <- getk(p$doc1$b2s, b)
          if (!is.null(other)) parse_err(sprintf("%s: local code %s for %s is already doc 1's code for %s (doc 1 grew: regenerate the local table with  i1.py translate … --to bin)", basename_of(local), b, a, other))
          doc1_add_local(p$doc1, a, b)
        }
      }
    }
  }
  add_text(p, text, path, trusted, default_notation(path))
}

# ---------------------------------------------------------------- checking
class_or_stmt <- function(ty) {
  r <- ty
  while (r[[1L]] == "K" && r[[2L]] == "→" && length(r[[3L]]) == 2L) r <- r[[3L]][[2L]]
  identical(r, K_("𝒦")) || identical(r, K_("𝒮"))
}
# the names a term refers to (an overloaded name stands for all its candidates)
refs <- function(t, bound, overloads) {
  switch(t[[1L]],
    TVar = { n <- t[[2L]]; if (n %in% bound) character(0) else { o <- getk(overloads, n); if (!is.null(o)) o else n } },
    TApp = { s <- refs(t[[2L]], bound, overloads); for (a in t[[3L]]) s <- union(s, refs(a, bound, overloads)); s },
    TLam = refs(t[[3L]], c(bound, vapply(t[[2L]], function(p) p[[1L]], "")), overloads),
    TAsc = refs(t[[2L]], bound, overloads),
    character(0))
}
# the unknowns (declared by the program, defined nowhere), in declaration order, and a first estimate of which program definitions need their values
unknowns_of <- function(c, stmts, from) {
  defined <- new.env(hash = TRUE, parent = emptyenv())
  for (e in stmts) { s <- e[[2L]]; if (s[[1L]] == "SDef") assign(s[[2L]], TRUE, envir = defined) }
  seen <- new.env(hash = TRUE, parent = emptyenv()); order <- character(0)
  for (e in drop_first(stmts, from)) {
    s <- e[[2L]]
    if (s[[1L]] == "SDecl" && !e[[3L]]) {
      n <- s[[2L]]
      if (has_key(defined, n) || class_or_stmt(s[[3L]]) || has_key(seen, n)) next
      assign(n, TRUE, envir = seen); order <- c(order, n)
    }
  }
  user <- Filter(function(s) s[[1L]] == "SDef", lapply(Filter(function(e) !e[[3L]], drop_first(stmts, from)), function(e) e[[2L]]))
  uses <- list()
  for (d in user) uses[[d[[2L]]]] <- refs(d[[4L]], unlist(d[[3L]]), c$overloads)
  tainted <- order
  repeat {
    nw <- character(0)
    for (n in names(uses)) if (!(n %in% tainted) && any(uses[[n]] %in% tainted)) nw <- c(nw, n)
    if (length(nw) == 0L) break
    tainted <- c(tainted, nw)
  }
  c$unknowns <- lapply(order, function(n) list(n, NULL))
  rm(list = ls(c$user_defined, all.names = TRUE), envir = c$user_defined)
  for (d in user) assign(d[[2L]], TRUE, envir = c$user_defined)
  rm(list = ls(c$raw_taint, all.names = TRUE), envir = c$raw_taint)
  for (n in tainted) if (!(n %in% order)) assign(n, TRUE, envir = c$raw_taint)
  rm(list = ls(c$taint, all.names = TRUE), envir = c$taint)
}

# program-local codes (doc 1 format) for the program's own symbols, assigned when the program is checked and in a fixed order
codes_of <- function(p) {
  order <- vapply(p$checker$unknowns, function(u) u[[1L]], "")
  for (e in p$statements) {
    s <- e[[2L]]
    if (s[[1L]] == "SDecl" && !e[[3L]] && s[[2L]] != env_name && has_key(p$checker$sigs, s[[2L]])) order <- c(order, s[[2L]])
  }
  for (n in order) doc1_code(p$doc1, n, TRUE)
}

# replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝  and add the table of definitions
quote_program <- function(p) {
  sts <- vector("list", length(p$statements))
  for (i in seq_along(p$statements)) sts[[i]] <- list(p$statements[[i]][[3L]], p$resolved[[i]])
  qd <- mk_quoter(p$checker, sts, p$doc1); qr <- qd[[1L]]
  st <- new.env(hash = FALSE, parent = emptyenv()); st$doc <- qd[[2L]]; st$needed <- character(0)
  replaced <- list()
  for (i in seq_along(p$resolved)) {
    r <- p$resolved[[i]]
    if (is.list(r) && r[[1L]] == "SDef" && has_quote(r[[4L]])) replaced[[length(replaced) + 1L]] <- list(i, list("SDef", r[[2L]], r[[3L]], quote_replace(qr, st, r[[4L]])))
  }
  tab <- quote_table(qr, st)
  for (e in replaced) p$resolved[[e[[1L]]]] <- e[[2L]]
  p$doc1 <- st$doc
  env_ty <- K_("𝔏", list(K_("𝔓", list(K_("𝔇"), K_("𝔔")))))
  tryCatch(declare(p$checker, env_name, env_ty), class_err = function(e) eval_err(sprintf("quote: ε⌜⌝ declaration: %s", e$msg)))
  at <- 0L
  while (at < length(p$statements) && p$statements[[at + 1L]][[3L]]) at <- at + 1L
  decl_st <- list("SDecl", env_name, env_ty); def_st <- list("SDef", env_name, list(), tab)
  ins <- function(lst, x) append(lst, list(x), after = at)
  p$statements <- ins(ins(p$statements, list("<quote>", def_st, FALSE)), list("<quote>", decl_st, FALSE))
  p$resolved <- ins(ins(p$resolved, def_st), decl_st)
}

# check the program: class errors are collected in `errors`; the statements that mention a relation on ℝ[i] or an unknown are then written as codes
check_program <- function(p) {
  p$statements <- Filter(function(e) !identical(e[[1L]], "<quote>"), p$statements)
  c <- p$checker
  unknowns_of(c, p$statements, p$pre_checked)
  n <- length(p$statements)
  resolved <- vector("list", n); errors <- list()
  for (i in seq_len(n)) {
    e <- p$statements[[i]]; st <- e[[2L]]
    if (i <= p$pre_checked) { resolved[[i]] <- st; next }
    r <- tryCatch({ nw <- check_statement(c, st, e[[3L]]); if (is.null(nw)) st else nw }, class_err = function(x) x)
    if (inherits(r, "class_err")) {
      what <- switch(st[[1L]], SDef = st[[2L]], SDecl = st[[2L]], pp_statement(st))
      errors[[length(errors) + 1L]] <- list(e[[1L]], what, r$msg)
    } else resolved[[i]] <- r
  }
  defs_for_taint <- list()
  for (i in seq_len(n)) { e <- p$statements[[i]]; r <- resolved[[i]]; if (!e[[3L]] && is.list(r) && r[[1L]] == "SDef") defs_for_taint[[length(defs_for_taint) + 1L]] <- list(r[[2L]], r[[3L]], r[[4L]]) }
  settle_taint(c, defs_for_taint)
  p$resolved <- resolved; p$errors <- errors
  if (length(errors) == 0L) {
    codes_of(p)
    if (any(vapply(p$resolved, function(r) is.list(r) && r[[1L]] == "SDef" && has_quote(r[[4L]]), TRUE))) quote_program(p)
    rm(list = ls(p$defined, all.names = TRUE), envir = p$defined)
    ud <- list()
    for (i in seq_along(p$resolved)) {
      r <- p$resolved[[i]]
      if (is.list(r) && r[[1L]] == "SDef") { assign(r[[2L]], TRUE, envir = p$defined); if (i > p$pre_count) ud[[length(ud) + 1L]] <- erase_def(r[[2L]], unlist(r[[3L]]), r[[4L]]) }
    }
    p$user_defs <- ud
  }
}

# ---------------------------------------------------------------- building
user_statements <- function(p) {
  out <- list()
  for (i in seq_along(p$statements)) if (!p$statements[[i]][[3L]] && !is.null(p$resolved[[i]])) out[[length(out) + 1L]] <- p$resolved[[i]]
  out
}
spec_text <- function(p) paste0(vapply(user_statements(p), function(s) paste0(pp_statement(s), "\n"), ""), collapse = "")
bin_text <- function(p) spec_statements_to_bin_text(user_statements(p), p$doc1, TRUE)
local_table <- function(p) doc1_render(p$doc1, "program-local symbols (same format as doc 1)")

# the human name of a spec symbol (reverse doc 2; a symbol of the program is its own name)
hum_name <- function(p, spec) {
  for (e in p$doc2[[1L]]) if (e[[3L]] %in% c("value", "infixl", "infixr", "infix", "prefix") && spec %in% e[[2L]]) return(e[[1L]])
  spec
}
# build the evaluator: the definitions of the embedded prelude are compiled when they are first needed
build_machine <- function(p) {
  defs <- list()
  for (i in seq_len(p$pre_count)) { d <- p$resolved[[i]]; if (is.list(d) && d[[1L]] == "SDef") defs[[length(defs) + 1L]] <- list(d[[2L]], list("term", d[[3L]], d[[4L]])) }
  for (d in p$user_defs) defs[[length(defs) + 1L]] <- list(d[[1L]], list("core", d[[2L]]))
  extra <- lapply(p$checker$unknowns, function(u) {
    h <- hum_name(p, u[[1L]])
    list(u[[1L]], new_th(list(S_FAIL, host_err("unknown", sprintf("%s is an unknown (it is declared and never defined, so it has no value); use it in a statement — a relation such as %s == 1 — which is simplified, not evaluated", h, h)))))
  })
  p$machine <- machine_build(defs, extra)
}
# the globals that some definition of the program uses and nothing defines (checked programs only)
missing_globals <- function(p) {
  if (length(p$errors) > 0L) return(character(0))
  isdef <- function(n) has_key(p$defined, n) || any(vapply(p$checker$unknowns, function(u) u[[1L]] == n, TRUE))
  out <- character(0)
  for (d in p$user_defs) {
    stack <- list(d[[2L]])
    while (length(stack) > 0L) {
      c <- stack[[length(stack)]]; stack[[length(stack)]] <- NULL
      switch(c[[1L]], CG = if (!isdef(c[[2L]])) out <- c(out, c[[2L]]), CL = stack[[length(stack) + 1L]] <- c[[2L]], CA = { stack[[length(stack) + 1L]] <- c[[3L]]; stack[[length(stack) + 1L]] <- c[[2L]] })
    }
  }
  sort(unique(out), method = "radix")
}
val <- function(p, n) global(p$machine, n)

# load the prelude and the files and check them.  files: a list of list(path, text)
load_program <- function(files, trusted_paths, with_prelude) {
  p <- if (with_prelude) prelude_program(rimo_root()) else new_program()
  for (f in files) add_file(p, f[[1L]], f[[2L]], f[[1L]] %in% trusted_paths)
  check_program(p)
  p
}
