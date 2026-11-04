//! data.rs -- the system files of the language, embedded at build time (lib/*.imo, docs/doc1.sbl, docs/doc2.sbl), so that
//! rustimo is one relocatable file that carries the same prelude as Pymo reads from lib/ and Haskimo embeds.

pub const DOC1: &str = include_str!("../../docs/doc1.sbl");
pub const DOC2: &str = include_str!("../../docs/doc2.sbl");

/// the prelude files (lib/*.imo), in loading order (pymo/imo.py PRELUDE), as (path, text)
pub fn lib_files() -> Vec<(&'static str, &'static str)> {
    vec![
        ("lib/logic.imo", include_str!("../../lib/logic.imo")),
        ("lib/number.imo", include_str!("../../lib/number.imo")),
        ("lib/algebra.imo", include_str!("../../lib/algebra.imo")),
        ("lib/bounded.imo", include_str!("../../lib/bounded.imo")),
        ("lib/analysis.imo", include_str!("../../lib/analysis.imo")),
        ("lib/arith.imo", include_str!("../../lib/arith.imo")),
        ("lib/list.imo", include_str!("../../lib/list.imo")),
        ("lib/real.imo", include_str!("../../lib/real.imo")),
        ("lib/linalg.imo", include_str!("../../lib/linalg.imo")),
        ("lib/set.imo", include_str!("../../lib/set.imo")),
        ("lib/text.imo", include_str!("../../lib/text.imo")),
        ("lib/poly.imo", include_str!("../../lib/poly.imo")),
        ("lib/complex.imo", include_str!("../../lib/complex.imo")),
        ("lib/numtheory.imo", include_str!("../../lib/numtheory.imo")),
        ("lib/ring.imo", include_str!("../../lib/ring.imo")),
        ("lib/field.imo", include_str!("../../lib/field.imo")),
        ("lib/group.imo", include_str!("../../lib/group.imo")),
        ("lib/galois.imo", include_str!("../../lib/galois.imo")),
        ("lib/prove.imo", include_str!("../../lib/prove.imo")),
        ("lib/solve.imo", include_str!("../../lib/solve.imo")),
        ("lib/codec.imo", include_str!("../../lib/codec.imo")),
    ]
}
