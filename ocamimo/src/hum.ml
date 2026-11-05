(* hum.ml -- the HUMAN notation of i-1 and doc 2 (port of rustimo/src/hum.rs).
   doc 2 line   <hum symbol> := <rhs> | <rhs> | ...  ; <role>          (⍝ starts a comment)
     rhs   a spec symbol, or a bin symbol (a numeral such as 11, or .B.)
     role  class | value | literal | infixl P | infixr P | infix P | prefix P
     several rhs  = an overload set; the checker picks one by the classes of the arguments.
   human statements (one per logical line)
     name in Class := expr | name in Class (an UNKNOWN of a number class) | name(x, y) in A -> B -> C := expr | A subseteq B
   human terms: 1, 12, 3.25  "text"  'c'  f(a, b)  a + b  ...  (e in Class)   x in Class |-> body *)
open Base
open Syntax
open Layers

(* ---------------------------------------------------------------- doc 2 *)
type entry = { hum : string; rhs : string list; role : string; prec : int option }
type doc2 = { entries : entry list; by_hum : (string, entry list) Hashtbl.t }

let doc2_make (entries : entry list) : doc2 =
  let by_hum = Hashtbl.create 1024 in
  List.iter
    (fun e ->
       let l = try Hashtbl.find by_hum e.hum with Not_found -> [] in
       Hashtbl.replace by_hum e.hum (e :: l))
    entries;
  Hashtbl.filter_map_inplace (fun _ l -> Some (List.rev l)) by_hum;
  { entries; by_hum }

let rfind_sub (s : string) (p : string) : int option =
  let ls = String.length s and lp = String.length p in
  let r = ref None and i = ref (ls - lp) in
  while !r = None && !i >= 0 do
    if String.sub s !i lp = p then r := Some !i;
    decr i
  done;
  !r

(* Python's s.split(): the pieces between runs of white space *)
let split_ws (s : string) : string list =
  let cs = decode s in
  let out = ref [] and start = ref (-1) in
  Array.iteri
    (fun i c ->
       if is_ws c then (if !start >= 0 then (out := string_of_cps cs !start i :: !out; start := -1))
       else if !start < 0 then start := i)
    cs;
  if !start >= 0 then out := string_of_cps cs !start (Array.length cs) :: !out;
  List.rev !out

let doc2_parse (text : string) : doc2 =
  let es = ref [] in
  List.iter
    (fun ln0 ->
       let ln1 = strip ln0 in
       if ln1 = "" || starts_with ln1 "⍝" then ()
       else begin
         let ln = match find_sub ln1 " ⍝ " with Some k -> String.sub ln1 0 k | None -> ln1 in
         match find_sub ln " := " with
         | None -> parse_err (Printf.sprintf "doc2: bad line %s" (py_repr ln))
         | Some k ->
           let hd = String.sub ln 0 k and rest = String.sub ln (k + 4) (String.length ln - k - 4) in
           let rhs, role =
             match rfind_sub rest " ; " with
             | Some j -> (String.sub rest 0 j, split_ws (String.sub rest (j + 3) (String.length rest - j - 3)))
             | None -> ("", split_ws rest)
           in
           if role = [] then parse_err "Prelude.head: empty list";
           es :=
             { hum = strip hd; rhs = List.map strip (split_on rhs " | "); role = List.hd role;
               prec = (match role with _ :: p :: _ -> int_of_string_opt p | _ -> None) }
             :: !es
       end)
    (String.split_on_char '\n' text);
  doc2_make (List.rev !es)

(* the first entry for a human symbol that has one of the roles *)
let find (d : doc2) (hum : string) (roles : string list) : entry option =
  match Hashtbl.find_opt d.by_hum hum with
  | None -> None
  | Some l -> List.find_opt (fun e -> List.mem e.role roles) l

let all_bin_chars (s : string) : bool =
  let ok = ref true in
  String.iter (fun c -> if c <> '0' && c <> '1' && c <> '.' then ok := false) s;
  !ok

(* key -> [spec symbols]  (bin-literal right-hand sides are handled by the reader, not listed here) *)
let overload_table (d : doc2) : (string, string list) Hashtbl.t =
  let m = Hashtbl.create 256 in
  List.iter
    (fun e ->
       if List.mem e.role [ "class"; "literal"; "syntax" ] then ()
       else begin
         let key = if e.role = "prefix" then "hum:prefix " ^ e.hum else "hum:" ^ e.hum in
         let v = List.filter (fun x -> not (x <> "" && all_bin_chars x)) e.rhs in
         Hashtbl.replace m key v
       end)
    d.entries;
  m

(* a bin symbol on the right of doc 2 means the spec symbol that doc 1 gives that code to *)
let remap (d : doc2) (d1 : doc1) : doc2 =
  doc2_make
    (List.map
       (fun e ->
          { e with rhs = List.map (fun x -> if is_bin_sym x then (match Hashtbl.find_opt d1.b2s x with Some s -> s | None -> x) else x) e.rhs })
       d.entries)

(* ---------------------------------------------------------------- lexer *)
type htok = HNum of string | HStr of string | HChr of int | HId of string | HOp of string

let show_tok = function
  | HNum s -> Printf.sprintf "('NUM', %s)" (py_repr s)
  | HStr s -> Printf.sprintf "('STR', %s)" (py_repr s)
  | HChr c -> Printf.sprintf "('CHR', %d)" c
  | HId s -> Printf.sprintf "('ID', %s)" (py_repr s)
  | HOp s -> Printf.sprintf "('OP', %s)" (py_repr s)

let is_digit c = c >= 48 && c <= 57
let is_ascii_letter c = (c >= 65 && c <= 90) || (c >= 97 && c <= 122)

(* the body of a quoted literal: any character but the quote and the backslash, or a backslash and any character but a newline;
   returns (body with its backslashes, index after the closing quote) *)
let quoted (cs : int array) (start : int) (q : int) : (int array * int) option =
  let n = Array.length cs in
  let body = ref [] and i = ref start and res = ref None and fin = ref false in
  while (not !fin) && !i < n do
    let x = cs.(!i) in
    if x = q then (res := Some (Array.of_list (List.rev !body), !i + 1); fin := true)
    else if x = 92 then begin
      if !i + 1 < n && cs.(!i + 1) <> 10 then (body := cs.(!i + 1) :: 92 :: !body; i := !i + 2) else fin := true
    end
    else (body := x :: !body; incr i)
  done;
  !res

let unescape (s : int array) : int array =
  let n = Array.length s in
  let out = ref [] and i = ref 0 in
  while !i < n do
    if s.(!i) = 92 && !i + 1 < n then begin
      let y = s.(!i + 1) in
      out := (if y = 110 then 10 else if y = 116 then 9 else y) :: !out;
      i := !i + 2
    end else (out := s.(!i) :: !out; incr i)
  done;
  Array.of_list (List.rev !out)

let lex_hum (line0 : string) : htok list =
  let cs0 = decode line0 in
  let n = ref (Array.length cs0) in
  while !n > 0 && is_ws cs0.(!n - 1) do decr n done;
  let cs = Array.sub cs0 0 !n in
  let n = !n in
  let i = ref 0 and out = ref [] and fin = ref false in
  while not !fin do
    while !i < n && is_ws cs.(!i) do incr i done;
    if !i >= n then fin := true
    else begin
      let c = cs.(!i) in
      let handled = ref false in
      if is_digit c then begin
        let j = ref !i in
        while !j < n && is_digit cs.(!j) do incr j done;
        let ip = string_of_cps cs !i !j in
        if !j + 1 < n && cs.(!j) = 46 && is_digit cs.(!j + 1) then begin
          let k = ref (!j + 1) in
          while !k < n && is_digit cs.(!k) do incr k done;
          out := HNum (ip ^ "." ^ string_of_cps cs (!j + 1) !k) :: !out;
          i := !k
        end else (out := HNum ip :: !out; i := !j);
        handled := true
      end;
      if (not !handled) && c = 34 then begin
        match quoted cs (!i + 1) 34 with
        | Some (body, next) ->
          let u = unescape body in
          out := HStr (string_of_cps u 0 (Array.length u)) :: !out;
          i := next;
          handled := true
        | None -> ()
      end;
      if (not !handled) && c = 39 then begin
        match quoted cs (!i + 1) 39 with
        | Some (body, next) ->
          let u = unescape body in
          if Array.length u = 1 then (out := HChr u.(0) :: !out; i := next; handled := true)
        | None -> ()
      end;
      if (not !handled) && c = 92 then begin
        let j = ref (!i + 1) in
        while !j < n && is_ascii_letter cs.(!j) do incr j done;
        if !j > !i + 1 then begin
          out := HId ("\\" ^ string_of_cps cs (!i + 1) !j) :: !out;
          i := !j;
          handled := true
        end
      end;
      if (not !handled) && (is_ascii_letter c || c = 95) then begin
        let j = ref !i in
        while !j < n && (is_ascii_letter cs.(!j) || cs.(!j) = 95 || is_digit cs.(!j)) do incr j done;
        out := HId (string_of_cps cs !i !j) :: !out;
        i := !j;
        handled := true
      end;
      if not !handled then begin
        let rest = string_of_cps cs !i (min n (!i + 3)) in
        match List.find_opt (fun op -> starts_with rest op) [ ":="; "|->"; "->"; "=="; "!="; "++" ] with
        | Some op ->
          out := HOp op :: !out;
          i := !i + String.length op
        | None ->
          if String.contains "-+*/^(),[]" (Char.chr (if c < 128 then c else 0)) && c < 128 then (out := HOp (String.make 1 (Char.chr c)) :: !out; incr i)
          else begin
            let take = string_of_cps cs !i (min n (!i + 12)) in
            parse_err (Printf.sprintf "human notation: cannot read %s" (py_repr take))
          end
      end
    end
  done;
  List.rev !out

(* a logical line ends at a newline outside parentheses; `--` starts a comment *)
let hum_logical_lines (text : string) : string list =
  let out = ref [] and cur = Buffer.create 256 and depth = ref 0 in
  let count ln ch = let k = ref 0 in String.iter (fun c -> if c = ch then incr k) ln; !k in
  List.iter
    (fun ln0 ->
       let ln =
         if contains_sub ln0 "--" && not (String.contains ln0 '"') then (match find_sub ln0 "--" with Some k -> String.sub ln0 0 k | None -> ln0)
         else ln0
       in
       Buffer.add_char cur ' ';
       Buffer.add_string cur ln;
       depth := !depth + count ln '(' - count ln ')' + count ln '[' - count ln ']';
       if !depth <= 0 then begin
         let s = strip (Buffer.contents cur) in
         if s <> "" then out := s :: !out;
         Buffer.clear cur;
         depth := 0
       end)
    (String.split_on_char '\n' text);
  let s = strip (Buffer.contents cur) in
  if s <> "" then out := s :: !out;
  List.rev !out

(* ---------------------------------------------------------------- parser *)
type hum = { doc : doc2; infix : (string, int * string) Hashtbl.t; prefix : (string, int) Hashtbl.t }

let mk_hum (d : doc2) : hum =
  let infix = Hashtbl.create 64 and prefix = Hashtbl.create 16 in
  List.iter
    (fun e ->
       if List.mem e.role [ "infixl"; "infixr"; "infix" ] then Hashtbl.replace infix e.hum ((match e.prec with Some p -> p | None -> 0), e.role);
       if e.role = "prefix" then Hashtbl.replace prefix e.hum (match e.prec with Some p -> p | None -> 0))
    d.entries;
  { doc = d; infix; prefix }

let oob () = parse_err "list index out of range"

module SS = Set.Make (String)

(* classes *)
let rec class_atom (h : hum) (ts : htok list) : ty * htok list =
  match ts with
  | HOp "(" :: rest -> (
      let c, r = class_expr h rest in
      match r with HOp ")" :: r' -> (c, r') | _ -> parse_err "missing )")
  | HId n :: rest -> (
      match find h.doc n [ "class" ] with
      | None -> parse_err (Printf.sprintf "%s is not a class in doc 2" n)
      | Some e -> (
          let name = List.hd e.rhs in
          if is_class_var name then (V name, rest)
          else
            match rest with
            | HOp "(" :: r2 ->
              let args, r3 = class_args h r2 in
              (K (name, args), r3)
            | _ -> (K (name, []), rest)))
  | t :: _ -> parse_err ("class expected, found " ^ show_tok t)
  | [] -> oob ()

and class_args (h : hum) (ts : htok list) : ty list * htok list =
  let out = ref [] and r = ref ts and res = ref None in
  while !res = None do
    let a, r1 = class_expr h !r in
    out := a :: !out;
    match r1 with
    | HOp "," :: r2 -> r := r2
    | HOp ")" :: r2 -> res := Some (List.rev !out, r2)
    | [] -> oob ()
    | _ -> parse_err "missing ) in class"
  done;
  match !res with Some x -> x | None -> assert false

and class_expr (h : hum) (ts : htok list) : ty * htok list =
  let l, r = class_atom h ts in
  match r with
  | HOp "->" :: r2 ->
    let rt, r3 = class_expr h r2 in
    (K ("→", [ l; rt ]), r3)
  | _ -> (l, r)

(* terms *)
let number (text : string) : term =
  match String.index_opt text '.' with
  | None -> Num (big_numeral_text (Bigint.parse_dec text))
  | Some k ->
    let a = String.sub text 0 k and b = String.sub text (k + 1) (String.length text - k - 1) in
    let den = Bigint.pow_small 10 (String.length b) in
    app "hum:/" [ Num (big_numeral_text (Bigint.parse_dec (a ^ b))); Num (big_numeral_text den) ]

let op_key = function HOp o | HId o -> Some o | _ -> None

let rec atom (h : hum) (ts : htok list) (scope : SS.t) : term * htok list =
  match ts with
  | [] -> oob ()
  | HNum s :: r -> (number s, r)
  | HStr s :: r -> (Str s, r)
  | HChr c :: r -> (Chr c, r)
  | HOp "[" :: r0 -> (
      let items, r1 = match r0 with HOp "]" :: _ -> ([], r0) | _ -> list_items h r0 scope in
      match r1 with
      | HOp "]" :: r2 ->
        let e = ref (var "hum:nil") in
        List.iter (fun a -> e := app "hum:cons" [ a; !e ]) (List.rev items);
        (!e, r2)
      | [] -> oob ()
      | _ -> parse_err "missing ] in list")
  | HOp "(" :: r0 -> (
      let e, r1 = hum_expr h r0 0 scope in
      match r1 with
      | HId "in" :: r2 -> (
          let c, r3 = class_expr h r2 in
          match r3 with HOp ")" :: r4 -> (Asc (e, c), r4) | [] -> oob () | _ -> parse_err "missing )")
      | HOp ")" :: r2 -> (e, r2)
      | [] -> oob ()
      | _ -> parse_err "missing )")
  | HId name :: r -> (
      let starts_paren = match r with HOp "(" :: _ -> true | _ -> false in
      let lit = if (not (SS.mem name scope)) && not starts_paren then find h.doc name [ "literal" ] else None in
      match lit with
      | Some l -> (Num (List.hd l.rhs), r)
      | None -> (
          let hd = if SS.mem name scope || find h.doc name [ "value" ] = None then var name else var ("hum:" ^ name) in
          match r with
          | HOp "(" :: r1 -> (
              match r1 with
              | HOp ")" :: r2 -> (App (hd, []), r2)
              | _ ->
                let args, r2 = call_args h r1 scope in
                (App (hd, args), r2))
          | _ -> (hd, r)))
  | t :: _ -> parse_err ("unexpected " ^ show_tok t)

and list_items (h : hum) (ts : htok list) (scope : SS.t) : term list * htok list =
  let out = ref [] and r = ref ts and res = ref None in
  while !res = None do
    let a, r1 = hum_expr h !r 0 scope in
    out := a :: !out;
    match r1 with HOp "," :: r2 -> r := r2 | _ -> res := Some (List.rev !out, r1)
  done;
  match !res with Some x -> x | None -> assert false

and call_args (h : hum) (ts : htok list) (scope : SS.t) : term list * htok list =
  let out = ref [] and r = ref ts and res = ref None in
  while !res = None do
    let a, r1 = hum_expr h !r 0 scope in
    out := a :: !out;
    match r1 with
    | HOp "," :: r2 -> r := r2
    | HOp ")" :: r2 -> res := Some (List.rev !out, r2)
    | [] -> oob ()
    | _ -> parse_err "missing ) in call"
  done;
  match !res with Some x -> x | None -> assert false

and hum_expr (h : hum) (ts : htok list) (minprec : int) (scope : SS.t) : term * htok list =
  if ts = [] then oob ();
  (* lambda:  x in Class |-> body *)
  let lam =
    match ts with
    | HId name :: HId "in" :: rest -> (
        let c, r1 = class_expr h rest in
        match r1 with
        | HOp "|->" :: r2 ->
          let sc = SS.add name scope in
          let body, r3 = hum_expr h r2 0 sc in
          Some (Lam ([ (name, Some c) ], body), r3)
        | _ -> None)
    | _ -> None
  in
  match lam with
  | Some x -> x
  | None ->
    let t0 = List.hd ts in
    let left, r =
      match op_key t0 with
      | Some key when Hashtbl.mem h.prefix key && not ((match t0 with HId _ -> true | _ -> false) && SS.mem key scope) ->
        let arg, r1 = hum_expr h (List.tl ts) (Hashtbl.find h.prefix key) scope in
        (app ("hum:prefix " ^ key) [ arg ], r1)
      | _ -> atom h ts scope
    in
    let left = ref left and r = ref r and res = ref None in
    while !res = None do
      let step =
        match !r with
        | t :: _ -> (
            match op_key t with
            | Some op -> (match Hashtbl.find_opt h.infix op with Some (prec, kind) when prec >= minprec -> Some (op, prec, kind) | _ -> None)
            | None -> None)
        | [] -> None
      in
      match step with
      | Some (op, prec, kind) ->
        let right, r1 = hum_expr h (List.tl !r) (if kind <> "infixr" then prec + 1 else prec) scope in
        left := app ("hum:" ^ op) [ !left; right ];
        r := r1
      | None -> res := Some (!left, !r)
    done;
    (match !res with Some x -> x | None -> assert false)

(* statements *)
let spec_name (h : hum) (name : string) : string =
  match find h.doc name [ "value" ] with
  | Some e when List.length e.rhs = 1 && not (all_bin_chars (List.hd e.rhs)) -> List.hd e.rhs
  | _ -> name

let rec type_to_term (t : ty) : term =
  match t with
  | V n -> var n
  | K (n, []) -> var n
  | K (n, a) -> App (var n, List.map type_to_term a)
  | F -> var "⊥"

let tok_text = function HNum s | HStr s | HId s | HOp s -> s | HChr c -> string_of_cp c

let param_list (ts : htok list) : string list * htok list =
  let out = ref [] and r = ref ts and res = ref None in
  while !res = None do
    match !r with
    | HOp ")" :: r' -> res := Some (List.rev !out, r')
    | t :: r' ->
      out := tok_text t :: !out;
      r := (match r' with HOp "," :: r'' -> r'' | _ -> r')
    | [] -> oob ()
  done;
  match !res with Some x -> x | None -> assert false

let hum_statement (h : hum) (line : string) : stmt list =
  let ts = lex_hum line in
  match position (function HId "subseteq" -> true | _ -> false) ts with
  | Some k ->
    let a, ra = class_expr h (take k ts) in
    let b, rb = class_expr h (drop (k + 1) ts) in
    if ra <> [] || rb <> [] then parse_err "assertion failed";
    [ Fact (app "⊆" [ type_to_term a; type_to_term b ]) ]
  | None -> (
      match ts with
      | HId name :: r0 -> (
          let params, r1 = match r0 with HOp "(" :: r -> param_list r | _ -> ([], r0) in
          match r1 with
          | HId "in" :: r2 -> (
              let cls, r3 = class_expr h r2 in
              match r3 with
              | [] ->
                if params <> [] then parse_err (Printf.sprintf "%s: a declaration without := takes no parameters (an unknown is a number)" name);
                [ Decl (spec_name h name, cls) ]
              | HOp ":=" :: r4 -> (
                  let sc = List.fold_left (fun s p -> SS.add p s) SS.empty params in
                  let body, r5 = hum_expr h r4 0 sc in
                  let sp = spec_name h name in
                  match r5 with
                  | t :: _ -> parse_err ("unexpected " ^ show_tok t)
                  | [] -> [ Decl (sp, cls); Def (sp, params, body) ])
              | _ -> parse_err "missing :=")
          | _ -> parse_err (Printf.sprintf "declare the class first:  %s in <Class> := …" name))
      | _ -> parse_err (Printf.sprintf "statement must start with a name: %s" (py_repr line)))

let hum_statements (h : hum) (text : string) : stmt list =
  List.concat_map (fun l -> hum_statement h l) (hum_logical_lines text)
