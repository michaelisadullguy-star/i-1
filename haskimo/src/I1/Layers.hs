-- | Layers.hs -- the three notation systems of i-1 and the system documents that connect them (port of pymo/layers.py).
--
--   bin   only  1 0 .  space ( ) newline
--         numeral      1011  1.01                (<= 1 radix point)
--         symbol       .B.                       B = a bit string (the code of the symbol, see doc 1)
--         markers      .  =  ↦      ..  =  ≔      ...  =  ∶
--   spec  unicode glyphs; the notation of the prelude (lib/*.imo); `⍝` starts a comment
--   hum   ASCII/TeX-like notation (Hum.hs)
--
--   doc 1   [spec sbl] := [bin sbl]            one line per symbol
--   doc 2   [hum sbl]  := [spec sbl] or [bin sbl] ...
module I1.Layers
  ( Doc1(..), doc1Parse, doc1Code, doc1Lookup, doc1AddLocal, doc1Render, isBinSym, isBinSymText
  , binToSpecText, specStatementsToBinText, specTermToBin
  , splitSections, defaultNotation
  ) where

import qualified Data.Map.Strict as M
import Data.Char (isDigit)
import Data.List (isSuffixOf)
import I1.Base
import I1.Syntax

-- ---------------------------------------------------------------- doc 1
data Doc1 = Doc1
  { dS2B :: M.Map String String
  , dB2S :: M.Map String String
  , dLocal :: [(String, String)]      -- ^ program-local symbols, in the order their codes were given
  }

-- | .B. with B a non-empty bit string
isBinSym :: String -> Bool
isBinSym s = case s of
  ('.' : r) | length r >= 2 -> let (mid, end) = splitAt (length r - 1) r in end == "." && all (`elem` "01") mid
  _ -> False

isBinSymText :: String -> Bool
isBinSymText = isBinSym

doc1Parse :: String -> Doc1
doc1Parse text = foldl add (Doc1 M.empty M.empty []) (lines text)
  where
    add d ln0 =
      let ln = strip ln0
      in if null ln || take 1 ln == "⍝" then d
         else case splitOn " := " ln of
           [a0, b0] ->
             let a = strip a0; b = strip b0
             in if not (isBinSym b) then throwParse ("doc1: bad binary symbol " ++ pyRepr b)
                else if M.member a (dS2B d) || M.member b (dB2S d) then throwParse ("doc1: duplicate " ++ a ++ " / " ++ b)
                else d { dS2B = M.insert a b (dS2B d), dB2S = M.insert b a (dB2S d) }
           _ -> throwParse ("doc1: bad line " ++ pyRepr ln)

doc1Lookup :: Doc1 -> String -> Maybe String
doc1Lookup d n = M.lookup n (dS2B d)

-- | the next free code:  .<max + 1 in binary>.
nextCode :: Doc1 -> String
nextCode d =
  let n = maximum (0 : [bitsToInt (init (tail b)) | b <- M.keys (dB2S d)])
  in '.' : toBin (n + 1) ++ "."
  where
    bitsToInt = foldl (\acc c -> acc * 2 + (if c == '1' then 1 else 0)) (0 :: Integer)
    toBin 0 = "0"
    toBin k = reverse (go k)
    go 0 = []
    go k = (if odd k then '1' else '0') : go (k `div` 2)

-- | the code of a symbol; a new local code is given when allowed
doc1Code :: Doc1 -> String -> Bool -> (Doc1, String)
doc1Code d name allowNew = case M.lookup name (dS2B d) of
  Just b -> (d, b)
  Nothing
    | not allowNew -> throwParse (pyRepr name ++ " has no binary symbol in doc 1")
    | otherwise ->
        let b = nextCode d
        in (d { dS2B = M.insert name b (dS2B d), dB2S = M.insert b name (dB2S d), dLocal = dLocal d ++ [(name, b)] }, b)

-- | add a symbol of a program-local table (not counted as a symbol the program created)
doc1AddLocal :: Doc1 -> String -> String -> Doc1
doc1AddLocal d a b = d { dS2B = M.insert a b (dS2B d), dB2S = M.insert b a (dB2S d) }

-- | the local table as text, in the format of doc 1
doc1Render :: Doc1 -> [String] -> String
doc1Render d header =
  unlines ([ "⍝ " ++ h | h <- header ] ++ [ a ++ " := " ++ b | (a, b) <- dLocal d ])

-- ---------------------------------------------------------------- bin lexer / translators
data BTok = BNL | BOpen | BClose | BNum String | BMark String | BSym String
  deriving (Eq, Show)

reservedSpec :: String -> Maybe String
reservedSpec "." = Just "↦"
reservedSpec ".." = Just "≔"
reservedSpec "..." = Just "∶"
reservedSpec _ = Nothing

reservedBin :: String -> Maybe String
reservedBin "↦" = Just "."
reservedBin "≔" = Just ".."
reservedBin "∶" = Just "..."
reservedBin _ = Nothing

lexBin :: String -> [BTok]
lexBin = go (0 :: Int)
  where
    go _ [] = []
    go d (c : cs)
      | c `elem` " \t\r" = go d cs
      | c == '\n' = if d == 0 then BNL : go d cs else go d cs
      | c == '(' = BOpen : go (d + 1) cs
      | c == ')' = BClose : go (d - 1) cs
      | c `elem` "01." =
          let (s, rest) = span (`elem` "01.") (c : cs)
              pts = length (filter (== '.') s)
              tok | Just _ <- reservedSpec s = BMark s
                  | pts == 0 = BNum s
                  | pts == 1 = BNum s
                  | isBinSym s = BSym s
                  | otherwise = throwParse ("bad binary token " ++ pyRepr s)
          in tok : go d rest
      | otherwise = throwParse ("character " ++ pyRepr [c] ++ " is not part of the binary notation")

-- | tokens to text (spaces only between atoms; newlines kept).  Nothing stands for a newline.
renderToks :: [Maybe String] -> String
renderToks = go True
  where
    go _ [] = []
    go _ (Nothing : r) = '\n' : go True r
    go first (Just t : r)
      | t == ")" || first = t ++ go (t == "(") r
      | otherwise = ' ' : t ++ go (t == "(") r

-- | bin text -> spec text, through doc 1 (and the program's local table)
binToSpecText :: String -> Doc1 -> String
binToSpecText text d = renderToks (map conv (lexBin text))
  where
    conv BNL = Nothing
    conv BOpen = Just "("
    conv BClose = Just ")"
    conv (BNum s) = Just s
    conv (BMark s) = case reservedSpec s of Just r -> Just r; Nothing -> Nothing
    conv (BSym s) = case M.lookup s (dB2S d) of
      Just n -> Just n
      Nothing -> throwParse ("binary symbol " ++ s ++ " is not defined in doc 1 (or the local table)")

-- | the statements re-spelled in bin notation; new program-local symbols get codes in order of first use
specStatementsToBinText :: [Stmt] -> Doc1 -> Bool -> (Doc1, String)
specStatementsToBinText sts d0 allowNew =
  let (d, toks) = foldl step (d0, []) sts
  in (d, renderToks toks)
  where
    step (d, acc) st =
      let (d', ts) = tokensOf d (lexSpec (ppStatement st))
      in (d', acc ++ ts ++ [Nothing])
    tokensOf d ts = foldl one (d, []) ts
    one (d, acc) t = case t of
      TOpen -> (d, acc ++ [Just "("])
      TClose -> (d, acc ++ [Just ")"])
      TkNum s -> (d, acc ++ [Just s])
      TkName n -> case reservedBin n of
        Just r -> (d, acc ++ [Just r])
        Nothing -> let (d', b) = doc1Code d n allowNew in (d', acc ++ [Just b])
      TkChr c ->
        let (d1, bc) = doc1Code d "𝕔" allowNew
        in (d1, acc ++ [Just "(", Just bc, Just (intNumeralText (toInteger c)), Just ")"])
      TkStr s ->
        let (d1, bcons) = doc1Code d "∷" allowNew
            (d2, bchr) = doc1Code d1 "𝕔" allowNew
            (d3, bnil) = doc1Code d2 "⊘" allowNew
            cells = concat [[Just "(", Just bcons, Just "(", Just bchr, Just (intNumeralText (toInteger (fromEnum ch))), Just ")"] | ch <- s]
        in (d3, acc ++ cells ++ [Just bnil] ++ replicate (length s) (Just ")"))
      TNL -> (d, acc)

-- | one spec term (as text) -> the same term in bin notation, through doc 1 (literals are expanded as the reader expands them)
specTermToBin :: String -> Doc1 -> String
specTermToBin text d = renderToks (concatMap conv (lexSpec text))
  where
    code n = snd (doc1Code d n False)
    conv t = case t of
      TOpen -> [Just "("]
      TClose -> [Just ")"]
      TkNum s -> [Just s]
      TkName n -> [Just (maybe (code n) id (reservedBin n))]
      TkChr c -> [Just "(", Just (code "𝕔"), Just (intNumeralText (toInteger c)), Just ")"]
      TkStr s ->
        concat [[Just "(", Just (code "∷"), Just "(", Just (code "𝕔"), Just (intNumeralText (toInteger (fromEnum ch))), Just ")"] | ch <- s]
          ++ [Just (code "⊘")] ++ replicate (length s) (Just ")")
      TNL -> []

-- ---------------------------------------------------------------- files: default notation by extension, `@bin` `@spec` `@hum` section headers
splitSections :: String -> String -> [(String, String)]
splitSections text def = finish (foldl step (def, [], []) (splitOn "\n" text))
  where
    step (mode, cur, acc) ln =
      let s = strip ln
      in if s `elem` ["@bin", "@spec", "@hum"]
           then (drop 1 s, [], if null cur then acc else acc ++ [(mode, joinNL (reverse cur))])
           else (mode, ln : cur, acc)
    finish (mode, cur, acc) = if null cur then acc else acc ++ [(mode, joinNL (reverse cur))]
    joinNL = foldr1' (\a b -> a ++ "\n" ++ b)
    foldr1' _ [] = ""
    foldr1' f xs = foldr1 f xs

defaultNotation :: FilePath -> String
defaultNotation path
  | ".bin.imo" `isSuffixOf` path = "bin"
  | ".hum.imo" `isSuffixOf` path = "hum"
  | otherwise = "spec"

_unusedDigit :: Char -> Bool
_unusedDigit = isDigit
