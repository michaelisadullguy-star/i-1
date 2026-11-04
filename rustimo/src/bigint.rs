//! bigint.rs -- arbitrary-precision integers and rationals, written for the host side of the interpreter only.
//!
//! The language computes with digit lists; the host never does arithmetic on language values except the isomorphism
//! "digit string <-> Gaussian integer" (the digits of a numeral, a code point, a decimal literal of the human notation) and the
//! few exact fractions that `eval` prints.  The numbers involved are small, so everything here is simple rather than fast:
//! sign + magnitude over 32-bit limbs, schoolbook multiplication, shift-and-subtract division.
use std::cmp::Ordering;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Int {
    neg: bool,
    mag: Vec<u32>, // little-endian limbs, no high zero limbs; zero is the empty vector (and not negative)
}

fn trim(v: &mut Vec<u32>) {
    while let Some(&0) = v.last() {
        v.pop();
    }
}

fn cmp_mag(a: &[u32], b: &[u32]) -> Ordering {
    if a.len() != b.len() {
        return a.len().cmp(&b.len());
    }
    for i in (0..a.len()).rev() {
        if a[i] != b[i] {
            return a[i].cmp(&b[i]);
        }
    }
    Ordering::Equal
}

fn add_mag(a: &[u32], b: &[u32]) -> Vec<u32> {
    let (long, short) = if a.len() >= b.len() { (a, b) } else { (b, a) };
    let mut out = Vec::with_capacity(long.len() + 1);
    let mut carry = 0u64;
    for i in 0..long.len() {
        let s = long[i] as u64 + if i < short.len() { short[i] as u64 } else { 0 } + carry;
        out.push(s as u32);
        carry = s >> 32;
    }
    if carry != 0 {
        out.push(carry as u32);
    }
    out
}

/// a - b for |a| >= |b|
fn sub_mag(a: &[u32], b: &[u32]) -> Vec<u32> {
    let mut out = Vec::with_capacity(a.len());
    let mut borrow = 0i64;
    for i in 0..a.len() {
        let mut d = a[i] as i64 - borrow - if i < b.len() { b[i] as i64 } else { 0 };
        if d < 0 {
            d += 1 << 32;
            borrow = 1;
        } else {
            borrow = 0;
        }
        out.push(d as u32);
    }
    trim(&mut out);
    out
}

fn mul_mag(a: &[u32], b: &[u32]) -> Vec<u32> {
    if a.is_empty() || b.is_empty() {
        return vec![];
    }
    let mut out = vec![0u32; a.len() + b.len()];
    for i in 0..a.len() {
        let mut carry = 0u64;
        for j in 0..b.len() {
            let t = a[i] as u64 * b[j] as u64 + out[i + j] as u64 + carry;
            out[i + j] = t as u32;
            carry = t >> 32;
        }
        out[i + b.len()] = carry as u32;
    }
    trim(&mut out);
    out
}

fn bit_len_mag(a: &[u32]) -> u64 {
    match a.last() {
        None => 0,
        Some(&top) => (a.len() as u64 - 1) * 32 + (32 - top.leading_zeros() as u64),
    }
}

fn shl_mag(a: &[u32], n: u64) -> Vec<u32> {
    if a.is_empty() {
        return vec![];
    }
    let limbs = (n / 32) as usize;
    let bits = (n % 32) as u32;
    let mut out = vec![0u32; limbs];
    if bits == 0 {
        out.extend_from_slice(a);
    } else {
        let mut carry = 0u32;
        for &x in a {
            out.push((x << bits) | carry);
            carry = x >> (32 - bits);
        }
        if carry != 0 {
            out.push(carry);
        }
    }
    out
}

fn shr_mag(a: &[u32], n: u64) -> Vec<u32> {
    let limbs = (n / 32) as usize;
    if limbs >= a.len() {
        return vec![];
    }
    let bits = (n % 32) as u32;
    let src = &a[limbs..];
    let mut out = Vec::with_capacity(src.len());
    if bits == 0 {
        out.extend_from_slice(src);
    } else {
        for i in 0..src.len() {
            let hi = if i + 1 < src.len() { src[i + 1] << (32 - bits) } else { 0 };
            out.push((src[i] >> bits) | hi);
        }
    }
    trim(&mut out);
    out
}

fn bit_mag(a: &[u32], i: u64) -> bool {
    let limb = (i / 32) as usize;
    limb < a.len() && (a[limb] >> (i % 32)) & 1 == 1
}

/// quotient and remainder of magnitudes (shift-and-subtract; the numbers of the host side are small)
fn divrem_mag(a: &[u32], b: &[u32]) -> (Vec<u32>, Vec<u32>) {
    assert!(!b.is_empty(), "division by zero");
    if cmp_mag(a, b) == Ordering::Less {
        return (vec![], a.to_vec());
    }
    if b.len() == 1 {
        let d = b[0] as u64;
        let mut q = vec![0u32; a.len()];
        let mut rem = 0u64;
        for i in (0..a.len()).rev() {
            let cur = (rem << 32) | a[i] as u64;
            q[i] = (cur / d) as u32;
            rem = cur % d;
        }
        trim(&mut q);
        return (q, if rem == 0 { vec![] } else { vec![rem as u32] });
    }
    let nbits = bit_len_mag(a);
    let mut q = vec![0u32; a.len()];
    let mut r: Vec<u32> = vec![];
    for i in (0..nbits).rev() {
        r = shl_mag(&r, 1);
        if bit_mag(a, i) {
            if r.is_empty() {
                r.push(1);
            } else {
                r[0] |= 1;
            }
        }
        if cmp_mag(&r, b) != Ordering::Less {
            r = sub_mag(&r, b);
            q[(i / 32) as usize] |= 1 << (i % 32);
        }
    }
    trim(&mut q);
    (q, r)
}

impl Int {
    pub fn zero() -> Int {
        Int { neg: false, mag: vec![] }
    }
    pub fn from_u64(v: u64) -> Int {
        let mut mag = vec![v as u32, (v >> 32) as u32];
        trim(&mut mag);
        Int { neg: false, mag }
    }
    pub fn from_i64(v: i64) -> Int {
        let mut r = Int::from_u64(v.unsigned_abs());
        r.neg = v < 0 && !r.mag.is_empty();
        r
    }
    fn make(neg: bool, mut mag: Vec<u32>) -> Int {
        trim(&mut mag);
        let neg = neg && !mag.is_empty();
        Int { neg, mag }
    }
    pub fn is_zero(&self) -> bool {
        self.mag.is_empty()
    }
    pub fn is_neg(&self) -> bool {
        self.neg
    }
    pub fn sign(&self) -> i32 {
        if self.mag.is_empty() {
            0
        } else if self.neg {
            -1
        } else {
            1
        }
    }
    pub fn neg(&self) -> Int {
        Int::make(!self.neg, self.mag.clone())
    }
    pub fn abs(&self) -> Int {
        Int::make(false, self.mag.clone())
    }
    pub fn add(&self, o: &Int) -> Int {
        if self.neg == o.neg {
            return Int::make(self.neg, add_mag(&self.mag, &o.mag));
        }
        match cmp_mag(&self.mag, &o.mag) {
            Ordering::Equal => Int::zero(),
            Ordering::Greater => Int::make(self.neg, sub_mag(&self.mag, &o.mag)),
            Ordering::Less => Int::make(o.neg, sub_mag(&o.mag, &self.mag)),
        }
    }
    pub fn sub(&self, o: &Int) -> Int {
        self.add(&o.neg())
    }
    pub fn mul(&self, o: &Int) -> Int {
        Int::make(self.neg != o.neg, mul_mag(&self.mag, &o.mag))
    }
    pub fn mul_small(&self, k: u32) -> Int {
        Int::make(self.neg, mul_mag(&self.mag, &[k]))
    }
    pub fn add_small(&self, k: u32) -> Int {
        self.add(&Int::from_u64(k as u64))
    }
    /// the parity of the value (the same for the negative number as for its magnitude)
    pub fn is_odd(&self) -> bool {
        self.mag.first().map_or(false, |l| l & 1 == 1)
    }
    /// half of an even number (exact)
    pub fn half_exact(&self) -> Int {
        Int::make(self.neg, shr_mag(&self.mag, 1))
    }

    pub fn bit_length(&self) -> u64 {
        bit_len_mag(&self.mag)
    }
    pub fn shl(&self, n: u64) -> Int {
        Int::make(self.neg, shl_mag(&self.mag, n))
    }
    pub fn cmp(&self, o: &Int) -> Ordering {
        match (self.sign(), o.sign()) {
            (a, b) if a != b => a.cmp(&b),
            (0, _) => Ordering::Equal,
            (1, _) => cmp_mag(&self.mag, &o.mag),
            _ => cmp_mag(&o.mag, &self.mag),
        }
    }
    /// truncating division: (quotient, remainder) with the sign of the dividend on the remainder
    pub fn divrem(&self, o: &Int) -> (Int, Int) {
        let (q, r) = divrem_mag(&self.mag, &o.mag);
        (Int::make(self.neg != o.neg, q), Int::make(self.neg, r))
    }
    pub fn gcd(&self, o: &Int) -> Int {
        let mut a = self.abs();
        let mut b = o.abs();
        while !b.is_zero() {
            let (_, r) = a.divrem(&b);
            a = b;
            b = r;
        }
        a
    }
    pub fn to_i64(&self) -> Option<i64> {
        if self.mag.len() > 2 {
            return None;
        }
        let m = self.mag.first().map_or(0u64, |&l| l as u64) | ((self.mag.get(1).map_or(0u64, |&l| l as u64)) << 32);
        if self.neg {
            if m <= i64::MAX as u64 + 1 {
                Some((m as i64).wrapping_neg())
            } else {
                None
            }
        } else if m <= i64::MAX as u64 {
            Some(m as i64)
        } else {
            None
        }
    }
    pub fn parse_dec(s: &str) -> Int {
        let mut r = Int::zero();
        let bytes: Vec<u8> = s.bytes().filter(|b| b.is_ascii_digit()).collect();
        for chunk in bytes.chunks(9) {
            let mut k = 0u32;
            for &b in chunk {
                k = k * 10 + (b - b'0') as u32;
            }
            r = r.mul_small(10u32.pow(chunk.len() as u32)).add_small(k);
        }
        r
    }
    pub fn pow_small(base: u32, exp: u32) -> Int {
        let mut r = Int::from_u64(1);
        for _ in 0..exp {
            r = r.mul_small(base);
        }
        r
    }
    pub fn to_dec(&self) -> String {
        if self.mag.is_empty() {
            return "0".to_string();
        }
        let mut chunks: Vec<u32> = vec![];
        let mut cur = self.mag.clone();
        while !cur.is_empty() {
            let mut rem = 0u64;
            for i in (0..cur.len()).rev() {
                let x = (rem << 32) | cur[i] as u64;
                cur[i] = (x / 1_000_000_000) as u32;
                rem = x % 1_000_000_000;
            }
            trim(&mut cur);
            chunks.push(rem as u32);
        }
        let mut s = String::new();
        if self.neg {
            s.push('-');
        }
        s.push_str(&chunks.last().unwrap().to_string());
        for c in chunks.iter().rev().skip(1) {
            s.push_str(&format!("{:09}", c));
        }
        s
    }
}

/// a rational number in lowest terms with a positive denominator (Haskell's Rational, for the `eval` command)
#[derive(Clone, Debug)]
pub struct Rat {
    pub num: Int,
    pub den: Int,
}

impl Rat {
    pub fn new(num: Int, den: Int) -> Rat {
        let (mut num, mut den) = (num, den);
        if den.is_neg() {
            num = num.neg();
            den = den.neg();
        }
        let g = num.gcd(&den);
        if !g.is_zero() && g != Int::from_u64(1) {
            num = num.divrem(&g).0;
            den = den.divrem(&g).0;
        }
        Rat { num, den }
    }
    pub fn is_zero(&self) -> bool {
        self.num.is_zero()
    }
    pub fn is_int(&self) -> bool {
        self.den == Int::from_u64(1)
    }
    /// the integer part, truncated towards zero
    pub fn truncate(&self) -> Int {
        self.num.divrem(&self.den).0
    }
    /// the nearest double (ties to even), as Haskell's fromRational and Python's float(Fraction) give it
    pub fn to_f64(&self) -> f64 {
        if self.num.is_zero() {
            return 0.0;
        }
        let neg = self.num.is_neg();
        let a = self.num.abs();
        let b = &self.den;
        // scale so that the quotient has 55 or 56 significant bits
        let shift: i64 = 55 - (a.bit_length() as i64 - b.bit_length() as i64);
        let (n, d) = if shift >= 0 { (a.shl(shift as u64), b.clone()) } else { (a.clone(), b.shl((-shift) as u64)) };
        let (q, r) = n.divrem(&d);
        let mut qbits = q.bit_length() as i64; // 55 or 56
        let mut q = q;
        let mut sticky = !r.is_zero();
        // value = q * 2^(-shift); the exponent of the leading bit is qbits - 1 - shift
        let mut exp2 = qbits - 1 - shift;
        // number of mantissa bits kept: 53, fewer for subnormals
        let keep: i64 = if exp2 >= -1022 { 53 } else { 53 - (-1022 - exp2) };
        if keep <= 0 {
            return if neg { -0.0 } else { 0.0 };
        }
        let drop = qbits - keep;
        if drop > 0 {
            let half_bit = q.bit_at((drop - 1) as u64);
            let below = q.low_bits_nonzero((drop - 1) as u64) || sticky;
            let mut m = q.shr((drop) as u64);
            if half_bit && (below || m.is_odd()) {
                m = m.add_small(1);
            }
            // rounding may carry into a new bit
            if m.bit_length() as i64 > keep {
                m = m.shr(1);
                exp2 += 1;
            }
            q = m;
            sticky = false;
            qbits = keep;
        }
        let _ = sticky;
        let mant = q.to_i64().unwrap_or(0) as u64;
        // value = mant * 2^(exp2 - (qbits - 1))
        let e = exp2 - (qbits - 1);
        let mut x = mant as f64;
        // scale by 2^e in safe steps
        let mut e = e;
        while e > 0 {
            let s = e.min(1000);
            x *= 2f64.powi(s as i32);
            e -= s;
        }
        while e < 0 {
            let s = (-e).min(1000);
            x /= 2f64.powi(s as i32);
            e += s;
        }
        if neg {
            -x
        } else {
            x
        }
    }
}

impl Int {
    fn bit_at(&self, i: u64) -> bool {
        bit_mag(&self.mag, i)
    }
    fn low_bits_nonzero(&self, n: u64) -> bool {
        // is any of the lowest n bits set?
        let full = (n / 32) as usize;
        for i in 0..full.min(self.mag.len()) {
            if self.mag[i] != 0 {
                return true;
            }
        }
        let rem = (n % 32) as u32;
        if rem > 0 && full < self.mag.len() {
            return self.mag[full] & ((1u32 << rem) - 1) != 0;
        }
        false
    }
    fn shr(&self, n: u64) -> Int {
        Int::make(self.neg, shr_mag(&self.mag, n))
    }
}

impl PartialOrd for Int {
    fn partial_cmp(&self, o: &Int) -> Option<Ordering> {
        Some(Int::cmp(self, o))
    }
}

impl Ord for Int {
    fn cmp(&self, o: &Int) -> Ordering {
        Int::cmp(self, o)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn arithmetic() {
        let a = Int::parse_dec("123456789012345678901234567890");
        let b = Int::parse_dec("987654321098765432109876543210");
        assert_eq!(a.add(&b).to_dec(), "1111111110111111111011111111100");
        assert_eq!(b.sub(&a).to_dec(), "864197532086419753208641975320");
        assert_eq!(a.mul(&b).to_dec(), "121932631137021795226185032733622923332237463801111263526900");
        let (q, r) = b.divrem(&a);
        assert_eq!(q.to_dec(), "8");
        assert_eq!(r.to_dec(), "9000000000900000000090");
        assert_eq!(Int::from_i64(-5).divrem(&Int::from_i64(2)).0.to_i64(), Some(-2));
        assert_eq!(Int::from_i64(-5).divrem(&Int::from_i64(2)).1.to_i64(), Some(-1));
        assert_eq!(a.gcd(&b).to_dec(), "9000000000900000000090");
    }

    #[test]
    fn floats() {
        let r = Rat::new(Int::from_i64(1), Int::from_i64(3));
        assert_eq!(r.to_f64(), 1.0 / 3.0);
        let r = Rat::new(Int::parse_dec("355"), Int::parse_dec("113"));
        assert_eq!(r.to_f64(), 355.0 / 113.0);
        let r = Rat::new(Int::from_i64(-7), Int::from_i64(2));
        assert_eq!(r.to_f64(), -3.5);
        let big = Rat::new(Int::parse_dec("1000000000000000000000000000000"), Int::parse_dec("3"));
        assert_eq!(big.to_f64(), 1e30 / 3.0);
    }
}
