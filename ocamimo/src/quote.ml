(* quote.ml -- the compiler side of statements (port of rustimo/src/quote.rs).  A statement — a relation on ℝ[i], a relation or predicate
   about an unknown, a connective with a statement operand (types.ml marks them Quote φ …) — is simplified from DEFINITIONS whenever it is
   evaluated or output, so its checked term φ is replaced by a term that builds φ's CODE at run time:
     numeral / Char / String / closed number or Boolean     (𝔮ⁿ value)
     symbol                                                (𝔮ˢ code)   its doc 1 code
     unknown x (declared, never defined)                   (𝔮ˢ code of x)   program-local codes, numbered in DECLARATION order
     application, λ, bound variable                        (𝔮ᵃ f a) (𝔮ˡ b) (𝔮ᵛ k)   de Bruijn indices
     a variable bound outside φ, of class Ω                its value (a statement IS its code)
     prop b, decide φ, ∧Ω ∨Ω ¬Ω ⇒Ω ⇔Ω                       transparent
   and the statement becomes  (simplify′ ε⌜⌝ ⌜φ⌝)  where  ε⌜⌝  is one table, for the whole program, of (code, ⌜definition⌝). *)
open Base
open Layers
open Syntax
open Types

let unfold = [ "exp"; "sin"; "cos"; "sinh"; "cosh"; "log"; "atan" ]

(* the name of the table of definitions *)
let env_name = "ε⌜⌝"

let transparent = [ "prop"; "decide"; "code_rd" ]

type quoter = {
  c : checker;
  defs : (string, string list * term * ty) Hashtbl.t; (* program symbol -> (params, body, declared class) *)
  prelude : (string, string list * term) Hashtbl.t; (* prelude symbol -> (params, body) *)
  unknowns : (string * int) list;
  stmt : (string, unit) Hashtbl.t; (* definitions that contain a statement *)
}

(* state: the doc 1 table (codes are given in order of first use) and the symbols whose definitions go into the table *)
type qs = { mutable doc : doc1; mutable needed : string list (* in order of need *) }

let digits (text : string) : term = app "↓ᶻ" [ Num text ]
let nat (k : int) : term = digits (numeral (to_digits_native k 0))

let rec has_quote = function
  | Quote _ -> true
  | App (f, args) -> has_quote f || List.exists has_quote args
  | Lam (_, b) -> has_quote b
  | _ -> false

(* statements of the program, resolved: (trusted, resolved statement) *)
let mk_quoter (c : checker) (sts : (bool * stmt option) list) (d0 : doc1) : quoter * doc1 =
  let defs = Hashtbl.create 64 and prelude = Hashtbl.create 16 in
  List.iter
    (fun (trusted, st) ->
       match st with
       | Some (Def (n, ps, b)) ->
         if not trusted then begin
           let cls = match Hashtbl.find_opt c.sigs n with Some (x :: _) -> x | _ -> kk "?" in
           Hashtbl.replace defs n (ps, b, cls)
         end
         else if List.mem n unfold then Hashtbl.replace prelude n (ps, b)
       | _ -> ())
    sts;
  let unknowns = List.filter_map (fun (n, k) -> match k with Some k -> Some (n, k) | None -> None) c.unknowns in
  let d1 = copy_doc1 d0 in
  List.iter (fun (n, _) -> ignore (doc1_code d1 n true)) unknowns;
  let stmt = Hashtbl.create 16 in
  Hashtbl.iter (fun n (_, b, _) -> if has_quote b then Hashtbl.replace stmt n ()) defs;
  ({ c; defs; prelude; unknowns; stmt }, d1)

let code (st : qs) (name : string) : term =
  let real = match List.assoc_opt name conn_o with Some b -> b | None -> name in
  let b = doc1_code st.doc real true in
  digits (String.sub b 1 (String.length b - 2))

let need (q : quoter) (st : qs) (name : string) : unit =
  if (Hashtbl.mem q.defs name || Hashtbl.mem q.prelude name || List.exists (fun (n, _) -> n = name) q.unknowns) && not (List.mem name st.needed) then
    st.needed <- st.needed @ [ name ]

let is_value_class (q : quoter) (c0 : ty option) : bool =
  match c0 with
  | None -> false
  | Some c0 -> (
      let c = norm q.c c0 in
      match c with K _ -> c = bool_ty || leq q.c c num_ty | _ -> false)

let rec has_rel (q : quoter) (t : term) : bool =
  match t with
  | Quote _ -> true
  | Var n -> List.mem n rel_r || is_conn_o n || Hashtbl.mem q.stmt n
  | App (f, args) -> has_rel q f || List.exists (has_rel q) args
  | Lam (_, b) -> has_rel q b
  | _ -> false

let rec free_in (t : term) (names : SS.t) : bool =
  match t with
  | Var n -> SS.mem n names
  | App (f, args) -> free_in f names || List.exists (fun a -> free_in a names) args
  | Lam (ps, b) -> free_in b (List.fold_left (fun r (n, _) -> SS.remove n r) names ps)
  | Quote (e, _) -> free_in e names
  | _ -> false

(* the code of a term.  ib: binders inside the quote (innermost last) with their classes; outer: classes of variables bound outside *)
let rec q_term (q : quoter) (st : qs) (t : term) (ib : (string * ty option) list) (outer : loc) (typed : bool) : term =
  let names = List.map fst ib in
  match t with
  | Quote (e, _) -> q_term q st e ib outer typed
  | Num _ | Chr _ | Str _ -> app "𝔮ⁿ" [ t ]
  | Var n -> (
      match rposition (fun m -> m = n) names with
      | Some idx -> app "𝔮ᵛ" [ nat (List.length names - idx) ]
      | None -> (
          match loc_lookup outer n with
          | Some oc ->
            if is_value_class q (Some oc) then app "𝔮ⁿ" [ t ]
            else if is_prop q.c oc then app "code_rd" [ t ]
            else begin
              let pos = match position (fun (m, _) -> m = n) outer with Some p -> p | None -> 0 in
              app "𝔮ᵛ" [ nat (List.length names + 1 + pos) ]
            end
          | None ->
            if List.exists (fun (m, _) -> m = n) q.unknowns then begin
              need q st n;
              let cd = code st n in
              app "𝔮ˢ" [ cd ]
            end
            else if typed && (not (Hashtbl.mem q.defs n)) && Hashtbl.mem q.c.sigs n && List.for_all (fun s -> is_value_class q (Some s)) (Hashtbl.find q.c.sigs n)
            then app "𝔮ⁿ" [ t ]
            else begin
              let direct =
                match Hashtbl.find_opt q.defs n with
                | Some (_, _, dcls) -> is_value_class q (Some dcls) && (not (Hashtbl.mem q.stmt n)) && not (unknownish q.c n)
                | None -> false
              in
              if direct then app "𝔮ⁿ" [ t ]
              else begin
                need q st n;
                let cd = code st n in
                app "𝔮ˢ" [ cd ]
              end
            end))
  | App (f, args) ->
    let transparent_case =
      if typed then (
        match f with
        | Var fn_ when List.mem fn_ transparent && (not (List.mem fn_ names)) && (not (loc_member outer fn_)) && List.length args = 1 ->
          Some (q_term q st (List.hd args) ib outer typed)
        | _ -> None)
      else None
    in
    (match transparent_case with
     | Some r -> r
     | None ->
       let value_case =
         if typed && not (has_rel q t) then begin
           let nameset = SS.of_list names in
           if not (free_in t nameset) then begin
             let both = SS.union (SS.of_list (loc_names outer)) nameset in
             if not (mentions q.c t both) then begin
               let loc = List.fold_left (fun l (n, mc) -> loc_insert l n (match mc with Some x -> x | None -> F)) outer ib in
               let klass = try Some (fst (synth q.c loc t)) with Class_error _ -> None in
               if is_value_class q klass then Some (app "𝔮ⁿ" [ t ]) else None
             end
             else None
           end
           else None
         end
         else None
       in
       (match value_case with
        | Some r -> r
        | None ->
          let out = ref (q_term q st f ib outer typed) in
          List.iter (fun a -> let qa = q_term q st a ib outer typed in out := app "𝔮ᵃ" [ !out; qa ]) args;
          !out))
  | Lam (ps, b) ->
    let inner = ib @ ps in
    let o = ref (q_term q st b inner outer typed) in
    List.iter (fun _ -> o := app "𝔮ˡ" [ !o ]) ps;
    !o
  | Asc _ -> parse_err "a statement cannot be written as a code: asc"

let definition_code (q : quoter) (st : qs) (name : string) : term =
  match List.find_opt (fun (n, _) -> n = name) q.unknowns with
  | Some (_, k) ->
    let cd = code st "𝔲" in
    let kn = numeral (to_digits_native k 0) in
    app "𝔮ᵃ" [ app "𝔮ˢ" [ cd ]; app "𝔮ⁿ" [ Num kn ] ]
  | None -> (
      match Hashtbl.find_opt q.defs name with
      | Some (params, body, cls) ->
        let cl = ref cls and ps = ref [] in
        List.iter
          (fun p ->
             match norm q.c !cl with
             | K (_, [ a0; a1 ]) -> ps := !ps @ [ (p, Some a0) ]; cl := a1
             | _ -> ps := !ps @ [ (p, None) ]; cl := F)
          params;
        let out = ref (q_term q st body !ps [] true) in
        List.iter (fun _ -> out := app "𝔮ˡ" [ !out ]) params;
        !out
      | None -> (
          match Hashtbl.find_opt q.prelude name with
          | Some (params, body) ->
            let ps = List.map (fun p -> (p, None)) params in
            let out = ref (q_term q st body ps [] false) in
            List.iter (fun _ -> out := app "𝔮ˡ" [ !out ]) params;
            !out
          | None -> parse_err (Printf.sprintf "no definition for %s to write as a code" name)))

(* replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝ *)
let rec quote_replace (q : quoter) (st : qs) (t : term) : term =
  match t with
  | Quote (e, loc) ->
    let cd = q_term q st e [] loc true in
    app "simplify′" [ var env_name; cd ]
  | App (f, args) ->
    let f2 = quote_replace q st f in
    let as2 = ref [] in
    List.iter (fun a -> as2 := quote_replace q st a :: !as2) args;
    App (f2, List.rev !as2)
  | Lam (ps, b) -> Lam (ps, quote_replace q st b)
  | _ -> t

(* the one table of definitions for the whole program *)
let quote_table (q : quoter) (st : qs) : term =
  let entries = ref [] and k = ref 0 in
  while !k < List.length st.needed do
    let name = List.nth st.needed !k in
    let cd = code st name in
    let dc = definition_code q st name in
    entries := (name, app "⊗" [ cd; dc ]) :: !entries;
    incr k
  done;
  let entries = List.rev !entries in
  let unk_names = List.map fst q.unknowns in
  let first =
    List.filter_map (fun (n, e) -> match position (fun u -> u = n) unk_names with Some i -> Some (i, e) | None -> None) entries
  in
  let first = List.stable_sort (fun (a, _) (b, _) -> compare a b) first in
  let rest = List.filter_map (fun (n, e) -> if List.mem n unk_names then None else Some e) entries in
  let all = List.map snd first @ rest in
  List.fold_right (fun e out -> app "∷" [ e; out ]) all (var "⊘")
