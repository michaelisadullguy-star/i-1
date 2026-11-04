-- | Quote.hs -- the compiler side of statements (port of pymo/quote.py).  A statement — a relation on ℝ[i], a relation or
-- predicate about an unknown, a connective with a statement operand (Types.hs marks them TQuote φ …) — is simplified from
-- DEFINITIONS whenever it is evaluated or output, so its checked term φ is replaced by a term that builds φ's CODE at run time:
--
--     numeral / Char / String / closed number or Boolean     (𝔮ⁿ value)       — decided directly (a subset of ℚ[i] or 𝔹)
--     symbol                                                (𝔮ˢ code)        — its doc 1 code (a numeral; a local code for the program's own symbols)
--     unknown x (declared, never defined)                   (𝔮ˢ code of x)   — program-local codes, numbered in DECLARATION order
--     application, λ, bound variable                        (𝔮ᵃ f a) (𝔮ˡ b) (𝔮ᵛ k)   — de Bruijn indices
--     a variable bound outside φ, not a number              (𝔮ᵛ k) with k beyond φ's binders: an unknown, the same for every use
--     a variable bound outside φ, of class Ω                its value (a statement IS its code)
--     prop b, decide φ, ∧Ω ∨Ω ¬Ω ⇒Ω ⇔Ω                       transparent: the code of b or φ, and the plain connectives ∧ ∨ ¬ ⇒ ⇔
--
-- and the statement becomes  (simplify′ ε⌜⌝ ⌜φ⌝)  where  ε⌜⌝  is one table, for the whole program, of (code, ⌜definition⌝).
-- Nothing is decided here: this is a spelling of terms as numbers, like the reader's expansion of numerals.
module I1.Quote (Quoter, QS(..), envName, mkQuoter, hasQuote, quoteReplace, quoteTable) where

import Control.Monad.State.Strict
import Data.List (elemIndex, sortOn)
import qualified Data.Map.Strict as M
import Data.Maybe (fromMaybe)
import qualified Data.Set as S
import I1.Base
import I1.Layers
import I1.Syntax
import I1.Types

unfold :: [String]
unfold = ["exp", "sin", "cos", "sinh", "cosh", "log", "atan"]

-- | the name of the table of definitions
envName :: String
envName = "ε⌜⌝"

transparent :: [String]
transparent = ["prop", "decide", "code_rd"]

data Quoter = Quoter
  { qC :: Checker
  , qDefs :: M.Map String ([String], Term, Ty)     -- ^ program symbol -> (params, body, declared class)
  , qPrelude :: M.Map String ([String], Term)      -- ^ prelude symbol -> (params, body)
  , qUnknowns :: [(String, Int)]
  , qStmt :: S.Set String                          -- ^ definitions that contain a statement
  }

-- | state: the doc 1 table (codes are given in order of first use) and the symbols whose definitions go into the table
data QS = QS { sDoc :: Doc1, sNeeded :: [String] }

type QM = State QS

app :: String -> [Term] -> Term
app f xs = TApp (TVar f) xs

digits :: String -> Term
digits text = app "↓ᶻ" [TNum text]

nat :: Int -> Term
nat k = digits (numeral (toDigits (toInteger k, 0)))

-- | statements of the program, resolved: (trusted, resolved statement)
mkQuoter :: Checker -> [(Bool, Maybe Stmt)] -> Doc1 -> (Quoter, Doc1)
mkQuoter c sts d0 =
  let defsP = M.fromList [ (n, (ps, b, head (M.findWithDefault [kk "?"] n (cSigs c)))) | (False, Just (Def n ps b)) <- sts ]
      pre = M.fromList [ (n, (ps, b)) | (True, Just (Def n ps b)) <- sts, n `elem` unfold ]
      unk = [(n, k) | (n, Just k) <- cUnknowns c]
      d1 = foldl (\d (n, _) -> fst (doc1Code d n True)) d0 unk
      stmt = S.fromList [n | (n, (_, b, _)) <- M.toList defsP, hasQuote b]
  in (Quoter c defsP pre unk stmt, d1)

hasQuote :: Term -> Bool
hasQuote t = case t of
  TQuote _ _ -> True
  TApp f as -> hasQuote f || any hasQuote as
  TLam _ b -> hasQuote b
  _ -> False

code :: String -> QM Term
code name = do
  st <- get
  let (d', b) = doc1Code (sDoc st) (fromMaybe name (lookup name connO)) True
  put st { sDoc = d' }
  return (digits (init (tail b)))

need :: Quoter -> String -> QM ()
need qr name =
  when (M.member name (qDefs qr) || M.member name (qPrelude qr) || name `elem` map fst (qUnknowns qr)) $
    modify (\st -> if name `elem` sNeeded st then st else st { sNeeded = sNeeded st ++ [name] })

isValueClass :: Quoter -> Maybe Ty -> Bool
isValueClass _ Nothing = False
isValueClass qr (Just c0) =
  let c = norm (qC qr) c0
  in case c of
       K _ _ -> c == boolTy || leq (qC qr) c numTy
       _ -> False

hasRel :: Quoter -> Term -> Bool
hasRel qr t = case t of
  TQuote _ _ -> True
  TVar n -> n `elem` relR || n `elem` map fst connO || S.member n (qStmt qr)
  TApp f as -> hasRel qr f || any (hasRel qr) as
  TLam _ b -> hasRel qr b
  _ -> False

freeIn :: Term -> S.Set String -> Bool
freeIn t names = case t of
  TVar n -> S.member n names
  TApp f as -> freeIn f names || any (`freeIn` names) as
  TLam ps b -> freeIn b (S.difference names (S.fromList (map fst ps)))
  TQuote e _ -> freeIn e names
  _ -> False

-- | the code of a term.  ib: binders inside the quote (innermost last) with their classes; outer: classes of variables bound outside
q :: Quoter -> Term -> [(String, Maybe Ty)] -> Loc -> Bool -> QM Term
q qr t ib outer typed = case t of
  TQuote e _ -> q qr e ib outer typed
  TNum _ -> return (app "𝔮ⁿ" [t])
  TChr _ -> return (app "𝔮ⁿ" [t])
  TStr _ -> return (app "𝔮ⁿ" [t])
  TVar n
    | n `elem` names ->
        let idx = maximum [i | (i, m) <- zip [0 :: Int ..] names, m == n]
        in return (app "𝔮ᵛ" [nat (length names - idx)])
    | Just oc <- lookup n outer ->
        if isValueClass qr (Just oc) then return (app "𝔮ⁿ" [t])
        else if isProp c oc then return (app "code_rd" [t])
        else return (app "𝔮ᵛ" [nat (length names + 1 + fromMaybe 0 (elemIndex n (map fst outer)))])
    | n `elem` map fst (qUnknowns qr) -> do
        need qr n
        cd <- code n
        return (app "𝔮ˢ" [cd])
    | typed && not (M.member n (qDefs qr)) && M.member n (cSigs c) && all (isValueClass qr . Just) (cSigs c M.! n) -> return (app "𝔮ⁿ" [t])
    | Just (_, _, dcls) <- M.lookup n (qDefs qr), isValueClass qr (Just dcls), not (S.member n (qStmt qr)), not (unknownish c n) ->
        return (app "𝔮ⁿ" [t])
    | otherwise -> do
        need qr n
        cd <- code n
        return (app "𝔮ˢ" [cd])
  TApp f as
    | typed, TVar fn <- f, fn `elem` transparent, fn `notElem` names, not (locMember fn outer), [a] <- as -> q qr a ib outer typed
    | typed && not (hasRel qr t) && not (freeIn t (S.fromList names))
        && not (mentions c t (S.union (S.fromList (locNames outer)) (S.fromList names))) && isValueClass qr (klass loc) -> return (app "𝔮ⁿ" [t])
    | otherwise -> do
        o0 <- q qr f ib outer typed
        foldM (\out a -> do qa <- q qr a ib outer typed; return (app "𝔮ᵃ" [out, qa])) o0 as
  TLam ps b -> do
    let inner = ib ++ ps
    o <- q qr b inner outer typed
    return (iterate (\x -> app "𝔮ˡ" [x]) o !! length ps)
  TAsc _ _ -> throwParse "a statement cannot be written as a code: asc"
  where
    c = qC qr
    names = map fst ib
    loc = foldl (\l (n, mc) -> locInsert n (fromMaybe F mc) l) outer ib
    klass l = either (const Nothing) (Just . fst) (synth c l t)

definitionCode :: Quoter -> String -> QM Term
definitionCode qr name
  | Just k <- lookup name (qUnknowns qr) = do
      cd <- code "𝔲"
      return (app "𝔮ᵃ" [app "𝔮ˢ" [cd], app "𝔮ⁿ" [TNum (numeral (toDigits (toInteger k, 0)))]])
  | Just (params, body, cls) <- M.lookup name (qDefs qr) = do
      let ps = walk cls params
          walk _ [] = []
          walk cl (p : rest) = case norm (qC qr) cl of
            K _ [a, r] -> (p, Just a) : walk r rest
            _ -> (p, Nothing) : walk F rest
      out <- q qr body ps [] True
      return (iterate (\x -> app "𝔮ˡ" [x]) out !! length params)
  | Just (params, body) <- M.lookup name (qPrelude qr) = do
      out <- q qr body [(p, Nothing) | p <- params] [] False
      return (iterate (\x -> app "𝔮ˡ" [x]) out !! length params)
  | otherwise = throwParse ("no definition for " ++ name ++ " to write as a code")

-- | replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝
quoteReplace :: Quoter -> Term -> QM Term
quoteReplace qr t = case t of
  TQuote e loc -> do
    cd <- q qr e [] loc True
    return (app "simplify′" [TVar envName, cd])
  TApp f as -> do
    f' <- quoteReplace qr f
    as' <- mapM (quoteReplace qr) as
    return (TApp f' as')
  TLam ps b -> TLam ps <$> quoteReplace qr b
  _ -> return t

-- | the one table of definitions for the whole program
quoteTable :: Quoter -> QM Term
quoteTable qr = do
  entries <- loop 0 []
  let unkNames = map fst (qUnknowns qr)
      first = [e | (_, e) <- sortOn (\(n, _) -> fromMaybe 0 (elemIndex n unkNames)) [x | x@(n, _) <- entries, n `elem` unkNames]]
      rest = [e | (n, e) <- entries, n `notElem` unkNames]
  return (foldr (\e out -> app "∷" [e, out]) (TVar "⊘") (first ++ rest))
  where
    loop k acc = do
      needed <- gets sNeeded
      if k >= length needed then return (reverse acc)
      else do
        let name = needed !! k
        cd <- code name
        dc <- definitionCode qr name
        loop (k + 1) ((name, app "⊗" [cd, dc]) : acc)
