{-# LANGUAGE TemplateHaskell #-}
-- | EmbedTH.hs -- compile-time embedding of the system files (lib/*.imo, docs/doc1.sbl, docs/doc2.sbl) into the executable,
-- so that haskimo is one relocatable file that carries the same prelude as Pymo reads from lib/.
module I1.EmbedTH (embedText, embedLib) where

import Language.Haskell.TH
import Language.Haskell.TH.Syntax (addDependentFile)
import System.IO

-- | the prelude, in loading order: lib/MANIFEST (one file of lib/ per line, ⍝ starts a comment), the list every core shares
preludeNames :: Q [String]
preludeNames = do
  addDependentFile "lib/MANIFEST"
  s <- runIO' (readUtf8 "lib/MANIFEST")
  return [ n | l <- lines s, let n = trim l, not (null n), take 1 n /= "⍝" ]
  where trim = reverse . dropWhile (`elem` " \t\r") . reverse . dropWhile (`elem` " \t\r")

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
embedLib = do
  names <- preludeNames
  listE
    [ do let p = "lib/" ++ n
         addDependentFile p
         s <- runIO' (readUtf8 p)
         tupE [litE (stringL p), litE (stringL s)]
    | n <- names ]

runIO' :: IO a -> Q a
runIO' = runIO
