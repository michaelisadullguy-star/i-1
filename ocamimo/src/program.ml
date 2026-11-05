(* program.ml -- loader / driver for i-1 programs (port of rustimo/src/program.rs).
   A file is read in the notation chosen by its extension (x.bin.imo, x.hum.imo, x.imo = spec) or by section headers (@bin @spec @hum on a
   line of their own).  Every section is translated to spec statements, the whole program is checked by the class checker, and the
   definitions are run by the evaluator (lazy, call-by-need).
   A symbol that the program declares and never defines is an UNKNOWN: its class must be a number class, a statement about it is simplified
   by lib/solve.imo, and evaluating it is a run-time error (Err (Unknown _)). *)
open Base
open Core
open Hum
open Layers
open Quote
open Syntax
open Types

type program = {
  mutable doc1 : doc1;
  doc2 : doc2;
  hum : hum;
  mutable statements : (string * stmt * bool) array; (* file, statement, trusted *)
  checker : checker;
  mutable resolved : stmt option array; (* aligned with `statements` (None: the statement had an error) *)
  mutable errors : (string * string * string) list; (* file, what, message *)
  notation_of : (string, string) Hashtbl.t; (* defined symbol -> the notation of the section that defines it *)
  mutable out_mode : string option; (* set by an  @out bin|spec|hum  line *)
  mutable pre_count : int; (* the number of statements that came from the embedded prelude (they are first, and trusted) *)
  mutable user_defs : (string * core) list; (* the definitions of the program itself, erased to de Bruijn terms (made by `check`) *)
  defined : (string, unit) Hashtbl.t; (* every name that is defined (prelude and program), made by `check` *)
  mutable machine : machine option;
}

type source_file = { path : string; text : string }

let new_program () : program =
  let d1 = doc1_parse Data_gen.doc1 in
  let d2 = remap (doc2_parse Data_gen.doc2) d1 in
  let checker = new_checker () in
  Hashtbl.iter (fun k v -> Hashtbl.replace checker.overloads k v) (overload_table d2);
  {
    doc1 = d1; doc2 = d2; hum = mk_hum d2; statements = [||]; checker; resolved = [||]; errors = []; notation_of = Hashtbl.create 64;
    out_mode = None; pre_count = 0; user_defs = []; defined = Hashtbl.create 16384; machine = None;
  }

(* add the text of a file (or of a string) in the given default notation *)
let add_text (p : program) (text : string) (name : string) (trusted : bool) (notation : string) : unit =
  let out_mode = ref p.out_mode in
  let lines = ref [] in
  List.iter
    (fun ln ->
       let words = split_ws ln in
       match words with
       | [ "@out"; w ] ->
         if w = "bin" || w = "spec" || w = "hum" then (out_mode := Some w; lines := "" :: !lines)
         else parse_err (Printf.sprintf "%s: @out takes bin, spec or hum, not %s" name w)
       | _ -> lines := ln :: !lines)
    (String.split_on_char '\n' text);
  let text2 = String.concat "\n" (List.rev !lines) in
  p.out_mode <- !out_mode;
  List.iter
    (fun (mode, chunk) ->
       let sts =
         match mode with
         | "spec" -> parse_statements chunk
         | "bin" -> parse_statements (bin_to_spec_text chunk p.doc1)
         | _ -> hum_statements p.hum chunk
       in
       if not trusted then List.iter (function Def (n, _, _) -> Hashtbl.replace p.notation_of n mode | _ -> ()) sts;
       p.statements <- Array.append p.statements (Array.of_list (List.map (fun st -> (name, st, trusted)) sts)))
    (split_sections text2 notation)

(* add a file; a bin program brings its local symbol table (x.sbl next to x.bin.imo) *)
let add_file (p : program) (f : source_file) (trusted : bool) : unit =
  let path = f.path in
  let before = match rfind_sub path ".imo" with Some k -> String.sub path 0 k | None -> path in
  let replace_all s a b = String.concat b (split_on s a) in
  let local = replace_all (replace_all (replace_all before ".bin" "") ".hum" "") ".spec" "" ^ ".sbl" in
  let uses_bin = default_notation path = "bin" || contains_sub ("\n" ^ f.text) "\n@bin" in
  if uses_bin && Sys.file_exists local && not (Sys.is_directory local) then begin
    let tbl = try read_utf8 local with Bad_utf8 e -> raise (Err (Parse (Printf.sprintf "%s: %s" local e))) in
    List.iter
      (fun line ->
         if contains_sub line " := " && not (starts_with line "⍝") then begin
           let parts = split_on line " := " in
           if List.length parts <> 2 then parse_err (Printf.sprintf "bad line in %s" (basename local));
           let a = strip (List.nth parts 0) and b = strip (List.nth parts 1) in
           if Hashtbl.mem p.doc1.s2b a then ()
           else begin
             (match Hashtbl.find_opt p.doc1.b2s b with
              | Some other ->
                parse_err
                  (Printf.sprintf "%s: local code %s for %s is already doc 1's code for %s (doc 1 grew: regenerate the local table with  i1.py translate … --to bin)"
                     (basename local) b a other)
              | None -> ());
             doc1_add_local p.doc1 a b
           end
         end)
      (String.split_on_char '\n' tbl)
  end;
  add_text p f.text path trusted (default_notation path)

(* ------------------------------------------------------------ checking *)
let is_class_or_stmt (ty : ty) : bool =
  let rec go = function K (n, [ _; b ]) when n = "→" -> go b | t -> t in
  let r = go ty in
  r = kk "𝒦" || r = kk "𝒮"

let rec refs (t : term) (bound : SS.t) (overloads : (string, string list) Hashtbl.t) : SS.t =
  match t with
  | Var n ->
    if SS.mem n bound then SS.empty
    else (match Hashtbl.find_opt overloads n with Some v -> SS.of_list v | None -> SS.singleton n)
  | App (f, args) -> List.fold_left (fun s a -> SS.union s (refs a bound overloads)) (refs f bound overloads) args
  | Lam (ps, b) -> refs b (List.fold_left (fun bd (n, _) -> SS.add n bd) bound ps) overloads
  | Asc (e, _) -> refs e bound overloads
  | _ -> SS.empty

(* the unknowns (declared by the program, defined nowhere), in declaration order, and a first estimate of which program definitions need
   their values *)
let unknowns_of (c : checker) (stmts : (string * stmt * bool) array) : unit =
  let defined = Hashtbl.create 1024 in
  Array.iter (fun (_, s, _) -> match s with Def (n, _, _) -> Hashtbl.replace defined n () | _ -> ()) stmts;
  let order = ref [] and seen = Hashtbl.create 16 in
  Array.iter
    (fun (_, s, trusted) ->
       match s with
       | Decl (n, ty) when not trusted ->
         if Hashtbl.mem defined n || is_class_or_stmt ty then ()
         else if not (Hashtbl.mem seen n) then (Hashtbl.replace seen n (); order := n :: !order)
       | _ -> ())
    stmts;
  let order = List.rev !order in
  let user = ref [] in
  Array.iter (fun (_, s, t) -> match s with Def (n, ps, b) when not t -> user := (n, ps, b) :: !user | _ -> ()) stmts;
  let user = List.rev !user in
  let uses = Hashtbl.create 64 in
  List.iter (fun (n, ps, b) -> Hashtbl.replace uses n (refs b (SS.of_list ps) c.overloads)) user;
  let tainted = ref (SS.of_list order) in
  let go = ref true in
  while !go do
    let nw = Hashtbl.fold (fun n u acc -> if (not (SS.mem n !tainted)) && SS.exists (fun x -> SS.mem x !tainted) u then n :: acc else acc) uses [] in
    if nw = [] then go := false else tainted := List.fold_left (fun s n -> SS.add n s) !tainted nw
  done;
  let order_set = SS.of_list order in
  c.unknowns <- List.map (fun n -> (n, None)) order;
  Hashtbl.reset c.user_defined;
  List.iter (fun (n, _, _) -> Hashtbl.replace c.user_defined n ()) user;
  Hashtbl.reset c.raw_taint;
  SS.iter (fun n -> if not (SS.mem n order_set) then Hashtbl.replace c.raw_taint n ()) !tainted;
  Hashtbl.reset c.taint

(* program-local codes (doc 1 format) for the program's own symbols, assigned when the program is checked and in a fixed order *)
let codes_of (p : program) : unit =
  let order = ref (List.rev_map fst p.checker.unknowns) in
  Array.iter
    (fun (_, s, trusted) ->
       match s with Decl (n, _) when (not trusted) && n <> env_name && Hashtbl.mem p.checker.sigs n -> order := n :: !order | _ -> ())
    p.statements;
  List.iter (fun n -> ignore (doc1_code p.doc1 n true)) (List.rev !order)

(* replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝  and add the table of definitions *)
let quote_program (p : program) : unit =
  let sts = Array.to_list (Array.mapi (fun i (_, _, t) -> (t, p.resolved.(i))) p.statements) in
  let qr, d1 = mk_quoter p.checker sts p.doc1 in
  let st = { doc = d1; needed = [] } in
  let replaced = ref [] in
  Array.iteri
    (fun i r ->
       match r with
       | Some (Def (n, ps, b)) when has_quote b ->
         let b2 = quote_replace qr st b in
         replaced := (i, Def (n, ps, b2)) :: !replaced
       | _ -> ())
    p.resolved;
  let tab = quote_table qr st in
  List.iter (fun (i, s) -> p.resolved.(i) <- Some s) !replaced;
  p.doc1 <- st.doc;
  let env_ty = K ("𝔏", [ K ("𝔓", [ kk "𝔇"; kk "𝔔" ]) ]) in
  (try declare p.checker env_name env_ty with Class_error e -> raise (Err (Eval (Printf.sprintf "quote: ε⌜⌝ declaration: %s" e))));
  let at = ref 0 in
  while !at < Array.length p.statements && (let _, _, t = p.statements.(!at) in t) do incr at done;
  let at = !at in
  let decl_st = Decl (env_name, env_ty) and def_st = Def (env_name, [], tab) in
  let ins arr x = Array.concat [ Array.sub arr 0 at; [| x |]; Array.sub arr at (Array.length arr - at) ] in
  p.statements <- ins (ins p.statements ("<quote>", def_st, false)) ("<quote>", decl_st, false);
  p.resolved <- ins (ins p.resolved (Some def_st)) (Some decl_st)

(* check the program: class errors are collected in `errors`; the statements that mention a relation on ℝ[i] or an unknown are then written
   as codes (quote.ml) *)
let check (p : program) : unit =
  p.statements <- Array.of_list (List.filter (fun (f, _, _) -> f <> "<quote>") (Array.to_list p.statements));
  unknowns_of p.checker p.statements;
  let n = Array.length p.statements in
  let resolved = Array.make n None in
  let errors = ref [] in
  for i = 0 to n - 1 do
    let file, st, trusted = p.statements.(i) in
    match (try Ok (check_statement p.checker st trusted) with Class_error e -> Error e) with
    | Ok (Some nw) -> resolved.(i) <- Some nw
    | Ok None -> resolved.(i) <- Some st
    | Error e ->
      let what = match st with Def (n, _, _) -> n | Decl (n, _) -> n | _ -> pp_statement st in
      errors := (file, what, e) :: !errors;
      resolved.(i) <- None
  done;
  let defs_for_taint = ref [] in
  Array.iteri
    (fun i (_, _, t) -> match resolved.(i) with Some (Def (n, ps, b)) when not t -> defs_for_taint := (n, ps, b) :: !defs_for_taint | _ -> ())
    p.statements;
  settle_taint p.checker (List.rev !defs_for_taint);
  p.resolved <- resolved;
  p.errors <- List.rev !errors;
  if p.errors = [] then begin
    codes_of p;
    if Array.exists (function Some (Def (_, _, b)) -> has_quote b | _ -> false) p.resolved then quote_program p;
    (* the definitions of the program, in de Bruijn form (those of the embedded prelude are erased when they are first needed) *)
    Hashtbl.reset p.defined;
    let ud = ref [] in
    Array.iteri
      (fun i r ->
         match r with
         | Some (Def (n, ps, b)) ->
           Hashtbl.replace p.defined n ();
           if i >= p.pre_count then ud := erase_def n ps b :: !ud
         | _ -> ())
      p.resolved;
    p.user_defs <- List.rev !ud
  end

(* ------------------------------------------------------------ building *)
let user_statements (p : program) : stmt list =
  let out = ref [] in
  Array.iteri (fun i (_, _, t) -> if not t then match p.resolved.(i) with Some s -> out := s :: !out | None -> ()) p.statements;
  List.rev !out

let spec_text (p : program) : string = String.concat "" (List.map (fun s -> pp_statement s ^ "\n") (user_statements p))
let bin_text (p : program) : string = spec_statements_to_bin_text (user_statements p) p.doc1 true
let local_table (p : program) : string = doc1_render p.doc1 [ "program-local symbols (same format as doc 1)" ]

(* the human name of a spec symbol (reverse doc 2; a symbol of the program is its own name) *)
let hum_name (p : program) (spec : string) : string =
  match
    List.find_opt (fun e -> List.mem e.role [ "value"; "infixl"; "infixr"; "infix"; "prefix" ] && List.mem spec e.rhs) p.doc2.entries
  with
  | Some e -> e.hum
  | None -> spec

(* build the evaluator: the definitions of the embedded prelude are compiled when they are first needed *)
let build_machine (p : program) : unit =
  let defs = ref [] in
  for i = 0 to p.pre_count - 1 do
    match p.resolved.(i) with Some (Def (n, ps, b)) -> defs := (n, STerm (ps, b)) :: !defs | _ -> ()
  done;
  List.iter (fun (n, c) -> defs := (n, SCore c) :: !defs) p.user_defs;
  let extra =
    List.map
      (fun (n, _) ->
         let h = hum_name p n in
         let msg =
           Printf.sprintf
             "%s is an unknown (it is declared and never defined, so it has no value); use it in a statement — a relation such as %s == 1 — which is simplified, not evaluated"
             h h
         in
         (n, mk (Fail (Unknown msg))))
      p.checker.unknowns
  in
  p.machine <- Some (Core.build (List.rev !defs) extra)

(* the globals that some definition of the program uses and nothing defines (checked programs only) *)
let missing (p : program) : string list =
  if p.errors <> [] then []
  else begin
    let defined n = Hashtbl.mem p.defined n || List.exists (fun (u, _) -> u = n) p.checker.unknowns in
    let out = ref SS.empty in
    List.iter
      (fun (_, c) ->
         (* iterative over the spine of applications to keep the native stack shallow for long numerals *)
         let stack = ref [ c ] in
         while !stack <> [] do
           let c = List.hd !stack in
           stack := List.tl !stack;
           match c with
           | CG g -> if not (defined g) then out := SS.add g !out
           | CL b -> stack := b :: !stack
           | CA (f, x) -> stack := f :: x :: !stack
           | CV _ -> ()
         done)
      p.user_defs;
    SS.elements !out
  end

let machine (p : program) : machine = match p.machine with Some m -> m | None -> failwith "the program is not built"
let val_ (p : program) (n : string) : v = Core.global (machine p) n

(* load the prelude and the files and check them *)
let load_program (files : source_file list) (trusted_paths : string list) (with_prelude : bool) : program =
  let p = new_program () in
  if with_prelude then begin
    List.iter (fun (path, text) -> add_file p { path; text } true) Data_gen.lib_files;
    p.pre_count <- Array.length p.statements
  end;
  List.iter (fun f -> add_file p f (List.mem f.path trusted_paths)) files;
  check p;
  p
