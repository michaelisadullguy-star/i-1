(* output.ml -- printing values: the output side of the three notations, and the `main` entry point (port of rustimo/src/output.rs).
   A value is printed as a NORMAL-FORM TERM in the chosen notation, so that what is printed can be read back, in that notation, as a term
   that denotes the same value.  Nothing is computed on the host: the normal forms are computed IN THE LANGUAGE (⊜, showq / showc,
   decimals); the host walks the value as its declared class describes it, reads digit strings and turns code points into characters.
   main ∶ 𝕊: its text is the output; main ∶ 𝔏 𝕊 / 𝔖 𝕊: one line per element; any other class: the value, as a term in the output notation. *)
open Base
open Core
open Hum
open Layers
open Program
open Syntax
open Types

let modes = [ "bin"; "spec"; "hum" ]

let undetermined =
  "undetermined: this truth value is neither proved nor refuted — a statement that depends on its unknowns, or a relation on ℝ[i] that no rule decides (declare it Prop to print its simplest form instead of a Bool)"

type cell = Cons of v * v | Nil

type printer = { p : program; mode : string; n : int }

let esc (q : int) (s : string) : string =
  let b = Buffer.create (String.length s) in
  Array.iter
    (fun c ->
       if c = 92 then Buffer.add_string b "\\\\"
       else if c = 10 then Buffer.add_string b "\\n"
       else if c = 9 then Buffer.add_string b "\\t"
       else if c = q then (Buffer.add_char b '\\'; add_cp b c)
       else add_cp b c)
    (decode s);
  Buffer.contents b

let make_printer p mode n = { p; mode; n }
let mach pr = machine pr.p
let chk pr = pr.p.checker
let is_hum pr = pr.mode = "hum"

(* take a list / string cell apart; ⍰ (an undetermined Boolean inside the text) is reported, never printed as text *)
let cell_of pr (v : v) : cell =
  match cell_or_nil (mach pr) v with VCons (h, t) -> Cons (h, t) | VNil -> Nil | _ -> print_err undetermined

let boolean_of pr (v : v) : bool =
  let m = mach pr in
  match apply_whnf m v [| m.vt; m.vf |] with VT -> true | VF -> false | _ -> print_err undetermined

let call pr (f : string) (args : v array) : v = call_g (mach pr) f args

(* a 𝕮 value (a natural numeral, as a ℚ[i] pair) -> character; its canonical form is a pair (n, 1) *)
let char_of pr (v : v) : int =
  let m = mach pr in
  let canon = call pr "⊜" [| v |] in
  let z, mm = to_pair m canon in
  let zd = to_list m z in
  let ok_den = to_list m mm = [| 1 |] in
  let cp = match val_digits_small zd with Some (re, im) -> if im = 0 && re >= 0 && re <= 0x10FFFF then Some re else None | None -> None in
  match (cp, ok_den) with Some c, true -> if c >= 0xD800 && c <= 0xDFFF then 0xFFFD else c | _ -> 0xFFFD

(* a 𝕊 value -> String (code point by code point) *)
let text_of pr (v : v) : string =
  let out = Buffer.create 64 in
  let cell = ref (cell_of pr v) in
  let fin = ref false in
  while not !fin do
    match !cell with
    | Nil -> fin := true
    | Cons (h, t) ->
      add_cp out (char_of pr h);
      cell := cell_of pr t
  done;
  Buffer.contents out

let digits_str pr (v : v) : string = numeral (to_list (mach pr) v)
let is_class pr (cls : ty) (name : string) : bool = leq (chk pr) cls (kk name) && leq (chk pr) (kk name) cls

let rec strip_quotes (t : term) : term =
  match t with
  | Quote (e, _) -> strip_quotes e
  | App (f, args) -> App (strip_quotes f, List.map strip_quotes args)
  | Lam (ps, b) -> Lam (ps, strip_quotes b)
  | _ -> t

(* ------------------------------------------------------------ the Speller: the human spelling of the code of a statement *)
type node = NN of v | NS of v | NA of v * v | NLam | NVar

(* text, precedence, kind *)
type piece = string * int * string

let formula_args = [ "∧"; "∨"; "¬"; "⇒"; "⇔"; "∧Ω"; "∨Ω"; "¬Ω"; "⇒Ω"; "⇔Ω"; "prop"; "decide"; "code_rd" ]
let spell_transparent = [ "⇡"; "prop"; "decide"; "code_rd" ]
let tight = [ "*"; "/"; "^" ]
let assoc = [ "+"; "*" ]

let par ((text, prec, kind) : piece) (need : int) (avoid : string list) : string =
  if prec < need || List.mem kind avoid then "(" ^ text ^ ")" else text

let node_of pr (v : v) : node =
  let m = mach pr in
  let not_a_code () = print_err "a statement whose code is not a code (undetermined, or not built by the simplifier)" in
  match (try Ok (apply_whnf m v m.code_cbs) with Err e -> Error e) with
  | Ok (VCN x) -> NN x
  | Ok (VCS x) -> NS x
  | Ok (VCA (f, a)) -> NA (f, a)
  | Ok (VCL _) -> NLam
  | Ok (VCV _) -> NVar
  | Ok _ -> not_a_code ()
  | Error (Unknown msg) -> raise (Err (Unknown msg))
  | Error _ -> not_a_code ()

let symbol_name pr (c : v) : string =
  let ds = trim_digits (to_list (mach pr) c) in
  let b = "." ^ numeral ds ^ "." in
  match Hashtbl.find_opt pr.p.doc1.b2s b with
  | Some n -> n
  | None -> print_err (Printf.sprintf "a statement mentions the symbol code %s, which neither doc 1 nor this program names" b)

(* reverse doc 2: the first entry that has the spec symbol on its right *)
let rev_entry pr (spec : string) : entry option =
  List.find_opt (fun e -> List.mem e.role [ "value"; "infixl"; "infixr"; "infix"; "prefix" ] && List.mem spec e.rhs) pr.p.doc2.entries

let number_piece pr (q : v) : piece =
  let t =
    try text_of pr (call pr "showc" [| q |])
    with Err (Eval _) -> print_err "a statement holds a value that is not a number where a number is expected"
  in
  let p =
    if contains_sub t " + " || contains_sub t " - " then 6
    else if ends_with t "i" || String.contains t '/' then 7
    else if starts_with t "-" then 8
    else 10
  in
  (t, p, "num")

let rec go pr (v : v) (formula : bool) : piece =
  match node_of pr v with
  | NN x ->
    if formula then begin
      let m = mach pr in
      match apply_whnf m x [| m.vt; m.vf |] with VT -> ("true", 10, "atom") | VF -> ("false", 10, "atom") | _ -> print_err undetermined
    end
    else number_piece pr x
  | NS c ->
    let nm = symbol_name pr c in
    app_piece pr nm [] formula
  | NA (f, a) ->
    (* the spine: head and arguments *)
    let args = ref [ a ] and cur = ref (node_of pr f) and res = ref None in
    while !res = None do
      match !cur with
      | NA (f2, a2) ->
        args := a2 :: !args;
        cur := node_of pr f2
      | NS c ->
        let nm = symbol_name pr c in
        res := Some (app_piece pr nm !args formula)
      | _ -> print_err "a statement applies something that is not a symbol (a λ): it has no human spelling"
    done;
    (match !res with Some r -> r | None -> assert false)
  | _ -> print_err "a statement contains a λ or a bound variable: it has no human spelling yet"

and app_piece pr (name : string) (args : v list) (formula : bool) : piece =
  let k = List.length args in
  let arg i = List.nth args i in
  if (name = "⊤" || name = "⊥") && k = 0 then ((if name = "⊤" then "true" else "false"), 10, "atom")
  else if List.mem name spell_transparent && k = 1 then go pr (arg 0) (formula && name <> "⇡")
  else if name = "⊘" && k = 0 then ("[]", 10, "atom")
  else if name = "∷" && k = 2 then begin
    let first, _, _ = go pr (arg 0) false in
    let items = list_loop pr (arg 1) [ first ] in
    ("[" ^ String.concat ", " items ^ "]", 10, "atom")
  end
  else if (name = "∨" || name = "∨Ω") && k = 2 then begin
    let a = go pr (arg 0) true in
    let b = go pr (arg 1) true in
    (par a 3 [ "and" ] ^ " or " ^ par b 2 [ "and" ], 2, "or")
  end
  else if (name = "∧" || name = "∧Ω") && k = 2 then begin
    let a = go pr (arg 0) true in
    let b = go pr (arg 1) true in
    (par a 4 [] ^ " and " ^ par b 3 [], 3, "and")
  end
  else if (name = "¬" || name = "¬Ω") && k = 1 then begin
    let a = go pr (arg 0) true in
    ("not " ^ par a 4 [], 4, "not")
  end
  else begin
    let sub = List.mem name formula_args in
    let entry = rev_entry pr name in
    let h = match entry with Some e -> e.hum | None -> name in
    let role = match entry with Some e -> e.role | None -> "value" in
    let prec = match entry with Some { prec = Some p; _ } -> p | _ -> 0 in
    if List.mem role [ "infixl"; "infixr"; "infix" ] && k = 2 then begin
      let a = go pr (arg 0) sub in
      let b = go pr (arg 1) sub in
      let ln, rn =
        if h = "^" then (10, prec)
        else if role = "infixl" then (prec, if List.mem h assoc then prec else prec + 1)
        else if role = "infixr" then (prec + 1, prec)
        else (prec + 1, prec + 1)
      in
      let sep = if List.mem h tight then h else " " ^ h ^ " " in
      (par a ln [] ^ sep ^ par b rn [], prec, "op")
    end
    else if role = "prefix" && k = 1 then begin
      let a = go pr (arg 0) sub in
      let x0 = par a prec [] in
      let x = if h = "-" && starts_with x0 "-" then (let t, _, _ = a in "(" ^ t ^ ")") else x0 in
      let first_alpha = h <> "" && (let c = (decode h).(0) in (c >= 65 && c <= 90) || (c >= 97 && c <= 122) || c > 127) in
      ((if first_alpha then h ^ " " ^ x else h ^ x), prec, "op")
    end
    else if k = 0 && role = "value" then (h, 10, "atom")
    else if role <> "value" then print_err (Printf.sprintf "%s applied to %d argument(s) has no human spelling" h k)
    else begin
      let as_ = List.map (fun a -> let t, _, _ = go pr a sub in t) args in
      (h ^ "(" ^ String.concat ", " as_ ^ ")", 10, "atom")
    end
  end

and list_loop pr (rest : v) (acc : string list) : string list =
  let bad () = print_err "a list code that does not end in ⊘" in
  let cur = ref rest and acc = ref acc and res = ref None in
  while !res = None do
    match node_of pr !cur with
    | NS c -> if symbol_name pr c = "⊘" then res := Some !acc else bad ()
    | NA (f, a) -> (
        match node_of pr f with
        | NA (f2, a2) -> (
            match node_of pr f2 with
            | NS c ->
              if symbol_name pr c = "∷" then begin
                let x, _, _ = go pr a2 false in
                acc := !acc @ [ x ];
                cur := a
              end
              else bad ()
            | _ -> bad ())
        | _ -> bad ())
    | _ -> bad ()
  done;
  match !res with Some r -> r | None -> assert false

let spell pr (v : v) : string = let t, _, _ = go pr v true in t

(* the spec term of a human statement, read in the program's context (unknowns declared): the checker chooses ≐ or ≐ᴿ, inserts ⇡ and prop,
   and marks statements — the marks are dropped, the term is what a reader of the output reads back *)
let reread pr (text : string) : string =
  let c = chk pr in
  let term =
    try
      let ts = lex_hum text in
      let term, rest = hum_expr pr.p.hum ts 0 SS.empty in
      (match rest with t :: _ -> parse_err ("unexpected " ^ show_tok t) | [] -> ());
      term
    with Err (Parse e) -> print_err (Printf.sprintf "the statement %s cannot be read in the human notation (%s)" (py_repr text) e)
  in
  match (try Ok (synth c [] term) with Class_error e -> Error e) with
  | Error e -> print_err (Printf.sprintf "the statement %s does not read back in this program: %s" (py_repr text) e)
  | Ok (cls, t) -> (
      match fit c t cls prop_ty with
      | None -> print_err (Printf.sprintf "%s reads back as a %s, not as a statement" (py_repr text) (show_type cls))
      | Some fitted -> pp_term (strip_quotes fitted))

let statement pr (v : v) : string =
  let text = spell pr v in
  if is_hum pr then text else reread pr text

let number pr (v : v) (cls : ty) : string =
  let m = mach pr in
  if is_hum pr then begin
    let f = if leq (chk pr) cls (kk "ℚ") then "showq" else "showc" in
    text_of pr (call pr f [| v |])
  end
  else begin
    let canon = call pr "⊜" [| v |] in
    let z, mm = to_pair m canon in
    let zt = digits_str pr z in
    let mt = digits_str pr mm in
    if mt = "1" then zt else Printf.sprintf "(÷ %s %s)" zt mt
  end

(* the normal-form term of v (of class cls) in spec or hum notation (bin is spelled from spec) *)
let rec term_of pr (v : v) (raw : ty) : string =
  let c = chk pr in
  let m = mach pr in
  let hum = is_hum pr in
  let cls = norm c raw in
  let hd, args = match cls with K (hd, args) -> (hd, args) | _ -> print_err (Printf.sprintf "cannot print a value whose class is not known (%s)" (show_type raw)) in
  if cls = prop_ty then statement pr v
  else if is_class pr raw "𝕊" || (hd = "𝔏" && args <> [] && norm c (List.hd args) = kk "𝕮") then begin
    let s = text_of pr v in
    "\"" ^ esc 34 s ^ "\""
  end
  else if leq c raw (kk "𝕮") then begin
    let ch = char_of pr v in
    "'" ^ esc 39 (string_of_cp ch) ^ "'"
  end
  else if leq c raw num_ty then number pr v raw
  else if hd = "𝔹" then begin
    let b = boolean_of pr v in
    if hum then (if b then "true" else "false") else if b then "⊤" else "⊥"
  end
  else if hd = "𝔒" then begin
    let k = to_ord m v in
    let names = if hum then [| "less"; "same"; "greater" |] else [| "⋖"; "≖"; "⋗" |] in
    names.(min k 2)
  end
  else if hd = "𝔏" then begin
    let el = List.hd args in
    ignore (cell_of pr v);
    if norm c el = bool_ty && not hum then Printf.sprintf "(◀ %s)" (digits_str pr v)
    else begin
      let items = ref [] in
      let cell = ref (cell_of pr v) in
      let fin = ref false in
      while not !fin do
        match !cell with
        | Nil -> fin := true
        | Cons (h, t) ->
          items := term_of pr h el :: !items;
          cell := cell_of pr t
      done;
      let items = List.rev !items in
      if hum then "[" ^ String.concat ", " items ^ "]"
      else List.fold_left (fun out x -> Printf.sprintf "(∷ %s %s)" x out) "⊘" (List.rev items)
    end
  end
  else if hd = "𝔓" then begin
    let a, b = to_pair m v in
    let x = term_of pr a (List.nth args 0) in
    let y = term_of pr b (List.nth args 1) in
    if hum then Printf.sprintf "pair(%s, %s)" x y else Printf.sprintf "(⊗ %s %s)" x y
  end
  else if hd = "𝔗" then begin
    let tag, body = to_pair m v in
    if to_bool m tag then begin
      let a, b = to_pair m body in
      let x = term_of pr a cls in
      let y = term_of pr b cls in
      if hum then Printf.sprintf "node(%s, %s)" x y else Printf.sprintf "(❁ %s %s)" x y
    end
    else begin
      let x = term_of pr body (List.nth args 0) in
      if hum then Printf.sprintf "leaf(%s)" x else Printf.sprintf "(❀ %s)" x
    end
  end
  else if hd = "𝔖" then begin
    let e = stream_nth m v pr.n in
    term_of pr e (List.nth args 0)
  end
  else if hd = "→" || hd = "𝔄" then
    print_err (Printf.sprintf "a value of class %s has no normal form to print (it is a function)" (show_type raw))
  else print_err (Printf.sprintf "cannot print a value of class %s" (show_type raw))

(* lit: the language value of a small natural number, built from its digits (the reader's numeral expansion) *)
let lit pr (k : int) : v =
  let m = mach pr in
  let digits = list_value m (to_digits_native k 0) in
  let one = list_value m [| 1 |] in
  call_g m "⊗" [| digits; one |]

(* the remark printed after a stream element (none in bin: the binary notation has no comments) *)
let comment pr (v : v) (cls0 : ty) : string =
  let c = chk pr in
  let m = mach pr in
  match norm c cls0 with
  | K (hd, [ el ]) when hd = "𝔖" && pr.mode <> "bin" ->
    let mark = if is_hum pr then "--" else "⍝" in
    let approx = ref "" in
    if leq c el num_ty then begin
      let x = stream_nth m v pr.n in
      let re_v = call pr "ℜ" [| x |] in
      let re = text_of pr (call pr "decimals" [| re_v; lit pr 12 |]) in
      let im = call pr "ℑ" [| x |] in
      let eq0 = call pr "≐" [| im; lit pr 0 |] in
      if not (to_bool m eq0) then begin
        let imt = text_of pr (call pr "decimals" [| im; lit pr 12 |]) in
        let stripped = let k = ref 0 in while !k < String.length imt && imt.[!k] = '-' do incr k done; String.sub imt !k (String.length imt - !k) in
        approx := Printf.sprintf ", ≈ %s %s %s i" re (if starts_with imt "-" then "-" else "+") stripped
      end
      else approx := Printf.sprintf ", ≈ %s" re
    end;
    Printf.sprintf "   %s element %d of the stream%s" mark pr.n !approx
  | _ -> ""

let show_value pr (v : v) (cls : ty) : string =
  let t = term_of pr v cls in
  let t2 = if pr.mode = "bin" then spec_term_to_bin t (copy_doc1 pr.p.doc1) else t in
  let cm = comment pr v cls in
  t2 ^ cm

(* ---------------------------------------------------------------- main *)
let output_mode (p : program) (override_ : string option) (name : string) : string =
  match override_ with
  | Some m -> m
  | None -> (match p.out_mode with Some m -> m | None -> (match Hashtbl.find_opt p.notation_of name with Some m -> m | None -> "spec"))

let run_main_inner (p : program) (mode0 : string option) (n : int option) (write : string -> unit) : string =
  let c = p.checker in
  let cls = match Hashtbl.find_opt c.sigs "main" with Some (x :: _) -> x | _ -> print_err "this program has no main:  define  main ∶ <class>  (spec),  main in <Class> := …  (hum)" in
  let mode = output_mode p mode0 "main" in
  let v = val_ p "main" in
  let pr = make_printer p mode (match n with Some k -> k | None -> 10) in
  let c0 = norm c cls in
  if leq c cls (kk "𝕊") then begin
    let cell = ref (cell_of pr v) in
    let fin = ref false in
    while not !fin do
      match !cell with
      | Nil -> fin := true
      | Cons (h, t) ->
        write (string_of_cp (char_of pr h));
        cell := cell_of pr t
    done;
    mode
  end
  else
    match c0 with
    | K (hd, [ el ]) when (hd = "𝔏" || hd = "𝔖") && norm c el = norm c (kk "𝕊") ->
      let cell = ref (cell_of pr v) in
      let k = ref 0 and fin = ref false in
      while not !fin do
        match !cell with
        | Cons (h, t) when (match n with None -> true | Some nn -> !k < nn) ->
          let s = text_of pr h in
          write (s ^ "\n");
          cell := cell_of pr t;
          incr k
        | _ -> fin := true
      done;
      mode
    | _ ->
      let s = show_value pr v cls in
      write (s ^ "\n");
      mode

(* evaluate `main` and write its output; returns the output notation used.  An unknown whose value is needed is reported (Print), as an
   undetermined truth value is. *)
let run_main (p : program) (mode0 : string option) (n : int option) (write : string -> unit) : string =
  try run_main_inner p mode0 n write with Err (Unknown m) -> raise (Err (Print m))
