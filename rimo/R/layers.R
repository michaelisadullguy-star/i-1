# layers.R -- the three notation systems of i-1 and the system documents that connect them (port of schimo/src/layers.rkt).
#   bin   only  1 0 .  space ( ) newline;  numeral 1011  1.01;  symbol .B. (B a bit string, the code of the symbol, see doc 1);  markers  . = ↦   .. = ≔   ... = ∶
#   spec  unicode glyphs; the notation of the prelude (lib/*.imo); `⍝` starts a comment
#   doc 1   [spec sbl] := [bin sbl]            one line per symbol

# ---------------------------------------------------------------- doc 1: an environment with s2b, b2s (environments name -> code) and local (a list of c(name, code), newest first)
doc1_empty <- function() { d <- new.env(hash = FALSE, parent = emptyenv()); d$s2b <- new.env(hash = TRUE, parent = emptyenv()); d$b2s <- new.env(hash = TRUE, parent = emptyenv()); d$local <- list(); d }
copy_doc1 <- function(d) {
  r <- new.env(hash = FALSE, parent = emptyenv())
  r$s2b <- list2env(as.list(d$s2b, all.names = TRUE), hash = TRUE, parent = emptyenv()); r$b2s <- list2env(as.list(d$b2s, all.names = TRUE), hash = TRUE, parent = emptyenv()); r$local <- d$local; r
}
bin_sym <- function(s) {                            # .B. with B a non-empty bit string
  n <- nchar(s)
  n >= 3L && startsWith(s, ".") && endsWith(s, ".") && grepl("^[01]*$", substr(s, 2L, n - 1L))
}
has_key <- function(env, key) exists(key, envir = env, inherits = FALSE)
getk <- function(env, key) if (exists(key, envir = env, inherits = FALSE)) get(key, envir = env, inherits = FALSE) else NULL

doc1_parse <- function(text) {
  d <- doc1_empty()
  for (ln0 in split_on(text, "\n")) {
    ln <- strip(ln0)
    if (ln == "" || starts_with(ln, "⍝")) next
    parts <- split_on(ln, " := ")
    if (length(parts) != 2L) parse_err(sprintf("doc1: bad line %s", py_repr(ln)))
    a <- strip(parts[1L]); b <- strip(parts[2L])
    if (!bin_sym(b)) parse_err(sprintf("doc1: bad binary symbol %s", py_repr(b)))
    if (has_key(d$s2b, a) || has_key(d$b2s, b)) parse_err(sprintf("doc1: duplicate %s / %s", a, b))
    assign(a, b, envir = d$s2b); assign(b, a, envir = d$b2s)
  }
  d
}

# the binary string without its high zeros; the larger of two; the successor
bin_strip <- function(s) sub("^0+", "", s)
bin_less <- function(a, b) { a <- bin_strip(a); b <- bin_strip(b); if (nchar(a) != nchar(b)) nchar(a) < nchar(b) else a < b }
bin_succ <- function(s) {
  b <- bin_strip(s); n <- nchar(b)
  if (n == 0L) return("1")
  ch <- strsplit(b, "")[[1]]; i <- n
  while (i >= 1L && ch[i] == "1") { ch[i] <- "0"; i <- i - 1L }
  if (i >= 1L) { ch[i] <- "1"; paste(ch, collapse = "") } else paste0("1", paste(ch, collapse = ""))
}
# the next free code:  .<max + 1 in binary>.
next_code <- function(d) {
  m <- ""
  for (b in ls(d$b2s, all.names = TRUE)) { bits <- substr(b, 2L, nchar(b) - 1L); if (bin_less(m, bits)) m <- bits }
  paste0(".", bin_succ(m), ".")
}
# the code of a symbol; a new local code is given when allowed
doc1_code <- function(d, name, allow_new) {
  b <- getk(d$s2b, name)
  if (!is.null(b)) return(b)
  if (!allow_new) parse_err(sprintf("%s has no binary symbol in doc 1", py_repr(name)))
  nb <- next_code(d)
  assign(name, nb, envir = d$s2b); assign(nb, name, envir = d$b2s)
  d$local <- c(list(c(name, nb)), d$local)
  nb
}
doc1_add_local <- function(d, a, b) { assign(a, b, envir = d$s2b); assign(b, a, envir = d$b2s) }
doc1_render <- function(d, header) {
  out <- character(0)
  for (h in header) out <- c(out, sprintf("⍝ %s\n", h))
  for (e in rev(d$local)) out <- c(out, sprintf("%s := %s\n", e[1L], e[2L]))
  paste(out, collapse = "")
}

# ---------------------------------------------------------------- bin lexer / translators
reserved_spec <- function(s) if (s == ".") "↦" else if (s == "..") "≔" else if (s == "...") "∶" else NULL
reserved_bin <- function(s) if (s == "↦") "." else if (s == "≔") ".." else if (s == "∶") "..." else NULL

lex_bin <- function(text) {
  cps <- str_cps(text); n <- length(cps); toks <- list(); d <- 0L; i <- 1L
  while (i <= n) {
    c <- cps[i]
    if (c == 32L || c == 9L || c == 13L) { i <- i + 1L }
    else if (c == 10L) { i <- i + 1L; if (d == 0L) toks[[length(toks) + 1L]] <- list("BNl") }
    else if (c == 40L) { i <- i + 1L; d <- d + 1L; toks[[length(toks) + 1L]] <- list("BOpen") }
    else if (c == 41L) { i <- i + 1L; d <- d - 1L; toks[[length(toks) + 1L]] <- list("BClose") }
    else if (c == 48L || c == 49L || c == 46L) {
      j <- i
      while (j <= n && (cps[j] == 48L || cps[j] == 49L || cps[j] == 46L)) j <- j + 1L
      s <- cps_str(cps[i:(j - 1L)]); pts <- sum(cps[i:(j - 1L)] == 46L)
      toks[[length(toks) + 1L]] <-
        if (!is.null(reserved_spec(s))) list("BMark", s)
        else if (pts <= 1L) list("BNum", s)
        else if (bin_sym(s)) list("BSym", s)
        else parse_err(sprintf("bad binary token %s", py_repr(s)))
      i <- j
    } else parse_err(sprintf("character %s is not part of the binary notation", py_repr(cp_string(c))))
  }
  toks
}

# tokens to text (spaces only between atoms; newlines kept).  NA stands for a newline.
render_toks <- function(toks) {
  buf <- newbuf(); first <- TRUE
  for (t in toks) {
    if (is.na(t)) { bpush(buf, "\n"); first <- TRUE }
    else { if (!(t == ")" || first)) bpush(buf, " "); bpush(buf, t); first <- (t == "(") }
  }
  paste(bvals(buf), collapse = "")
}

# bin text -> spec text, through doc 1 (and the program's local table)
bin_to_spec_text <- function(text, d) {
  toks <- lex_bin(text)
  out <- character(length(toks))
  for (i in seq_along(toks)) {
    t <- toks[[i]]
    out[i] <- switch(t[[1L]], BNl = NA_character_, BOpen = "(", BClose = ")", BNum = t[[2L]], BMark = reserved_spec(t[[2L]]),
      BSym = { r <- getk(d$b2s, t[[2L]]); if (is.null(r)) parse_err(sprintf("binary symbol %s is not defined in doc 1 (or the local table)", t[[2L]])); r })
  }
  render_toks(out)
}

# the tokens of spec text re-spelled in bin notation (the shared part of the two translators)
bin_of_spec_toks <- function(toks, d, allow_new, strings_in_order) {
  out <- newbuf(); push <- function(s) bpush(out, s)
  for (t in toks) {
    switch(t[[1L]],
      Open = push("("), Close = push(")"), num = push(t[[2L]]),
      name = { r <- reserved_bin(t[[2L]]); if (!is.null(r)) push(r) else push(doc1_code(d, t[[2L]], allow_new)) },
      chr = { bc <- doc1_code(d, "𝕔", allow_new); push("("); push(bc); push(int_numeral_text(t[[2L]])); push(")") },
      str = {
        cs <- str_cps(t[[2L]])
        if (strings_in_order) {
          bcons <- doc1_code(d, "∷", allow_new); bchr <- doc1_code(d, "𝕔", allow_new); bnil <- doc1_code(d, "⊘", allow_new)
          for (ch in cs) { push("("); push(bcons); push("("); push(bchr); push(int_numeral_text(ch)); push(")") }
          push(bnil); for (ch in cs) push(")")
        } else {
          for (ch in cs) { bcons <- doc1_code(d, "∷", allow_new); bchr <- doc1_code(d, "𝕔", allow_new); push("("); push(bcons); push("("); push(bchr); push(int_numeral_text(ch)); push(")") }
          push(doc1_code(d, "⊘", allow_new)); for (ch in cs) push(")")
        }
      },
      Nl = NULL)
  }
  bvals(out)
}

# the statements re-spelled in bin notation; new program-local symbols get codes in order of first use
spec_statements_to_bin_text <- function(sts, d, allow_new) {
  all <- character(0)
  for (st in sts) all <- c(all, bin_of_spec_toks(lex_spec(pp_statement(st)), d, allow_new, TRUE), NA_character_)
  render_toks(all)
}
# one spec term (as text) -> the same term in bin notation, through doc 1 (literals are expanded as the reader expands them)
spec_term_to_bin <- function(text, d) render_toks(bin_of_spec_toks(lex_spec(text), d, FALSE, FALSE))

# ---------------------------------------------------------------- files: default notation by extension, `@bin` `@spec` `@hum` section headers.  Returns a list of c(mode, text) pairs.
split_sections <- function(text, def) {
  lines <- split_on(text, "\n"); mode <- def; cur <- character(0); acc <- list()
  for (ln in lines) {
    s <- strip(ln)
    if (s %in% c("@bin", "@spec", "@hum")) {
      if (length(cur) > 0L) acc[[length(acc) + 1L]] <- list(mode, paste(cur, collapse = "\n"))
      mode <- substr(s, 2L, nchar(s)); cur <- character(0)
    } else cur <- c(cur, ln)
  }
  if (length(cur) > 0L) acc[[length(acc) + 1L]] <- list(mode, paste(cur, collapse = "\n"))
  acc
}
default_notation <- function(path) if (ends_with(path, ".bin.imo")) "bin" else if (ends_with(path, ".hum.imo")) "hum" else "spec"
