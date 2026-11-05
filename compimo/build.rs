// build.rs -- the prelude files, as Rust source: one include_str! per line of lib/MANIFEST, in loading order (the list every core shares).
use std::{env, fs, path::Path};

fn main() {
    let dir = env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR");
    let lib = Path::new(&dir).join("..").join("lib");
    let list = fs::read_to_string(lib.join("MANIFEST")).expect("lib/MANIFEST");
    let mut out = String::from("vec![\n");
    for line in list.lines() {
        let name = line.trim();
        if name.is_empty() || name.starts_with('⍝') {
            continue;
        }
        let path = lib.join(name);
        out.push_str(&format!("        (\"lib/{}\", include_str!({:?})),\n", name, path.to_str().expect("path")));
    }
    out.push_str("    ]\n");
    fs::write(Path::new(&env::var("OUT_DIR").expect("OUT_DIR")).join("lib_files.rs"), out).expect("lib_files.rs");
    println!("cargo:rerun-if-changed=../lib/MANIFEST");
}
