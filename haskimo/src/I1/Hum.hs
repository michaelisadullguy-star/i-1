-- | Hum.hs -- the HUMAN notation of i-1 and doc 2 (port of pymo/hum.py).
--
-- doc 2 line   <hum symbol> := <rhs> | <rhs> | ...  ; <role>          (⍝ starts a comment)
--     rhs   a spec symbol, or a bin symbol (a numeral such as 11, or .B.)
--     role  class | value | literal | infixl P | infixr P | infix P | prefix P
--     several rhs  = an overload set; the checker picks one by the classes of the arguments.
--
-- human statements (one per logical line)
--     name in Class := expr                      declaration + definition
--     name in Class                              declaration only: an UNKNOWN of a number class
--     name(x, y) in A -> B -> C := expr          parameters take their classes from the declaration
--     A subseteq B                               fact (⊆ A B)
-- human terms
--     1, 12, 3.25   "text"  'c'   f(a, b)   a + b   a - b   -a   a * b   a / b   a == b   a geq b   (e in Class)
--     x in Class |-> body                        lambda (binder classes are mandatory)
module I1.Hum
  ( Entry(..), Doc2(..), doc2Parse, doc2Find, doc2OverloadTable, doc2Remap
  , HTok(..), lexHum, showTok, Hum(..), mkHum, humExpr, humStatements, humStatement, specName, typeToTerm
  ) where

import qualified Data.Map.Strict as M
import qualified Data.Set as S
import Data.Char (isAlpha, isAscii, isDigit, isSpace)
import Data.List (findIndex, isPrefixOf)
import Data.Maybe (fromMaybe, isNothing)
import I1.Base
import I1.Layers (Doc1(..), isBinSym)
import I1.Syntax

-- ---------------------------------------------------------------- doc 2
data Entry = Entry
  { eHum :: String
  , eRhs :: [String]
  , eRole :: String
  , ePrec :: Maybe Int
  } deriving Show

data Doc2 = Doc2
  { d2Entries :: [Entry]
  , d2ByHum :: M.Map String [Entry]
  }

mkDoc2 :: [Entry] -> Doc2
mkDoc2 es = Doc2 es (M.fromListWith (flip (++)) [(eHum e, [e]) | e <- es])

doc2Parse :: String -> Doc2
doc2Parse text = mkDoc2 (concatMap entry (splitOn "\n" text))
  where
    entry ln0 =
      let ln1 = strip ln0
      in if null ln1 || take 1 ln1 == "⍝" then []
         else
           let ln = head (splitOn " ⍝ " ln1)
               (hd, rest) = case breakOn " := " ln of
                 Just (a, b) -> (a, b)
                 Nothing -> throwParse ("doc2: bad line " ++ pyRepr ln)
               (rhs, role) = case rpartition " ; " rest of
                 Just (a, b) -> (a, words b)
                 Nothing -> ("", words rest)
           in [Entry (strip hd) (map strip (splitOn " | " rhs)) (head role) (case drop 1 role of (p : _) -> Just (read p); _ -> Nothing)]

-- | split at the first occurrence of sep
breakOn :: String -> String -> Maybe (String, String)
breakOn sep s = go [] s
  where
    go _ [] = Nothing
    go acc r@(c : cs)
      | sep `isPrefixOf` r = Just (reverse acc, drop (length sep) r)
      | otherwise = go (c : acc) cs

-- | split at the last occurrence of sep
rpartition :: String -> String -> Maybe (String, String)
rpartition sep s = case positions of
  [] -> Nothing
  ps -> let k = last ps in Just (take k s, drop (k + length sep) s)
  where
    n = length sep
    positions = [k | k <- [0 .. length s - n], sep `isPrefixOf` drop k s]

-- | the first entry for a human symbol that has one of the roles
doc2Find :: Doc2 -> String -> [String] -> Maybe Entry
doc2Find d hum roles = case [e | e <- M.findWithDefault [] hum (d2ByHum d), eRole e `elem` roles] of
  (e : _) -> Just e
  [] -> Nothing

-- | key -> [spec symbols]  (bin-literal right-hand sides are handled by the reader, not listed here)
doc2OverloadTable :: Doc2 -> M.Map String [String]
doc2OverloadTable d = M.fromList
  [ (key e, [x | x <- eRhs e, not (all (`elem` "01.") x && not (null x))])
  | e <- d2Entries d, eRole e `notElem` ["class", "literal", "syntax"] ]
  where key e = if eRole e == "prefix" then "hum:prefix " ++ eHum e else "hum:" ++ eHum e

-- | a bin symbol on the right of doc 2 means the spec symbol that doc 1 gives that code to
doc2Remap :: Doc1 -> Doc2 -> Doc2
doc2Remap d1 d = mkDoc2 [e { eRhs = map conv (eRhs e) } | e <- d2Entries d]
  where conv x | isBinSym x = fromMaybe x (M.lookup x (dB2S d1))
               | otherwise = x

-- ---------------------------------------------------------------- lexer
data HTok = HNum String | HStr String | HChr Int | HId String | HOp String
  deriving (Eq, Show)

lexHum :: String -> [HTok]
lexHum line0 = go (reverse (dropWhile isSpace (reverse line0)))
  where
    go s0 = case dropWhile isSpace s0 of
      [] -> []
      s@(c : cs)
        | isDigit c ->
            let (ip, r) = span isDigit s
            in case r of
                 ('.' : r'@(d : _)) | isDigit d -> let (fp, r2) = span isDigit r' in HNum (ip ++ "." ++ fp) : go r2
                 _ -> HNum ip : go r
        | c == '"', Just (body, r) <- quoted '"' cs -> HStr (unescape body) : go r
        | c == '\'', Just (body, r) <- quoted '\'' cs, length (unescape body) == 1 -> HChr (fromEnum (head (unescape body))) : go r
        | c == '\\', (nm@(_ : _), r) <- span isAsciiLetter cs -> HId ('\\' : nm) : go r
        | isAsciiLetter c || c == '_' ->
            let (nm, r) = span (\x -> isAsciiLetter x || x == '_' || isDigit x) s in HId nm : go r
        | Just (op, r) <- operator s -> HOp op : go r
        | otherwise -> throwParse ("human notation: cannot read " ++ pyRepr (take 12 s))
    isAsciiLetter x = isAscii x && isAlpha x
    operator s = case [op | op <- [":=", "|->", "->", "==", "!=", "++"], op `isPrefixOf` s] of
      (op : _) -> Just (op, drop (length op) s)
      [] -> case s of
        (x : r) | x `elem` "-+*/^(),[]" -> Just ([x], r)
        _ -> Nothing
    -- the body of a quoted literal: any character but the quote and the backslash, or a backslash and any character
    quoted q = body []
      where
        body _ [] = Nothing
        body acc (x : xs)
          | x == q = Just (reverse acc, xs)
          | x == '\\' = case xs of
              (y : ys) | y /= '\n' -> body (y : x : acc) ys
              _ -> Nothing
          | otherwise = body (x : acc) xs
    unescape ('\\' : y : r) = (case y of 'n' -> '\n'; 't' -> '\t'; _ -> y) : unescape r
    unescape (x : r) = x : unescape r
    unescape [] = []

-- | a logical line ends at a newline outside parentheses; `--` starts a comment
humLogicalLines :: String -> [String]
humLogicalLines text = go (splitOn "\n" text) "" (0 :: Int)
  where
    go [] cur _ = [strip cur | not (null (strip cur))]
    go (ln0 : rest) cur depth =
      let ln = if "--" `isIn` ln0 && '"' `notElem` ln0 then head (splitOn "--" ln0) else ln0
          cur' = cur ++ " " ++ ln
          depth' = depth + count '(' ln - count ')' ln + count '[' ln - count ']' ln
      in if depth' <= 0
           then [strip cur' | not (null (strip cur'))] ++ go rest "" 0
           else go rest cur' depth'
    count c = length . filter (== c)
    isIn pat s = any (pat `isPrefixOf`) (tails' s)
    tails' [] = [[]]
    tails' s@(_ : r) = s : tails' r

-- ---------------------------------------------------------------- parser
data Hum = Hum
  { hDoc :: Doc2
  , hInfix :: M.Map String (Int, String)
  , hPrefix :: M.Map String Int
  }

mkHum :: Doc2 -> Hum
mkHum d = Hum d
  (M.fromList [(eHum e, (fromMaybe 0 (ePrec e), eRole e)) | e <- d2Entries d, eRole e `elem` ["infixl", "infixr", "infix"]])
  (M.fromList [(eHum e, fromMaybe 0 (ePrec e)) | e <- d2Entries d, eRole e == "prefix"])

oob :: a
oob = throwParse "list index out of range"

-- classes
classAtom :: Hum -> [HTok] -> (Ty, [HTok])
classAtom h ts = case ts of
  (HOp "(" : r) ->
    let (c, r') = classExpr h r
    in case r' of
         (HOp ")" : r'') -> (c, r'')
         _ -> throwParse "missing )"
  (HId n : r) -> case doc2Find (hDoc h) n ["class"] of
    Nothing -> throwParse (n ++ " is not a class in doc 2")
    Just e ->
      let name = head (eRhs e)
      in if name `elem` classVars then (V name, r)
         else case r of
           (HOp "(" : r1) ->
             let (args, rest) = classArgs r1
             in (K name args, rest)
           _ -> (K name [], r)
  (t : _) -> throwParse ("class expected, found " ++ showTok t)
  [] -> oob
  where
    classArgs r0 =
      let (a, r1) = classExpr h r0
      in case r1 of
           (HOp "," : r2) -> let (as, rest) = classArgs r2 in (a : as, rest)
           (HOp ")" : r2) -> ([a], r2)
           [] -> oob
           _ -> throwParse "missing ) in class"

classExpr :: Hum -> [HTok] -> (Ty, [HTok])
classExpr h ts =
  let (l, r) = classAtom h ts
  in case r of
       (HOp "->" : r') -> let (rt, r'') = classExpr h r' in (K "→" [l, rt], r'')
       _ -> (l, r)

showTok :: HTok -> String
showTok t = case t of
  HNum s -> "('NUM', " ++ pyRepr s ++ ")"
  HStr s -> "('STR', " ++ pyRepr s ++ ")"
  HChr c -> "('CHR', " ++ show c ++ ")"
  HId s -> "('ID', " ++ pyRepr s ++ ")"
  HOp s -> "('OP', " ++ pyRepr s ++ ")"

-- terms
number :: String -> Term
number text = case break (== '.') text of
  (a, []) -> TNum (intNumeralText (read a))
  (a, _ : b) -> TApp (TVar "hum:/") [TNum (intNumeralText (read (a ++ b))), TNum (intNumeralText (10 ^ length b))]

atom :: Hum -> [HTok] -> S.Set String -> (Term, [HTok])
atom h ts scope = case ts of
  [] -> oob
  (HNum s : r) -> (number s, r)
  (HStr s : r) -> (TStr s, r)
  (HChr c : r) -> (TChr c, r)
  (HOp "[" : r0) ->
    let (items, r1) = case r0 of
          (HOp "]" : _) -> ([], r0)
          _ -> listItems r0
    in case r1 of
         (HOp "]" : r2) -> (foldr (\a e -> TApp (TVar "hum:cons") [a, e]) (TVar "hum:nil") items, r2)
         [] -> oob
         _ -> throwParse "missing ] in list"
  (HOp "(" : r0) ->
    let (e, r1) = humExpr h r0 0 scope
    in case r1 of
         (HId "in" : r2) ->
           let (c, r3) = classExpr h r2
           in case r3 of
                (HOp ")" : r4) -> (TAsc e c, r4)
                [] -> oob
                _ -> throwParse "missing )"
         (HOp ")" : r2) -> (e, r2)
         [] -> oob
         _ -> throwParse "missing )"
  (HId name : r) ->
    case () of
      _ | not (S.member name scope), Just lit <- doc2Find (hDoc h) name ["literal"], not (startsParen r) ->
            (TNum (head (eRhs lit)), r)
        | otherwise ->
            let hd = if S.member name scope || isNothing (doc2Find (hDoc h) name ["value"]) then TVar name else TVar ("hum:" ++ name)
            in case r of
                 (HOp "(" : r1) -> case r1 of
                   (HOp ")" : r2) -> (TApp hd [], r2)
                   _ -> let (args, r2) = callArgs r1 in (TApp hd args, r2)
                 _ -> (hd, r)
  (t : _) -> throwParse ("unexpected " ++ showTok t)
  where
    startsParen (HOp "(" : _) = True
    startsParen _ = False
    listItems r0 =
      let (a, r1) = humExpr h r0 0 scope
      in case r1 of
           (HOp "," : r2) -> let (as, rest) = listItems r2 in (a : as, rest)
           _ -> ([a], r1)
    callArgs r0 =
      let (a, r1) = humExpr h r0 0 scope
      in case r1 of
           (HOp "," : r2) -> let (as, rest) = callArgs r2 in (a : as, rest)
           (HOp ")" : r2) -> ([a], r2)
           [] -> oob
           _ -> throwParse "missing ) in call"

humExpr :: Hum -> [HTok] -> Int -> S.Set String -> (Term, [HTok])
humExpr h ts minprec scope = case ts of
  [] -> oob
  -- lambda:  x in Class |-> body
  (HId name : HId "in" : r0)
    | (c, r1) <- classExpr h r0, (HOp "|->" : r2) <- r1 ->
        let (body, r3) = humExpr h r2 0 (S.insert name scope)
        in (TLam [(name, Just c)] body, r3)
  _ ->
    let (left, r) = case ts of
          (t : r0)
            | Just key <- opKey t, M.member key (hPrefix h), not (isId t && S.member key scope) ->
                let (arg, r1) = humExpr h r0 (hPrefix h M.! key) scope
                in (TApp (TVar ("hum:prefix " ++ key)) [arg], r1)
          _ -> atom h ts scope
    in loop left r
  where
    opKey (HOp o) = Just o
    opKey (HId o) = Just o
    opKey _ = Nothing
    isId (HId _) = True
    isId _ = False
    loop left r = case r of
      (t : r0)
        | Just op <- opKey t, Just (prec, kind) <- M.lookup op (hInfix h), prec >= minprec ->
            let (right, r1) = humExpr h r0 (if kind /= "infixr" then prec + 1 else prec) scope
            in loop (TApp (TVar ("hum:" ++ op)) [left, right]) r1
      _ -> (left, r)

-- statements
specName :: Hum -> String -> String
specName h name = case doc2Find (hDoc h) name ["value"] of
  Just e | [x] <- eRhs e, not (all (`elem` "01.") x) -> x
  _ -> name

typeToTerm :: Ty -> Term
typeToTerm (V n) = TVar n
typeToTerm (K n []) = TVar n
typeToTerm (K n as) = TApp (TVar n) (map typeToTerm as)
typeToTerm F = TVar "⊥"

humStatement :: Hum -> String -> [Stmt]
humStatement h line =
  let ts = lexHum line
  in case findIndex (== HId "subseteq") ts of
       Just k ->
         let (a, ra) = classExpr h (take k ts)
             (b, rb) = classExpr h (drop (k + 1) ts)
         in if not (null ra) then throwParse "assertion failed"
            else if not (null rb) then throwParse "assertion failed"
            else [Fact (TApp (TVar "⊆") [typeToTerm a, typeToTerm b])]
       Nothing -> case ts of
         (HId name : r0) ->
           let (params, r1) = case r0 of
                 (HOp "(" : r) -> paramList r
                 _ -> ([], r0)
           in case r1 of
                (HId "in" : r2) ->
                  let (cls, r3) = classExpr h r2
                  in case r3 of
                       [] -> if not (null params)
                               then throwParse (name ++ ": a declaration without := takes no parameters (an unknown is a number)")
                               else [Decl (specName h name) cls]
                       (HOp ":=" : r4) ->
                         let (body, r5) = humExpr h r4 0 (S.fromList params)
                             sp = specName h name
                         in case r5 of
                              [] -> [Decl sp cls, Def sp params body]
                              (t : _) -> throwParse ("unexpected " ++ showTok t)
                       _ -> throwParse "missing :="
                _ -> throwParse ("declare the class first:  " ++ name ++ " in <Class> := …")
         _ -> throwParse ("statement must start with a name: " ++ pyRepr line)
  where
    paramList r = case r of
      (HOp ")" : r') -> ([], r')
      (t : r') ->
        let nm = tokText t
            (more, r'') = case r' of
              (HOp "," : r2) -> paramList r2
              _ -> paramList r'
        in (nm : more, r'')
      [] -> oob
    tokText t = case t of
      HNum s -> s
      HStr s -> s
      HChr c -> [toEnum c]
      HId s -> s
      HOp s -> s

humStatements :: Hum -> String -> [Stmt]
humStatements h text = concatMap (humStatement h) (humLogicalLines text)
