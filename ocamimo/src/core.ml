(* core.ml -- the lazy evaluator of i-1 (port of rustimo/src/core.rs).
   A definition is an untyped lambda term in de Bruijn form.  Evaluation is call-by-need, on an explicit stack, so that the depth of a
   computation is limited by memory and not by the stack of the host:
     * every term is compiled once to `code` with FLAT closures: a lambda captures exactly the variables it uses, a delayed argument
       (a thunk) too; a frame is the captured values followed by the arguments of the call;
     * a chain of applications ((f a) b) c is one call f [a, b, c], a chain of lambdas one lambda of arity n (eval/apply);
     * an argument that is a variable or a global is passed as the pointer that is already there, a lambda is built at once, every
       other argument becomes a thunk that is evaluated at most once (update frames);
     * every closed application is evaluated at most once for the whole run (floated out into a shared thunk);
     * the decoders apply a language value to builder constants of the host (markers, list and pair builders, ...) and read what comes back. *)
open Base
open Syntax

type prim = PCons | PPair | PCodeN | PCodeS | PCodeA | PCodeL | PCodeV

type v = { mutable st : st }

and st =
  | Done of value (* evaluated, and not a function *)
  | Delayed of thunkinfo * v array (* not evaluated yet *)
  | Clo of laminfo * v array (* a function value: a lambda with what it captured *)
  | Pap of v * v array (* a partial application of a Clo or a Prim (never of another Pap): the function and the arguments held so far *)
  | Lazy of int (* a global that is not compiled yet (the index of its source) *)
  | Prim of prim (* a builder of the host *)
  | Running
  | Fail of err

(* a value of the language in weak head normal form, or what a decoder gets back from one *)
and value =
  | Fun of v
  | VT
  | VF
  | VCons of v * v
  | VNil
  | VPair of v * v
  | VInt of int
  | VCN of v
  | VCS of v
  | VCA of v * v
  | VCL of v
  | VCV of v

and code =
  | Var of int (* a variable of the frame *)
  | Const of v (* a global, or a shared closed term or lambda *)
  | Lam of laminfo (* build a closure from the frame *)
  | App of code * arg array (* call a function expression with arguments *)
  | Call of v * arg array (* call a global lambda of known arity with at least that many arguments *)
  | CallVar of int * arg array (* call a variable of the frame *)
  | PapC of papspec (* a global lambda of known arity applied to fewer arguments: the partial application is built at once *)

and arg = AVar of int | AConst of v | ALam of laminfo | ADelay of thunkinfo | APap of papspec
and papspec = { pg : v; pargs : arg array }
and laminfo = { arity : int; lcaps : int array; lbody : code }
and thunkinfo = { tcaps : int array; tbody : code }

let mk (st : st) : v = { st }
let done_ (x : value) : v = mk (Done x)
let dummy : v = { st = Running }
let no_caps : v array = [||]

let prim_arity = function PCons | PPair | PCodeA -> 2 | _ -> 1

let run_prim (p : prim) (a : v array) : value =
  match p with
  | PCons -> VCons (a.(0), a.(1))
  | PPair -> VPair (a.(0), a.(1))
  | PCodeN -> VCN a.(0)
  | PCodeS -> VCS a.(0)
  | PCodeA -> VCA (a.(0), a.(1))
  | PCodeL -> VCL a.(0)
  | PCodeV -> VCV a.(0)

let describe = function
  | Fun _ -> "function"
  | VT -> "true"
  | VF -> "false"
  | VCons _ -> "cons cell"
  | VNil -> "nil"
  | VPair _ -> "pair"
  | VInt k -> string_of_int k
  | VCN _ -> "number code"
  | VCS _ -> "symbol code"
  | VCA _ -> "application code"
  | VCL _ -> "lambda code"
  | VCV _ -> "variable code"

(* ---------------------------------------------------------------- compiling de Bruijn terms *)
(* a term with the levels (absolute binder depths) of its free variables *)
type ann =
  | NV of int
  | NG of string
  | NL of int * ann * int list (* arity, body, free levels bound outside *)
  | NA of ann * ann * int list

let fv_of = function NV _ | NG _ -> [] | NL (_, _, fv) | NA (_, _, fv) -> fv
let free_levels = function NV l -> [ l ] | NG _ -> [] | NL (_, _, fv) | NA (_, _, fv) -> fv
let is_closed = function NV _ -> false | NG _ -> true | NL (_, _, fv) | NA (_, _, fv) -> fv = []

let rec union_sorted (a : int list) (b : int list) : int list =
  match (a, b) with
  | [], l | l, [] -> l
  | x :: xs, y :: ys -> if x < y then x :: union_sorted xs b else if y < x then y :: union_sorted a ys else x :: union_sorted xs ys

(* annotate a term at binder depth `depth`; a run of lambdas becomes one lambda of that arity *)
let rec annotate (t : core) (depth : int) : ann =
  match t with
  | CV k -> NV (depth - k)
  | CG g -> NG g
  | CL _ ->
    let n = ref 0 and cur = ref t in
    while (match !cur with CL b -> cur := b; incr n; true | _ -> false) do () done;
    let body = annotate !cur (depth + !n) in
    let fv = List.filter (fun l -> l < depth) (free_levels body) in
    NL (!n, body, fv)
  | CA (f, x) ->
    let fa = annotate f depth in
    let xa = annotate x depth in
    NA (fa, xa, union_sorted (free_levels fa) (free_levels xa))

(* level -> slot of the frame being compiled for *)
type scope = { mutable slots : int array }

let scope_new () = { slots = [||] }

let scope_set (s : scope) (level : int) (slot : int) : unit =
  if Array.length s.slots <= level then begin
    let n = Array.make (level + 1) (-1) in
    Array.blit s.slots 0 n 0 (Array.length s.slots);
    s.slots <- n
  end;
  s.slots.(level) <- slot

let scope_slot (s : scope) (level : int) : int =
  let r = if level < Array.length s.slots then s.slots.(level) else -1 in
  if r < 0 then failwith "i-1: internal error: a free variable is not in the frame";
  r

type linker = { globals : (string, v) Hashtbl.t; arities : (string, int) Hashtbl.t }

(* the chain of applications of an open application, as its head and its arguments in order; a closed inner application is the head
   (it is shared), not part of the chain *)
let spine (a : ann) : ann * ann list =
  let rec go cur args first =
    match cur with
    | NA (f, x, _) when first || not (is_closed cur) -> go f (x :: args) false
    | _ -> (cur, args)
  in
  go a [] true

let link_global (lk : linker) (g : string) : v =
  match Hashtbl.find_opt lk.globals g with
  | Some v -> v
  | None -> mk (Fail (Eval (Printf.sprintf "i-1: %s has no compiled body" g)))

let rec gen_lam (lk : linker) (a : ann) (depth : int) (sc : scope) : laminfo =
  match a with
  | NL (arity, body, fv) ->
    let caps = Array.of_list (List.map (fun l -> scope_slot sc l) fv) in
    let inner = scope_new () in
    List.iteri (fun j l -> scope_set inner l j) fv;
    for p = 0 to arity - 1 do scope_set inner (depth + p) (List.length fv + p) done;
    let b = gen lk body (depth + arity) inner false in
    { arity; lcaps = caps; lbody = b }
  | _ -> failwith "gen_lam"

(* the code of a delayed argument: a frame of its own free variables *)
and gen_thunk (lk : linker) (a : ann) (depth : int) (sc : scope) : thunkinfo =
  let fv = fv_of a in
  let caps = Array.of_list (List.map (fun l -> scope_slot sc l) fv) in
  let inner = scope_new () in
  List.iteri (fun j l -> scope_set inner l j) fv;
  { tcaps = caps; tbody = gen lk a depth inner true }

(* a closed term as a shared value: a closure is made now, an application is a thunk evaluated at most once *)
and shared (lk : linker) (a : ann) (depth : int) : v =
  match a with
  | NL _ -> mk (Clo (gen_lam lk a depth (scope_new ()), no_caps))
  | _ -> mk (Delayed ({ tcaps = [||]; tbody = gen lk a depth (scope_new ()) true }, no_caps))

and gen_arg (lk : linker) (a : ann) (depth : int) (sc : scope) : arg =
  match a with
  | NV l -> AVar (scope_slot sc l)
  | NG g -> AConst (link_global lk g)
  | _ when is_closed a -> AConst (shared lk a depth)
  | NL _ -> ALam (gen_lam lk a depth sc)
  | NA _ -> (
      (* a known function applied to too few arguments is a value: build it now instead of delaying the work *)
      let head, args = spine a in
      match head with
      | NG g when (match Hashtbl.find_opt lk.arities g with Some n -> List.length args < n | None -> false) ->
        APap (gen_pap lk g args depth sc)
      | _ -> ADelay (gen_thunk lk a depth sc))

and gen_pap (lk : linker) (g : string) (args : ann list) (depth : int) (sc : scope) : papspec =
  { pg = link_global lk g; pargs = Array.of_list (List.map (fun x -> gen_arg lk x depth sc) args) }

(* `root`: the term is the body of a thunk or of a global (it is evaluated once, so it is not floated out again) *)
and gen (lk : linker) (a : ann) (depth : int) (sc : scope) (root : bool) : code =
  match a with
  | NV l -> Var (scope_slot sc l)
  | NG g -> Const (link_global lk g)
  | NL _ -> if is_closed a then Const (shared lk a depth) else Lam (gen_lam lk a depth sc)
  | NA _ -> (
      if (not root) && is_closed a then Const (shared lk a depth)
      else begin
        let cur, args = spine a in
        let gargs () = Array.of_list (List.map (fun x -> gen_arg lk x depth sc) args) in
        match cur with
        | NG g when Hashtbl.mem lk.arities g ->
          let n = Hashtbl.find lk.arities g in
          if List.length args >= n then Call (link_global lk g, gargs ()) else PapC (gen_pap lk g args depth sc)
        | NV l ->
          let slot = scope_slot sc l in
          CallVar (slot, gargs ())
        | _ ->
          let head = gen lk cur depth sc false in
          App (head, gargs ())
      end)

(* the state of a global definition: a closed lambda is a function value at once, anything else a delayed expression *)
let gen_def (lk : linker) (c : core) : st =
  let a = annotate c 0 in
  match a with
  | NL _ -> Clo (gen_lam lk a 0 (scope_new ()), no_caps)
  | _ -> Delayed ({ tcaps = [||]; tbody = gen lk a 0 (scope_new ()) true }, no_caps)

(* ---------------------------------------------------------------- the machine *)
type cont = KUpdate of v | KArg of v

(* where the code of a global comes from: a term already in de Bruijn form, or a checked definition to erase when it is first needed *)
type source = SCore of core | STerm of string list * term

let rec term_lams = function Syntax.Lam (ps, b) -> List.length ps + term_lams b | Syntax.Asc (e, _) | Syntax.Quote (e, _) -> term_lams e | _ -> 0
let term_arity ps body = List.length ps + term_lams body

let core_arity (c : core) : int =
  let rec go n = function CL b -> go (n + 1) b | _ -> n in
  go 0 c

type machine = {
  mglobals : (string, v) Hashtbl.t;
  marity : (string, int) Hashtbl.t;
  lazy_src : source option array;
  mutable conts : cont array;
  mutable ntop : int;
  mutable frame : v array;
  vt : v;
  vf : v;
  vnil : v;
  cons_cb : v;
  pair_cb : v;
  ints : v array;
  code_cbs : v array;
  mutable app_infos : thunkinfo array;
}

let push (m : machine) (k : cont) : unit =
  if m.ntop >= Array.length m.conts then begin
    let n = Array.make (max 64 (2 * Array.length m.conts)) (KArg dummy) in
    Array.blit m.conts 0 n 0 m.ntop;
    m.conts <- n
  end;
  Array.unsafe_set m.conts m.ntop k;
  m.ntop <- m.ntop + 1

let pop (m : machine) : cont =
  m.ntop <- m.ntop - 1;
  let k = Array.unsafe_get m.conts m.ntop in
  Array.unsafe_set m.conts m.ntop (KArg dummy);
  k

(* how many further arguments (at most `want`) are waiting on the stack above `base` *)
let waiting (m : machine) (base : int) (want : int) : int =
  let n = ref 0 in
  while !n < want && m.ntop > base + !n && (match Array.unsafe_get m.conts (m.ntop - 1 - !n) with KArg _ -> true | _ -> false) do incr n done;
  !n

let pick (frame : v array) (idx : int array) : v array =
  let n = Array.length idx in
  if n = 0 then no_caps
  else begin
    let r = Array.make n dummy in
    for i = 0 to n - 1 do Array.unsafe_set r i (Array.unsafe_get frame (Array.unsafe_get idx i)) done;
    r
  end

(* the value of an argument: a variable and a global are passed as they are, a lambda is built at once, a partial application of a known
   function too, anything else is delayed *)
let rec make_arg (a : arg) (frame : v array) : v =
  match a with
  | AVar i -> Array.unsafe_get frame i
  | AConst c -> c
  | ALam info -> mk (Clo (info, pick frame info.lcaps))
  | ADelay info -> mk (Delayed (info, pick frame info.tcaps))
  | APap spec -> make_pap spec frame

and make_pap (spec : papspec) (frame : v array) : v =
  let n = Array.length spec.pargs in
  let held = Array.make n dummy in
  for i = 0 to n - 1 do held.(i) <- make_arg spec.pargs.(i) frame done;
  mk (Pap (spec.pg, held))

let build (defs : (string * source) list) (extra : (string * v) list) : machine =
  let globals = Hashtbl.create 16384 in
  (* the ready values first (they win over a definition of the same name), then the placeholders: definitions refer to each other (and to
     themselves) through them, and are compiled when they are first needed *)
  List.iter (fun (n, v) -> Hashtbl.replace globals n v) extra;
  let arity = Hashtbl.create 16384 in
  let last = Hashtbl.create 16384 in
  List.iteri (fun i (n, _) -> Hashtbl.replace last n i) defs; (* a later definition of the same name wins *)
  let lazy_src = Array.make (List.length defs) None in
  List.iteri
    (fun i (n, src) ->
       if Hashtbl.find last n = i && not (Hashtbl.mem globals n) then begin
         let ar = match src with SCore c -> core_arity c | STerm (ps, b) -> term_arity ps b in
         if ar > 0 then Hashtbl.replace arity n ar;
         Hashtbl.replace globals n (mk (Lazy i));
         lazy_src.(i) <- Some src
       end)
    defs;
  let prim p = mk (Prim p) in
  {
    mglobals = globals;
    marity = arity;
    lazy_src;
    conts = Array.make 1024 (KArg dummy);
    ntop = 0;
    frame = [||];
    vt = done_ VT;
    vf = done_ VF;
    vnil = done_ VNil;
    cons_cb = prim PCons;
    pair_cb = prim PPair;
    ints = [| done_ (VInt 0); done_ (VInt 1); done_ (VInt 2) |];
    code_cbs = [| prim PCodeN; prim PCodeS; prim PCodeA; prim PCodeL; prim PCodeV |];
    app_infos = [||];
  }

(* compile a global that has not been needed before *)
let compile_global (m : machine) (idx : int) : st =
  let src = m.lazy_src.(idx) in
  m.lazy_src.(idx) <- None;
  let core =
    match src with
    | Some (SCore c) -> Ok c
    | Some (STerm (ps, b)) -> (try Ok (snd (erase_def "" ps b)) with Err e -> Error e)
    | None -> Error (Eval "i-1: internal error: a global was compiled twice")
  in
  match core with Error e -> Fail e | Ok c -> gen_def { globals = m.mglobals; arities = m.marity } c

let global (m : machine) (g : string) : v =
  match Hashtbl.find_opt m.mglobals g with Some v -> v | None -> raise (Err (Eval (Printf.sprintf "i-1: %s is not defined" g)))

let has_global (m : machine) (g : string) : bool = Hashtbl.mem m.mglobals g

(* the lazy application of f to args: a thunk that is evaluated when it is needed *)
let app (m : machine) (f : v) (args : v array) : v =
  let n = Array.length args in
  if Array.length m.app_infos <= n then begin
    let old = Array.length m.app_infos in
    let infos =
      Array.init (n + 1) (fun k ->
          if k < old then m.app_infos.(k)
          else begin
            (* frame: [f, a1 .. ak]; body: f a1 .. ak *)
            let body = if k = 0 then Var 0 else App (Var 0, Array.init k (fun i -> AVar (i + 1))) in
            { tcaps = Array.init (k + 1) (fun i -> i); tbody = body }
          end)
    in
    m.app_infos <- infos
  end;
  let caps = Array.make (n + 1) f in
  Array.blit args 0 caps 1 n;
  mk (Delayed (m.app_infos.(n), caps))

(* apply a lambda (`clo` is the thunk that holds it; `held` the arguments of the partial application it may be inside) *)
let call_clo (m : machine) (base : int) (info : laminfo) (caps : v array) (held : v array) (clo : v) (first : v) : [ `Eval of code | `Value of value ] =
  let nh = Array.length held in
  let need = info.arity - nh in
  let extra = waiting m base (need - 1) in
  if extra + 1 < need then begin
    (* not enough arguments yet: a partial application *)
    let h = Array.make (nh + 1 + extra) first in
    Array.blit held 0 h 0 nh;
    for k = 1 to extra do
      match pop m with KArg a -> h.(nh + k) <- a | _ -> ()
    done;
    `Value (Fun (mk (Pap (clo, h))))
  end else begin
    let nc = Array.length caps in
    let fr = Array.make (nc + nh + need) first in
    Array.blit caps 0 fr 0 nc;
    Array.blit held 0 fr nc nh;
    fr.(nc + nh) <- first;
    for k = 1 to need - 1 do
      match pop m with KArg a -> fr.(nc + nh + k) <- a | _ -> ()
    done;
    m.frame <- fr;
    `Eval info.lbody
  end

let call_prim (m : machine) (base : int) (p : prim) (held : v array) (prim_v : v) (first : v) : value =
  let nh = Array.length held in
  let need = prim_arity p - nh in
  let extra = waiting m base (need - 1) in
  let args = Array.make (nh + 1 + extra) first in
  Array.blit held 0 args 0 nh;
  for k = 1 to extra do
    match pop m with KArg a -> args.(nh + k) <- a | _ -> ()
  done;
  if extra + 1 < need then Fun (mk (Pap (prim_v, args))) else run_prim p args

(* evaluate  start args  to weak head normal form *)
let run (m : machine) (start : v) (args : v array) : value =
  let base = m.ntop in
  for k = Array.length args - 1 downto 0 do push m (KArg args.(k)) done;
  let rec force (t : v) : value =
    match t.st with
    | Done x -> deliver x
    | Clo _ | Pap _ | Prim _ -> deliver (Fun t)
    | Running -> raise (Err (Eval "<<loop>>"))
    | Fail e -> raise (Err e)
    | Lazy i ->
      t.st <- compile_global m i;
      force t
    | Delayed (info, caps) ->
      t.st <- Running;
      m.frame <- caps;
      push m (KUpdate t);
      eval info.tbody
  and eval_var (t : v) : value =
    match t.st with
    | Done x -> deliver x
    | Clo _ | Pap _ | Prim _ -> deliver (Fun t)
    | _ -> force t
  and eval (code : code) : value =
    match code with
    | Var i -> eval_var (Array.unsafe_get m.frame i)
    | Const t -> eval_var t
    | Lam info -> deliver (Fun (mk (Clo (info, pick m.frame info.lcaps))))
    | Call (g, args) -> (
        (match g.st with Lazy i -> g.st <- compile_global m i | _ -> ());
        match g.st with
        | Clo (info, _) when info.arity <= Array.length args ->
          let n = info.arity in
          let fr = m.frame in
          for k = Array.length args - 1 downto n do push m (KArg (make_arg args.(k) fr)) done;
          let nf = Array.make n dummy in
          for k = 0 to n - 1 do Array.unsafe_set nf k (make_arg (Array.unsafe_get args k) fr) done;
          m.frame <- nf;
          eval info.lbody
        | _ ->
          let fr = m.frame in
          for k = Array.length args - 1 downto 0 do push m (KArg (make_arg args.(k) fr)) done;
          force g)
    | CallVar (i, args) -> (
        let t = Array.unsafe_get m.frame i in
        match t.st with
        | Clo (info, caps) when info.arity = Array.length args ->
          let fr = m.frame in
          let nc = Array.length caps and na = Array.length args in
          let nf = Array.make (nc + na) dummy in
          Array.blit caps 0 nf 0 nc;
          for k = 0 to na - 1 do Array.unsafe_set nf (nc + k) (make_arg (Array.unsafe_get args k) fr) done;
          m.frame <- nf;
          eval info.lbody
        | _ ->
          let fr = m.frame in
          for k = Array.length args - 1 downto 0 do push m (KArg (make_arg args.(k) fr)) done;
          eval_var t)
    | PapC spec -> deliver (Fun (make_pap spec m.frame))
    | App (f, args) ->
      let fr = m.frame in
      for k = Array.length args - 1 downto 0 do push m (KArg (make_arg args.(k) fr)) done;
      eval f
  (* deliver the value to what is waiting for it *)
  and deliver (x : value) : value =
    if m.ntop <= base then x
    else
      match pop m with
      | KUpdate t ->
        t.st <- Done x;
        deliver x
      | KArg first -> (
          match x with
          | Fun f -> (
              let entered =
                match f.st with
                | Clo (info, caps) -> call_clo m base info caps no_caps f first
                | Prim p -> `Value (call_prim m base p no_caps f first)
                | Pap (b, held) -> (
                    (match b.st with Lazy i -> b.st <- compile_global m i | _ -> ());
                    match b.st with
                    | Clo (info, caps) -> call_clo m base info caps held b first
                    | Prim p -> `Value (call_prim m base p held b first)
                    | _ -> failwith "i-1: internal error: a partial application of a non-function")
                | _ -> failwith "i-1: internal error: a function value is not a function"
              in
              match entered with `Eval code -> eval code | `Value v -> deliver v)
          | other -> raise (Err (Eval ("a value that is not a function was applied: " ^ describe other))))
  in
  try force start
  with Err e ->
    (* an error: the thunks under evaluation keep it (evaluating them again gives the same error), the rest of the work is dropped *)
    while m.ntop > base do
      match pop m with KUpdate t -> t.st <- Fail e | _ -> ()
    done;
    raise (Err e)

let whnf (m : machine) (v : v) : value = run m v [||]
let apply_whnf (m : machine) (f : v) (args : v array) : value = run m f args

(* ---------------------------------------------------------------- decoding *)
let to_bool (m : machine) (v : v) : bool = match apply_whnf m v [| m.vt; m.vf |] with VT -> true | _ -> false

(* the truth value that a Boolean selects between the markers: Some true, Some false, or None for anything else (⍰) *)
let tri (m : machine) (v : v) : bool option =
  match apply_whnf m v [| m.vt; m.vf |] with VT -> Some true | VF -> Some false | _ -> None

(* take a list cell apart: Cons, Nil, or (for an undetermined value) something else *)
let cell_or_nil (m : machine) (v : v) : value = apply_whnf m v [| m.cons_cb; m.vnil |]

(* an ordering (lib/bounded.imo): a Scott value with three alternatives, read as 0, 1 or 2 *)
let to_ord (m : machine) (v : v) : int =
  match apply_whnf m v [| m.ints.(0); m.ints.(1); m.ints.(2) |] with VInt r -> r | _ -> raise (Err (Eval "an ordering was expected"))

(* a list of booleans (digits, least significant first) *)
let to_list (m : machine) (v : v) : int array =
  let out = ref [] and cur = ref v and fin = ref false in
  while not !fin do
    match cell_or_nil m !cur with
    | VCons (h, t) ->
      out := (if to_bool m h then 1 else 0) :: !out;
      cur := t
    | VNil -> fin := true
    | _ -> raise (Err (Eval "a list was expected"))
  done;
  Array.of_list (List.rev !out)

let to_pair (m : machine) (v : v) : v * v =
  match apply_whnf m v [| m.pair_cb |] with VPair (a, b) -> (a, b) | _ -> raise (Err (Eval "a pair was expected"))

(* element n (from 0) of a stream *)
let stream_nth (m : machine) (v : v) (n : int) : v =
  let cur = ref v and k = ref n and res = ref None in
  while !res = None do
    match cell_or_nil m !cur with
    | VCons (h, t) -> if !k = 0 then res := Some h else (decr k; cur := t)
    | _ -> raise (Err (Eval "a stream was expected"))
  done;
  match !res with Some h -> h | None -> assert false

(* the digit list (LSB first) as a language value *)
let list_value (m : machine) (ds : int array) : v =
  let tv = global m "⊤" and fv = global m "⊥" and cons = global m "∷" in
  let acc = ref fv in
  for i = Array.length ds - 1 downto 0 do
    acc := app m cons [| (if ds.(i) <> 0 then tv else fv); !acc |]
  done;
  !acc

(* the lazy application of the global f to the arguments *)
let call_g (m : machine) (f : string) (args : v array) : v = app m (global m f) args

(* the Gaussian integer of a digit-list value *)
let gi_of (m : machine) (v : v) : gi = val_digits (to_list m v)
