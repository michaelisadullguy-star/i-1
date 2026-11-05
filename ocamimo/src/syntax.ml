(* syntax.ml -- the SPEC notation reader of i-1 (port of rustimo/src/syntax.rs).
   spec text -> statements:  Def name params body | Decl name type | Fact term.
   Named term AST: Num Chr Str Var App Lam (Asc and Quote are made by the human reader and the class checker).
   Types: K name args (class constructor application), V name (class variable), F (the flexible class); '->' is the constructor of functions. *)
open Base

type ty = K of string * ty list | V of string | F

(* an insertion-ordered map from names to classes (a Python dict) *)
type loc = (string * ty) list

type term =
  | Num of string
  | Chr of int
  | Str of string
  | Var of string
  | App of term * term list
  | Lam of (string * ty option) list * term
  | Asc of term * ty
  | Quote of term * loc (* a statement (class Omega) with the classes of the variables bound outside it *)

type stmt = Def of string * string list * term | Decl of string * ty | Fact of term

(* the runtime term in de Bruijn form *)
type core = CV of int | CL of core | CA of core * core | CG of string

let kk n = K (n, [])
let app f xs = App (Var f, xs)
let var n = Var n

let loc_insert (loc : loc) (n : string) (t : ty) : loc =
  if List.mem_assoc n loc then List.map (fun (m, u) -> if m = n then (m, t) else (m, u)) loc else loc @ [ (n, t) ]

let loc_lookup (loc : loc) (n : string) : ty option = List.assoc_opt n loc
let loc_member (loc : loc) (n : string) : bool = List.mem_assoc n loc
let loc_names (loc : loc) : string list = List.map fst loc

let class_vars = [ "α"; "β"; "γ"; "δ"; "ε" ]
let is_class_var n = List.mem n class_vars

(* ---------------------------------------------------------------- list helpers *)
let rec take n l = if n <= 0 then [] else match l with [] -> [] | x :: r -> x :: take (n - 1) r
let rec drop n l = if n <= 0 then l else match l with [] -> [] | _ :: r -> drop (n - 1) r

let position (f : 'a -> bool) (l : 'a list) : int option =
  let rec go i = function [] -> None | x :: r -> if f x then Some i else go (i + 1) r in
  go 0 l

let rposition (f : 'a -> bool) (l : 'a list) : int option =
  let rec go i last = function [] -> last | x :: r -> go (i + 1) (if f x then Some i else last) r in
  go 0 None l

(* ---------------------------------------------------------------- Haskell-style `show` (the messages of Haskimo quote it) *)
let hs_names =
  [| "NUL"; "SOH"; "STX"; "ETX"; "EOT"; "ENQ"; "ACK"; "a"; "b"; "t"; "n"; "v"; "f"; "r"; "SO"; "SI"; "DLE"; "DC1"; "DC2"; "DC3"; "DC4";
     "NAK"; "SYN"; "ETB"; "CAN"; "EM"; "SUB"; "ESC"; "FS"; "GS"; "RS"; "US" |]

let hs_show_str (s : string) : string =
  let cs = decode s in
  let b = Buffer.create (String.length s + 2) in
  Buffer.add_char b '"';
  Array.iteri
    (fun i u ->
       let next = if i + 1 < Array.length cs then Some cs.(i + 1) else None in
       if u = 34 then Buffer.add_string b "\\\""
       else if u = 92 then Buffer.add_string b "\\\\"
       else if u < 32 then begin
         Buffer.add_char b '\\';
         Buffer.add_string b hs_names.(u);
         if u = 14 && next = Some 72 then Buffer.add_string b "\\&"
       end
       else if u = 127 then Buffer.add_string b "\\DEL"
       else if u > 126 then begin
         Buffer.add_string b (Printf.sprintf "\\%d" u);
         match next with Some n when n >= 48 && n <= 57 -> Buffer.add_string b "\\&" | _ -> ()
       end
       else Buffer.add_char b (Char.chr u))
    cs;
  Buffer.add_char b '"';
  Buffer.contents b

let hs_show_list_str (xs : string list) : string = "[" ^ String.concat "," (List.map hs_show_str xs) ^ "]"

let rec hs_show_ty (t : ty) : string =
  match t with
  | V n -> "V " ^ hs_show_str n
  | F -> "F"
  | K (n, args) -> Printf.sprintf "K %s [%s]" (hs_show_str n) (String.concat "," (List.map hs_show_ty args))

(* ---------------------------------------------------------------- lexer *)
type tok = Nl | Open | Close | TNum of string | TChr of int | TStr of string | Name of string

let hs_show_tok = function
  | Nl -> "TNL"
  | Open -> "TOpen"
  | Close -> "TClose"
  | TNum s -> "TkNum " ^ hs_show_str s
  | TChr c -> Printf.sprintf "TkChr %d" c
  | TStr s -> "TkStr " ^ hs_show_str s
  | Name s -> "TkName " ^ hs_show_str s

let is_delim c = c = 32 || c = 9 || c = 13 || c = 10 || c = 40 || c = 41 || c = 48 || c = 49 || c = 46 || c = 39 || c = 34

let lex_spec (text : string) : tok list =
  let cs = decode text in
  let n = Array.length cs in
  let i = ref 0 and d = ref 0 and out = ref [] in
  while !i < n do
    let c = cs.(!i) in
    if c = 32 || c = 9 || c = 13 then incr i
    else if c = 10 then (if !d = 0 then out := Nl :: !out; incr i)
    else if c = 40 then (out := Open :: !out; incr d; incr i)
    else if c = 41 then (out := Close :: !out; decr d; incr i)
    else if c = 48 || c = 49 || c = 46 then begin
      let j = ref !i in
      while !j < n && (cs.(!j) = 48 || cs.(!j) = 49 || cs.(!j) = 46) do incr j done;
      let s = string_of_cps cs !i !j in
      let dots = ref 0 in
      String.iter (fun ch -> if ch = '.' then incr dots) s;
      if !dots > 1 then parse_err (Printf.sprintf "bad numeral %s (spec notation allows one radix point)" (py_repr s));
      out := TNum s :: !out;
      i := !j
    end
    else if c = 39 || c = 34 then begin
      (* literal: up to the closing quote; a backslash escapes the next character (n, t as in Python) *)
      let body = Buffer.create 16 and blen = ref 0 and first = ref 0 in
      let j = ref (!i + 1) and fin = ref false in
      while not !fin do
        if !j >= n then parse_err "unterminated literal";
        let x = cs.(!j) in
        if x = c then (incr j; fin := true)
        else if x = 92 then begin
          if !j + 1 >= n then parse_err "string index out of range";
          let y = cs.(!j + 1) in
          let y = if y = 110 then 10 else if y = 116 then 9 else y in
          if !blen = 0 then first := y;
          add_cp body y;
          incr blen;
          j := !j + 2
        end else begin
          if !blen = 0 then first := x;
          add_cp body x;
          incr blen;
          incr j
        end
      done;
      if c = 39 then begin
        if !blen = 1 then out := TChr !first :: !out
        else parse_err (Printf.sprintf "char literal needs exactly one character: %s" (py_repr (Buffer.contents body)))
      end
      else out := TStr (Buffer.contents body) :: !out;
      i := !j
    end
    else begin
      let j = ref !i in
      while !j < n && not (is_delim cs.(!j)) do incr j done;
      let name = string_of_cps cs !i !j in
      if name = "\xe2\x8d\x9d" then begin
        (* the comment sign: everything up to the end of the line *)
        let k = ref !j in
        while !k < n && cs.(!k) <> 10 do incr k done;
        i := !k
      end else begin
        out := Name name :: !out;
        i := !j
      end
    end
  done;
  List.rev !out

(* token trees: an atom or a parenthesised group *)
type tt = Atom of tok | Grp of tt list

let rec hs_show_tt = function
  | Atom k ->
    let s = hs_show_tok k in
    if String.contains s ' ' then "Atom (" ^ s ^ ")" else "Atom " ^ s
  | Grp xs -> "Grp [" ^ String.concat "," (List.map hs_show_tt xs) ^ "]"

(* token list (one line, no Nl) -> token trees *)
let trees (ts : tok list) : tt list =
  let arr = Array.of_list ts in
  let n = Array.length arr in
  let i = ref 0 in
  let rec go () =
    let out = ref [] and stop = ref false in
    while (not !stop) && !i < n do
      match arr.(!i) with
      | Open ->
        incr i;
        let inner = go () in
        if !i < n && arr.(!i) = Close then (incr i; out := Grp inner :: !out) else parse_err "missing )"
      | Close -> stop := true
      | t -> out := Atom t :: !out; incr i
    done;
    List.rev !out
  in
  let r = go () in
  if !i < n then parse_err "unexpected )";
  r

(* the logical lines (split at top-level newlines) of a token stream, each as a list of token trees *)
let logical_lines (toks : tok list) : tt list list =
  let lines = ref [] and cur = ref [] in
  List.iter (fun t -> if t = Nl then (lines := List.rev !cur :: !lines; cur := []) else cur := t :: !cur) toks;
  lines := List.rev !cur :: !lines;
  List.fold_left (fun acc l -> let tt = trees l in if tt = [] then acc else tt :: acc) [] (List.rev !lines) |> List.rev

(* ---------------------------------------------------------------- terms *)
let is_name (t : tt) (n : string) : bool = match t with Atom (Name m) -> m = n | _ -> false

let rec parse_item (t : tt) : term =
  match t with
  | Atom (TNum s) -> Num s
  | Atom (TChr c) -> Chr c
  | Atom (TStr s) -> Str s
  | Atom (Name n) -> Var n
  | Atom k -> parse_err ("unexpected " ^ hs_show_tok k)
  | Grp inner -> (
      match rposition (fun x -> is_name x "\xe2\x86\xa6") inner with
      | Some k -> Lam (parse_binders (take k inner), parse_seq (drop (k + 1) inner))
      | None -> parse_seq inner)

and parse_binders (ts : tt list) : (string * ty option) list =
  match ts with
  | [] -> []
  | Atom (Name name) :: rest -> (
      match rest with
      | colon :: after when is_name colon "\xe2\x88\xb6" ->
        let ty, rest' = parse_type_atom after in
        (name, Some ty) :: parse_binders rest'
      | _ -> (name, None) :: parse_binders rest)
  | t :: _ -> parse_err ("bad binder " ^ hs_show_tt t)

and parse_seq (ts : tt list) : term =
  match ts with
  | [] -> parse_err "empty application"
  | [ x ] -> parse_item x
  | x :: xs ->
    let f = parse_item x in
    let args = List.map parse_item xs in
    App (f, args)

(* ---------------------------------------------------------------- types *)
and parse_type_atom (ts : tt list) : ty * tt list =
  match ts with
  | Atom (Name n) :: rest -> ((if is_class_var n then V n else K (n, [])), rest)
  | Grp inner :: rest -> (parse_type_seq inner, rest)
  | t :: _ -> parse_err ("bad type " ^ hs_show_tt t)
  | [] -> parse_err "list index out of range"

and type_atoms (ts : tt list) : ty list =
  match ts with
  | [] -> []
  | _ ->
    let a, r = parse_type_atom ts in
    a :: type_atoms r

and parse_type_seq (inner : tt list) : ty =
  match inner with
  | [] -> parse_err "empty type"
  | first :: rest when is_name first "\xe2\x86\x92" -> (
      match type_atoms rest with
      | [ x; b ] -> K ("\xe2\x86\x92", [ x; b ])
      | _ -> parse_err "\xe2\x86\x92 takes two classes")
  | _ -> (
      match position (fun x -> is_name x "\xe2\x86\x92") inner with
      | Some k ->
        let l = parse_type_seq (take k inner) in
        let r = parse_type_seq (drop (k + 1) inner) in
        K ("\xe2\x86\x92", [ l; r ])
      | None -> (
          let hd, r = parse_type_atom inner in
          let args = type_atoms r in
          if args = [] then hd
          else match hd with K (n, []) -> K (n, args) | other -> parse_err ("bad class application " ^ hs_show_ty other)))

let arrow = "\xe2\x86\x92"

let rec show_type (t : ty) : string =
  match t with
  | V n -> n
  | F -> "\xe2\x8a\xa5"
  | K (n, [ a; b ]) when n = arrow ->
    let l = show_type a in
    let l = match a with K (m, _) when m = arrow -> "(" ^ l ^ ")" | _ -> l in
    l ^ " \xe2\x86\x92 " ^ show_type b
  | K (n, []) -> n
  | K (n, args) ->
    let a = List.map (fun a -> match a with K (m, _) when m = arrow -> "(" ^ show_type a ^ ")" | _ -> show_type a) args in
    "(" ^ n ^ " " ^ String.concat " " a ^ ")"

(* ---------------------------------------------------------------- statements *)
let rec has_assign (t : tt) : bool =
  match t with Atom (Name n) -> n = "\xe2\x89\x94" | Grp xs -> List.exists has_assign xs | _ -> false

let statement (ln : tt list) : stmt =
  if List.exists has_assign ln then begin
    match position (fun t -> is_name t "\xe2\x89\x94") ln with
    | Some k ->
      let hd = take k ln and body = drop (k + 1) ln in
      let names = List.filter_map (function Atom (Name n) -> Some n | _ -> None) hd in
      if hd = [] || List.length names <> List.length hd then parse_err ("bad definition head " ^ hs_show_list_str names);
      Def (List.hd names, List.tl names, parse_seq body)
    | None -> parse_err "assertion failed"
  end
  else begin
    let decl =
      match ln with
      | a :: b :: _ :: _ when is_name b "\xe2\x88\xb6" -> (
          match a with Atom (Name n) -> Some (Decl (n, parse_type_seq (drop 2 ln))) | _ -> parse_err "assertion failed")
      | _ -> None
    in
    match decl with Some d -> d | None -> Fact (parse_seq ln)
  end

let parse_statements (text : string) : stmt list =
  let toks = lex_spec text in
  List.map statement (logical_lines toks)

(* ---------------------------------------------------------------- erasure to the runtime (de Bruijn) term *)
let int_ast (s : string) : core =
  let r = ref (CG "\xe2\x8a\xa5") in
  String.iter
    (fun ch ->
       let d = CG (if ch = '1' then "\xe2\x8a\xa4" else "\xe2\x8a\xa5") in
       r := CA (CA (CG "\xe2\x88\xb7", d), !r))
    s;
  !r

(* the reader's expansion of a numeral: the pair (digits, denominator), digits LSB first *)
let num_ast (s : string) : core =
  let pair a b = CA (CA (CG "\xe2\x8a\x97", a), b) in
  match String.index_opt s '.' with
  | None -> pair (int_ast s) (int_ast "1")
  | Some k ->
    let x = String.sub s 0 k and y = String.sub s (k + 1) (String.length s - k - 1) in
    let bits = x ^ y in
    if bits = "" then parse_err "empty numeral";
    let den = "1" ^ String.make (String.length y) '0' in
    pair (int_ast bits) (int_ast den)

(* scope: the binders in scope, innermost FIRST *)
let rec erase (scope : string list) (t : term) : core =
  match t with
  | Num s -> num_ast s
  | Chr c -> num_ast (int_numeral_text c)
  | Str s ->
    let cs = decode s in
    let r = ref (CG "\xe2\x8a\x98") in
    for i = Array.length cs - 1 downto 0 do
      let c = num_ast (int_numeral_text cs.(i)) in
      r := CA (CA (CG "\xe2\x88\xb7", c), !r)
    done;
    !r
  | Var nm -> (
      match position (fun x -> x = nm) scope with Some idx -> CV (idx + 1) | None -> CG nm)
  | App (f, args) ->
    let acc = ref (erase scope f) in
    List.iter (fun a -> let x = erase scope a in acc := CA (!acc, x)) args;
    !acc
  | Lam (ps, b) ->
    let scope' = List.fold_left (fun sc (n, _) -> n :: sc) scope ps in
    let body = ref (erase scope' b) in
    List.iter (fun _ -> body := CL !body) ps;
    !body
  | Asc (e, _) -> erase scope e
  | Quote (e, _) -> erase scope e

let erase_def (name : string) (params : string list) (body : term) : string * core =
  let scope = List.fold_left (fun sc n -> n :: sc) [] params in
  let c = ref (erase scope body) in
  List.iter (fun _ -> c := CL !c) params;
  (name, !c)

(* ---------------------------------------------------------------- pretty printer (spec text) *)
let rec pp_type (t : ty) : string =
  match t with
  | V n -> n
  | F -> "\xe2\x8a\xa5"
  | K (n, [ a; b ]) when n = arrow -> Printf.sprintf "(\xe2\x86\x92 %s %s)" (pp_type a) (pp_type b)
  | K (n, []) -> n
  | K (n, args) -> Printf.sprintf "(%s %s)" n (String.concat " " (List.map pp_type args))

let esc_with (s : string) (q : int) : string =
  let b = Buffer.create (String.length s) in
  Array.iter
    (fun ch ->
       if ch = 92 then Buffer.add_string b "\\\\"
       else if ch = 10 then Buffer.add_string b "\\n"
       else if ch = q then (Buffer.add_char b '\\'; add_cp b ch)
       else add_cp b ch)
    (decode s);
  Buffer.contents b

let rec pp_term (t : term) : string =
  match t with
  | Num s -> s
  | Chr c -> "'" ^ esc_with (string_of_cp c) 39 ^ "'"
  | Str s -> "\"" ^ esc_with s 34 ^ "\""
  | Var n -> n
  | App (f, args) -> "(" ^ String.concat " " (pp_term f :: List.map pp_term args) ^ ")"
  | Lam (ps, b) ->
    let p = List.map (fun (n, ty) -> match ty with None -> n | Some ty -> n ^ " \xe2\x88\xb6 " ^ pp_type ty) ps in
    "(" ^ String.concat " " p ^ " \xe2\x86\xa6 " ^ pp_term b ^ ")"
  | Asc (e, _) -> pp_term e
  | Quote (e, _) -> pp_term e

let pp_statement (s : stmt) : string =
  match s with
  | Def (n, ps, b) -> String.concat " " (n :: ps) ^ " \xe2\x89\x94 " ^ pp_term b
  | Decl (n, ty) -> n ^ " \xe2\x88\xb6 " ^ pp_type ty
  | Fact t -> pp_term t

(* ---------------------------------------------------------------- Python repr of the tuple form of a term (for error messages) *)
let tuple_of (xs : string list) : string =
  match xs with [] -> "()" | [ x ] -> "(" ^ x ^ ",)" | _ -> "(" ^ String.concat ", " xs ^ ")"

let rec repr_ty (t : ty) : string =
  match t with
  | V n -> Printf.sprintf "('V', %s)" (py_repr n)
  | F -> "('F', '\xe2\x8a\xa5')"
  | K (n, args) -> Printf.sprintf "('K', %s, %s)" (py_repr n) (tuple_of (List.map repr_ty args))

let rec repr_term (t : term) : string =
  let tup xs = "(" ^ String.concat ", " xs ^ ")" in
  match t with
  | Num s -> tup [ "'num'"; py_repr s ]
  | Chr c -> tup [ "'chr'"; string_of_int c ]
  | Str s -> tup [ "'str'"; py_repr s ]
  | Var n -> tup [ "'var'"; py_repr n ]
  | App (f, args) -> tup [ "'app'"; repr_term f; "[" ^ String.concat ", " (List.map repr_term args) ^ "]" ]
  | Lam (ps, b) ->
    tup
      [ "'lam'";
        "[" ^ String.concat ", " (List.map (fun (n, ty) -> tup [ py_repr n; (match ty with None -> "None" | Some ty -> repr_ty ty) ]) ps) ^ "]";
        repr_term b ]
  | Asc (e, ty) -> tup [ "'asc'"; repr_term e; repr_ty ty ]
  | Quote (e, _) -> tup [ "'quote'"; repr_term e ]
