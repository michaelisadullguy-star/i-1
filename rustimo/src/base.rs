//! base.rs -- reference arithmetic of the base b = i-1 with digits {0,1}, and small host helpers.
//!
//! Port of haskimo/src/I1/Base.hs (itself a port of pymo/base_b.py): `val_digits`, `to_digits`, `numeral`, and the few Python
//! behaviours the rest of the implementation must reproduce exactly (repr of a string, "%.12g" of a float).  The isomorphism
//! "digit string <-> Gaussian integer" is the only arithmetic the host ever does on language values.
use crate::bigint::Int;
use std::io::Read;

// ---------------------------------------------------------------- errors of the host
/// The kinds of error that stop a computation: a syntax error in a source text, the value of an unknown was needed, a value cannot
/// be printed, and an error of the evaluator (a value that is not a function was applied, a loop).  Class errors are not errors of
/// this kind: the class checker returns them as values.
#[derive(Clone, Debug)]
pub enum Err {
    Parse(String),
    Unknown(String),
    Print(String),
    Eval(String),
}

impl Err {
    pub fn text(&self) -> &str {
        match self {
            Err::Parse(m) | Err::Unknown(m) | Err::Print(m) | Err::Eval(m) => m,
        }
    }
}

pub type R<T> = Result<T, Err>;

pub fn parse_err<T>(m: impl Into<String>) -> R<T> {
    Err(Err::Parse(m.into()))
}

pub fn print_err<T>(m: impl Into<String>) -> R<T> {
    Err(Err::Print(m.into()))
}

// ---------------------------------------------------------------- Gaussian integers
pub type GI = (Int, Int);

/// multiply by the base i-1:  (a + bi)(-1 + i) = (-a - b) + (a - b)i
fn times_b(p: &GI) -> GI {
    (p.0.add(&p.1).neg(), p.0.sub(&p.1))
}

/// the Gaussian integer with the digits ds (least significant first)
pub fn val_digits(ds: &[u8]) -> GI {
    let mut s: GI = (Int::zero(), Int::zero());
    let mut p: GI = (Int::from_i64(1), Int::zero());
    for &d in ds {
        if d != 0 {
            s = (s.0.add(&p.0), s.1.add(&p.1));
        }
        p = times_b(&p);
    }
    s
}

/// the same, for digit lists that are short enough for 64-bit arithmetic (None when they are not)
pub fn val_digits_small(ds: &[u8]) -> Option<(i64, i64)> {
    let mut end = ds.len();
    while end > 0 && ds[end - 1] == 0 {
        end -= 1;
    }
    if end > 100 {
        return None;
    }
    let (mut sa, mut sb) = (0i64, 0i64);
    let (mut pa, mut pb) = (1i64, 0i64);
    for &d in &ds[..end] {
        if d != 0 {
            sa += pa;
            sb += pb;
        }
        let (na, nb) = (-pa - pb, pa - pb);
        pa = na;
        pb = nb;
    }
    Some((sa, sb))
}

/// Penney: the canonical least-significant-first digit list of a Gaussian integer
pub fn to_digits(g: &GI) -> Vec<u8> {
    let (mut x, mut y) = (g.0.clone(), g.1.clone());
    let mut out = vec![];
    while !(x.is_zero() && y.is_zero()) {
        let d = x.add(&y).is_odd();
        let x1 = if d { x.sub(&Int::from_i64(1)) } else { x.clone() };
        // (-x' + y) / 2 and (-x' - y) / 2, both exact
        let nx = x1.neg().add(&y).half_exact();
        let ny = x1.neg().sub(&y).half_exact();
        out.push(d as u8);
        x = nx;
        y = ny;
    }
    out
}

/// most significant digit first ("0" for zero)
pub fn numeral(ds: &[u8]) -> String {
    if ds.is_empty() {
        return "0".to_string();
    }
    ds.iter().rev().map(|&d| if d != 0 { '1' } else { '0' }).collect()
}

/// the numeral text of a natural number (a code point, a digit count, ...), as the reader writes it
pub fn int_numeral_text(n: u64) -> String {
    numeral(&to_digits(&(Int::from_u64(n), Int::zero())))
}

/// the numeral text of a big natural number
pub fn big_numeral_text(n: &Int) -> String {
    numeral(&to_digits(&(n.clone(), Int::zero())))
}

/// the digits without the most significant zeros: the canonical digit string of the number they denote
pub fn trim_digits(ds: &[u8]) -> Vec<u8> {
    let mut end = ds.len();
    while end > 0 && ds[end - 1] == 0 {
        end -= 1;
    }
    ds[..end].to_vec()
}

// ---------------------------------------------------------------- Python look-alikes
fn py_printable(c: char) -> bool {
    if c == ' ' {
        return true;
    }
    if c.is_control() || c.is_whitespace() {
        return false;
    }
    let u = c as u32;
    // format characters, surrogates are not chars; private use areas
    !matches!(u, 0xAD | 0x600..=0x605 | 0x61C | 0x6DD | 0x70F | 0x180E | 0x200B..=0x200F | 0x202A..=0x202E | 0x2060..=0x2064
        | 0x2066..=0x206F | 0xFEFF | 0xFFF9..=0xFFFB | 0xE000..=0xF8FF | 0xF0000..=0x10FFFF)
}

/// Python's repr() of a str
pub fn py_repr(s: &str) -> String {
    let has_sq = s.contains('\'');
    let has_dq = s.contains('"');
    let q = if has_sq && !has_dq { '"' } else { '\'' };
    let mut out = String::new();
    out.push(q);
    for c in s.chars() {
        if c == q {
            out.push('\\');
            out.push(c);
        } else if c == '\\' {
            out.push_str("\\\\");
        } else if c == '\n' {
            out.push_str("\\n");
        } else if c == '\r' {
            out.push_str("\\r");
        } else if c == '\t' {
            out.push_str("\\t");
        } else if py_printable(c) {
            out.push(c);
        } else if (c as u32) < 0x100 {
            out.push_str(&format!("\\x{:02x}", c as u32));
        } else if (c as u32) < 0x10000 {
            out.push_str(&format!("\\u{:04x}", c as u32));
        } else {
            out.push_str(&format!("\\U{:08x}", c as u32));
        }
    }
    out.push(q);
    out
}

/// Python's  format(x, '.<p>g')  of a float (p significant digits, trailing zeros removed)
pub fn fmt_g(p: usize, x: f64) -> String {
    if x == 0.0 {
        return if x.is_sign_negative() { "-0".to_string() } else { "0".to_string() };
    }
    if x.is_infinite() {
        return if x < 0.0 { "-inf".to_string() } else { "inf".to_string() };
    }
    if x.is_nan() {
        return "nan".to_string();
    }
    // Rust's exact, correctly rounded scientific formatting gives the p significant digits and the exponent
    let sci = format!("{:.*e}", p - 1, x.abs());
    let (mant, exp) = sci.split_once('e').unwrap();
    let e: i32 = exp.parse().unwrap();
    let digits: String = mant.chars().filter(|c| c.is_ascii_digit()).collect(); // p digits
    let neg = if x < 0.0 { "-" } else { "" };
    let body = if e < -4 || e >= p as i32 {
        let t = digits[1..].trim_end_matches('0');
        let m = if t.is_empty() { digits[..1].to_string() } else { format!("{}.{}", &digits[..1], t) };
        let ex = e.abs();
        format!("{}e{}{}{}", m, if e < 0 { '-' } else { '+' }, if ex < 10 { "0" } else { "" }, ex)
    } else if e >= 0 {
        let (ip, fp) = digits.split_at(e as usize + 1);
        let fp = fp.trim_end_matches('0');
        if fp.is_empty() {
            ip.to_string()
        } else {
            format!("{}.{}", ip, fp)
        }
    } else {
        let fp = format!("{}{}", "0".repeat((-e - 1) as usize), digits);
        format!("0.{}", fp.trim_end_matches('0'))
    };
    format!("{}{}", neg, body)
}

// ---------------------------------------------------------------- string helpers

/// Python's  s.strip()
pub fn strip(s: &str) -> &str {
    s.trim_matches(|c: char| c.is_whitespace())
}

pub fn basename(p: &str) -> &str {
    p.rsplit('/').next().unwrap_or(p)
}

/// read a whole file as UTF-8 (the language's source files are UTF-8, whatever the locale).  A file that is not valid UTF-8 is an
/// error (`InvalidData`), as in Pymo and Haskimo: the bytes are never replaced by U+FFFD behind the author's back.
pub fn read_utf8(path: &str) -> std::io::Result<String> {
    let mut bytes = vec![];
    std::fs::File::open(path)?.read_to_end(&mut bytes)?;
    String::from_utf8(bytes).map_err(|e| {
        let at = e.utf8_error().valid_up_to();
        let b = e.as_bytes()[at];
        std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            format!("cannot decode byte sequence starting from {} (position {})", b, at),
        )
    })
}



#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn digits_round_trip() {
        for n in 0..200i64 {
            for m in -50..50i64 {
                let g = (Int::from_i64(n), Int::from_i64(m));
                let ds = to_digits(&g);
                let back = val_digits(&ds);
                assert_eq!(back, g);
                assert_eq!(val_digits_small(&ds), Some((n, m)));
            }
        }
        assert_eq!(int_numeral_text(1), "1");
        assert_eq!(int_numeral_text(2), "1100");
        assert_eq!(numeral(&[]), "0");
    }

    #[test]
    fn python_formats() {
        assert_eq!(fmt_g(12, 0.1), "0.1");
        assert_eq!(fmt_g(12, 1.0 / 3.0), "0.333333333333");
        assert_eq!(fmt_g(12, 123456789012345.0), "1.23456789012e+14");
        assert_eq!(fmt_g(12, 1e-5), "1e-05");
        assert_eq!(fmt_g(12, 100.0), "100");
        assert_eq!(fmt_g(10, 3.5), "3.5");
        assert_eq!(py_repr("a'b"), "\"a'b\"");
        assert_eq!(py_repr("it's \"x\""), "'it\\'s \"x\"'");
    }
}
