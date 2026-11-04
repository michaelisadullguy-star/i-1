-- | Base.hs -- reference arithmetic of the base b = i-1 with digits {0,1}, and small host helpers.
--
-- Port of pymo/base_b.py (val, to_digits, numeral) and of the few Python behaviours that the rest of the
-- implementation must reproduce exactly (repr of a string, "%.12g" of a float).  The isomorphism
-- "digit string <-> Gaussian integer" is the only arithmetic the host ever does on language values.
module I1.Base
  ( GI, gadd, gmul, bGI
  , valDigits, toDigits, numeral, intNumeralText
  , pyRepr, fmtG, ImoError(..), throwParse, throwUnknown, throwPrint
  , splitOn, replaceAll, strip, isPrefixOf', basename, readUtf8
  ) where

import Control.Exception (Exception, throw)
import Data.Bits ((.&.))
import Data.Char (generalCategory, GeneralCategory(..), isSpace, ord)
import Data.List (isPrefixOf, dropWhileEnd)
import Numeric (showHex)
import System.IO

-- ---------------------------------------------------------------- errors of the host
-- | The three kinds of error that leave a pure computation as exceptions (the class checker uses Either instead).
data ImoError
  = ParseError String      -- ^ a syntax error in a source text (Python: AssertionError / SyntaxError / IndexError)
  | UnknownError String    -- ^ the value of an unknown (declared, never defined) was needed
  | PrintError String      -- ^ a value cannot be printed
  deriving Show

instance Exception ImoError

throwParse :: String -> a
throwParse = throw . ParseError

throwUnknown :: String -> a
throwUnknown = throw . UnknownError

throwPrint :: String -> a
throwPrint = throw . PrintError

-- ---------------------------------------------------------------- Gaussian integers
type GI = (Integer, Integer)

gadd, gmul :: GI -> GI -> GI
gadd (a, b) (c, d) = (a + c, b + d)
gmul (a, b) (c, d) = (a * c - b * d, a * d + b * c)

-- | the base i-1
bGI :: GI
bGI = (-1, 1)

-- | the Gaussian integer with the digits ds (least significant first)
valDigits :: [Int] -> GI
valDigits = go (0, 0) (1, 0)
  where
    go s _ [] = s
    go s p (d : r) = go (if d /= 0 then gadd s p else s) (gmul p bGI) r

-- | Penney: the canonical least-significant-first digit list of a Gaussian integer
toDigits :: GI -> [Int]
toDigits (x0, y0) = go x0 y0
  where
    go 0 0 = []
    go x y =
      let d = (x + y) .&. 1
          x' = x - d
      in fromIntegral d : go ((negate x' + y) `div` 2) ((negate x' - y) `div` 2)

-- | most significant digit first ("0" for zero)
numeral :: [Int] -> String
numeral [] = "0"
numeral ds = concatMap show (reverse ds)

-- | the numeral text of a natural number (a code point, a digit count, ...), as the reader writes it
intNumeralText :: Integer -> String
intNumeralText n = numeral (toDigits (n, 0))

-- ---------------------------------------------------------------- Python look-alikes
-- | Python's repr() of a str
pyRepr :: String -> String
pyRepr s = q : concatMap esc s ++ [q]
  where
    q | '\'' `elem` s && '"' `notElem` s = '"'
      | otherwise = '\''
    esc c
      | c == q = ['\\', c]
      | c == '\\' = "\\\\"
      | c == '\n' = "\\n"
      | c == '\r' = "\\r"
      | c == '\t' = "\\t"
      | printable c = [c]
      | ord c < 0x100 = "\\x" ++ hex 2 (ord c)
      | ord c < 0x10000 = "\\u" ++ hex 4 (ord c)
      | otherwise = "\\U" ++ hex 8 (ord c)
    hex n v = let h = showHex v "" in replicate (n - length h) '0' ++ h
    printable c = c == ' ' || (case generalCategory c of
      Control -> False; Format -> False; Surrogate -> False; PrivateUse -> False; NotAssigned -> False
      LineSeparator -> False; ParagraphSeparator -> False; Space -> False; _ -> True)

-- | Python's  format(x, '.<p>g')  of a float given as an exact rational (the float's own value), p significant digits
fmtG :: Int -> Rational -> String
fmtG p x
  | x == 0 = "0"
  | otherwise =
      let neg = x < 0
          ax = abs x
          e0 = floorLog10 ax
          (n, e) = scaled ax e0
          digits = show n                       -- p digits
          body | e < -4 || e >= p = sci digits e
               | otherwise = fixed digits e
      in (if neg then "-" else "") ++ body
  where
    -- n = ax / 10^(e-p+1) rounded half to even; fixes e when rounding carries to 10^p
    scaled ax e0 =
      let r = roundHalfEven (ax / (10 ^^ (e0 - p + 1)))
      in if r >= 10 ^ p then (roundHalfEven (ax / (10 ^^ (e0 + 1 - p + 1))), e0 + 1) else (r, e0)
    sci ds e =
      let h = head ds
          t' = dropWhileEnd (== '0') (tail ds)
          mant = if null t' then [h] else h : '.' : t'
          sign = if e < 0 then '-' else '+'
          ex = abs e
      in mant ++ "e" ++ [sign] ++ (if ex < 10 then "0" else "") ++ show ex
    fixed ds e
      | e >= 0 =
          let (ip, fp) = splitAt (e + 1) ds
              fp' = dropWhileEnd (== '0') fp
          in if null fp' then ip else ip ++ "." ++ fp'
      | otherwise =
          let fp = replicate (negate e - 1) '0' ++ ds
              fp' = dropWhileEnd (== '0') fp
          in "0." ++ fp'

floorLog10 :: Rational -> Int
floorLog10 x = go (length (show (floor x :: Integer)) - 1)
  where
    -- start from an estimate and correct it
    go e0 = fix e0
    fix e | x < 10 ^^ e = fix (e - 1)
          | x >= 10 ^^ (e + 1) = fix (e + 1)
          | otherwise = e

roundHalfEven :: Rational -> Integer
roundHalfEven r =
  let f = floor r :: Integer
      d = r - fromInteger f
  in if d < 1 / 2 then f else if d > 1 / 2 then f + 1 else (if even f then f else f + 1)

-- ---------------------------------------------------------------- string helpers
-- | Python's  s.split(sep)
splitOn :: String -> String -> [String]
splitOn sep s = go [] s
  where
    n = length sep
    go acc [] = [reverse acc]
    go acc r@(c : cs)
      | sep `isPrefixOf` r = reverse acc : go [] (drop n r)
      | otherwise = go (c : acc) cs

-- | Python's  s.replace(old, new)
replaceAll :: String -> String -> String -> String
replaceAll old new = go
  where
    n = length old
    go [] = []
    go r@(c : cs)
      | old `isPrefixOf` r = new ++ go (drop n r)
      | otherwise = c : go cs

-- | Python's  s.strip()
strip :: String -> String
strip = dropWhileEnd isSpace . dropWhile isSpace

isPrefixOf' :: String -> String -> Bool
isPrefixOf' = isPrefixOf

basename :: FilePath -> FilePath
basename p = reverse (takeWhile (/= '/') (reverse p))

-- | read a whole file as UTF-8 (the language's source files are UTF-8, whatever the locale)
readUtf8 :: FilePath -> IO String
readUtf8 path = do
  h <- openFile path ReadMode
  hSetEncoding h utf8
  s <- hGetContents h
  length s `seq` hClose h
  return s
