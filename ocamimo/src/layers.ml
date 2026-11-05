(* layers.ml -- the three notation systems of i-1 and the system documents that connect them (port of rustimo/src/layers.rs).
     bin   only  1 0 .  space ( ) newline;  numeral 1011  1.01;  symbol .B. (B a bit string, the code of the symbol, see doc 1);
           markers  . = ↦   .. = ≔   ... = ∶
     spec  unicode glyphs; the notation of the prelude (lib/*.imo); `⍝` starts a comment
     hum   ASCII/TeX-like notation (hum.ml)
     doc 1   [spec sbl] := [bin sbl]            one line per symbol *)
open Base
open Syntax

(* ---------------------------------------------------------------- doc 1 *)
type doc1 = {
  s2b : (string, string) Hashtbl.t;
  b2s : (string, string) Hashtbl.t;
  mutable local : (string * string) list; (* program-local symbols, newest first *)
}

(* .B. with B a non-empty bit string *)
let is_bin_sym (s : string) : bool =
  let n = String.length s in
  n >= 3 && s.[0] = '.' && s.[n - 1] = '.'
  && (let ok = ref true in
      for i = 1 to n - 2 do if s.[i] <> '0' && s.[i] <> '1' then ok := false done;
      !ok)

let doc1_empty () : doc1 = { s2b = Hashtbl.create 1024; b2s = Hashtbl.create 1024; local = [] }

let copy_doc1 (d : doc1) : doc1 = { s2b = Hashtbl.copy d.s2b; b2s = Hashtbl.copy d.b2s; local = d.local }

let doc1_parse (text : string) : doc1 =
  let d = doc1_empty () in
  List.iter
    (fun ln0 ->
       let ln = strip ln0 in
       if ln = "" || starts_with ln "⍝" then ()
       else begin
         let parts = split_on ln " := " in
         if List.length parts <> 2 then parse_err (Printf.sprintf "doc1: bad line %s" (py_repr ln));
         let a = strip (List.nth parts 0) and b = strip (List.nth parts 1) in
         if not (is_bin_sym b) then parse_err (Printf.sprintf "doc1: bad binary symbol %s" (py_repr b));
         if Hashtbl.mem d.s2b a || Hashtbl.mem d.b2s b then parse_err (Printf.sprintf "doc1: duplicate %s / %s" a b);
         Hashtbl.replace d.s2b a b;
         Hashtbl.replace d.b2s b a
       end)
    (String.split_on_char '\n' text);
  d

(* the binary string without its high zeros; the larger of two; the successor *)
let bin_strip (s : string) : string =
  let n = String.length s in
  let i = ref 0 in
  while !i < n && s.[!i] = '0' do incr i done;
  String.sub s !i (n - !i)

let bin_less (a : string) (b : string) : bool =
  let a = bin_strip a and b = bin_strip b in
  if String.length a <> String.length b then String.length a < String.length b else a < b

let bin_succ (s : string) : string =
  let s = bin_strip s in
  let b = Bytes.of_string s in
  let i = ref (Bytes.length b - 1) in
  while !i >= 0 && Bytes.get b !i = '1' do Bytes.set b !i '0'; decr i done;
  if !i >= 0 then (Bytes.set b !i '1'; Bytes.to_string b) else "1" ^ Bytes.to_string b

(* the next free code:  .<max + 1 in binary>. *)
let next_code (d : doc1) : string =
  let m = ref "" in
  Hashtbl.iter
    (fun b _ ->
       let bits = String.sub b 1 (String.length b - 2) in
       if bin_less !m bits then m := bits)
    d.b2s;
  "." ^ bin_succ !m ^ "."

(* the code of a symbol; a new local code is given when allowed *)
let doc1_code (d : doc1) (name : string) (allow_new : bool) : string =
  match Hashtbl.find_opt d.s2b name with
  | Some b -> b
  | None ->
    if not allow_new then parse_err (Printf.sprintf "%s has no binary symbol in doc 1" (py_repr name));
    let b = next_code d in
    Hashtbl.replace d.s2b name b;
    Hashtbl.replace d.b2s b name;
    d.local <- (name, b) :: d.local;
    b

(* add a symbol of a program-local table (not counted as a symbol the program created) *)
let doc1_add_local (d : doc1) (a : string) (b : string) : unit =
  Hashtbl.replace d.s2b a b;
  Hashtbl.replace d.b2s b a

(* the local table as text, in the format of doc 1 *)
let doc1_render (d : doc1) (header : string list) : string =
  let b = Buffer.create 256 in
  List.iter (fun h -> Buffer.add_string b (Printf.sprintf "⍝ %s\n" h)) header;
  List.iter (fun (a, c) -> Buffer.add_string b (Printf.sprintf "%s := %s\n" a c)) (List.rev d.local);
  Buffer.contents b

(* ---------------------------------------------------------------- bin lexer / translators *)
type btok = BNl | BOpen | BClose | BNum of string | BMark of string | BSym of string

let reserved_spec = function "." -> Some "↦" | ".." -> Some "≔" | "..." -> Some "∶" | _ -> None
let reserved_bin = function "↦" -> Some "." | "≔" -> Some ".." | "∶" -> Some "..." | _ -> None

let lex_bin (text : string) : btok list =
  let cs = decode text in
  let n = Array.length cs in
  let i = ref 0 and d = ref 0 and out = ref [] in
  while !i < n do
    let c = cs.(!i) in
    if c = 32 || c = 9 || c = 13 then incr i
    else if c = 10 then (if !d = 0 then out := BNl :: !out; incr i)
    else if c = 40 then (out := BOpen :: !out; incr d; incr i)
    else if c = 41 then (out := BClose :: !out; decr d; incr i)
    else if c = 48 || c = 49 || c = 46 then begin
      let j = ref !i in
      while !j < n && (cs.(!j) = 48 || cs.(!j) = 49 || cs.(!j) = 46) do incr j done;
      let s = string_of_cps cs !i !j in
      let pts = ref 0 in
      String.iter (fun ch -> if ch = '.' then incr pts) s;
      if reserved_spec s <> None then out := BMark s :: !out
      else if !pts <= 1 then out := BNum s :: !out
      else if is_bin_sym s then out := BSym s :: !out
      else parse_err (Printf.sprintf "bad binary token %s" (py_repr s));
      i := !j
    end
    else parse_err (Printf.sprintf "character %s is not part of the binary notation" (py_repr (string_of_cp c)))
  done;
  List.rev !out

(* tokens to text (spaces only between atoms; newlines kept).  None stands for a newline. *)
let render_toks (toks : string option list) : string =
  let b = Buffer.create 1024 in
  let first = ref true in
  List.iter
    (function
      | None -> Buffer.add_char b '\n'; first := true
      | Some t ->
        if not (t = ")" || !first) then Buffer.add_char b ' ';
        Buffer.add_string b t;
        first := (t = "("))
    toks;
  Buffer.contents b

(* bin text -> spec text, through doc 1 (and the program's local table) *)
let bin_to_spec_text (text : string) (d : doc1) : string =
  let toks =
    List.map
      (function
        | BNl -> None
        | BOpen -> Some "("
        | BClose -> Some ")"
        | BNum s -> Some s
        | BMark s -> (match reserved_spec s with Some r -> Some r | None -> None)
        | BSym s -> (
            match Hashtbl.find_opt d.b2s s with
            | Some n -> Some n
            | None -> parse_err (Printf.sprintf "binary symbol %s is not defined in doc 1 (or the local table)" s)))
      (lex_bin text)
  in
  render_toks toks

(* the tokens of spec text re-spelled in bin notation (the shared part of the two translators) *)
let bin_of_spec_toks (toks : tok list) (d : doc1) (allow_new : bool) (strings_in_order : bool) : string option list =
  let out = ref [] in
  let push s = out := Some s :: !out in
  List.iter
    (function
      | Open -> push "("
      | Close -> push ")"
      | TNum s -> push s
      | Name n -> (match reserved_bin n with Some r -> push r | None -> push (doc1_code d n allow_new))
      | TChr c ->
        let bc = doc1_code d "𝕔" allow_new in
        push "("; push bc; push (int_numeral_text c); push ")"
      | TStr s ->
        let cs = decode s in
        if strings_in_order then begin
          let bcons = doc1_code d "∷" allow_new in
          let bchr = doc1_code d "𝕔" allow_new in
          let bnil = doc1_code d "⊘" allow_new in
          Array.iter (fun ch -> push "("; push bcons; push "("; push bchr; push (int_numeral_text ch); push ")") cs;
          push bnil;
          Array.iter (fun _ -> push ")") cs
        end else begin
          Array.iter
            (fun ch ->
               let bcons = doc1_code d "∷" allow_new in
               let bchr = doc1_code d "𝕔" allow_new in
               push "("; push bcons; push "("; push bchr; push (int_numeral_text ch); push ")")
            cs;
          push (doc1_code d "⊘" allow_new);
          Array.iter (fun _ -> push ")") cs
        end
      | Nl -> ())
    toks;
  List.rev !out

(* the statements re-spelled in bin notation; new program-local symbols get codes in order of first use *)
let spec_statements_to_bin_text (sts : stmt list) (d : doc1) (allow_new : bool) : string =
  let toks = ref [] in
  List.iter
    (fun st ->
       let t = bin_of_spec_toks (lex_spec (pp_statement st)) d allow_new true in
       toks := (None :: List.rev t) @ !toks)
    sts;
  render_toks (List.rev !toks)

(* one spec term (as text) -> the same term in bin notation, through doc 1 (literals are expanded as the reader expands them) *)
let spec_term_to_bin (text : string) (d : doc1) : string =
  render_toks (bin_of_spec_toks (lex_spec text) d false false)

(* ---------------------------------------------------------------- files: default notation by extension, `@bin` `@spec` `@hum` section headers *)
let split_sections (text : string) (def : string) : (string * string) list =
  let mode = ref def and cur = ref [] and acc = ref [] in
  List.iter
    (fun ln ->
       let s = strip ln in
       if s = "@bin" || s = "@spec" || s = "@hum" then begin
         if !cur <> [] then acc := (!mode, String.concat "\n" (List.rev !cur)) :: !acc;
         cur := [];
         mode := String.sub s 1 (String.length s - 1)
       end
       else cur := ln :: !cur)
    (String.split_on_char '\n' text);
  if !cur <> [] then acc := (!mode, String.concat "\n" (List.rev !cur)) :: !acc;
  List.rev !acc

let default_notation (path : string) : string =
  if ends_with path ".bin.imo" then "bin" else if ends_with path ".hum.imo" then "hum" else "spec"
