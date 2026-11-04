{-# LANGUAGE ScopedTypeVariables #-}
-- | Output.hs -- printing values: the output side of the three notations, and the `main` entry point (port of pymo/output.py).
--
-- A value is printed as a NORMAL-FORM TERM in the chosen notation, so that what is printed can be read back, in that notation, as a
-- term that denotes the same value.  Nothing is computed on the host:
--   * the normal forms are computed IN THE LANGUAGE:  ⊜ (canonical z/m) for spec and bin numbers, showq / showc (decimal text,
--     reduced real and imaginary parts) for human numbers, decimals for the approximations shown next to stream elements;
--   * the host walks the value as its declared class describes it (a list cell by cell, a pair as two parts, a tree node by node),
--     reads digit strings (a digit is ⊤ or ⊥) and spells them, and turns code points into characters.
--
-- `main`
--   * main ∶ 𝕊           its text is the output, written as it is (the program formats itself: lib/text.imo);
--   * main ∶ 𝔏 𝕊 / 𝔖 𝕊   one line per element (a stream of lines is printed as long as it lasts, or `n` lines);
--   * any other class    the value, as a normal-form term in the output notation, and a newline.
--
-- Statements (class Prop, spec Ω): a value of Ω is the CODE of a statement in simplest form (computed in the language by
-- simplify′).  The host spells the code in the human notation (Speller); for spec and bin output that text is read again — in the
-- program's context — by the human reader and the class checker, and the resulting spec term is printed.
{-# LANGUAGE ScopedTypeVariables #-}
module I1.Output
  ( Printer(..), modes, undetermined, outputMode, runMain, showValue, termOf
  , cellOf, Cell(..), booleanOf
  ) where

import Control.Exception
import Data.Char (isAlpha)
import Data.List (intercalate, isPrefixOf, isSuffixOf, isInfixOf)
import qualified Data.Map.Strict as M
import Data.Maybe (fromMaybe)
import qualified Data.Set as S
import I1.Base
import I1.Core
import I1.Hum
import I1.Layers
import I1.Program
import I1.Syntax
import I1.Types

modes :: [String]
modes = ["bin", "spec", "hum"]

undetermined :: String
undetermined = "undetermined: this truth value is neither proved nor refuted — a statement that depends on its unknowns, or a "
               ++ "relation on ℝ[i] that no rule decides (declare it Prop to print its simplest form instead of a Bool)"

data Cell = CCons V V | CNil

-- | take a list / string cell apart; ⍰ (an undetermined Boolean inside the text) is reported, never printed as text
cellOf :: V -> Cell
cellOf v = case cellOrNil v of
  VCons h t -> CCons h t
  VNil -> CNil
  _ -> throwPrint undetermined

booleanOf :: V -> Bool
booleanOf v = case apply (apply v VT) VF of
  VT -> True
  VF -> False
  _ -> throwPrint undetermined

esc :: Char -> String -> String
esc q = concatMap f
  where
    f '\\' = "\\\\"
    f '\n' = "\\n"
    f '\t' = "\\t"
    f c | c == q = ['\\', c]
        | otherwise = [c]

data Printer = Printer { prP :: Program, prMode :: String, prN :: Int }

prC :: Printer -> Checker
prC = pChecker . prP

callPr :: Printer -> String -> [V] -> V
callPr pr f args = callG (fromMaybe (error "the program is not built") (pMachine (prP pr))) f args

-- | a 𝕊 value -> String (code point by code point)
textOf :: Printer -> V -> IO String
textOf pr v = go (cellOf v) []
  where
    go CNil acc = return (reverse acc)
    go (CCons h t) acc = do
      ch <- charOf pr h
      go (cellOf t) (ch : acc)

-- | a 𝕮 value (a natural numeral, as a ℚ[i] pair) -> character; its canonical form is a pair (n, 1)
charOf :: Printer -> V -> IO Char
charOf pr v = do
  let (z, m) = toPair (callPr pr "⊜" [v])
      cp = giOf z
  evaluate (if snd cp == 0 && fst cp >= 0 && fst cp <= 0x10FFFF && toList m == [1] then toEnum (fromInteger (fst cp)) else '\xfffd')

digitsStr :: V -> String
digitsStr = numeral . toList

isClass :: Printer -> Ty -> String -> Bool
isClass pr cls name = leq (prC pr) cls (kk name) && leq (prC pr) (kk name) cls

-- | the normal-form term of v (of class cls) in spec or hum notation (bin is spelled from spec)
termOf :: Printer -> V -> Ty -> IO String
termOf pr v raw = do
  let c = prC pr
      hum = prMode pr == "hum"
      cls = norm c raw
  case cls of
    K hd args
      | cls == propTy -> statement pr v
      | isClass pr raw "𝕊" || (hd == "𝔏" && not (null args) && norm c (head' args) == kk "𝕮") -> do
          s <- textOf pr v
          return ("\"" ++ esc '"' s ++ "\"")
      | leq c raw (kk "𝕮") -> do
          ch <- charOf pr v
          return ("'" ++ esc '\'' [ch] ++ "'")
      | leq c raw numTy -> number pr v raw
      | hd == "𝔹" -> do
          b <- evaluate (booleanOf v)
          return (if hum then (if b then "true" else "false") else (if b then "⊤" else "⊥"))
      | hd == "𝔒" -> do
          k <- evaluate (toOrd v)
          return ((if hum then ["less", "same", "greater"] else ["⋖", "≖", "⋗"]) !! k)
      | hd == "𝔏" -> do
          let el = head' args
          _ <- evaluate (cellOf v)
          if norm c el == boolTy && not hum
            then return ("(◀ " ++ digitsStr v ++ ")")
            else do
              items <- listItems (cellOf v) el
              if hum then return ("[" ++ intercalate ", " items ++ "]")
              else return (foldr (\x out -> "(∷ " ++ x ++ " " ++ out ++ ")") "⊘" items)
      | hd == "𝔓" -> do
          let (a, b) = toPair v
          x <- termOf pr a (args !! 0)
          y <- termOf pr b (args !! 1)
          return (if hum then "pair(" ++ x ++ ", " ++ y ++ ")" else "(⊗ " ++ x ++ " " ++ y ++ ")")
      | hd == "𝔗" -> do
          let (tag, body) = toPair v
          if toBool tag
            then do
              let (a, b) = toPair body
              x <- termOf pr a cls
              y <- termOf pr b cls
              return (if hum then "node(" ++ x ++ ", " ++ y ++ ")" else "(❁ " ++ x ++ " " ++ y ++ ")")
            else do
              x <- termOf pr body (head' args)
              return (if hum then "leaf(" ++ x ++ ")" else "(❀ " ++ x ++ ")")
      | hd == "𝔖" -> termOf pr (streamNth v (prN pr)) (head' args)
      | hd == "→" || hd == "𝔄" ->
          throwPrint ("a value of class " ++ showType raw ++ " has no normal form to print (it is a function)")
      | otherwise -> throwPrint ("cannot print a value of class " ++ showType raw)
    _ -> throwPrint ("cannot print a value whose class is not known (" ++ showType raw ++ ")")
  where
    head' = head
    listItems CNil _ = return []
    listItems (CCons h t) el = do
      x <- termOf pr h el
      xs <- listItems (cellOf t) el
      return (x : xs)

number :: Printer -> V -> Ty -> IO String
number pr v cls
  | prMode pr == "hum" = textOf pr (callPr pr (if leq (prC pr) cls (kk "ℚ") then "showq" else "showc") [v])
  | otherwise = do
      let (z, m) = toPair (callPr pr "⊜" [v])
          zt = digitsStr z
          mt = digitsStr m
      return (if mt == "1" then zt else "(÷ " ++ zt ++ " " ++ mt ++ ")")

-- ---------------------------------------------------------------- statements (class Ω)
statement :: Printer -> V -> IO String
statement pr v = do
  text <- spell pr v
  if prMode pr == "hum" then return text else reread pr text

-- | the spec term of a human statement, read in the program's context (unknowns declared): the checker chooses ≐ or ≐ᴿ, inserts
-- ⇡ and prop, and marks statements — the marks are dropped, the term is what a reader of the output reads back
reread :: Printer -> String -> IO String
reread pr text = do
  let p = prP pr
      c = pChecker p
  parsed <- try (evaluate (let ts = lexHum text
                               (term, rest) = humExpr (pHum p) ts 0 S.empty
                           in if not (null rest) then throwParse ("unexpected " ++ showTok (head rest)) else (length (show term) `seq` term)))
  term <- case parsed of
    Left (ParseError e) -> throwPrint ("the statement " ++ pyRepr text ++ " cannot be read in the human notation (" ++ e ++ ")")
    Left e -> throwIO e
    Right t -> return t
  case synth c [] term of
    Left e -> throwPrint ("the statement " ++ pyRepr text ++ " does not read back in this program: " ++ e)
    Right (cls, t) -> case fit c t cls propTy of
      Nothing -> throwPrint (pyRepr text ++ " reads back as a " ++ showType cls ++ ", not as a statement")
      Just fitted -> return (ppTerm (stripQuotes fitted))

stripQuotes :: Term -> Term
stripQuotes t = case t of
  TQuote e _ -> stripQuotes e
  TApp f as -> TApp (stripQuotes f) (map stripQuotes as)
  TLam ps b -> TLam ps (stripQuotes b)
  _ -> t

-- | the remark printed after a stream element (none in bin: the binary notation has no comments)
comment :: Printer -> V -> Ty -> IO String
comment pr v cls0 = do
  let c = prC pr
      cls = norm c cls0
  case cls of
    K "𝔖" [el] | prMode pr /= "bin" -> do
      let mark = if prMode pr == "hum" then "--" else "⍝"
      approx <-
        if leq c el numTy
          then do
            let x = streamNth v (prN pr)
            re <- textOf pr (callPr pr "decimals" [callPr pr "ℜ" [x], lit pr 12])
            let im = callPr pr "ℑ" [x]
            if not (toBool (callPr pr "≐" [im, lit pr 0]))
              then do
                imt <- textOf pr (callPr pr "decimals" [im, lit pr 12])
                return (", ≈ " ++ re ++ " " ++ (if "-" `isPrefixOf` imt then "-" else "+") ++ " " ++ dropWhile (== '-') imt ++ " i")
              else return (", ≈ " ++ re)
          else return ""
      return ("   " ++ mark ++ " element " ++ show (prN pr) ++ " of the stream" ++ approx)
    _ -> return ""

-- | the language value of a small natural number, built from its digits (the reader's numeral expansion)
lit :: Printer -> Int -> V
lit pr k =
  let m = fromMaybe (error "the program is not built") (pMachine (prP pr))
  in callG m "⊗" [listValue m (toDigits (toInteger k, 0)), listValue m [1]]

showValue :: Printer -> V -> Ty -> IO String
showValue pr v cls = do
  t <- termOf pr v cls
  let t' = if prMode pr == "bin" then specTermToBin t (pDoc1 (prP pr)) else t
  cm <- comment pr v cls
  return (t' ++ cm)

-- ---------------------------------------------------------------- the Speller: the human spelling of the code of a statement
data Node = NN V | NS V | NA V V | NL V | NV V

codeCbs :: [V]
codeCbs = [Fn (\x -> VCN x), Fn (\c -> VCS c), Fn (\f -> Fn (\a -> VCA f a)), Fn (\b -> VCL b), Fn (\k -> VCV k)]

nodeOf :: V -> IO Node
nodeOf v = do
  r <- try (evaluate (foldl apply v codeCbs))
  case r of
    Right (VCN x) -> return (NN x)
    Right (VCS x) -> return (NS x)
    Right (VCA f a) -> return (NA f a)
    Right (VCL b) -> return (NL b)
    Right (VCV k) -> return (NV k)
    Right _ -> notACode
    Left (e :: SomeException) -> case fromException e of
      Just (UnknownError m) -> throwIO (UnknownError m)
      _ -> notACode
  where notACode = throwPrint "a statement whose code is not a code (undetermined, or not built by the simplifier)"

type Piece = (String, Int, String)       -- text, precedence, kind

formulaArgs, spellTransparent, tight, assoc :: [String]
formulaArgs = ["∧", "∨", "¬", "⇒", "⇔", "∧Ω", "∨Ω", "¬Ω", "⇒Ω", "⇔Ω", "prop", "decide", "code_rd"]
spellTransparent = ["⇡", "prop", "decide", "code_rd"]
tight = ["*", "/", "^"]
assoc = ["+", "*"]

spell :: Printer -> V -> IO String
spell pr v = do
  (t, _, _) <- go pr v True
  return t

symbolName :: Printer -> V -> IO String
symbolName pr c = do
  let b = "." ++ numeral (toDigits (giOf c)) ++ "."
  case M.lookup b (dB2S (pDoc1 (prP pr))) of
    Just n -> return n
    Nothing -> throwPrint ("a statement mentions the symbol code " ++ b ++ ", which neither doc 1 nor this program names")

go :: Printer -> V -> Bool -> IO Piece
go pr v formula = do
  n <- nodeOf v
  case n of
    NN x ->
      if formula
        then case apply (apply x VT) VF of
          VT -> return ("true", 10, "atom")
          VF -> return ("false", 10, "atom")
          _ -> throwPrint undetermined
        else numberPiece pr x
    NS c -> do
      nm <- symbolName pr c
      appPiece pr nm [] formula
    NA _ _ -> do
      (hd, args) <- spine n []
      case hd of
        NS c -> do
          nm <- symbolName pr c
          appPiece pr nm args formula
        _ -> throwPrint "a statement applies something that is not a symbol (a λ): it has no human spelling"
    _ -> throwPrint "a statement contains a λ or a bound variable: it has no human spelling yet"
  where
    spine (NA f a) acc = do
      f' <- nodeOf f
      spine f' (a : acc)
    spine nd acc = return (nd, acc)

numberPiece :: Printer -> V -> IO Piece
numberPiece pr q = do
  r <- try (textOf pr (callPr pr "showc" [q]))
  t <- case r of
    Right t -> return t
    Left (e :: SomeException) -> case (fromException e :: Maybe ImoError) of
      Just ie -> throwIO ie
      Nothing -> throwPrint "a statement holds a value that is not a number where a number is expected"
  let p | " + " `isInfixOf` t || " - " `isInfixOf` t = 6
        | "i" `isSuffixOf` t || '/' `elem` t = 7
        | "-" `isPrefixOf` t = 8
        | otherwise = 10
  return (t, p, "num")

par :: Piece -> Int -> [String] -> String
par (t, p, k) need avoid = if p < need || k `elem` avoid then "(" ++ t ++ ")" else t

appPiece :: Printer -> String -> [V] -> Bool -> IO Piece
appPiece pr name args formula
  | name `elem` ["⊤", "⊥"] && k == 0 = return (if name == "⊤" then "true" else "false", 10, "atom")
  | name `elem` spellTransparent && k == 1 = go pr (head args) (formula && name /= "⇡")
  | name == "⊘" && k == 0 = return ("[]", 10, "atom")
  | name == "∷" && k == 2 = do
      (first, _, _) <- go pr (args !! 0) False
      items <- listLoop (args !! 1) [first]
      return ("[" ++ intercalate ", " items ++ "]", 10, "atom")
  | name `elem` ["∨", "∨Ω"] && k == 2 = do
      a <- go pr (args !! 0) True
      b <- go pr (args !! 1) True
      return (par a 3 ["and"] ++ " or " ++ par b 2 ["and"], 2, "or")
  | name `elem` ["∧", "∧Ω"] && k == 2 = do
      a <- go pr (args !! 0) True
      b <- go pr (args !! 1) True
      return (par a 4 [] ++ " and " ++ par b 3 [], 3, "and")
  | name `elem` ["¬", "¬Ω"] && k == 1 = do
      a <- go pr (head args) True
      return ("not " ++ par a 4 [], 4, "not")
  | otherwise = generic
  where
    k = length args
    sub = name `elem` formulaArgs
    entry = M.lookup name (revTable pr)
    h = maybe name eHum entry
    role = maybe "value" eRole entry
    listLoop rest acc = do
      n <- nodeOf rest
      case n of
        NS c -> do
          nm <- symbolName pr c
          if nm == "⊘" then return acc else bad
        NA f a -> do
          hnode <- nodeOf f
          case hnode of
            NA f2 a2 -> do
              hh <- nodeOf f2
              case hh of
                NS c -> do
                  nm <- symbolName pr c
                  if nm == "∷"
                    then do (x, _, _) <- go pr a2 False
                            listLoop a (acc ++ [x])
                    else bad
                _ -> bad
            _ -> bad
        _ -> bad
    bad = throwPrint "a list code that does not end in ⊘"
    generic
      | role `elem` ["infixl", "infixr", "infix"] && k == 2 = do
          let p' = fromMaybe 0 (entry >>= ePrec)
          a <- go pr (args !! 0) sub
          b <- go pr (args !! 1) sub
          let (ln, rn)
                | h == "^" = (10, p')
                | role == "infixl" = (p', if h `elem` assoc then p' else p' + 1)
                | role == "infixr" = (p' + 1, p')
                | otherwise = (p' + 1, p' + 1)
              sep = if h `elem` tight then h else " " ++ h ++ " "
          return (par a ln [] ++ sep ++ par b rn [], p', "op")
      | role == "prefix" && k == 1 = do
          let p' = fromMaybe 0 (entry >>= ePrec)
          a@(at, _, _) <- go pr (head args) sub
          let x0 = par a p' []
              x = if h == "-" && "-" `isPrefixOf` x0 then "(" ++ at ++ ")" else x0
          return (if isAlpha (head' h) then h ++ " " ++ x else h ++ x, p', "op")
      | k == 0 && role == "value" = return (h, 10, "atom")
      | role /= "value" = throwPrint (h ++ " applied to " ++ show k ++ " argument(s) has no human spelling")
      | otherwise = do
          as <- mapM (\a -> do (t, _, _) <- go pr a sub; return t) args
          return (h ++ "(" ++ intercalate ", " as ++ ")", 10, "atom")
    head' [] = ' '
    head' (x : _) = x

-- | reverse doc 2: the first entry that has the spec symbol on its right
revTable :: Printer -> M.Map String Entry
revTable pr = M.fromListWith (\_ old -> old)
  [ (x, e) | e <- d2Entries (pDoc2 (prP pr)), eRole e `elem` ["value", "infixl", "infixr", "infix", "prefix"], x <- eRhs e ]

-- ---------------------------------------------------------------- main
outputMode :: Program -> Maybe String -> String -> String
outputMode p override name = case override of
  Just m -> m
  Nothing -> case pOutMode p of
    Just m -> m
    Nothing -> M.findWithDefault "spec" name (pNotationOf p)

-- | evaluate `main` and write its output; returns the output notation used.  An unknown whose value is needed is reported
-- (PrintError), as an undetermined truth value is.
runMain :: Program -> Maybe String -> Maybe Int -> (String -> IO ()) -> IO String
runMain p mode0 n write =
  handle (\e -> case e of UnknownError m -> throwIO (PrintError m); _ -> throwIO e) body
  where
    body = do
      let c = pChecker p
      case M.lookup "main" (cSigs c) of
        Nothing -> throwPrint "this program has no main:  define  main ∶ <class>  (spec),  main in <Class> := …  (hum)"
        Just [] -> throwPrint "this program has no main:  define  main ∶ <class>  (spec),  main in <Class> := …  (hum)"
        Just (cls : _) -> do
          let mode = outputMode p mode0 "main"
              v = pval p "main"
              pr = Printer p mode (fromMaybe 10 n)
              c0 = norm c cls
          if leq c cls (kk "𝕊")
            then do
              let loop CNil = return ()
                  loop (CCons h t) = do
                    ch <- charOf pr h
                    write [ch]
                    loop (cellOf t)
              loop (cellOf v)
              return mode
            else case c0 of
              K hd [el] | hd `elem` ["𝔏", "𝔖"], norm c el == norm c (kk "𝕊") -> do
                let loop CNil _ = return ()
                    loop (CCons h t) k
                      | maybe True (k <) n = do
                          s <- textOf pr h
                          write (s ++ "\n")
                          loop (cellOf t) (k + 1 :: Int)
                    loop _ _ = return ()
                loop (cellOf v) 0
                return mode
              _ -> do
                s <- showValue pr v cls
                write (s ++ "\n")
                return mode
