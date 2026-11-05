(* types.ml -- the class checker of i-1 (port of rustimo/src/types.rs).
   Rules (all enforced here)
     * every symbol must be DECLARED  (name ∶ class)  before it is defined or used;
     * classes are terms: atoms (ℕ ℤ ℚ ℝ ℤ[i] ℚ[i] ℝ[i] 𝔹 𝕮 𝕊 𝔻 …) and constructors (→ A B) (𝔏 A) (𝔖 A) (𝔗 A) (𝔄 A) (𝔓 A B);
     * a symbol may carry several declarations (overloads = an intersection of classes);
     * facts (⊆ A B) subclass, (≣ A B) class equation, (↪ f) f is a canonical (widening) coercion;
     * lambda binders must be annotated; definition parameters take their classes from the declaration;
     * numerals get the smallest class containing their value;
     * 'trusted' files (the prelude) have their signatures recorded but their bodies are NOT checked.
   A class error is raised as Class_error (the host's own exceptions are Base.Err): the program is checked statement by statement and
   every error is collected. *)
open Base
open Syntax

exception Class_error of string

let cerr s = raise (Class_error s)

module SS = Set.Make (String)

let arrow = "→"
let rel_r = [ "≐ᴿ"; "≠ᴿ"; "≺ᴿ"; "⩽ᴿ"; "≻ᴿ"; "⩾ᴿ" ]
let conn_o = [ ("∧Ω", "∧"); ("∨Ω", "∨"); ("¬Ω", "¬"); ("⇒Ω", "⇒"); ("⇔Ω", "⇔") ]
let is_conn_o n = List.mem_assoc n conn_o
let coercion_cost name = if name = "decide" then 2 else 1

(* the domains of unknowns: the first number class (in this order) that contains the declared class *)
let domains = [ ("ℕ", 6); ("ℤ", 5); ("ℚ", 3); ("ℤ[i]", 4); ("ℚ[i]", 2); ("ℝ", 1); ("ℝ[i]", 0) ]
let prop_ty = kk "Ω"
let bool_ty = kk "𝔹"
let num_ty = kk "ℚ[i]"

type mode = Pos | Neg | Eq

let flip = function Pos -> Neg | Neg -> Pos | Eq -> Eq

(* class variable -> class, small and persistent *)
type subst = (string * ty) list

let subst_get (s : subst) n = List.assoc_opt n s
let subst_insert (s : subst) n t : subst = if List.mem_assoc n s then List.map (fun (m, u) -> if m = n then (m, t) else (m, u)) s else s @ [ (n, t) ]

let chain (t : ty) : ty list * ty =
  let rec go acc = function K (n, [ a; b ]) when n = arrow -> go (a :: acc) b | cur -> (List.rev acc, cur) in
  go [] t

let mk_chain (ps : ty list) (r : ty) : ty = List.fold_right (fun p out -> K (arrow, [ p; out ])) ps r

(* the same class, where the flexible class ⊥ equals anything *)
let rec flex_eq (x : ty) (y : ty) : bool =
  if x = y || x = F || y = F then true
  else match (x, y) with K (n, xs), K (m, ys) -> n = m && List.length xs = List.length ys && List.for_all2 flex_eq xs ys | _ -> false

let rec has_var = function V _ -> true | K (_, a) -> List.exists has_var a | F -> false

(* substitute class variables; with flex, the unbound ones become the flexible class ⊥ *)
let rec apply_subst (t : ty) (s : subst) (flex : bool) : ty =
  match t with
  | V n -> (match subst_get s n with Some r -> r | None -> if flex then F else t)
  | K (n, a) -> K (n, List.map (fun x -> apply_subst x s flex) a)
  | F -> F

let comma_sep xs = String.concat ", " xs
let semi_sep xs = String.concat "; " xs

let nth l i = List.nth l i

(* the smallest class containing the value of a numeral written in base i-1 *)
let num_class (text : string) : ty =
  let bits, k =
    match String.index_opt text '.' with
    | None -> (text, 0)
    | Some p -> (String.sub text 0 p ^ String.sub text (p + 1) (String.length text - p - 1), String.length text - p - 1)
  in
  let n = String.length bits in
  let digits = Array.init n (fun i -> if bits.[n - 1 - i] = '1' then 1 else 0) in
  let z = val_digits digits in
  (* den = b^k, n = |den|^2 = 2^k *)
  let den = ref (Bigint.one, Bigint.zero) in
  for _ = 1 to k do den := (Bigint.neg (Bigint.add (fst !den) (snd !den)), Bigint.sub (fst !den) (snd !den)) done;
  let d0 = fst !den and d1 = snd !den in
  let nn = Bigint.add (Bigint.mul d0 d0) (Bigint.mul d1 d1) in
  let re_num = Bigint.add (Bigint.mul (fst z) d0) (Bigint.mul (snd z) d1) in
  let im_num = Bigint.sub (Bigint.mul (snd z) d0) (Bigint.mul (fst z) d1) in
  let divisible x = Bigint.is_zero (snd (Bigint.divrem x nn)) in
  if Bigint.is_zero im_num then (if divisible re_num then (if not (Bigint.is_neg re_num) then kk "ℕ" else kk "ℤ") else kk "ℚ")
  else if divisible re_num && divisible im_num then kk "ℤ[i]"
  else kk "ℚ[i]"

(* ---------------------------------------------------------------- the checker *)
type checker = {
  classes : (string, int) Hashtbl.t; (* name -> arity *)
  formers : (string, unit) Hashtbl.t; (* symbols whose declared result is 𝒮 *)
  sigs : (string, ty list) Hashtbl.t; (* value symbol -> classes *)
  mutable facts : (ty * ty) list; (* (sub, super) *)
  mutable fact_idx : (ty, ty list) Hashtbl.t; (* normalised sub -> its supers, in order *)
  eqs : (string, ty) Hashtbl.t; (* atom -> class *)
  mutable coercions : string list;
  cov : (string, unit) Hashtbl.t; (* the covariant class constructors *)
  defined : (string, unit) Hashtbl.t;
  overloads : (string, string list) Hashtbl.t; (* human symbol -> spec symbols *)
  mutable unknowns : (string * int option) list; (* unknown -> its domain code, in declaration order *)
  user_defined : (string, unit) Hashtbl.t;
  raw_taint : (string, unit) Hashtbl.t; (* program symbols whose definitions mention an unknown (estimated before checking) *)
  taint : (string, bool) Hashtbl.t; (* program symbol -> does its checked body need the value of an unknown? *)
}

let new_checker () : checker =
  let classes = Hashtbl.create 1024 in
  Hashtbl.replace classes "→" 2;
  Hashtbl.replace classes "𝒦" 0;
  Hashtbl.replace classes "𝒮" 0;
  let cov = Hashtbl.create 16 in
  List.iter (fun s -> Hashtbl.replace cov s ()) [ "𝔏"; "𝔖"; "𝔗"; "𝔓" ];
  {
    classes; formers = Hashtbl.create 64; sigs = Hashtbl.create 16384; facts = []; fact_idx = Hashtbl.create 64; eqs = Hashtbl.create 16;
    coercions = []; cov; defined = Hashtbl.create 16384; overloads = Hashtbl.create 256; unknowns = []; user_defined = Hashtbl.create 64;
    raw_taint = Hashtbl.create 16; taint = Hashtbl.create 64;
  }

let copy_checker (c : checker) : checker =
  {
    classes = Hashtbl.copy c.classes; formers = Hashtbl.copy c.formers; sigs = Hashtbl.copy c.sigs; facts = c.facts;
    fact_idx = Hashtbl.copy c.fact_idx; eqs = Hashtbl.copy c.eqs; coercions = c.coercions; cov = Hashtbl.copy c.cov;
    defined = Hashtbl.copy c.defined; overloads = Hashtbl.copy c.overloads; unknowns = c.unknowns;
    user_defined = Hashtbl.copy c.user_defined; raw_taint = Hashtbl.copy c.raw_taint; taint = Hashtbl.copy c.taint;
  }

(* ------------------------------------------------------------ class terms *)
let rec term_to_type (t : term) : ty =
  match t with
  | Var n -> if is_class_var n then V n else kk n
  | App (Var n, args) -> K (n, List.map term_to_type args)
  | _ -> cerr ("not a class expression: " ^ repr_term t)

(* ------------------------------------------------------------ classes *)
let rec norm (c : checker) (t : ty) : ty =
  match t with
  | K (n, []) -> (match Hashtbl.find_opt c.eqs n with Some e -> norm c e | None -> t)
  | K (n, a) -> K (n, List.map (norm c) a)
  | _ -> t

let rec wf (c : checker) (t : ty) : unit =
  match t with
  | V _ | F -> ()
  | K (name, args) -> (
      match Hashtbl.find_opt c.classes name with
      | None -> cerr ("undeclared class " ^ name)
      | Some k ->
        if k <> List.length args then cerr (Printf.sprintf "class %s takes %d argument(s), got %d" name k (List.length args))
        else List.iter (wf c) args)

let leq (c : checker) (a : ty) (b : ty) : bool =
  let seen = ref [] in
  let rec leq_s a0 b0 =
    let a = norm c a0 and b = norm c b0 in
    if a = b || a = F then true
    else begin
      let s =
        match (a, b) with
        | K (n, xs), K (m, ys) when n = m && xs <> [] && List.length xs = List.length ys ->
          if n = arrow then leq_s (nth ys 0) (nth xs 0) && leq_s (nth xs 1) (nth ys 1)
          else if Hashtbl.mem c.cov n then List.for_all2 leq_s xs ys
          else flex_eq a b
        | _ -> false
      in
      if s then true
      else
        match Hashtbl.find_opt c.fact_idx a with
        | None -> false
        | Some supers ->
          List.exists
            (fun y ->
               let key = (a, y) in
               if List.mem key !seen then false
               else begin
                 seen := key :: !seen;
                 let r = leq_s y b in
                 seen := List.tl !seen;
                 r
               end)
            supers
    end
  in
  leq_s a b

(* a and every class that contains it, by the declared subclass facts *)
let ups (c : checker) (a : ty) : ty list =
  let todo = ref [ norm c a ] and out = ref [] in
  while !todo <> [] do
    let x = List.hd !todo in
    todo := List.tl !todo;
    if not (List.mem x !out) then begin
      (match Hashtbl.find_opt c.fact_idx x with Some supers -> List.iter (fun y -> todo := norm c y :: !todo) supers | None -> ());
      out := !out @ [ x ]
    end
  done;
  !out

(* the least class containing both a and b (e.g. ℤ[i] and ℚ give ℚ[i]); None if there is none or it is not unique *)
let rec join (c : checker) (a0 : ty) (b0 : ty) : ty option =
  let a = norm c a0 and b = norm c b0 in
  let covcase =
    match (a, b) with
    | K (n, xs), K (m, ys) when n = m && Hashtbl.mem c.cov n && xs <> [] && List.length xs = List.length ys ->
      let js = List.map2 (fun x y -> if leq c y x then Some x else if leq c x y then Some y else join c x y) xs ys in
      if List.for_all (fun j -> j <> None) js then Some (Some (K (n, List.map Option.get js))) else Some None
    | _ -> None
  in
  match covcase with
  | Some r -> r
  | None -> (
      let ub = ups c b in
      let common = List.filter (fun x -> List.mem x ub) (ups c a) in
      let least = List.filter (fun x -> not (List.exists (fun d -> d <> x && leq c d x) common)) common in
      match least with [ x ] -> Some x | _ -> None)

(* ------------------------------------------------------------ matching a pattern against an actual class *)
let rec first_some f = function [] -> None | x :: r -> (match f x with Some y -> Some y | None -> first_some f r)

let rec do_match (c : checker) (p0 : ty) (a0 : ty) (s : subst) (mode : mode) : subst option =
  let p = norm c p0 and a = norm c a0 in
  match p with
  | V pn -> (
      match subst_get s pn with
      | Some b ->
        if a = F then Some s
        else if b = F then Some (subst_insert s pn a)
        else if mode = Eq then (if flex_eq b a then Some s else None)
        else if leq c a b then Some s
        else if leq c b a then Some (if mode = Pos then subst_insert s pn a else s)
        else if mode = Pos then (match join c a b with Some j -> Some (subst_insert s pn j) | None -> None)
        else None
      | None -> Some (subst_insert s pn a))
  | _ ->
    if not (has_var p) then begin
      if a = F then Some s
      else begin
        let ok = match mode with Pos -> leq c a p | Neg -> leq c p a | Eq -> flex_eq p a in
        if ok then Some s else None
      end
    end
    else if a = F then Some s
    else begin
      let structural =
        match (p, a) with
        | K (pn, pas), K (an, aas) when pn = an && List.length pas = List.length aas ->
          let cur = ref (Some s) in
          (try
             List.iteri
               (fun i (pp, aa) ->
                  let m = if pn = arrow then (if i = 0 then flip mode else mode) else if Hashtbl.mem c.cov pn then mode else Eq in
                  cur := (match !cur with Some cs -> do_match c pp aa cs m | None -> None);
                  if !cur = None then raise Exit)
               (List.combine pas aas)
           with Exit -> ());
          !cur
        | _ -> None
      in
      match structural with
      | Some _ -> structural
      | None ->
        if mode = Pos then (match Hashtbl.find_opt c.fact_idx a with Some supers -> first_some (fun y -> do_match c p y s mode) supers | None -> None)
        else None
    end

(* the domain code of an unknown of class t: the first number class, in the order ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i], that contains t *)
let domain (c : checker) (t0 : ty) : int option =
  let t = norm c t0 in
  match t with
  | K _ when not (has_var t) ->
    (match List.find_opt (fun (name, _) -> Hashtbl.mem c.classes name && leq c t (kk name)) domains with Some (_, k) -> Some k | None -> None)
  | _ -> None

(* is `name` an unknown, or a program symbol whose value needs the value of an unknown? *)
let unknownish (c : checker) (name : string) : bool =
  if List.exists (fun (n, _) -> n = name) c.unknowns then true
  else match Hashtbl.find_opt c.taint name with Some b -> b | None -> Hashtbl.mem c.raw_taint name

(* does the (checked) term t mention an unknown (or a symbol that needs one) — outside quoted statements? *)
let rec mentions (c : checker) (t : term) (bound : SS.t) : bool =
  match t with
  | Var n -> (not (SS.mem n bound)) && unknownish c n
  | App (f, args) -> mentions c f bound || List.exists (fun a -> mentions c a bound) args
  | Lam (ps, b) -> mentions c b (List.fold_left (fun bd (n, _) -> SS.add n bd) bound ps)
  | _ -> false

let is_prop (c : checker) (t : ty) : bool = norm c t = prop_ty

(* ------------------------------------------------------------ declarations and facts *)
let declare (c : checker) (name : string) (t : ty) : unit =
  let ps, r = chain t in
  if r = kk "𝒦" then begin
    if List.exists (fun p -> p <> kk "𝒦") ps then cerr (name ^ ": a class constructor takes classes only");
    Hashtbl.replace c.classes name (List.length ps)
  end
  else if r = kk "𝒮" then Hashtbl.replace c.formers name ()
  else begin
    wf c t;
    let old = try Hashtbl.find c.sigs name with Not_found -> [] in
    Hashtbl.replace c.sigs name (if List.mem t old then old else old @ [ t ])
  end

let reindex (c : checker) : unit =
  let idx = Hashtbl.create 64 in
  List.iter
    (fun (x, y) ->
       let k = norm c x in
       let l = try Hashtbl.find idx k with Not_found -> [] in
       Hashtbl.replace idx k (l @ [ y ]))
    c.facts;
  c.fact_idx <- idx

(* a declared statement: raises Class_error for class errors, Base.Err for the exceptions of the host *)
let fact (c : checker) (term : term) : unit =
  match term with
  | App (Var h, args) when Hashtbl.mem c.formers h -> (
      let arg i = match List.nth_opt args i with Some a -> a | None -> raise (Err (Parse "Prelude.!!: index too large")) in
      match h with
      | "⊆" | "≣" ->
        let a0 = arg 0 in
        let b0 = arg 1 in
        let a = term_to_type a0 in
        let b = term_to_type b0 in
        wf c a;
        wf c b;
        if h = "⊆" then begin
          c.facts <- c.facts @ [ (a, b) ];
          reindex c
        end
        else begin
          match a with
          | K (n, []) ->
            Hashtbl.replace c.eqs n b;
            reindex c
          | _ -> parse_err "class equation: left side must be an atomic class"
        end
      | "↗" -> (
          match args with
          | Var n :: _ ->
            if (match Hashtbl.find_opt c.classes n with Some k -> k | None -> 0) >= 1 then Hashtbl.replace c.cov n ()
            else cerr (Printf.sprintf "covariant: %s is not a class constructor" n)
          | _ -> cerr "covariant:  is not a class constructor")
      | "↪" -> (
          match args with
          | Var f :: _ -> if Hashtbl.mem c.sigs f then c.coercions <- c.coercions @ [ f ] else cerr (Printf.sprintf "coercion %s is not declared" f)
          | _ -> cerr "coercion  is not declared")
      | _ -> cerr ("unknown statement " ^ h))
  | _ -> cerr ("not a declared statement: " ^ repr_term term)

(* ------------------------------------------------------------ terms *)
(* candidate (symbol, class) pairs for a head symbol *)
let entries_for (c : checker) (hd : string) : (string * ty) list =
  let names = match Hashtbl.find_opt c.overloads hd with Some l -> l | None -> [ hd ] in
  List.concat_map
    (fun n ->
       match Hashtbl.find_opt c.sigs n with
       | None -> cerr ("undeclared symbol " ^ n)
       | Some es -> List.map (fun e -> (n, e)) es)
    names

let sigs_of (c : checker) (cn : string) : ty list = match Hashtbl.find_opt c.sigs cn with Some v -> v | None -> []

let best_coercion (c : checker) (p : ty) (a_ty : ty) (s : subst) : (string * subst) option =
  let best = ref None in
  List.iter
    (fun cn ->
       List.iter
         (fun ce ->
            let cps, cr = chain ce in
            match cps with
            | [ cp ] when leq c a_ty cp -> (
                match do_match c p (apply_subst cr [] false) s Pos with
                | Some s1 ->
                  best :=
                    (match !best with
                     | None -> Some (cn, cr, s1)
                     | Some ((_, bcr, _) as b) -> if leq c cr bcr then Some (cn, cr, s1) else Some b)
                | None -> ())
            | _ -> ())
         (sigs_of c cn))
    c.coercions;
  match !best with Some (cn, _, s1) -> Some (cn, s1) | None -> None

(* apply a class `entry` to args [(class, term)].  -> (result class, new args, cost) or None *)
let try_apply (c : checker) (entry : ty) (args : (ty * term) list) : (ty * term list * int) option =
  let t = ref entry and s = ref [] and cost = ref 0 and nw = ref [] in
  try
    List.iter
      (fun (a_ty, term) ->
         match norm c !t with
         | K (n, [ p; r ]) when n = arrow ->
           (match do_match c p a_ty !s Pos with
            | Some s2 ->
              s := s2;
              nw := term :: !nw
            | None -> (
                match best_coercion c p a_ty !s with
                | None -> raise Exit
                | Some (cname, s1) ->
                  s := s1;
                  cost := !cost + coercion_cost cname;
                  nw := App (var cname, [ term ]) :: !nw));
           t := r
         | _ -> raise Exit)
      args;
    Some (apply_subst !t !s true, List.rev !nw, !cost)
  with Exit -> None

let resolve_app (c : checker) (hd : string) (args : (ty * term) list) (label : string) : string * ty * term list =
  let ents = entries_for c hd in
  let cands = List.filter_map (fun (name, entry) -> match try_apply c entry args with Some r -> Some (name, entry, r) | None -> None) ents in
  if cands = [] then
    cerr
      (Printf.sprintf "no declaration of %s accepts (%s);  candidates: %s" label
         (comma_sep (List.map (fun (t, _) -> show_type t) args))
         (comma_sep (List.map (fun (n, e) -> n ^ " ∶ " ^ show_type e) ents)));
  let mn = List.fold_left (fun m (_, _, (_, _, cost)) -> min m cost) max_int cands in
  let cands2 = List.filter (fun (_, _, (_, _, cost)) -> cost = mn) cands in
  let more_specific (_, x1, _) (_, y1, _) =
    let p1, _ = chain x1 and p2, _ = chain y1 in
    let n = min (List.length args) (min (List.length p1) (List.length p2)) in
    List.for_all2 (fun a b -> leq c a b) (take n p1) (take n p2)
  in
  let best = List.filter (fun x -> List.for_all (fun y -> more_specific x y) cands2) cands2 in
  let pool = if best = [] then cands2 else best in
  if List.length best <> 1 then begin
    let sigs = ref [] in
    List.iter (fun (n, _, (rt, _, _)) -> let s = (n, rt) in if not (List.mem s !sigs) then sigs := !sigs @ [ s ]) pool;
    if List.length !sigs <> 1 then
      cerr (Printf.sprintf "ambiguous use of %s: %s" label (semi_sep (List.map (fun (n, e, _) -> n ^ " ∶ " ^ show_type e) cands2)))
  end;
  let name, _, (rt, nw, _) = List.hd pool in
  (name, rt, nw)

(* the checked application (name new…) of class rt — marked as a quoted statement (class Ω) when it is one *)
let statement_of (c : checker) (loc : loc) (name : string) (rt : ty) (nw : term list) : ty * term =
  let app_t = App (var name, nw) in
  let bound = SS.of_list (loc_names loc) in
  let r = norm c rt in
  if List.mem name rel_r && List.length nw = 2 then (prop_ty, Quote (app_t, loc))
  else if is_conn_o name && is_prop c rt then (prop_ty, Quote (app_t, loc))
  else if (r = prop_ty || r = bool_ty) && List.exists (fun a -> mentions c a bound) nw then (prop_ty, Quote (app_t, loc))
  else (rt, app_t)

let rec map_seq f = function [] -> [] | x :: r -> let y = f x in y :: map_seq f r

let rec synth (c : checker) (loc : loc) (t : term) : ty * term =
  match t with
  | Num s -> (num_class s, t)
  | Chr _ -> (kk "𝕮", t)
  | Str _ -> (kk "𝕊", t)
  | Var n -> (
      match loc_lookup loc n with
      | Some ty -> (ty, t)
      | None ->
        let ents = entries_for c n in
        (match ents with
         | [ (name, e) ] -> (apply_subst e [] true, var name)
         | _ -> cerr (Printf.sprintf "%s is overloaded (%d declarations): use it applied to arguments" n (List.length ents))))
  | Asc (e, ty) -> (
      wf c ty;
      let got, term = synth c loc e in
      match fit c term got ty with
      | Some fixed -> (ty, fixed)
      | None -> cerr (Printf.sprintf "ascription: a term of class %s is not in %s" (show_type got) (show_type ty)))
  | Lam (ps, body) ->
    let loc2 = ref loc and ptys = ref [] in
    List.iter
      (fun (n, mty) ->
         match mty with
         | None -> cerr (Printf.sprintf "binder %s has no class: write (%s ∶ class ↦ …)" n n)
         | Some ty ->
           wf c ty;
           loc2 := loc_insert !loc2 n ty;
           ptys := !ptys @ [ ty ])
      ps;
    let rt, body2 = synth c !loc2 body in
    (mk_chain !ptys rt, Lam (ps, body2))
  | Quote _ -> (prop_ty, t)
  | App (f, as_) -> (
      let args = map_seq (fun a -> synth c loc a) as_ in
      match f with
      | Var h when not (loc_member loc h) -> (
          let r = try Ok (resolve_app c h args h) with Class_error e -> Error e in
          match r with
          | Ok (name, rt, nw) -> statement_of c loc name rt nw
          | Error e -> (match join_list c loc t with None -> cerr e | Some j -> j))
      | _ -> (
          let ft, fterm = synth c loc f in
          match try_apply c ft args with
          | None ->
            cerr (Printf.sprintf "cannot apply a function of class %s to (%s)" (show_type ft) (comma_sep (List.map (fun (a, _) -> show_type a) args)))
          | Some (r, nw, _) -> (r, App (fterm, nw))))

(* a cons chain (a list literal) whose elements are truth values and statements is a list of statements: the truth values are made
   statements (prop).  None when that is not the case. *)
and join_list (c : checker) (loc : loc) (t : term) : (ty * term) option =
  let items = ref [] and tl = ref t and go = ref true in
  while !go do
    match !tl with
    | App (Var h, [ x0; x1 ]) when (h = "∷" || h = "hum:cons") && not (loc_member loc h) ->
      items := x0 :: !items;
      tl := x1
    | _ -> go := false
  done;
  let items = List.rev !items in
  if items = [] || not (Hashtbl.mem c.sigs "∷") then None
  else begin
    let el = map_seq (fun x -> synth c loc x) items in
    let tc, tt = synth c loc !tl in
    let list_prop = K ("𝔏", [ prop_ty ]) in
    if (not (List.exists (fun (cl, _) -> is_prop c cl) el || norm c tc = list_prop)) || not (leq c tc list_prop) then None
    else begin
      (* build from the last element outwards *)
      let out = ref (Some tt) in
      List.iter
        (fun (cl, x) ->
           match !out with
           | None -> ()
           | Some o ->
             if is_prop c cl then out := Some (App (var "∷", [ x; o ]))
             else if leq c cl bool_ty then out := Some (App (var "∷", [ App (var "prop", [ x ]); o ]))
             else out := None)
        (List.rev el);
      match !out with Some o -> Some (list_prop, o) | None -> None
    end
  end

(* term (of class got) made to fit the class want: as it is, through one coercion, element by element for a list or pair literal, or — for a λ — by
   fitting its body.  None when it does not fit. *)
and fit (c : checker) (term : term) (got : ty) (want : ty) : term option =
  if leq c got want then Some term
  else begin
    let g = norm c got and w = norm c want in
    (* through one coercion *)
    let via = ref None in
    List.iter
      (fun cn ->
         List.iter
           (fun ce ->
              let cps, cr = chain ce in
              match cps with [ cp ] when leq c got cp && leq c cr want -> via := Some (App (var cn, [ term ])) | _ -> ())
           (sigs_of c cn))
      c.coercions;
    if !via <> None then !via
    else if term = var "⊘" && (match w with K ("𝔏", _) -> true | _ -> false) then Some term
    else begin
      (* a list or pair literal, element by element *)
      let lit =
        match (term, g, w) with
        | App (Var h, [ a0; a1 ]), K (gn, gargs), K (wn, wargs) when gn = wn ->
          let r1 =
            if h = "∷" && gn = "𝔏" then (
              match fit c a0 (nth gargs 0) (nth wargs 0) with
              | Some h2 -> (match fit c a1 got want with Some t2 -> Some (App (var "∷", [ h2; t2 ])) | None -> None)
              | None -> None)
            else None
          in
          if r1 <> None then r1
          else if h = "⊗" && gn = "𝔓" then (
            match fit c a0 (nth gargs 0) (nth wargs 0) with
            | Some x -> (match fit c a1 (nth gargs 1) (nth wargs 1) with Some y -> Some (App (var "⊗", [ x; y ])) | None -> None)
            | None -> None)
          else None
        | _ -> None
      in
      if lit <> None then lit
      else
        match term with
        | Lam (ps, b) ->
          let n = List.length ps in
          let pg, rg = chain g and pw, rw = chain w in
          if List.length pg >= n && List.length pw >= n && List.for_all2 (fun x y -> leq c y x) (take n pg) (take n pw) then begin
            let rest_g = mk_chain (drop n pg) rg and rest_w = mk_chain (drop n pw) rw in
            match fit c b rest_g rest_w with Some nb -> Some (Lam (ps, nb)) | None -> None
          end
          else None
        | _ -> None
    end
  end

(* after checking: which program symbols need the value of an unknown (the least fixed point over their checked bodies) *)
let settle_taint (c : checker) (defs : (string * string list * term) list) : unit =
  Hashtbl.reset c.taint;
  List.iter (fun (n, _, _) -> Hashtbl.replace c.taint n false) defs;
  let changed = ref true in
  while !changed do
    changed := false;
    List.iter
      (fun (n, ps, body) ->
         if not (match Hashtbl.find_opt c.taint n with Some b -> b | None -> false) then begin
           let bound = SS.of_list ps in
           if mentions c body bound then (Hashtbl.replace c.taint n true; changed := true)
         end)
      defs
  done

let check_entry (c : checker) (name : string) (params : string list) (body : term) (entry : ty) : term =
  let ps, r = chain entry in
  if List.length params > List.length ps then
    cerr (Printf.sprintf "%s has %d parameters but its class %s has only %d" name (List.length params) (show_type entry) (List.length ps));
  let loc = ref [] in
  List.iteri (fun i p -> loc := loc_insert !loc p (nth ps i)) params;
  let want = mk_chain (drop (List.length params) ps) r in
  let got, newbody = synth c !loc body in
  match fit c newbody got want with
  | None -> cerr (Printf.sprintf "%s: the body has class %s but %s was declared" name (show_type got) (show_type want))
  | Some fixed -> fixed

(* ------------------------------------------------------------ statements *)
(* check one statement; the checker keeps the effects it has before an error (as Python's checker does) and the resolved statement is
   returned (None: the statement is as it was written).  Class errors are raised as Class_error, exceptions of the host as Base.Err. *)
let check_statement (c : checker) (st : stmt) (trusted : bool) : stmt option =
  match st with
  | Decl (name, ty) ->
    declare c name ty;
    if (not trusted) && List.exists (fun (n, _) -> n = name) c.unknowns then begin
      if List.length (sigs_of c name) > 1 then cerr (Printf.sprintf "%s is declared but never defined, so it is an unknown, and an unknown has one class" name);
      match domain c ty with
      | None ->
        cerr
          (Printf.sprintf
             "%s is declared but never defined, so it is an unknown; an unknown must be a number (a class below ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i] — human \\NN \\ZZ \\QQ \\Z \\Q \\RR \\CC), not %s"
             name (show_type ty))
      | Some k ->
        c.unknowns <- List.map (fun (n, d) -> if n = name then (n, Some k) else (n, d)) c.unknowns;
        None
    end
    else None
  | Fact t -> fact c t; None
  | Def (name, params, body) ->
    if Hashtbl.mem c.defined name then cerr (Printf.sprintf "%s is defined twice" name);
    if not (Hashtbl.mem c.sigs name) then cerr (Printf.sprintf "%s is defined before it is declared:  write  %s ∶ <class>  first" name name);
    Hashtbl.replace c.defined name ();
    if trusted then None
    else begin
      let entries = sigs_of c name in
      let out = ref None in
      List.iter
        (fun entry ->
           let newbody = check_entry c name params body entry in
           if !out = None then begin
             let bound = SS.of_list params in
             let t = mentions c newbody bound in
             Hashtbl.replace c.taint name t;
             out := Some (Def (name, params, newbody))
           end)
        entries;
      match !out with Some s -> Some s | None -> cerr "no declaration"
    end
