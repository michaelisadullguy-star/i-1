//! data.rs -- the system files of the language, embedded at build time (lib/*.imo, docs/doc1.sbl, docs/doc2.sbl), so that
//! rustimo is one relocatable file that carries the same prelude as Pymo reads from lib/ and Haskimo embeds.

pub const DOC1: &str = include_str!("../../docs/doc1.sbl");
pub const DOC2: &str = include_str!("../../docs/doc2.sbl");

/// the prelude files (lib/*.imo), in loading order (lib/MANIFEST, turned into code by build.rs), as (path, text)
pub fn lib_files() -> Vec<(&'static str, &'static str)> {
    include!(concat!(env!("OUT_DIR"), "/lib_files.rs"))
}
