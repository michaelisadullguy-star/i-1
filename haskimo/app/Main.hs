{-# LANGUAGE ScopedTypeVariables #-}
-- | Main.hs -- command line of Haskimo, the Haskell interpreter of i-1 (port of pymo/i1.py, the command line of Pymo).
--
--   haskimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  haskimo FILE...)
--   haskimo check   FILE...                                load the prelude and FILE(s), run the class checker
--   haskimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table
--   haskimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class
--   haskimo text    FILE... NAME                           evaluate NAME as a String and print it
--
-- The commands, options and output are those of  python3 pymo/i1.py  (Pymo, its parallel core in Python).
module Main (main) where

import Control.Exception
import Data.List (isPrefixOf, isSuffixOf)
import qualified Data.Map.Strict as M
import Data.Maybe (fromMaybe)
import Data.Ratio
import System.Directory (doesFileExist)
import System.Environment (getArgs)
import System.Exit
import System.IO
import I1.Base
import I1.Core
import I1.Hum (specName)
import I1.Layers
import I1.Output
import I1.Program
import I1.Serve (serve)
import I1.Syntax
import I1.Types

usage :: String
usage = unlines
  [ "haskimo -- Haskimo, the Haskell interpreter of i-1 (same commands and output as Pymo, python3 pymo/i1.py)"
  , ""
  , "  haskimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  haskimo FILE...)"
  , "  haskimo check   FILE...                                load the prelude and FILE(s), run the class checker"
  , "  haskimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table"
  , "  haskimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class (value, stream element N, tree, string, Bool)"
  , "  haskimo text    FILE... NAME                           evaluate NAME as a String and print it"
  , "  haskimo serve   FILE...                                load FILE(s) and answer requests on standard input (tests/core_haskimo.py)"
  , ""
  , "`run` prints main ∶ 𝕊 as text, a list or stream of strings line by line, and any other value as a normal-form term in the output"
  , "notation: --out, else an `@out bin|spec|hum` line in the program, else the notation main is written in.  --n N picks the stream"
  , "element shown for a stream (default 10), or the number of lines of a stream of strings."
  , ""
  , "FILE notation follows the extension:  x.imo / x.spec.imo = spec,  x.hum.imo = human,  x.bin.imo = binary (prelude.bin.imo is trusted)."
  ]

loadFiles :: [FilePath] -> IO Program
loadFiles files = do
  srcs <- mapM (\f -> SourceFile f <$> readUtf8 f) files
  let prelude = [f | f <- files, "prelude.bin.imo" `isSuffixOf` f]
  p <- loadProgram srcs prelude (null prelude)
  case missingOf p of
    [] -> return p
    ms -> throwIO (ParseError ("these symbols are used and not defined: " ++ unwords ms))

reportErrors :: Program -> IO ()
reportErrors p = mapM_ (\(f, w, m) ->
  putStrLn ("error in " ++ basename f ++ ": " ++ (if w `isPrefixOf` m then m else w ++ ": " ++ m))) (pErrors p)

-- ---------------------------------------------------------------- values of ℚ[i], as Pymo shows them
qval :: V -> (Rational, Rational)
qval v =
  let (p, d) = toPair v
      (a0, a1) = giOf p
      (b0, b1) = giOf d
      n = b0 * b0 + b1 * b1
  in ((a0 * b0 + a1 * b1) % n, (a1 * b0 - a0 * b1) % n)

showFrac :: Rational -> String
showFrac r = if denominator r == 1 then show (numerator r) else show (numerator r) ++ "/" ++ show (denominator r)

toF :: Rational -> Rational
toF r = toRational (fromRational r :: Double)

qfmt :: V -> String
qfmt v =
  let (re, im) = qval v
      s = if im == 0 then showFrac re else showFrac re ++ " + " ++ showFrac im ++ " i"
  in s ++ "   (≈ " ++ fmtG 12 (toF re) ++ (if im == 0 then "" else " + " ++ fmtG 12 (toF im) ++ " i") ++ ")"

sfmt :: V -> String
sfmt v = case cellOrNil v of
  VCons h t -> toEnum (fromInteger (truncate (fst (qval h)))) : sfmt t
  _ -> []

tfmt :: Program -> V -> Maybe Int -> String
tfmt p v n =
  let leftF = pval p "◀"
      rightF = pval p "▶"
  in if toBool (apply leftF v)
       then let (a, b) = toPair (apply rightF v) in "⟨" ++ tfmt p a n ++ ", " ++ tfmt p b n ++ "⟩"
       else
         let leaf0 = apply rightF v
             leaf = maybe leaf0 (streamNth leaf0) n
             (re, im) = qval leaf
         in case n of
              Just _ -> fmtG 10 (toF re) ++ (if im == 0 then "" else " + " ++ fmtG 10 (toF im) ++ " i")
              Nothing -> if im == 0 then showFrac re else "(" ++ showFrac re ++ " + " ++ showFrac im ++ " i)"

-- | evaluate NAME and print it according to its declared class
showName :: Program -> String -> Maybe Int -> IO String
showName p name n = do
  let c = pChecker p
      cls = norm c (head (M.findWithDefault [] name (cSigs c)))
      v = pval p name
      hd = case cls of K h _ -> h; _ -> ""
  case cls of
    K h _ | h == "𝔖" || h == "ℝ" -> do
      let k = fromMaybe 10 n
      return ("element " ++ show k ++ " of the stream:  " ++ qfmt (streamNth v k))
    K "𝔏" [K "𝕮" _] -> return (sfmt v)
    K "𝔗" [inner] -> do
      let streams = case inner of K "𝔖" _ -> True; _ -> False
          k = fromMaybe 10 n
      return ((if streams then "element " ++ show k ++ " of each leaf:  " else "") ++ tfmt p v (if streams then Just k else Nothing))
    _ | hd == "𝔹" -> return (if toBool v then "true" else "false")
      | 'Ω' `elem` showType cls -> showValue (Printer p "hum" 10) v cls
      | otherwise -> return (qfmt v)

-- ---------------------------------------------------------------- commands
runCmd :: [String] -> IO ExitCode
runCmd args0 = do
  let (out, r1) = takeOpt "--out" args0
      (nOpt, rest) = takeOpt "--n" r1
  case out of
    Just o | o `notElem` modes -> do putStrLn ("--out takes one of " ++ commaJoin modes); return (ExitFailure 2)
    _ -> do
      p <- loadFiles rest
      if not (null (pErrors p)) then reportErrors p >> return (ExitFailure 1)
      else do
        r <- try (runMain p out (fmap read nOpt) (\s -> hPutStr stdout s))
        case r of
          Right _ -> return ExitSuccess
          Left (PrintError e) -> do putStrLn ("error: " ++ e); return (ExitFailure 1)
          Left e -> throwIO e

commaJoin :: [String] -> String
commaJoin [] = ""
commaJoin xs = foldr1 (\a b -> a ++ ", " ++ b) xs

-- | remove  OPT value  from an argument list
takeOpt :: String -> [String] -> (Maybe String, [String])
takeOpt opt args = case break (== opt) args of
  (a, _ : v : b) -> (Just v, a ++ b)
  _ -> (Nothing, args)

main :: IO ()
main = do
  hSetEncoding stdout utf8
  hSetEncoding stderr utf8
  tty <- hIsTerminalDevice stdout
  hSetBuffering stdout (if tty then NoBuffering else BlockBuffering Nothing)      -- a terminal sees the output as it is produced, a pipe gets blocks
  args <- getArgs
  code <- dispatch args `catches`
    [ Handler (\(e :: ExitCode) -> throwIO e)
    , Handler (\(e :: ImoError) -> do hFlush stdout; hPutStrLn stderr ("haskimo: " ++ describeErr e); return (ExitFailure 1))
    , Handler (\(e :: SomeException) -> do hFlush stdout; hPutStrLn stderr ("haskimo: " ++ show e); return (ExitFailure 1)) ]
  hFlush stdout
  exitWith code
  where
    describeErr e = case e of
      ParseError m -> m
      UnknownError m -> m
      PrintError m -> m

dispatch :: [String] -> IO ExitCode
dispatch args = case args of
  [] -> putStr usage >> return ExitSuccess
  (h : _) | h `elem` ["-h", "--help"] -> putStr usage >> return ExitSuccess
  (cmd : rest) -> do
    isFile <- doesFileExist cmd
    let (cmd', rest') = if cmd `notElem` ["run", "check", "eval", "text", "translate", "serve"] && isFile then ("run", args) else (cmd, rest)
    case cmd' of
      "run" -> runCmd rest'
      "serve" -> serveCmd rest'
      "translate" -> translateCmd rest'
      c | c `elem` ["check", "eval", "text"] -> queryCmd c rest'
      _ -> putStr usage >> return (ExitFailure 2)

-- | load the program and serve requests about its values: the protocol of I1.Serve
serveCmd :: [FilePath] -> IO ExitCode
serveCmd files = do
  p <- loadFiles files
  if not (null (pErrors p))
    then do
      putStrLn ("ERRORS " ++ show (length (pErrors p)))
      mapM_ (\(f, w, m) -> putStrLn (f ++ "\t" ++ w ++ "\t" ++ map (\c -> if c == '\n' || c == '\t' then ' ' else c) m)) (pErrors p)
      hFlush stdout
      return (ExitFailure 1)
    else do
      putStrLn "OK"
      hFlush stdout
      serve p
      return ExitSuccess

translateCmd :: [String] -> IO ExitCode
translateCmd rest = do
  let to = case dropWhile (/= "--to") rest of (_ : t : _) -> t; _ -> error "--to is missing"
      files = [x | x <- rest, x /= "--to", x /= to]
  p <- loadFiles files
  if not (null (pErrors p)) then reportErrors p >> return (ExitFailure 1)
  else do
    if to == "spec"
      then putStr (specText p)
      else do
        let (p', t) = binText p
        putStr t
        if not (null (dLocal (pDoc1 p'))) then putStr ("\n" ++ localTable p') else return ()
    return ExitSuccess

queryCmd :: String -> [String] -> IO ExitCode
queryCmd cmd rest = do
  (files, name, n) <-
    if cmd == "check" then return (rest, Nothing, Nothing)
    else do
      flags <- mapM (\x -> do e <- doesFileExist x; return (x, e)) rest
      let fs = [x | (x, True) <- flags]
          tl = [x | (x, False) <- flags]
      case tl of
        [] -> throwIO (ParseError "a name is expected")
        (nm : more) -> return (fs, Just nm, case more of (k : _) -> Just (read k :: Int); _ -> Nothing)
  p <- loadFiles files
  if not (null (pErrors p)) then reportErrors p >> return (ExitFailure 1)
  else if cmd == "check"
    then do putStrLn ("ok: " ++ show (length (userStatements p)) ++ " statements checked"); return ExitSuccess
    else do
      let nm = specName (pHum p) (fromMaybe "" name)
      r <- try (do
        s <- if cmd == "text" then evaluate' (sfmt (pval p nm)) else showName p nm n
        putStrLn s)
      case r of
        Right () -> return ExitSuccess
        Left (e :: ImoError) -> case e of
          UnknownError m -> putStrLn ("error: " ++ m) >> return (ExitFailure 1)
          PrintError m -> putStrLn ("error: " ++ m) >> return (ExitFailure 1)
          _ -> throwIO e
  where
    evaluate' s = length s `seq` return s

