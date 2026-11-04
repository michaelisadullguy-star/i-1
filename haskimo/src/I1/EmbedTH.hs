{-# LANGUAGE TemplateHaskell #-}
-- | EmbedTH.hs -- compile-time embedding of the system files (lib/*.imo, docs/doc1.sbl, docs/doc2.sbl) into the executable,
-- so that haskimo is one relocatable file that carries the same prelude as Pymo reads from lib/.
module I1.EmbedTH (embedText, embedLib, preludeNames) where

import Language.Haskell.TH
import Language.Haskell.TH.Syntax (addDependentFile)
import System.IO

-- | the prelude, in loading order (pymo/imo.py PRELUDE)
preludeNames :: [String]
preludeNames =
  [ "logic.imo", "number.imo", "algebra.imo", "bounded.imo", "analysis.imo", "arith.imo", "list.imo", "real.imo"
  , "linalg.imo", "set.imo", "text.imo", "poly.imo", "complex.imo", "numtheory.imo", "ring.imo", "field.imo"
  , "group.imo", "galois.imo", "prove.imo", "solve.imo", "codec.imo" ]

readUtf8 :: FilePath -> IO String
readUtf8 p = do
  h <- openFile p ReadMode
  hSetEncoding h utf8
  s <- hGetContents h
  length s `seq` hClose h
  return s

embedText :: FilePath -> Q Exp
embedText p = do
  addDependentFile p
  s <- runIO' (readUtf8 p)
  litE (stringL s)

-- | [(path, text)] of the prelude files, in loading order
embedLib :: Q Exp
embedLib = listE
  [ do let p = "lib/" ++ n
       addDependentFile p
       s <- runIO' (readUtf8 p)
       tupE [litE (stringL p), litE (stringL s)]
  | n <- preludeNames ]

runIO' :: IO a -> Q a
runIO' = runIO
