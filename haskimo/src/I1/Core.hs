-- | Core.hs -- the lazy evaluator of i-1 (port of the Machine of pymo/imo_core.py).
--
-- A definition is an untyped lambda term in de Bruijn form.  Evaluation is call-by-need: here it is Haskell's own laziness.
--   * a value is a function from a (lazy) argument to a value;
--   * a global is a shared lazy value, resolved through a knot-tied map;
--   * every closed application is evaluated at most once for the whole run (it is floated out into a shared value).
-- The decoders apply a language value to builder constants of the host (VT, VF, VCons, ...) and read what comes back.
module I1.Core
  ( V(..), Machine, buildMachine, buildMachineWith, missingGlobals, global, apply
  , toBool, toList, toPair, toOrd, streamNth, listValue, callG, cellOrNil
  , consCb, nilV, pairCb
  , digitsOf, natural, giOf
  ) where

import qualified Data.Map.Lazy as M
import I1.Base
import I1.Syntax (Core(..))

-- | a value of the language, or what a decoder gets back from one
data V
  = Fn (V -> V)
  | VT | VF                -- ^ results of applying a Church boolean to the markers
  | VCons V V | VNil       -- ^ results of applying a Scott list to the list builders
  | VPair V V              -- ^ result of applying a pair to the pair builder
  | VInt Int               -- ^ result of applying an ordering to numbers
  | VCN V | VCS V | VCA V V | VCL V | VCV V   -- ^ the five constructors of a code (lib/prove.imo)

apply :: V -> V -> V
apply (Fn f) x = f x
apply v _ = error ("a value that is not a function was applied: " ++ describe v)

describe :: V -> String
describe v = case v of
  Fn _ -> "function"
  VT -> "true"
  VF -> "false"
  VCons _ _ -> "cons cell"
  VNil -> "nil"
  VPair _ _ -> "pair"
  VInt k -> show k
  VCN _ -> "number code"
  VCS _ -> "symbol code"
  VCA _ _ -> "application code"
  VCL _ -> "lambda code"
  VCV _ -> "variable code"

type Machine = M.Map String V

-- | link the definitions (a global that is used and not defined is an error when it is evaluated)
buildMachine :: [(String, Core)] -> Machine
buildMachine defs = buildMachineWith defs []

-- | the same, with some globals given as ready values (the unknowns, whose value is an error)
buildMachineWith :: [(String, Core)] -> [(String, V)] -> Machine
buildMachineWith defs extra = m
  where
    m = M.fromList ([(n, snd (comp glob c) []) | (n, c) <- defs] ++ extra)
    glob g = case M.lookup g m of
      Just v -> v
      Nothing -> error ("i-1: " ++ g ++ " has no compiled body")

-- | the globals that some definition uses and nothing defines
missingGlobals :: [(String, Core)] -> [String] -> [String]
missingGlobals defs extra =
  let defined = M.fromList [(n, ()) | (n, _) <- defs] `M.union` M.fromList [(n, ()) | n <- extra]
      used c acc = case c of
        CG g -> if M.member g defined then acc else g : acc
        CL b -> used b acc
        CA f x -> used f (used x acc)
        CV _ -> acc
  in M.keys (M.fromList [(g, ()) | (_, c) <- defs, g <- used c []])

global :: Machine -> String -> V
global m g = case M.lookup g m of
  Just v -> v
  Nothing -> error ("i-1: " ++ g ++ " is not defined")

-- | compile a term to a function of its environment (the bound variables, innermost first);
-- the Int is the number of environment entries the term needs (0: closed).
-- An argument that is a variable, a global or a closed term is passed as the pointer that is already there: no thunk is built for it.
comp :: (String -> V) -> Core -> (Int, [V] -> V)
comp glob = go
  where
    go (CV k) = (k, \env -> env !! (k - 1))
    go (CG g) = let v = glob g in (0, \_ -> v)
    go (CL b) =
      let (nb, cb) = go b
          n = max 0 (nb - 1)
      in if n == 0
           then let v = Fn (\x -> cb [x]) in (0, \_ -> v)
           else (n, \env -> Fn (\x -> cb (x : env)))
    go (CA f x) =
      let (nf, cf) = go f
          (nx, cx) = go x
          n = max nf nx
          bad v = error ("a value that is not a function was applied: " ++ describe v)
          run = case (f, x) of
            (CG g, _) -> let fv = glob g in withArg (\_ h -> case fv of Fn k -> k h; v -> bad v) nx cx x
            _ -> withArg (\env h -> case cf env of Fn k -> k h; v -> bad v) nx cx x
      in if n == 0 then let v = run [] in (0, \_ -> v) else (n, run)
    -- build the application from  "apply the function to this argument"  and the way the argument is obtained
    withArg :: ([V] -> V -> V) -> Int -> ([V] -> V) -> Core -> [V] -> V
    withArg app nx cx x = case x of
      CV 1 -> \env -> case env of (v : _) -> app env v; [] -> app env (cx env)
      CV 2 -> \env -> case env of (_ : v : _) -> app env v; _ -> app env (cx env)
      CV 3 -> \env -> case env of (_ : _ : v : _) -> app env v; _ -> app env (cx env)
      CV 4 -> \env -> case env of (_ : _ : _ : v : _) -> app env v; _ -> app env (cx env)
      CG g -> let gv = glob g in \env -> app env gv
      _ | nx == 0 -> let c = cx [] in \env -> app env c
        | otherwise -> \env -> app env (cx env)

-- ---------------------------------------------------------------- decoding
toBool :: V -> Bool
toBool v = case apply (apply v VT) VF of
  VT -> True
  _ -> False

consCb :: V
consCb = Fn (\h -> Fn (\t -> VCons h t))

nilV :: V
nilV = VNil

pairCb :: V
pairCb = Fn (\a -> Fn (\b -> VPair a b))

-- | an ordering (lib/bounded.imo): a Scott value with three alternatives, read as 0, 1 or 2
toOrd :: V -> Int
toOrd v = case apply (apply (apply v (VInt 0)) (VInt 1)) (VInt 2) of
  VInt r -> r
  _ -> error "an ordering was expected"

-- | take a list cell apart: VCons, VNil, or (for an undetermined value) something else
cellOrNil :: V -> V
cellOrNil v = apply (apply v consCb) VNil

-- | a list of booleans (digits, least significant first)
toList :: V -> [Int]
toList v = case cellOrNil v of
  VCons h t -> (if toBool h then 1 else 0) : toList t
  VNil -> []
  _ -> error "a list was expected"

toPair :: V -> (V, V)
toPair v = case apply v pairCb of
  VPair a b -> (a, b)
  _ -> error "a pair was expected"

-- | element n (from 0) of a stream
streamNth :: V -> Int -> V
streamNth v n
  | n <= 0 = case cellOrNil v of
      VCons h _ -> h
      _ -> error "a stream was expected"
  | otherwise = case cellOrNil v of
      VCons _ t -> streamNth t (n - 1)
      _ -> error "a stream was expected"

-- | the digit list (LSB first) as a language value
listValue :: Machine -> [Int] -> V
listValue m ds = foldr (\d acc -> apply (apply cons (if d /= 0 then tv else fv)) acc) fv ds
  where
    tv = global m "⊤"
    fv = global m "⊥"
    cons = global m "∷"

-- | apply the global f to the arguments
callG :: Machine -> String -> [V] -> V
callG m f = foldl apply (global m f)

-- ---------------------------------------------------------------- numbers read back from values
-- | the digit string of a value (least significant first)
digitsOf :: V -> [Int]
digitsOf = toList

-- | a natural number from a digit-list value (only to name a character)
natural :: V -> Integer
natural v = fst (giOf v)

-- | the Gaussian integer of a digit-list value
giOf :: V -> GI
giOf = valDigits . toList
