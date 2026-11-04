{-# LANGUAGE ScopedTypeVariables #-}
-- | Serve.hs -- "haskimo serve FILE...": a loaded program as a service, for the shared test suite.
--
-- The library suites of tests/ were written against the Python API of Pymo (load a program, take the value of a symbol, decode it).
-- To run the same suites on Haskimo, tests/core_haskimo.py starts  haskimo serve  and speaks this protocol: one request per line on
-- standard input, one answer per line on standard output.  Values stay inside haskimo and are named by HANDLES (small numbers);
-- only digit strings, truth values and the shape of lists and pairs cross the pipe — what the Python decoders (to_list, to_pair,
-- to_bool, stream_nth) read from a value in Pymo.
--
--   after the load:  OK   |   ERRORS n   followed by n lines  file TAB what TAB message
--
--   NAME x            -> S spec-name           the spec symbol of a human name (Hum.specName)
--   V s               -> H h                   the value of the global s
--   APPLY f a ...     -> H h                   f applied to the values a ...  (lazily)
--   MK bits           -> H h                   a digit list (least significant digit first; bits may be empty)
--   CELL h            -> N  |  C hh ht         a list cell
--   LIST h            -> L n h1 ... hn         all the elements of a (finite) list
--   PAIR h            -> P ha hb
--   BOOL h            -> B 1 | B 0 | B ?
--   DIGITS h          -> D bits                a digit list, least significant digit first
--   Q h               -> Q zbits|dbits         a pair of digit lists (an element of ℚ[i])
--   ORD h             -> O k                   an ordering (0, 1 or 2: the alternative it selects)
--   NTH h n           -> H h'                  element n of a stream
--   CLASS s           -> T json                the declared class of the symbol s, normalised: ["K",name,[args]] ["V",name] ["F","⊥"]
--   an error          -> ERR message           (the exception, on one line)
module I1.Serve (serve) where

import Control.Exception
import Data.IORef
import qualified Data.IntMap.Lazy as IM
import qualified Data.Map.Strict as M
import System.IO
import I1.Core
import I1.Hum (specName)
import I1.Program
import I1.Syntax
import I1.Types

data Tab = Tab !Int (IM.IntMap V)

serve :: Program -> IO ()
serve p = do
  hSetEncoding stdin utf8
  hSetEncoding stdout utf8
  hSetBuffering stdout (BlockBuffering Nothing)
  ref <- newIORef (Tab 0 IM.empty)
  let new :: V -> IO Int
      new v = atomicModifyIORef' ref (\(Tab n t) -> (Tab (n + 1) (IM.insert n v t), n))
      get :: String -> IO V
      get s = case reads s of
        [(h, "")] -> do
          Tab _ t <- readIORef ref
          maybe (throwIO (ErrorCall ("no handle " ++ s))) return (IM.lookup h t)
        _ -> throwIO (ErrorCall ("bad handle " ++ show s))
      bitsOf :: V -> String
      bitsOf v = map (\d -> if d == 1 then '1' else '0') (toList v)
      handle :: [String] -> IO String
      handle ws = case ws of
        ["NAME", n] -> return ("S " ++ specName (pHum p) n)
        ["V", n] -> case pMachine p >>= M.lookup n of
          Just v -> do h <- new v; return ("H " ++ show h)
          Nothing -> throwIO (ErrorCall (n ++ " is not defined"))
        ("APPLY" : f : as) -> do
          fv <- get f
          avs <- mapM get as
          h <- new (foldl apply fv avs)
          return ("H " ++ show h)
        ("MK" : rest) -> do
          let bits = concat rest
          m <- maybe (throwIO (ErrorCall "the program is not built")) return (pMachine p)
          h <- new (listValue m [if c == '1' then 1 else 0 | c <- bits])
          return ("H " ++ show h)
        ["CELL", h] -> do
          v <- get h
          case cellOrNil v of
            VCons a b -> do ha <- new a; hb <- new b; return ("C " ++ show ha ++ " " ++ show hb)
            VNil -> return "N"
            _ -> throwIO (ErrorCall "a list was expected")
        ["LIST", h] -> do
          v <- get h
          let walk x acc = case cellOrNil x of
                VCons a b -> do ha <- new a; walk b (ha : acc)
                VNil -> return (reverse acc)
                _ -> throwIO (ErrorCall "a list was expected")
          hs <- walk v []
          return (unwords ("L" : show (length hs) : map show hs))
        ["PAIR", h] -> do
          v <- get h
          let (a, b) = toPair v
          ha <- new a
          hb <- new b
          return ("P " ++ show ha ++ " " ++ show hb)
        ["BOOL", h] -> do
          v <- get h
          return (case apply (apply v VT) VF of VT -> "B 1"; VF -> "B 0"; _ -> "B ?")
        ["DIGITS", h] -> do v <- get h; return ("D " ++ bitsOf v)
        ["Q", h] -> do
          v <- get h
          let (z, d) = toPair v
          return ("Q " ++ bitsOf z ++ "|" ++ bitsOf d)
        ["ORD", h] -> do v <- get h; return ("O " ++ show (toOrd v))
        ["NTH", h, n] -> do
          v <- get h
          r <- new (streamNth v (read n))
          return ("H " ++ show r)
        ["CLASS", s] -> case M.lookup s (cSigs (pChecker p)) of
          Just (t : _) -> return ("T " ++ json (norm (pChecker p) t))
          _ -> throwIO (ErrorCall (s ++ " has no declared class"))
        _ -> throwIO (ErrorCall ("bad request " ++ show (unwords ws)))
      loop = do
        eof <- isEOF
        if eof then return () else do
          line <- getLine
          case words line of
            ["QUIT"] -> return ()
            ws -> do
              r <- try (handle ws >>= \s -> evaluate (length s) >> return s)
              reply (case r of
                       Right s -> s
                       Left (e :: SomeException) -> "ERR " ++ oneLine (show e))
              loop
      reply s = putStrLn s >> hFlush stdout
  loop

oneLine :: String -> String
oneLine = map (\c -> if c == '\n' || c == '\t' then ' ' else c)

json :: Ty -> String
json t = case t of
  K n as -> "[\"K\"," ++ str n ++ ",[" ++ commas (map json as) ++ "]]"
  V n -> "[\"V\"," ++ str n ++ "]"
  F -> "[\"F\",\"⊥\"]"
  where
    str s = "\"" ++ concatMap esc s ++ "\""
    esc '"' = "\\\""
    esc '\\' = "\\\\"
    esc c = [c]
    commas [] = ""
    commas xs = foldr1 (\a b -> a ++ "," ++ b) xs
