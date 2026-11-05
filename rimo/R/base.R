# base.R -- reference arithmetic of the base b = i-1 with digits {0,1}, errors of the host, and the Python look-alikes
# (port of schimo/src/base.rkt).  Big integers and rationals come from the CRAN package gmp (bigz, bigq).
suppressMessages(library(gmp))

# ---------------------------------------------------------------- errors of the host: kind is "parse", "print" or "eval"
host_err <- function(kind, msg) structure(class = c("host_err", "error", "condition"), list(message = msg, call = NULL, kind = kind, msg = msg))
parse_err <- function(m) stop(host_err("parse", m))
print_err <- function(m) stop(host_err("print", m))
eval_err <- function(m) stop(host_err("eval", m))

# ---------------------------------------------------------------- characters: a code point is an integer
cp_ok <- function(c) if (c < 0L || c > 1114111L || (c >= 55296L && c <= 57343L)) 65533L else c
cp_string <- function(c) { c <- cp_ok(c); if (c == 0L) "" else intToUtf8(c) }
str_cps <- function(s) if (nchar(s, "bytes") == 0L) integer(0) else utf8ToInt(s)
cps_str <- function(v) if (length(v) == 0L) "" else intToUtf8(v)

# the position of the first bad byte of a byte vector that is not UTF-8 (strict, as Python's decoder), or NA
utf8_error <- function(bs) {
  n <- length(bs); i <- 1L; b <- as.integer(bs)
  cont <- function(k) (i + k) <= n && bitwAnd(b[i + k], 0xC0L) == 0x80L
  while (i <= n) {
    c <- b[i]
    if (c < 0x80L) i <- i + 1L
    else if (c >= 0xC2L && c < 0xE0L && cont(1L)) i <- i + 2L
    else if (c >= 0xE0L && c < 0xF0L && cont(1L) && cont(2L)) {
      c1 <- b[i + 1L]
      if ((c == 0xE0L && c1 < 0xA0L) || (c == 0xEDL && c1 >= 0xA0L)) return(i - 1L)
      i <- i + 3L
    } else if (c >= 0xF0L && c < 0xF5L && cont(1L) && cont(2L) && cont(3L)) {
      c1 <- b[i + 1L]
      if ((c == 0xF0L && c1 < 0x90L) || (c == 0xF4L && c1 >= 0x90L)) return(i - 1L)
      i <- i + 4L
    } else return(i - 1L)
  }
  NA_integer_
}

bad_utf8 <- function(msg) structure(class = c("bad_utf8", "error", "condition"), list(message = msg, call = NULL))
read_file <- function(path) { n <- file.size(path); if (is.na(n)) stop(sprintf("cannot open %s", path)); if (n == 0) raw(0) else readBin(path, "raw", n) }
read_utf8 <- function(path) {
  bs <- read_file(path)
  if (any(bs == as.raw(0L))) bs <- bs[bs != as.raw(0L)]
  s <- rawToChar(bs)
  if (!validUTF8(s)) {
    at <- utf8_error(bs)
    stop(bad_utf8(sprintf("cannot decode byte sequence starting from %d (position %d)", as.integer(bs[at + 1L]), at)))
  }
  Encoding(s) <- "UTF-8"; s
}

# ---------------------------------------------------------------- Gaussian integers: list(re, im) of bigz
times_b <- function(g) list(-(g[[1]] + g[[2]]), g[[1]] - g[[2]])

# the Gaussian integer with the digits ds (an integer vector of 0/1, least significant first)
val_digits <- function(ds) {
  sa <- as.bigz(0); sb <- as.bigz(0); pa <- as.bigz(1); pb <- as.bigz(0)
  for (d in ds) {
    if (d != 0L) { sa <- sa + pa; sb <- sb + pb }
    np <- -(pa + pb); pb <- pa - pb; pa <- np
  }
  list(sa, sb)
}

# the same, or NULL when the digit list is longer than the native arithmetic of the other cores would take
trim_digits <- function(ds) { e <- length(ds); while (e > 0L && ds[e] == 0L) e <- e - 1L; ds[seq_len(e)] }
val_digits_small <- function(ds) { ds <- trim_digits(ds); if (length(ds) > 100L) NULL else val_digits(ds) }

# Penney: the canonical least-significant-first digit list of a Gaussian integer (re, im: bigz)
to_digits <- function(g) {
  x <- g[[1]]; y <- g[[2]]; out <- integer(0); k <- 0L
  zero <- as.bigz(0); two <- as.bigz(2)
  while (!(x == zero && y == zero)) {
    d <- (x + y) %% two != zero
    x1 <- if (d) x - 1 else x
    nx <- (-x1 + y) %/% two
    ny <- (-x1 - y) %/% two
    k <- k + 1L; out[k] <- if (d) 1L else 0L
    x <- nx; y <- ny
  }
  out
}
# a small non-negative integer (a double or an integer) as a digit list, quickly
small_digits <- function(n) {
  x <- n; y <- 0; out <- integer(0); k <- 0L
  while (!(x == 0 && y == 0)) {
    d <- (x + y) %% 2 != 0
    x1 <- if (d) x - 1 else x
    nx <- (-x1 + y) / 2
    ny <- (-x1 - y) / 2
    k <- k + 1L; out[k] <- if (d) 1L else 0L
    x <- nx; y <- ny
  }
  out
}

# most significant digit first ("0" for zero)
numeral <- function(ds) { n <- length(ds); if (n == 0L) "0" else paste(c("0", "1")[rev(ds) + 1L], collapse = "") }
.numcache <- new.env(hash = TRUE, parent = emptyenv())
int_numeral_text <- function(n) {
  key <- as.character(n); r <- .numcache[[key]]
  if (is.null(r)) { r <- numeral(small_digits(n)); .numcache[[key]] <- r }
  r
}
big_numeral_text <- function(n) numeral(to_digits(list(as.bigz(n), as.bigz(0))))

# ---------------------------------------------------------------- Python look-alikes
.ws_cps <- c(9:13, 32L, 133L, 160L, 5760L, 8192:8202, 8232L, 8233L, 8239L, 8287L, 12288L)
py_printable <- function(c) {
  if (c == 32L) return(TRUE)
  if (c < 32L || (c >= 127L && c <= 159L)) return(FALSE)
  if (c < 1114112L && !(c >= 55296L && c <= 57343L) && c %in% .ws_cps) return(FALSE)
  !(c == 173L || (c >= 1536L && c <= 1541L) || c == 1564L || c == 1757L || c == 1807L || c == 6158L || (c >= 8203L && c <= 8207L) || (c >= 8234L && c <= 8238L) ||
      (c >= 8288L && c <= 8292L) || (c >= 8294L && c <= 8303L) || c == 65279L || (c >= 65529L && c <= 65531L) || (c >= 57344L && c <= 63743L) || (c >= 983040L && c <= 1114111L))
}
hex_pad <- function(n, width) { s <- tolower(format(as.hexmode(n))); paste0(strrep("0", max(0L, width - nchar(s))), s) }

# Python's repr() of a str, given as a vector of code points
py_repr_cps <- function(cps) {
  has_sq <- any(cps == 39L); has_dq <- any(cps == 34L)
  q <- if (has_sq && !has_dq) 34L else 39L
  out <- character(length(cps)); 
  for (i in seq_along(cps)) {
    c <- cps[i]
    out[i] <- if (c == q) paste0("\\", intToUtf8(c))
      else if (c == 92L) "\\\\" else if (c == 10L) "\\n" else if (c == 13L) "\\r" else if (c == 9L) "\\t"
      else if (py_printable(c)) intToUtf8(cp_ok(c))
      else if (c < 256L) paste0("\\x", hex_pad(c, 2L)) else if (c < 65536L) paste0("\\u", hex_pad(c, 4L)) else paste0("\\U", hex_pad(c, 8L))
  }
  paste0(intToUtf8(q), paste(out, collapse = ""), intToUtf8(q))
}
py_repr <- function(s) py_repr_cps(str_cps(s))

# an exact rational (bigq) -> the double nearest to it (round half to even), as Python's int / int
ratio_double <- function(num, den) {
  num <- as.bigz(num); den <- as.bigz(den)
  if (num == 0) return(0)
  neg <- num < 0; a <- abs(num)
  # scale so that the quotient has 54..55 significant bits
  la <- as.integer(ceiling(log2(as.numeric(a)))); ld <- as.integer(ceiling(log2(as.numeric(den))))
  if (!is.finite(la)) la <- nchar(as.character(a, 2)); if (!is.finite(ld)) ld <- nchar(as.character(den, 2))
  la <- nchar(as.character(a, 2)); ld <- nchar(as.character(den, 2))
  sh <- 55L - (la - ld)                     # quotient of a * 2^sh by den has 55 or 56 bits
  if (sh >= 0) { n <- a * as.bigz(2)^sh; d <- den } else { n <- a; d <- den * as.bigz(2)^(-sh) }
  q <- n %/% d; r <- n - q * d
  bits <- nchar(as.character(q, 2)); extra <- bits - 53L
  # round q to 53 bits, half to even, taking the remainder into account
  p2 <- as.bigz(2)^extra; low <- q %% p2; hi <- q %/% p2
  half <- p2 %/% 2
  up <- (low > half) || (low == half && (r != 0 || (hi %% 2) == 1))
  if (low == half && r == 0 && (hi %% 2) == 0) up <- FALSE
  if (low == half && r != 0) up <- TRUE
  if (up) hi <- hi + 1
  v <- as.numeric(hi) * 2^(extra - sh)
  if (neg) -v else v
}

# Python's format(x, '.<p>g') of a double: p significant digits, trailing zeros removed, exponent form outside [1e-4, 10^p)
fmt_g <- function(p, x) {
  if (is.nan(x)) return("nan")
  if (x == Inf) return("inf"); if (x == -Inf) return("-inf")
  if (x == 0) return(if (1 / x < 0) "-0" else "0")
  neg <- x < 0
  q <- as.bigq(abs(x))                          # the exact value of the double
  num <- numerator(q); den <- denominator(q)
  ten <- as.bigz(10)
  e0 <- nchar(as.character(num %/% den)) - 1L   # decimal exponent guess (integer part digits); fixed up below
  if (num < den) { e0 <- -1L; while (num * ten^(-e0 - 1L) < den) e0 <- e0 - 1L; e0 <- e0 }
  # 10^e0 <= r < 10^(e0+1)
  ge <- function(e) if (e >= 0) num >= den * ten^e else num * ten^(-e) >= den
  while (!ge(e0)) e0 <- e0 - 1L
  while (ge(e0 + 1L)) e0 <- e0 + 1L
  digits_at <- function(e) {                    # round(r / 10^(e - (p - 1))), half to even
    sh <- e - (p - 1L)
    n2 <- if (sh >= 0) num else num * ten^(-sh); d2 <- if (sh >= 0) den * ten^sh else den
    qq <- n2 %/% d2; rr <- n2 - qq * d2
    twice <- rr * 2
    if (twice > d2 || (twice == d2 && (qq %% 2) == 1)) qq + 1 else qq
  }
  d0 <- digits_at(e0)
  if (d0 >= ten^p) { e <- e0 + 1L; d <- digits_at(e) } else { e <- e0; d <- d0 }
  ds <- as.character(d)
  sign <- if (neg) "-" else ""
  trim_zeros <- function(s) sub("0+$", "", s)
  if (e < -4L || e >= p) {
    t <- trim_zeros(substr(ds, 2L, nchar(ds)))
    m <- if (t == "") substr(ds, 1L, 1L) else paste0(substr(ds, 1L, 1L), ".", t)
    ex <- abs(e)
    paste0(sign, m, "e", if (e < 0L) "-" else "+", if (ex < 10L) "0" else "", ex)
  } else if (e >= 0L) {
    ip <- substr(ds, 1L, e + 1L); fp <- trim_zeros(substr(ds, e + 2L, nchar(ds)))
    paste0(sign, if (fp == "") ip else paste0(ip, ".", fp))
  } else {
    fp <- trim_zeros(paste0(strrep("0", -e - 1L), ds))
    paste0(sign, "0.", fp)
  }
}

# ---------------------------------------------------------------- string helpers
ws_char <- function(c) c %in% .ws_cps
strip <- function(s) { cps <- str_cps(s); n <- length(cps); lo <- 1L; while (lo <= n && ws_char(cps[lo])) lo <- lo + 1L; hi <- n; while (hi >= lo && ws_char(cps[hi])) hi <- hi - 1L; cps_str(cps[lo:hi][seq_len(max(0L, hi - lo + 1L))]) }
basename_of <- function(p) sub("^.*/", "", p)
starts_with <- function(s, p) substr(s, 1L, nchar(p)) == p
ends_with <- function(s, p) nchar(s) >= nchar(p) && substr(s, nchar(s) - nchar(p) + 1L, nchar(s)) == p
split_on <- function(s, sep) {                      # the pieces between the separators, empty ones included (as Python's split)
  if (nchar(s, "bytes") == 0L) return("")
  r <- strsplit(s, sep, fixed = TRUE)[[1]]
  if (endsWith(s, sep)) r <- c(r, "")
  if (length(r) == 0L) "" else r
}
split_lines <- function(s) split_on(s, "\n")
# a growing buffer of strings
newbuf <- function() { e <- new.env(hash = FALSE, parent = emptyenv()); e$v <- character(256L); e$n <- 0L; e }
bpush <- function(e, s) { n <- e$n + 1L; if (n > length(e$v)) length(e$v) <- 2L * length(e$v); e$v[n] <- s; e$n <- n; invisible(NULL) }
bvals <- function(e) e$v[seq_len(e$n)]
split_ws <- function(s) { r <- strsplit(s, "[ \t\n\r\f\v]+")[[1]]; r[r != ""] }

# the position (1-based, in characters) of the first occurrence of p in s at or after start, or NULL
find_sub <- function(s, p, start = 1L) {
  if (nchar(p) == 0L) return(if (start <= nchar(s) + 1L) start else NULL)
  if (start > nchar(s)) return(NULL)
  r <- regexpr(p, if (start > 1L) substr(s, start, nchar(s)) else s, fixed = TRUE)[1L]
  if (r < 0L) NULL else r + start - 1L
}
contains_sub <- function(s, p) grepl(p, s, fixed = TRUE)
rfind_sub <- function(s, p) { m <- gregexpr(p, s, fixed = TRUE)[[1L]]; if (m[1L] < 0L) NULL else m[length(m)] }

basename_of <- function(p) sub("^.*/", "", p)
bq_trunc <- function(q) { n <- numerator(q); d <- denominator(q); r <- n %/% d; if (n < 0 && r * d != n) r + 1 else r }

drop_first <- function(x, n) if (n > 0L) x[-seq_len(n)] else x       # x[-integer(0)] would be empty

# a decimal numeral (digits only, leading zeros allowed) as a bigz: gmp reads "025" as octal
bz_dec <- function(s) as.bigz(sub("^0+(?=.)", "", s, perl = TRUE))
