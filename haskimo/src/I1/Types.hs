-- | Types.hs -- the class checker of i-1 (port of pymo/imotypes.py).
--
-- Rules (all enforced here)
--   * every symbol must be DECLARED  (name ∶ class)  before it is defined or used;
--   * classes are terms:  atoms (ℕ ℤ ℚ ℝ ℤ[i] ℚ[i] ℝ[i] 𝔹 𝕮 𝕊 𝔻 …)  and constructors  (→ A B) (𝔏 A) (𝔖 A) (𝔗 A) (𝔄 A) (𝔓 A B);
--   * a symbol may carry several declarations (overloads = an intersection of classes);
--   * facts   (⊆ A B)  subclass,   (≣ A B)  class equation,   (↪ f)  f is a canonical (widening) coercion;
--   * lambda binders must be annotated   (x ∶ A ↦ …);   definition parameters take their classes from the declaration;
--   * numerals get the smallest class containing their value:  ℕ ⊆ ℤ ⊆ ℤ[i] ⊆ ℚ[i],  ℤ ⊆ ℚ ⊆ ℚ[i],  radix numerals are ℚ or ℚ[i];
--   * 'trusted' files (the prelude) have their signatures recorded but their bodies are NOT checked.
--
-- Statements (the class Prop, spec Ω): a user symbol that is declared and never defined is an UNKNOWN; STATEMENTS have class Ω and
-- are marked  TQuote φ (classes of the variables bound outside φ); Quote.hs writes φ as a code and the simplifier computes its
-- simplest form when it is evaluated.
--
-- The checker is pure: every function takes the checker and returns a result in  Either String  (Left = an ImoTypeError message).
module I1.Types
  ( Checker(..), emptyChecker, Check
  , kk, propTy, boolTy, numTy, chain, mkChain, hasVar, subst, termToType, numClass
  , relR, connO, domains
  , norm, wf, leq, join, domain, unknownish, mentions, isProp
  , declare, entriesFor, synth, fit, settleTaint, checkStatement
  ) where

import Control.Monad (foldM, when)
import Data.List (nub)
import qualified Data.Map.Strict as M
import Data.Ratio
import qualified Data.Set as S
import I1.Base
import I1.Syntax

type Check a = Either String a

-- | the covariant class constructors
cov :: [String]
cov = ["𝔏", "𝔖", "𝔗", "𝔓"]

relR :: [String]
relR = ["≐ᴿ", "≠ᴿ", "≺ᴿ", "⩽ᴿ", "≻ᴿ", "⩾ᴿ"]

-- | connectives on statements -> the connective their code uses
connO :: [(String, String)]
connO = [("∧Ω", "∧"), ("∨Ω", "∨"), ("¬Ω", "¬"), ("⇒Ω", "⇒"), ("⇔Ω", "⇔")]

coercionCost :: String -> Int
coercionCost "decide" = 2
coercionCost _ = 1

-- | the domains of unknowns: the first number class (in this order) that contains the declared class
domains :: [(String, Int)]
domains = [("ℕ", 6), ("ℤ", 5), ("ℚ", 3), ("ℤ[i]", 4), ("ℚ[i]", 2), ("ℝ", 1), ("ℝ[i]", 0)]

kk :: String -> Ty
kk n = K n []

propTy, boolTy, numTy :: Ty
propTy = kk "Ω"
boolTy = kk "𝔹"
numTy = kk "ℚ[i]"

arrow :: String
arrow = "→"

-- ---------------------------------------------------------------- the checker
data Checker = Checker
  { cClasses :: M.Map String Int               -- ^ name -> arity
  , cFormers :: S.Set String                   -- ^ symbols whose declared result is 𝒮
  , cSigs :: M.Map String [Ty]                 -- ^ value symbol -> classes
  , cFacts :: [(Ty, Ty)]                       -- ^ (sub, super)
  , cFactIdx :: M.Map Ty [Ty]                  -- ^ normalised sub -> its supers, in order
  , cEqs :: M.Map String Ty                    -- ^ atom -> class
  , cCoercions :: [String]
  , cCov :: S.Set String                       -- ^ the covariant class constructors: the built-in ones and those declared with (↗ C)
  , cDefined :: S.Set String
  , cOverloads :: M.Map String [String]        -- ^ human symbol -> spec symbols
  , cUnknowns :: [(String, Maybe Int)]         -- ^ unknown -> its domain code, in declaration order
  , cUserDefined :: S.Set String
  , cRawTaint :: S.Set String                  -- ^ program symbols whose definitions mention an unknown (estimated before checking)
  , cTaint :: M.Map String Bool                -- ^ program symbol -> does its checked body need the value of an unknown?
  }

emptyChecker :: Checker
emptyChecker = Checker
  { cClasses = M.fromList [("→", 2), ("𝒦", 0), ("𝒮", 0)]
  , cFormers = S.empty, cSigs = M.empty, cFacts = [], cFactIdx = M.empty, cEqs = M.empty, cCoercions = [], cCov = S.fromList cov
  , cDefined = S.empty, cOverloads = M.empty, cUnknowns = [], cUserDefined = S.empty, cRawTaint = S.empty, cTaint = M.empty }

-- ---------------------------------------------------------------- class terms
termToType :: Term -> Check Ty
termToType t = case t of
  TVar n -> Right (if n `elem` classVars then V n else kk n)
  TApp (TVar n) as -> K n <$> mapM termToType as
  _ -> Left ("not a class expression: " ++ reprTerm t)

chain :: Ty -> ([Ty], Ty)
chain (K "→" [a, b]) = let (ps, r) = chain b in (a : ps, r)
chain t = ([], t)

mkChain :: [Ty] -> Ty -> Ty
mkChain ps r = foldr (\p acc -> K arrow [p, acc]) r ps

hasVar :: Ty -> Bool
hasVar (V _) = True
hasVar (K _ as) = any hasVar as
hasVar F = False

-- | substitute class variables; with flex, the unbound ones become the flexible class ⊥
subst :: Ty -> M.Map String Ty -> Bool -> Ty
subst t s flex = case t of
  V n -> case M.lookup n s of
    Just r -> r
    Nothing -> if flex then F else t
  K n as -> K n [subst a s flex | a <- as]
  F -> F

-- | the smallest class containing the value of a numeral written in base i-1
numClass :: String -> Ty
numClass text =
  let (bits, k) = case break (== '.') text of
        (a, []) -> (a, 0 :: Int)
        (a, _ : b) -> (a ++ b, length b)
      z = valDigits [if c == '1' then 1 else 0 | c <- reverse bits]
      den = iterate (gmul bGI) (1, 0) !! k
      n = fst den ^ (2 :: Int) + snd den ^ (2 :: Int)
      re = (fst z * fst den + snd z * snd den) % n
      im = (snd z * fst den - fst z * snd den) % n
  in if im == 0
       then (if denominator re == 1 then (if re >= 0 then kk "ℕ" else kk "ℤ") else kk "ℚ")
       else if denominator re == 1 && denominator im == 1 then kk "ℤ[i]" else kk "ℚ[i]"

-- ---------------------------------------------------------------- classes
norm :: Checker -> Ty -> Ty
norm c t = case t of
  K n [] | Just e <- M.lookup n (cEqs c) -> norm c e
  K n as -> K n (map (norm c) as)
  _ -> t

wf :: Checker -> Ty -> Check ()
wf _ (V _) = Right ()
wf _ F = Right ()
wf c (K name args) = case M.lookup name (cClasses c) of
  Nothing -> Left ("undeclared class " ++ name)
  Just k
    | k /= length args -> Left ("class " ++ name ++ " takes " ++ show k ++ " argument(s), got " ++ show (length args))
    | otherwise -> mapM_ (wf c) args

-- | the same class, where the flexible class ⊥ (an unconstrained polymorphic constant, e.g. emptydict ∶ Dict α) equals anything
flexEq :: Ty -> Ty -> Bool
flexEq x y = x == y || x == F || y == F || case (x, y) of
  (K n xs, K m ys) -> n == m && length xs == length ys && and (zipWith flexEq xs ys)
  _ -> False

leq :: Checker -> Ty -> Ty -> Bool
leq c = leqS c S.empty

leqS :: Checker -> S.Set (Ty, Ty) -> Ty -> Ty -> Bool
leqS c seen a0 b0 =
  a == b || a == F || structural || viaFacts
  where
    a = norm c a0
    b = norm c b0
    structural = case (a, b) of
      (K n as, K m bs)
        | n == m, not (null as), length as == length bs ->
            if n == arrow then leqS c seen (head bs) (head as) && leqS c seen (as !! 1) (bs !! 1)
            else if S.member n (cCov c) then and (zipWith (leqS c seen) as bs)
            else flexEq a b
      _ -> False
    viaFacts = or [ leqS c (S.insert (a, y) seen) y b | y <- M.findWithDefault [] a (cFactIdx c), not (S.member (a, y) seen) ]

-- | a and every class that contains it, by the declared subclass facts
ups :: Checker -> Ty -> [Ty]
ups c a = go [norm c a] []
  where
    go [] out = reverse out
    go (x : todo) out
      | x `elem` out = go todo out
      | otherwise = go (reverse (map (norm c) (M.findWithDefault [] x (cFactIdx c))) ++ todo) (x : out)

-- | the least class containing both a and b (e.g. ℤ[i] and ℚ give ℚ[i]); Nothing if there is none or it is not unique
join :: Checker -> Ty -> Ty -> Maybe Ty
join c a0 b0 =
  let a = norm c a0
      b = norm c b0
  in case (a, b) of
       (K n as, K m bs)
         | n == m, S.member n (cCov c), not (null as), length as == length bs ->
             let js = [ if leq c y x then Just x else if leq c x y then Just y else join c x y | (x, y) <- zip as bs ]
             in if any (== Nothing) js then Nothing else Just (K n [j | Just j <- js])
       _ ->
         let ub = ups c b
             common = [x | x <- ups c a, x `elem` ub]
             least = [x | x <- common, not (any (\d -> d /= x && leq c d x) common)]
         in case least of [l] -> Just l; _ -> Nothing

data Mode = Pos | Neg | Eq deriving Eq

flipMode :: Mode -> Mode
flipMode Pos = Neg
flipMode Neg = Pos
flipMode Eq = Eq

type Subst = M.Map String Ty

-- | match pattern p (may contain class variables) against actual class a; mode: pos (a <= p), neg (p <= a), eq
match :: Checker -> Ty -> Ty -> Subst -> Mode -> Maybe Subst
match c p0 a0 s mode =
  case p of
    V pn -> case M.lookup pn s of
      Just b
        | a == F -> Just s
        | b == F -> Just (M.insert pn a s)
        | mode == Eq -> if flexEq b a then Just s else Nothing
        | leq c a b -> Just s
        | leq c b a -> Just (if mode == Pos then M.insert pn a s else s)
        | mode == Pos -> case join c a b of
            Just j -> Just (M.insert pn j s)
            Nothing -> Nothing
        | otherwise -> Nothing
      Nothing -> Just (M.insert pn a s)
    _
      | not (hasVar p) ->
          if a == F then Just s
          else if (case mode of Pos -> leq c a p; Neg -> leq c p a; Eq -> flexEq p a) then Just s else Nothing
      | a == F -> Just s
      | otherwise ->
          let structural = case (p, a) of
                (K pn pas, K an aas)
                  | pn == an, length pas == length aas ->
                      foldM (\s' (i, (pp, aa)) ->
                               let m | pn == arrow = if i == (0 :: Int) then flipMode mode else mode
                                     | S.member pn (cCov c) = mode
                                     | otherwise = Eq
                               in match c pp aa s' m) s (zip [0 ..] (zip pas aas))
                _ -> Nothing
          in case structural of
               Just r -> Just r
               Nothing
                 | mode == Pos -> firstJust [match c p y s mode | y <- M.findWithDefault [] a (cFactIdx c)]
                 | otherwise -> Nothing
  where
    p = norm c p0
    a = norm c a0

firstJust :: [Maybe a] -> Maybe a
firstJust [] = Nothing
firstJust (Just x : _) = Just x
firstJust (Nothing : r) = firstJust r

-- | the domain code of an unknown of class t: the first number class, in the order ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i], that contains t
domain :: Checker -> Ty -> Maybe Int
domain c t0 =
  let t = norm c t0
  in case t of
       K _ _ | not (hasVar t) ->
         case [k | (name, k) <- domains, M.member name (cClasses c), leq c t (kk name)] of
           (k : _) -> Just k
           [] -> Nothing
       _ -> Nothing

-- | is `name` an unknown, or a program symbol whose value needs the value of an unknown?
unknownish :: Checker -> String -> Bool
unknownish c name
  | name `elem` map fst (cUnknowns c) = True
  | otherwise = case M.lookup name (cTaint c) of
      Just b -> b
      Nothing -> S.member name (cRawTaint c)

-- | does the (checked) term t mention an unknown (or a symbol that needs one) — outside quoted statements?
mentions :: Checker -> Term -> S.Set String -> Bool
mentions c t bound = case t of
  TVar n -> not (S.member n bound) && unknownish c n
  TApp f as -> mentions c f bound || any (\a -> mentions c a bound) as
  TLam ps b -> mentions c b (S.union bound (S.fromList (map fst ps)))
  _ -> False

isProp :: Checker -> Ty -> Bool
isProp c t = norm c t == propTy

-- ---------------------------------------------------------------- declarations and facts
declare :: Checker -> String -> Ty -> Check Checker
declare c name t =
  let (ps, r) = chain t
  in if r == kk "𝒦"
       then if any (/= kk "𝒦") ps then Left (name ++ ": a class constructor takes classes only")
            else Right c { cClasses = M.insert name (length ps) (cClasses c) }
       else if r == kk "𝒮" then Right c { cFormers = S.insert name (cFormers c) }
       else do
         wf c t
         let old = M.findWithDefault [] name (cSigs c)
             new = if t `elem` old then old else old ++ [t]
         Right c { cSigs = M.insert name new (cSigs c) }

reindex :: Checker -> Checker
reindex c = c { cFactIdx = M.fromListWith (++) [(norm c x, [y]) | (x, y) <- reverse (cFacts c)] }

fact :: Checker -> Term -> Check Checker
fact c term = case term of
  TApp (TVar h) args | S.member h (cFormers c) ->
    case h of
      "⊆" -> do
        a <- termToType (args !! 0)
        b <- termToType (args !! 1)
        wf c a
        wf c b
        Right (reindex c { cFacts = cFacts c ++ [(a, b)] })
      "≣" -> do
        a <- termToType (args !! 0)
        b <- termToType (args !! 1)
        wf c a
        wf c b
        case a of
          K n [] -> Right (reindex c { cEqs = M.insert n b (cEqs c) })
          _ -> throwParse "class equation: left side must be an atomic class"
      "↗" -> case args of
        (TVar n : _) ->
          if M.findWithDefault 0 n (cClasses c) >= 1 then Right c { cCov = S.insert n (cCov c) }
          else Left ("covariant: " ++ n ++ " is not a class constructor")
        _ -> Left "covariant:  is not a class constructor"
      "↪" -> case args of
        (TVar f : _) ->
          if M.member f (cSigs c) then Right c { cCoercions = cCoercions c ++ [f] }
          else Left ("coercion " ++ f ++ " is not declared")
        _ -> Left "coercion  is not declared"
      _ -> Left ("unknown statement " ++ h)
  _ -> Left ("not a declared statement: " ++ reprTerm term)

-- ---------------------------------------------------------------- terms
-- | candidate (symbol, class) pairs for a head symbol
entriesFor :: Checker -> String -> Check [(String, Ty)]
entriesFor c hd = do
  let names = M.findWithDefault [hd] hd (cOverloads c)
  fmap concat (mapM (\n -> case M.lookup n (cSigs c) of
                            Nothing -> Left ("undeclared symbol " ++ n)
                            Just es -> Right [(n, e) | e <- es]) names)

-- | apply a class `entry` to args [(class, term)].  -> (result class, new args, cost) or Nothing
tryApply :: Checker -> Ty -> [(Ty, Term)] -> Maybe (Ty, [Term], Int)
tryApply c entry args0 = go entry args0 M.empty 0 []
  where
    go t [] s cost new = Just (subst t s True, reverse new, cost)
    go t ((aTy, term) : rest) s cost new =
      case norm c t of
        K "→" [p, r] ->
          case match c p aTy s Pos of
            Just s' -> go r rest s' cost (term : new)
            Nothing ->
              case bestCoercion p aTy s of
                Nothing -> Nothing
                Just (cname, s1) -> go r rest s1 (cost + coercionCost cname) (TApp (TVar cname) [term] : new)
        _ -> Nothing
    bestCoercion p aTy s = pick Nothing
      [ (cn, cr, s1)
      | cn <- cCoercions c, ce <- M.findWithDefault [] cn (cSigs c)
      , let (cps, cr) = chain ce, length cps == 1
      , leq c aTy (head cps)
      , Just s1 <- [match c p (subst cr M.empty False) s Pos] ]
    pick best [] = fmap (\(cn, _, s1) -> (cn, s1)) best
    pick Nothing (x : xs) = pick (Just x) xs
    pick (Just b@(_, bcr, _)) (x@(_, cr, _) : xs) = pick (Just (if leq c cr bcr then x else b)) xs

resolveApp :: Checker -> String -> [(Ty, Term)] -> String -> Check (String, Ty, [Term])
resolveApp c hd args label = do
  ents <- entriesFor c hd
  let cands = [(name, entry, r) | (name, entry) <- ents, Just r <- [tryApply c entry args]]
      cost (_, _, (_, _, k)) = k
  when (null cands) $
    Left ("no declaration of " ++ label ++ " accepts (" ++ commaSep [showType (fst a) | a <- args]
          ++ ");  candidates: " ++ commaSep [n ++ " ∶ " ++ showType e | (n, e) <- ents])
  let mn = minimum (map cost cands)
      cands' = [x | x <- cands, cost x == mn]
      moreSpecific (_, e1, _) (_, e2, _) =
        let (p1, _) = chain e1
            (p2, _) = chain e2
            n = minimum [length args, length p1, length p2]
        in and (zipWith (leq c) (take n p1) (take n p2))
      best = [x | x <- cands', all (moreSpecific x) cands']
      pool = if null best then cands' else best
      sig (name, _, (rt, _, _)) = (name, rt)
  when (length best /= 1 && length (nub (map sig pool)) /= 1) $
    Left ("ambiguous use of " ++ label ++ ": " ++ semiSep [n ++ " ∶ " ++ showType e | (n, e, _) <- cands'])
  let (name, _, (rt, new, _)) = head pool
  Right (name, rt, new)

commaSep, semiSep :: [String] -> String
commaSep = foldr1' ", "
semiSep = foldr1' "; "

foldr1' :: String -> [String] -> String
foldr1' _ [] = ""
foldr1' sep xs = foldr1 (\a b -> a ++ sep ++ b) xs

synth :: Checker -> Loc -> Term -> Check (Ty, Term)
synth c loc t = case t of
  TNum s -> Right (numClass s, t)
  TChr _ -> Right (kk "𝕮", t)
  TStr _ -> Right (kk "𝕊", t)
  TVar n -> case locLookup n loc of
    Just ty -> Right (ty, t)
    Nothing -> do
      ents <- entriesFor c n
      case ents of
        [(name, e)] -> Right (subst e M.empty True, TVar name)
        _ -> Left (n ++ " is overloaded (" ++ show (length ents) ++ " declarations): use it applied to arguments")
  TAsc e ty -> do
    wf c ty
    (got, term) <- synth c loc e
    case fit c term got ty of
      Just fixed -> Right (ty, fixed)
      Nothing -> Left ("ascription: a term of class " ++ showType got ++ " is not in " ++ showType ty)
  TLam ps body -> do
    (loc2, ptys) <- foldM (\(l, acc) (n, mty) -> case mty of
                              Nothing -> Left ("binder " ++ n ++ " has no class: write (" ++ n ++ " ∶ class ↦ …)")
                              Just ty -> do wf c ty; Right (locInsert n ty l, acc ++ [ty])) (loc, []) ps
    (rt, body') <- synth c loc2 body
    Right (mkChain ptys rt, TLam ps body')
  TQuote _ _ -> Right (propTy, t)
  TApp f as -> do
    args <- mapM (synth c loc) as
    case f of
      TVar h | not (locMember h loc) ->
        case resolveApp c h args h of
          Left e -> do
            joined <- joinList c loc t
            case joined of
              Nothing -> Left e
              Just j -> Right j
          Right (name, rt, new) -> Right (statement c loc name rt new)
      _ -> do
        (ft, fterm) <- synth c loc f
        case tryApply c ft args of
          Nothing -> Left ("cannot apply a function of class " ++ showType ft ++ " to (" ++ commaSep [showType (fst a) | a <- args] ++ ")")
          Just (r, new, _) -> Right (r, TApp fterm new)

-- | the checked application (name new…) of class rt — marked as a quoted statement (class Ω) when it is one
statement :: Checker -> Loc -> String -> Ty -> [Term] -> (Ty, Term)
statement c loc name rt new
  | name `elem` relR && length new == 2 = (propTy, TQuote app loc)
  | name `elem` map fst connO && isProp c rt = (propTy, TQuote app loc)
  | (r == propTy || r == boolTy) && any (\a -> mentions c a bound) new = (propTy, TQuote app loc)
  | otherwise = (rt, app)
  where
    app = TApp (TVar name) new
    bound = S.fromList (locNames loc)
    r = norm c rt

-- | a cons chain (a list literal) whose elements are truth values and statements is a list of statements: the truth values are
-- made statements (prop).  Nothing when that is not the case.
joinList :: Checker -> Loc -> Term -> Check (Maybe (Ty, Term))
joinList c loc t =
  let (items, tl) = collect t []
  in if null items || not (M.member "∷" (cSigs c)) then Right Nothing
     else do
       el <- mapM (synth c loc) items
       (tc, tt) <- synth c loc tl
       let listProp = K "𝔏" [propTy]
       if not (any (isProp c . fst) el || norm c tc == listProp) || not (leq c tc listProp)
         then Right Nothing
         else Right (build (reverse el) tt)
  where
    collect tm acc = case tm of
      TApp (TVar h) [x, rest] | h `elem` ["∷", "hum:cons"], not (locMember h loc) -> collect rest (acc ++ [x])
      _ -> (acc, tm)
    build [] out = Just (K "𝔏" [propTy], out)
    build ((cl, x) : rest) out
      | isProp c cl = build rest (TApp (TVar "∷") [x, out])
      | leq c cl boolTy = build rest (TApp (TVar "∷") [TApp (TVar "prop") [x], out])
      | otherwise = Nothing

-- | term (of class got) made to fit the class want: as it is, through one coercion, element by element for a list or pair
-- literal, or — for a λ — by fitting its body.  Nothing when it does not fit.
fit :: Checker -> Term -> Ty -> Ty -> Maybe Term
fit c term got want
  | leq c got want = Just term
  | Just fixed <- viaCoercion = Just fixed
  | term == TVar "⊘", K "𝔏" _ <- w = Just term
  | Just r <- literal = Just r
  | Just r <- lambda = Just r
  | otherwise = Nothing
  where
    g = norm c got
    w = norm c want
    viaCoercion = case [ TApp (TVar cn) [term]
                       | cn <- cCoercions c, ce <- M.findWithDefault [] cn (cSigs c)
                       , let (cps, cr) = chain ce, length cps == 1, leq c got (head cps), leq c cr want ] of
      [] -> Nothing
      xs -> Just (last xs)
    literal = case (term, g, w) of
      (TApp (TVar h) [a, b], K gn gargs, K wn wargs)
        | gn == wn ->
            let consCase = if h == "∷" && gn == "𝔏"
                  then do h' <- fit c a (head gargs) (head wargs)
                          t' <- fit c b got want
                          Just (TApp (TVar "∷") [h', t'])
                  else Nothing
                pairCase = if h == "⊗" && gn == "𝔓"
                  then do x <- fit c a (gargs !! 0) (wargs !! 0)
                          y <- fit c b (gargs !! 1) (wargs !! 1)
                          Just (TApp (TVar "⊗") [x, y])
                  else Nothing
            in case consCase of Just r -> Just r; Nothing -> pairCase
      _ -> Nothing
    lambda = case term of
      TLam ps b ->
        let n = length ps
            (pg, rg) = chain g
            (pw, rw) = chain w
        in if length pg >= n && length pw >= n && and (zipWith (\x y -> leq c y x) (take n pg) (take n pw))
             then fmap (TLam ps) (fit c b (mkChain (drop n pg) rg) (mkChain (drop n pw) rw))
             else Nothing
      _ -> Nothing

-- | after checking: which program symbols need the value of an unknown (the least fixed point over their checked bodies)
settleTaint :: Checker -> [(String, [String], Term)] -> Checker
settleTaint c0 defs = go c0 { cTaint = M.fromList [(n, False) | (n, _, _) <- defs] }
  where
    go c =
      let (c', changed) = foldl step (c, False) defs
          step (cc, ch) (n, ps, body)
            | not (M.findWithDefault False n (cTaint cc)) && mentions cc body (S.fromList ps) = (cc { cTaint = M.insert n True (cTaint cc) }, True)
            | otherwise = (cc, ch)
      in if changed then go c' else c'

-- ---------------------------------------------------------------- statements
-- | check one statement; returns the checker as it stands afterwards (also after an error: the effects Python's checker has
-- before it raises are kept) and the resolved statement
checkStatement :: Checker -> Stmt -> Bool -> (Checker, Check Stmt)
checkStatement c st trusted = case st of
  Decl name ty -> case declare c name ty of
    Left e -> (c, Left e)
    Right c1
      | not trusted, Just _ <- lookup name (cUnknowns c1) ->
          if length (M.findWithDefault [] name (cSigs c1)) > 1
            then (c1, Left (name ++ " is declared but never defined, so it is an unknown, and an unknown has one class"))
            else case domain c1 ty of
              Nothing -> (c1, Left (name ++ " is declared but never defined, so it is an unknown; an unknown must be a number "
                                    ++ "(a class below ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i] — human \\NN \\ZZ \\QQ \\Z \\Q \\RR \\CC), not " ++ showType ty))
              Just k -> (c1 { cUnknowns = [(n, if n == name then Just k else v) | (n, v) <- cUnknowns c1] }, Right st)
      | otherwise -> (c1, Right st)
  Fact t -> case fact c t of
    Left e -> (c, Left e)
    Right c1 -> (c1, Right st)
  Def name params body
    | S.member name (cDefined c) -> (c, Left (name ++ " is defined twice"))
    | not (M.member name (cSigs c)) ->
        (c, Left (name ++ " is defined before it is declared:  write  " ++ name ++ " ∶ <class>  first"))
    | otherwise ->
        let c1 = c { cDefined = S.insert name (cDefined c) }
        in if trusted then (c1, Right st) else loop c1 (M.findWithDefault [] name (cSigs c1)) Nothing
      where
        loop cc [] out = (cc, maybe (Left "no declaration") Right out)
        loop cc (entry : rest) out =
          case checkEntry cc entry of
            Left e -> (cc, Left e)
            Right newbody -> case out of
              Nothing ->
                let cc' = cc { cTaint = M.insert name (mentions cc newbody (S.fromList params)) (cTaint cc) }
                in loop cc' rest (Just (Def name params newbody))
              Just _ -> loop cc rest out
        checkEntry cc entry = do
          let (ps, r) = chain entry
          when (length params > length ps) $
            Left (name ++ " has " ++ show (length params) ++ " parameters but its class " ++ showType entry ++ " has only " ++ show (length ps))
          let loc = foldl (\l (p, i) -> locInsert p (ps !! i) l) [] (zip params [0 ..])
              want = mkChain (drop (length params) ps) r
          (got, newbody) <- synth cc loc body
          case fit cc newbody got want of
            Nothing -> Left (name ++ ": the body has class " ++ showType got ++ " but " ++ showType want ++ " was declared")
            Just fixed -> Right fixed
