-- | Program.hs -- loader / driver for i-1 programs (port of pymo/imo.py).
--
-- A file is read in the notation chosen by its extension (x.bin.imo, x.hum.imo, x.imo = spec) or by section headers
-- (@bin  @spec  @hum on a line of their own).  Every section is translated to spec statements, the whole program is
-- checked by the class checker, and the definitions are run by the evaluator (lazy, call-by-need).
--
-- A symbol that the program declares and never defines is an UNKNOWN: its class must be a number class, a statement about it is
-- simplified by lib/solve.imo, and evaluating it is a run-time error (UnknownError).
module I1.Program
  ( Program(..), newProgram, addText, addFile, checkProgram, buildProgram, loadProgram
  , userStatements, specText, binText, localTable, humName, pval, missingOf, SourceFile(..)
  ) where

import Control.Monad.State.Strict (runState)
import Data.List (isInfixOf, isPrefixOf)
import qualified Data.Map.Strict as M
import qualified Data.Set as S
import System.Directory (doesFileExist)
import I1.Base
import I1.Core
import I1.Data
import I1.Hum
import I1.Layers
import I1.Quote
import I1.Syntax
import I1.Types

data Program = Program
  { pDoc1 :: Doc1
  , pDoc2 :: Doc2
  , pHum :: Hum
  , pStatements :: [(FilePath, Stmt, Bool)]       -- ^ file, statement, trusted
  , pChecker :: Checker
  , pResolved :: [Maybe Stmt]                      -- ^ aligned with pStatements (Nothing: the statement had an error)
  , pErrors :: [(FilePath, String, String)]       -- ^ file, what, message
  , pNotationOf :: M.Map String String            -- ^ defined symbol -> the notation of the section that defines it
  , pOutMode :: Maybe String                      -- ^ set by an  @out bin|spec|hum  line
  , pMachine :: Maybe Machine
  }

-- | a source file: its path and its text
data SourceFile = SourceFile FilePath String

newProgram :: Program
newProgram =
  let d1 = doc1Parse doc1Text
      d2 = doc2Remap d1 (doc2Parse doc2Text)
  in Program { pDoc1 = d1, pDoc2 = d2, pHum = mkHum d2, pStatements = []
             , pChecker = emptyChecker { cOverloads = doc2OverloadTable d2 }
             , pResolved = [], pErrors = [], pNotationOf = M.empty, pOutMode = Nothing, pMachine = Nothing }

-- | add the text of a file (or of a string) in the given default notation
addText :: Program -> String -> FilePath -> Bool -> String -> Program
addText p text name trusted notation =
  let ls = splitOn "\n" text
      (outMode, lsRev) = foldl scan (pOutMode p, []) ls
      scan (m, acc) ln = case words ln of
        ["@out", w] | w `elem` ["bin", "spec", "hum"] -> (Just w, "" : acc)
                    | otherwise -> throwParse (name ++ ": @out takes bin, spec or hum, not " ++ w)
        _ -> (m, ln : acc)
      ls' = reverse lsRev
      text' = case ls' of
        [] -> ""
        _ -> foldr1 (\a b -> a ++ "\n" ++ b) ls'
      sections = splitSections text' notation
      step prog (mode, chunk) =
        let sts = case mode of
              "spec" -> parseStatements chunk
              "bin" -> parseStatements (binToSpecText chunk (pDoc1 prog))
              _ -> humStatements (pHum prog) chunk
            added = [(name, st, trusted) | st <- sts]
            notes = [(n, mode) | not trusted, Def n _ _ <- sts]
        in prog { pStatements = pStatements prog ++ added
                , pNotationOf = foldl (\m (n, md) -> M.insert n md m) (pNotationOf prog) notes }
  in foldl step p { pOutMode = outMode } sections

-- | add a file; a bin program brings its local symbol table (x.sbl next to x.bin.imo)
addFile :: Program -> SourceFile -> Bool -> IO Program
addFile p (SourceFile path text) trusted = do
  let local = replaceAll ".spec" "" (replaceAll ".hum" "" (replaceAll ".bin" "" (beforeLastImo path))) ++ ".sbl"
      usesBin = defaultNotation path == "bin" || "\n@bin" `isInfixOf` ('\n' : text)
  p1 <- if not usesBin then return p else do
    ex <- doesFileExist local
    if not ex then return p else do
      tbl <- readUtf8 local
      return (foldl (addLocal local) p (splitOn "\n" tbl))
  return (addText p1 text path trusted (defaultNotation path))
  where
    beforeLastImo s = case [k | k <- [0 .. length s - 4], ".imo" `isPrefixOf` drop k s] of
      [] -> s
      ks -> take (last ks) s
    addLocal local prog line
      | " := " `isInfixOf` line && take 1 line /= "⍝" =
          case splitOn " := " line of
            [a0, b0] ->
              let a = strip a0
                  b = strip b0
                  d = pDoc1 prog
              in if M.member a (dS2B d) then prog
                 else case M.lookup b (dB2S d) of
                   Just other -> throwParse (basename local ++ ": local code " ++ b ++ " for " ++ a ++ " is already doc 1's code for " ++ other
                                             ++ " (doc 1 grew: regenerate the local table with  i1.py translate … --to bin)")
                   Nothing -> prog { pDoc1 = doc1AddLocal d a b }
            _ -> throwParse ("bad line in " ++ basename local)
      | otherwise = prog

-- ---------------------------------------------------------------- checking
checkProgram :: Program -> Program
checkProgram p0 =
  let stmts0 = [x | x@(f, _, _) <- pStatements p0, f /= "<quote>"]
      c0 = unknownsOf stmts0 (pChecker p0)
      (cFinal, rev) = foldl step (c0, []) stmts0
      step (c, acc) (f, st, trusted) =
        let (c', r) = checkStatement c st trusted
        in case r of
             Right st' -> (c', (Right st', f, st) : acc)
             Left e -> (c', (Left e, f, st) : acc)
      results = reverse rev
      resolved = [either (const Nothing) Just r | (r, _, _) <- results]
      errors = [ (f, what st, e) | (Left e, f, st) <- results ]
      what st = case st of
        Def n _ _ -> n
        Decl n _ -> n
        _ -> ppStatement st
      defsForTaint = [ (n, ps, b) | ((_, _, t), Just (Def n ps b)) <- zip stmts0 resolved, not t ]
      c1 = settleTaint cFinal defsForTaint
      p1 = p0 { pStatements = stmts0, pChecker = c1, pResolved = resolved, pErrors = errors }
  in if not (null errors) then p1
     else
       let p2 = codesOf p1
       in if any (\r -> case r of Just (Def _ _ b) -> hasQuote b; _ -> False) (pResolved p2) then quoteProgram p2 else p2

-- | the unknowns (declared by the program, defined nowhere), in declaration order, and a first estimate of which program
-- definitions need their values
unknownsOf :: [(FilePath, Stmt, Bool)] -> Checker -> Checker
unknownsOf stmts c =
  let defined = S.fromList [n | (_, Def n _ _, _) <- stmts]
      order = nubOrd [ n | (_, Decl n ty, False) <- stmts, not (S.member n defined), not (isClassOrStmt ty) ]
      isClassOrStmt ty = let r = lastResult ty in r == K "𝒦" [] || r == K "𝒮" []
      lastResult (K "→" [_, b]) = lastResult b
      lastResult t = t
      user = [(n, ps, b) | (_, Def n ps b, False) <- stmts]
      refs t bound = case t of
        TVar n -> if S.member n bound then S.empty else S.fromList (M.findWithDefault [n] n (cOverloads c))
        TApp f as -> S.unions (refs f bound : [refs a bound | a <- as])
        TLam ps b -> refs b (S.union bound (S.fromList (map fst ps)))
        TAsc e _ -> refs e bound
        _ -> S.empty
      uses = M.fromList [(n, refs b (S.fromList ps)) | (n, ps, b) <- user]
      grow tainted =
        let new = [n | (n, u) <- M.toList uses, not (S.member n tainted), not (S.null (S.intersection u tainted))]
        in if null new then tainted else grow (S.union tainted (S.fromList new))
      tainted = grow (S.fromList order)
  in c { cUnknowns = [(n, Nothing) | n <- order]
       , cUserDefined = S.fromList [n | (n, _, _) <- user]
       , cRawTaint = S.difference tainted (S.fromList order)
       , cTaint = M.empty }

nubOrd :: [String] -> [String]
nubOrd = go S.empty
  where go _ [] = []
        go seen (x : xs) | S.member x seen = go seen xs
                         | otherwise = x : go (S.insert x seen) xs

-- | program-local codes (doc 1 format) for the program's own symbols, assigned when the program is checked and in a fixed order
codesOf :: Program -> Program
codesOf p =
  let c = pChecker p
      order = map fst (cUnknowns c)
              ++ [n | (_, Decl n _, False) <- pStatements p, n /= envName, M.member n (cSigs c)]
      d = foldl (\dd n -> fst (doc1Code dd n True)) (pDoc1 p) order
  in p { pDoc1 = d }

-- | replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝  and add the table of definitions
quoteProgram :: Program -> Program
quoteProgram p =
  let c = pChecker p
      (qr, d1) = mkQuoter c (zip [t | (_, _, t) <- pStatements p] (pResolved p)) (pDoc1 p)
      action = do
        rs <- mapM (\r -> case r of
                       Just (Def n ps b) | hasQuote b -> do b' <- quoteReplace qr b; return (Just (Def n ps b'))
                       _ -> return r) (pResolved p)
        tab <- quoteTable qr
        return (rs, tab)
      ((resolved', tab), st) = runState action (QS d1 [])
      d2 = sDoc st
      envTy = K "𝔏" [K "𝔓" [K "𝔇" [], K "𝔔" []]]
      c' = either (error "quote: ε⌜⌝ declaration") id (declare c envName envTy)
      at = length (takeWhile (\(_, _, t) -> t) (pStatements p))
      declSt = Decl envName envTy
      defSt = Def envName [] tab
      stmts' = take at (pStatements p) ++ [("<quote>", declSt, False), ("<quote>", defSt, False)] ++ drop at (pStatements p)
      res' = take at resolved' ++ [Just declSt, Just defSt] ++ drop at resolved'
  in p { pDoc1 = d2, pChecker = c', pStatements = stmts', pResolved = res' }

-- ---------------------------------------------------------------- building
userStatements :: Program -> [Stmt]
userStatements p = [r | ((_, _, False), Just r) <- zip (pStatements p) (pResolved p)]

specText :: Program -> String
specText p = concatMap (\s -> ppStatement s ++ "\n") (userStatements p)

binText :: Program -> (Program, String)
binText p =
  let (d, t) = specStatementsToBinText (userStatements p) (pDoc1 p) True
  in (p { pDoc1 = d }, t)

localTable :: Program -> String
localTable p = doc1Render (pDoc1 p) ["program-local symbols (same format as doc 1)"]

-- | the human name of a spec symbol (reverse doc 2; a symbol of the program is its own name)
humName :: Program -> String -> String
humName p spec =
  case [eHum e | e <- d2Entries (pDoc2 p), eRole e `elem` ["value", "infixl", "infixr", "infix", "prefix"], spec `elem` eRhs e] of
    (h : _) -> h
    [] -> spec

buildProgram :: Program -> Program
buildProgram p =
  let c = pChecker p
      defs = [eraseDef n ps b | Just (Def n ps b) <- pResolved p]
      unknowns = map fst (cUnknowns c)
      boom n = let h = humName p n in
        throwUnknown (h ++ " is an unknown (it is declared and never defined, so it has no value); "
                      ++ "use it in a statement — a relation such as " ++ h ++ " == 1 — which is simplified, not evaluated")
      m = buildMachineWith defs [(n, boom n) | n <- unknowns]
  in p { pMachine = Just m }

-- | the globals that some definition uses and nothing defines (checked programs only)
missingOf :: Program -> [String]
missingOf p
  | not (null (pErrors p)) = []
  | otherwise =
      let defs = [eraseDef n ps b | Just (Def n ps b) <- pResolved p]
      in missingGlobals defs (map fst (cUnknowns (pChecker p)))

pval :: Program -> String -> V
pval p n = case pMachine p of
  Just m -> global m n
  Nothing -> error "the program is not built"

-- | load the prelude and the files, check, and build
loadProgram :: [SourceFile] -> [FilePath] -> Bool -> IO Program
loadProgram files trustedPaths withPrelude = do
  let p0 = newProgram
      pre = if withPrelude then [SourceFile f t | (f, t) <- libFiles] else []
  p1 <- foldlM' (\p sf -> addFile p sf True) p0 pre
  p2 <- foldlM' (\p sf@(SourceFile f _) -> addFile p sf (f `elem` trustedPaths)) p1 files
  let p3 = checkProgram p2
  return (if null (pErrors p3) then buildProgram p3 else p3)

foldlM' :: (a -> b -> IO a) -> a -> [b] -> IO a
foldlM' _ a [] = return a
foldlM' f a (x : xs) = do a' <- f a x; a' `seq` foldlM' f a' xs
