//! selftest.rs -- `compimo selftest [N] [SEED]`: the native arithmetic on digit strings against the definitions of the prelude.
//!
//! A program applies the functions of lib/number.imo (⊞ᶻ ⊟ᶻ ⊠ᶻ ⊖ᶻ ≡ ⊡ ∅ᶻ ⩾ᶻ realᶻ) to random strings of digits, including strings with zeros at the high
//! end, and prints every result as a string of 0 and 1.  It is run twice by this very executable: as it is (the native versions are used) and with IMO_NONAT=1 (the
//! definitions are compiled and used): the outputs must be the same, byte for byte.  Given the path of another core (--against PATH, e.g. build/rustimo) the output
//! is compared with that core as well.
use std::process::Command;

struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }
    fn below(&mut self, n: u64) -> u64 {
        self.next() % n
    }
}

/// a digit string written most significant digit first (so the list, least significant first, is the reverse)
fn numeral(r: &mut Rng) -> String {
    const LENS: [u64; 13] = [0, 1, 2, 3, 4, 6, 8, 12, 20, 33, 60, 90, 120];
    let n = LENS[r.below(LENS.len() as u64) as usize];
    let mut ds: String = (0..n).map(|_| if r.below(2) == 0 { '0' } else { '1' }).collect();
    if r.below(2) == 0 {
        ds = format!("{}{}", "0".repeat(r.below(5) as usize), ds);
    }
    if ds.is_empty() {
        ds = "0".to_string();
    }
    ds
}

fn list(ds: &str) -> String {
    let mut r = "⊘".to_string();
    for c in ds.chars() {
        r = format!("(∷ {} {})", if c == '1' { "⊤" } else { "⊥" }, r);
    }
    r
}

fn program(n: usize, seed: u64) -> String {
    let mut r = Rng(seed.wrapping_mul(0x9E3779B97F4A7C15) | 1);
    let mut s = String::new();
    s.push_str("dstr ∶ 𝔇 → 𝕊\ndstr ξ ≔ (⫶ (η ∶ 𝔹 ↦ (⁇ η '1' '0')) ξ)\nbstr ∶ 𝔹 → 𝕊\nbstr ξ ≔ (⁇ ξ \"T\" \"F\")\nmain ∶ 𝔏 𝕊\nmain ≔ ");
    let mut items = vec![];
    for _ in 0..n {
        let (x, y) = (list(&numeral(&mut r)), list(&numeral(&mut r)));
        items.push(format!("(dstr (⊞ᶻ {} {}))", x, y));
        items.push(format!("(dstr (⊟ᶻ {} {}))", x, y));
        items.push(format!("(dstr (⊠ᶻ {} {}))", x, y));
        items.push(format!("(dstr (⊖ᶻ {}))", x));
        items.push(format!("(bstr (≡ {} {}))", x, y));
        items.push(format!("(dstr (⊡ {}))", x));
        items.push(format!("(bstr (∅ᶻ {}))", x));
        items.push(format!("(bstr (⩾ᶻ {} {}))", x, y));
        items.push(format!("(bstr (realᶻ {}))", x));
    }
    for it in &items {
        s.push_str(&format!("(∷ {} ", it));
    }
    s.push('⊘');
    s.push_str(&")".repeat(items.len()));
    s.push('\n');
    s
}

fn run(exe: &str, file: &std::path::Path, nonat: bool) -> Result<String, String> {
    let mut cmd = Command::new(exe);
    cmd.arg("run").arg(file);
    if nonat {
        cmd.env("IMO_NONAT", "1");
    }
    let out = cmd.output().map_err(|e| format!("cannot run {}: {}", exe, e))?;
    Ok(String::from_utf8_lossy(&out.stdout).to_string() + &String::from_utf8_lossy(&out.stderr))
}

pub fn selftest(args: &[String]) -> i32 {
    let mut n = 25usize;
    let mut seed = 1u64;
    let mut against: Option<String> = None;
    let mut it = args.iter();
    let mut pos = 0;
    while let Some(a) = it.next() {
        if a == "--against" {
            against = it.next().cloned();
        } else if pos == 0 {
            n = a.parse().unwrap_or(n);
            pos += 1;
        } else {
            seed = a.parse().unwrap_or(seed);
        }
    }
    let me = std::env::current_exe().map(|p| p.to_string_lossy().to_string()).unwrap_or_else(|_| "compimo".to_string());
    let dir = std::env::temp_dir().join(format!("compimo-selftest-{}", std::process::id()));
    let _ = std::fs::create_dir_all(&dir);
    let mut bad = 0;
    for round in 0..4u64 {
        let file = dir.join(format!("native{}.imo", round));
        if std::fs::write(&file, program(n, seed + round)).is_err() {
            eprintln!("selftest: cannot write {}", file.display());
            return 2;
        }
        let a = run(&me, &file, false);
        let b = run(&me, &file, true);
        match (a, b) {
            (Ok(a), Ok(b)) => {
                let lines = a.lines().count();
                if a == b && lines >= 9 * n {
                    println!("round {}: {} results, native == definition", round, lines);
                } else {
                    println!("round {}: DIFFERENT ({} and {} lines)", round, a.lines().count(), b.lines().count());
                    bad += 1;
                }
                if let Some(other) = &against {
                    match run(other, &file, false) {
                        Ok(c) if c == a => println!("round {}: == {}", round, other),
                        Ok(_) => {
                            println!("round {}: DIFFERENT from {}", round, other);
                            bad += 1;
                        }
                        Err(e) => {
                            println!("{}", e);
                            bad += 1;
                        }
                    }
                }
            }
            (Err(e), _) | (_, Err(e)) => {
                println!("{}", e);
                bad += 1;
            }
        }
    }
    let _ = std::fs::remove_dir_all(&dir);
    if bad == 0 {
        println!("selftest: ok");
        0
    } else {
        println!("selftest: {} failures", bad);
        1
    }
}
