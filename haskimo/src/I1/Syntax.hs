-- | Syntax.hs -- the SPEC notation reader of i-1 (port of pymo/syntax.py).
--
-- spec text  ->  statements:
--   Def name params body        name x y ≔ term
--   Decl name type              name ∶ type
--   Fact term                   (⊆ A B)   (≣ A B)   (↪ f)
-- Named term AST: TNum TChr TStr TVar TApp TLam (TAsc and TQuote are made by the human reader and the class checker).
-- Types:  K name args  class constructor application;  V name  class variable;  '→' is the constructor of functions.
-- Comment: everything after the name ⍝ up to the end of the line.
module I1.Syntax
  ( Ty(..), Term(..), Stmt(..), Core(..), Tok(..), Loc
  , classVars, lexSpec, parseStatements, parseTypeSeq, parseTermLine
  , showType, ppType, ppTerm, ppStatement, reprTerm
  , numAst, erase, eraseDef, expandLiterals
  , locInsert, locLookup, locMember, locNames
  ) where

import Data.List (intercalate)
import I1.Base

-- ---------------------------------------------------------------- the data
-- | a class: constructor application, class variable, or the flexible class ⊥ of an unconstrained polymorphic constant
data Ty = K String [Ty] | V String | F
  deriving (Eq, Ord, Show)

data Term
  = TNum String
  | TChr Int
  | TStr String
  | TVar String
  | TApp Term [Term]
  | TLam [(String, Maybe Ty)] Term
  | TAsc Term Ty
  | TQuote Term Loc          -- ^ a statement (class Ω) with the classes of the variables bound outside it
  deriving (Eq, Show)

data Stmt
  = Def String [String] Term
  | Decl String Ty
  | Fact Term
  deriving (Eq, Show)

-- | the runtime term in de Bruijn form
data Core = CV !Int | CL Core | CA Core Core | CG String
  deriving (Eq, Ord, Show)

-- | an insertion-ordered map from names to classes (a Python dict)
type Loc = [(String, Ty)]

locInsert :: String -> Ty -> Loc -> Loc
locInsert n t [] = [(n, t)]
locInsert n t ((m, u) : r)
  | m == n = (n, t) : r
  | otherwise = (m, u) : locInsert n t r

locLookup :: String -> Loc -> Maybe Ty
locLookup = lookup

locMember :: String -> Loc -> Bool
locMember n l = any ((== n) . fst) l

locNames :: Loc -> [String]
locNames = map fst

classVars :: [String]
classVars = ["α", "β", "γ", "δ", "ε"]

-- ---------------------------------------------------------------- lexer
data Tok = TNL | TOpen | TClose | TkNum String | TkChr Int | TkStr String | TkName String
  deriving (Eq, Show)

lexSpec :: String -> [Tok]
lexSpec = go (0 :: Int)
  where
    go _ [] = []
    go d (c : cs)
      | c `elem` " \t\r" = go d cs
      | c == '\n' = if d == 0 then TNL : go d cs else go d cs
      | c == '(' = TOpen : go (d + 1) cs
      | c == ')' = TClose : go (d - 1) cs
      | c `elem` "01." =
          let (s, rest) = span (`elem` "01.") (c : cs)
          in if length (filter (== '.') s) > 1
               then throwParse ("bad numeral " ++ pyRepr s ++ " (spec notation allows one radix point)")
               else TkNum s : go d rest
      | c `elem` "'\"" =
          let (s, rest) = literal c cs
          in if c == '\''
               then (case s of
                       [ch] -> TkChr (fromEnum ch) : go d rest
                       _ -> throwParse ("char literal needs exactly one character: " ++ pyRepr s))
               else TkStr s : go d rest
      | otherwise =
          let (name, rest) = break (`elem` " \t\r\n()01.'\"") (c : cs)
          in if name == "⍝" then go d (dropWhile (/= '\n') rest) else TkName name : go d rest
    literal q = body []
      where
        body _ [] = throwParse "unterminated literal"
        body acc (x : xs)
          | x == q = (reverse acc, xs)
          | x == '\\' = case xs of
              (y : ys) -> body (esc y : acc) ys
              [] -> throwParse "string index out of range"
          | otherwise = body (x : acc) xs
        esc 'n' = '\n'
        esc 't' = '\t'
        esc y = y

-- | token trees: an atom or a parenthesised group
data TT = Atom Tok | Grp [TT]
  deriving (Eq, Show)

-- | the logical lines (split at top-level newlines) of a token stream, each as a list of token trees
logicalLines :: [Tok] -> [[TT]]
logicalLines toks = filter (not . null) (map trees (splitNL toks))
  where
    splitNL ts = case break (== TNL) ts of
      (a, []) -> [a]
      (a, _ : r) -> a : splitNL r

-- | token list (one line, no TNL) -> token trees
trees :: [Tok] -> [TT]
trees ts = case go ts of
  (r, []) -> r
  (_, _) -> throwParse "unexpected )"
  where
    go [] = ([], [])
    go (TOpen : r) =
      let (inner, r') = go r
      in case r' of
           (TClose : r'') -> let (more, rest) = go r'' in (Grp inner : more, rest)
           _ -> throwParse "missing )"
    go r@(TClose : _) = ([], r)
    go (t : r) = let (more, rest) = go r in (Atom t : more, rest)

-- ---------------------------------------------------------------- terms
parseItem :: TT -> Term
parseItem (Atom (TkNum s)) = TNum s
parseItem (Atom (TkChr c)) = TChr c
parseItem (Atom (TkStr s)) = TStr s
parseItem (Atom (TkName n)) = TVar n
parseItem (Atom t) = throwParse ("unexpected " ++ show t)
parseItem (Grp inner) =
  case lastArrow inner of
    Just k -> TLam (parseBinders (take k inner)) (parseSeq (drop (k + 1) inner))
    Nothing -> parseSeq inner
  where
    lastArrow xs = case [k | (k, Atom (TkName "↦")) <- zip [0 ..] xs] of
      [] -> Nothing
      ks -> Just (last ks)

parseBinders :: [TT] -> [(String, Maybe Ty)]
parseBinders [] = []
parseBinders (Atom (TkName name) : Atom (TkName "∶") : r) =
  let (ty, r') = parseTypeAtom r in (name, Just ty) : parseBinders r'
parseBinders (Atom (TkName name) : r) = (name, Nothing) : parseBinders r
parseBinders (t : _) = throwParse ("bad binder " ++ show t)

parseSeq :: [TT] -> Term
parseSeq [] = throwParse "empty application"
parseSeq [x] = parseItem x
parseSeq (x : xs) = TApp (parseItem x) (map parseItem xs)

-- | one term from the text of a line (used by the human reader's tests and by the printer)
parseTermLine :: String -> Term
parseTermLine = parseSeq . trees . filter (/= TNL) . lexSpec

-- ---------------------------------------------------------------- types
parseTypeAtom :: [TT] -> (Ty, [TT])
parseTypeAtom (Atom (TkName n) : r) = ((if n `elem` classVars then V n else K n []), r)
parseTypeAtom (Grp inner : r) = (parseTypeSeq inner, r)
parseTypeAtom (t : _) = throwParse ("bad type " ++ show t)
parseTypeAtom [] = throwParse "list index out of range"

parseTypeSeq :: [TT] -> Ty
parseTypeSeq [] = throwParse "empty type"
parseTypeSeq (Atom (TkName "→") : r0) =
  case atoms r0 of
    [a, b] -> K "→" [a, b]
    _ -> throwParse "→ takes two classes"
  where
    atoms [] = []
    atoms xs = let (a, r) = parseTypeAtom xs in a : atoms r
parseTypeSeq inner =
  case break (== Atom (TkName "→")) inner of
    (l, _ : r) -> K "→" [parseTypeSeq l, parseTypeSeq r]
    _ ->
      let (hd, r) = parseTypeAtom inner
          args = atoms r
      in if null args then hd
         else case hd of
           K n [] -> K n args
           _ -> throwParse ("bad class application " ++ show hd)
  where
    atoms [] = []
    atoms xs = let (a, r) = parseTypeAtom xs in a : atoms r

showType :: Ty -> String
showType (V n) = n
showType F = "⊥"
showType (K "→" [a, b]) =
  let l = showType a
      l' = case a of K "→" _ -> "(" ++ l ++ ")"; _ -> l
  in l' ++ " → " ++ showType b
showType (K n []) = n
showType (K n args) = "(" ++ n ++ " " ++ unwords (map arg args) ++ ")"
  where arg a@(K "→" _) = "(" ++ showType a ++ ")"
        arg a = showType a

-- ---------------------------------------------------------------- statements
parseStatements :: String -> [Stmt]
parseStatements text = map statement (logicalLines (lexSpec text))
  where
    statement ln
      | any hasAssign ln =
          case break (== Atom (TkName "≔")) ln of
            (hd, _ : body) ->
              let names = [n | Atom (TkName n) <- hd]
              in if null hd || length names /= length hd
                   then throwParse ("bad definition head " ++ show [n | Atom (TkName n) <- hd])
                   else Def (head names) (tail names) (parseSeq body)
            (_, []) -> throwParse "assertion failed"
      | length ln >= 3, (Atom (TkName _) : Atom (TkName "∶") : _) <- ln =
          case ln of
            (Atom (TkName n) : _ : r) -> Decl n (parseTypeSeq r)
            _ -> throwParse "assertion failed"
      | length ln >= 3, (_ : Atom (TkName "∶") : _) <- ln = throwParse "assertion failed"
      | otherwise = Fact (parseSeq ln)
    hasAssign (Atom (TkName "≔")) = True
    hasAssign (Grp xs) = any hasAssign xs
    hasAssign _ = False

-- ---------------------------------------------------------------- erasure to the runtime (de Bruijn) term
-- | the reader's expansion of a numeral: the pair (digits, denominator) of Gaussian integers, digits LSB first
numAst :: String -> Core
numAst s
  | '.' `notElem` s = CA (CA (CG "⊗") (intAst s)) (intAst "1")
  | otherwise =
      let (a, b0) = break (== '.') s
          b = drop 1 b0
          bits = a ++ b
      in if null bits then throwParse "empty numeral"
         else CA (CA (CG "⊗") (intAst bits)) (intAst ('1' : replicate (length b) '0'))

intAst :: String -> Core
intAst = foldl (\r ch -> CA (CA (CG "∷") (CG (if ch == '1' then "⊤" else "⊥"))) r) (CG "⊥")

-- | scope: the binders in scope, innermost FIRST
erase :: [String] -> Term -> Core
erase scope t = case t of
  TNum s -> numAst s
  TChr c -> numAst (intNumeralText (toInteger c))
  TStr s -> foldr (\ch r -> CA (CA (CG "∷") (numAst (intNumeralText (toInteger (fromEnum ch))))) r) (CG "⊘") s
  TVar nm -> case lookup nm (zip scope [1 ..]) of
    Just k -> CV k
    Nothing -> CG nm
  TApp f as -> foldl (\acc a -> CA acc (erase scope a)) (erase scope f) as
  TLam ps b ->
    let names = map fst ps
        body = erase (reverse names ++ scope) b
    in iterate CL body !! length names
  TAsc e _ -> erase scope e
  TQuote e _ -> erase scope e

eraseDef :: String -> [String] -> Term -> (String, Core)
eraseDef name params body =
  (name, iterate CL (erase (reverse params) body) !! length params)

-- | a term with its Char and String literals written out as the binary notation writes them (numerals and ∷ … ⊘)
expandLiterals :: Term -> Term
expandLiterals t = case t of
  TChr c -> TApp (TVar "𝕔") [TNum (intNumeralText (toInteger c))]
  TStr s -> foldr (\ch r -> TApp (TVar "∷") [TApp (TVar "𝕔") [TNum (intNumeralText (toInteger (fromEnum ch)))], r]) (TVar "⊘") s
  TApp f as -> TApp (expandLiterals f) (map expandLiterals as)
  TLam ps b -> TLam ps (expandLiterals b)
  _ -> t

-- ---------------------------------------------------------------- pretty printer (spec text)
ppType :: Ty -> String
ppType (V n) = n
ppType F = "⊥"
ppType (K "→" [a, b]) = "(→ " ++ ppType a ++ " " ++ ppType b ++ ")"
ppType (K n []) = n
ppType (K n args) = "(" ++ n ++ " " ++ unwords (map ppType args) ++ ")"

ppTerm :: Term -> String
ppTerm t = case t of
  TNum s -> s
  TChr c -> "'" ++ concatMap esc [toEnum c] ++ "'"
    where esc '\\' = "\\\\"
          esc '\'' = "\\'"
          esc '\n' = "\\n"
          esc ch = [ch]
  TStr s -> "\"" ++ concatMap esc s ++ "\""
    where esc '\\' = "\\\\"
          esc '"' = "\\\""
          esc '\n' = "\\n"
          esc ch = [ch]
  TVar n -> n
  TApp f as -> "(" ++ unwords (ppTerm f : map ppTerm as) ++ ")"
  TLam ps b ->
    let p (n, Nothing) = n
        p (n, Just ty) = n ++ " ∶ " ++ ppType ty
    in "(" ++ unwords (map p ps) ++ " ↦ " ++ ppTerm b ++ ")"
  TAsc e _ -> ppTerm e
  TQuote e _ -> ppTerm e

ppStatement :: Stmt -> String
ppStatement (Def n ps b) = unwords (n : ps) ++ " ≔ " ++ ppTerm b
ppStatement (Decl n ty) = n ++ " ∶ " ++ ppType ty
ppStatement (Fact t) = ppTerm t

-- ---------------------------------------------------------------- Python repr of the tuple form of a term (for error messages)
reprTerm :: Term -> String
reprTerm t = case t of
  TNum s -> tup ["'num'", pyRepr s]
  TChr c -> tup ["'chr'", show c]
  TStr s -> tup ["'str'", pyRepr s]
  TVar n -> tup ["'var'", pyRepr n]
  TApp f as -> tup ["'app'", reprTerm f, "[" ++ intercalate ", " (map reprTerm as) ++ "]"]
  TLam ps b -> tup ["'lam'", "[" ++ intercalate ", " [tup [pyRepr n, maybe "None" reprTy ty] | (n, ty) <- ps] ++ "]", reprTerm b]
  TAsc e ty -> tup ["'asc'", reprTerm e, reprTy ty]
  TQuote e _ -> tup ["'quote'", reprTerm e]
  where
    tup xs = "(" ++ intercalate ", " xs ++ ")"

reprTy :: Ty -> String
reprTy (V n) = "('V', " ++ pyRepr n ++ ")"
reprTy F = "('F', '⊥')"
reprTy (K n as) = "('K', " ++ pyRepr n ++ ", " ++ tupleOf (map reprTy as) ++ ")"
  where tupleOf [] = "()"
        tupleOf [x] = "(" ++ x ++ ",)"
        tupleOf xs = "(" ++ intercalate ", " xs ++ ")"
