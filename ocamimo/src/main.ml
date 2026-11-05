(* main.ml -- command line of OCamimo, the OCaml interpreter of i-1 (port of rustimo/src/main.rs).
     ocamimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  ocamimo FILE...)
     ocamimo check   FILE...                                load the prelude and FILE(s), run the class checker
     ocamimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table
     ocamimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class (value, stream element N, tree, string, Bool)
     ocamimo text    FILE... NAME                           evaluate NAME as a String and print it
   The commands, options and output are those of Pymo, Haskimo and Rustimo: the cores are parallel. *)
open Base
open Core
open Layers
open Hum
open Output
open Program
open Syntax
open Types

let usage =
  "ocamimo -- OCamimo, the OCaml interpreter of i-1 (same commands and output as Pymo, Haskimo and Rustimo)\n\n\
  \  ocamimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  ocamimo FILE...)\n\
  \  ocamimo check   FILE...                                load the prelude and FILE(s), run the class checker\n\
  \  ocamimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table\n\
  \  ocamimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class (value, stream element N, tree, string, Bool)\n\
  \  ocamimo text    FILE... NAME                           evaluate NAME as a String and print it\n\n\
   `run` prints main ∶ 𝕊 as text, a list or stream of strings line by line, and any other value as a normal-form term in the output\n\
   notation: --out, else an `@out bin|spec|hum` line in the program, else the notation main is written in.  --n N picks the stream\n\
   element shown for a stream (default 10), or the number of lines of a stream of strings.\n\n\
   FILE notation follows the extension:  x.imo / x.spec.imo = spec,  x.hum.imo = human,  x.bin.imo = binary (prelude.bin.imo is trusted).\n"

let put (s : string) : unit = print_string s
let line (s : string) : unit = print_string s; print_char '\n'

let io_reason (f : string) (e : string) : string =
  if not (Sys.file_exists f) then "does not exist (No such file or directory)"
  else (match String.rindex_opt e ':' with Some k -> String.trim (String.sub e (k + 1) (String.length e - k - 1)) | None -> e)

let load_files (files : string list) (build : bool) : program =
  let srcs =
    List.map
      (fun f ->
         let text =
           try read_utf8 f with
           | Bad_utf8 e -> raise (Err (Parse (Printf.sprintf "%s: hGetContents: invalid argument (%s)" f e)))
           | Sys_error e -> raise (Err (Parse (Printf.sprintf "%s: openFile: %s" f (io_reason f e))))
         in
         { path = f; text })
      files
  in
  let prelude = List.filter (fun f -> ends_with f "prelude.bin.imo") files in
  let p = load_program srcs prelude (prelude = []) in
  let missing = Program.missing p in
  if missing <> [] then parse_err ("these symbols are used and not defined: " ^ String.concat " " missing);
  if build && p.errors = [] then build_machine p;
  p

let report_errors (p : program) : unit =
  List.iter
    (fun (f, w, m) ->
       let text = if starts_with m w then m else w ^ ": " ^ m in
       line (Printf.sprintf "error in %s: %s" (basename f) text))
    p.errors

(* ---------------------------------------------------------------- values of ℚ[i], as Pymo shows them *)
type q = { re : Bigint.rat; im : Bigint.rat }

let qval (m : machine) (v : v) : q =
  let p, d = to_pair m v in
  let a0, a1 = gi_of m p in
  let b0, b1 = gi_of m d in
  let n = Bigint.add (Bigint.mul b0 b0) (Bigint.mul b1 b1) in
  if Bigint.is_zero n then raise (Err (Eval "Ratio has zero denominator"));
  {
    re = Bigint.rat_new (Bigint.add (Bigint.mul a0 b0) (Bigint.mul a1 b1)) n;
    im = Bigint.rat_new (Bigint.sub (Bigint.mul a1 b0) (Bigint.mul a0 b1)) n;
  }

let show_frac (r : Bigint.rat) : string =
  if Bigint.rat_is_int r then Bigint.to_dec r.num else Bigint.to_dec r.num ^ "/" ^ Bigint.to_dec r.den

let qfmt (m : machine) (v : v) : string =
  let q = qval m v in
  let im_zero = Bigint.rat_is_zero q.im in
  let s = if im_zero then show_frac q.re else Printf.sprintf "%s + %s i" (show_frac q.re) (show_frac q.im) in
  let tail = if im_zero then "" else Printf.sprintf " + %s i" (fmt_g 12 (Bigint.rat_to_float q.im)) in
  Printf.sprintf "%s   (≈ %s%s)" s (fmt_g 12 (Bigint.rat_to_float q.re)) tail

let sfmt (m : machine) (v : v) : string =
  let out = Buffer.create 64 in
  let cur = ref v and fin = ref false in
  while not !fin do
    match cell_or_nil m !cur with
    | VCons (h, t) ->
      let q = qval m h in
      let k = match Bigint.to_int_opt (Bigint.rat_truncate q.re) with Some k -> k | None -> 0xfffd in
      add_cp out (if k < 0 || k > 0x10FFFF then 0xFFFD else k);
      cur := t
    | _ -> fin := true
  done;
  Buffer.contents out

let rec tfmt (p : program) (v : v) (n : int option) : string =
  let m = machine p in
  let left_f = val_ p "◀" and right_f = val_ p "▶" in
  let is_left = Core.app m left_f [| v |] in
  if to_bool m is_left then begin
    let r = Core.app m right_f [| v |] in
    let a, b = to_pair m r in
    let sa = tfmt p a n in
    let sb = tfmt p b n in
    Printf.sprintf "⟨%s, %s⟩" sa sb
  end
  else begin
    let leaf0 = Core.app m right_f [| v |] in
    let leaf = match n with Some k -> stream_nth m leaf0 k | None -> leaf0 in
    let q = qval m leaf in
    match n with
    | Some _ ->
      fmt_g 10 (Bigint.rat_to_float q.re) ^ (if Bigint.rat_is_zero q.im then "" else Printf.sprintf " + %s i" (fmt_g 10 (Bigint.rat_to_float q.im)))
    | None -> if Bigint.rat_is_zero q.im then show_frac q.re else Printf.sprintf "(%s + %s i)" (show_frac q.re) (show_frac q.im)
  end

(* evaluate NAME and print it according to its declared class *)
let show_name (p : program) (name : string) (n : int option) : string =
  let c = p.checker in
  let m = machine p in
  let cls = match Hashtbl.find_opt c.sigs name with Some (t :: _) -> norm c t | _ -> raise (Err (Eval "Prelude.head: empty list")) in
  let v = val_ p name in
  let hd = match cls with K (h, _) -> h | _ -> "" in
  let early =
    match cls with
    | K (h, _) when h = "𝔖" || h = "ℝ" ->
      let k = match n with Some k -> k | None -> 10 in
      Some (Printf.sprintf "element %d of the stream:  %s" k (qfmt m (stream_nth m v k)))
    | K (h, [ K (x, _) ]) when h = "𝔏" && x = "𝕮" -> Some (sfmt m v)
    | K (h, [ a ]) when h = "𝔗" ->
      let streams = (match a with K (x, _) -> x = "𝔖" | _ -> false) in
      let k = match n with Some k -> k | None -> 10 in
      let body = tfmt p v (if streams then Some k else None) in
      Some ((if streams then Printf.sprintf "element %d of each leaf:  " k else "") ^ body)
    | _ -> None
  in
  match early with
  | Some s -> s
  | None ->
    if hd = "𝔹" then (if to_bool m v then "true" else "false")
    else if contains_sub (show_type cls) "Ω" then show_value (make_printer p "hum" 10) v cls
    else qfmt m v

(* ---------------------------------------------------------------- commands *)
(* remove  OPT value  from an argument list *)
let take_opt (opt : string) (args : string list) : string option * string list =
  match position (fun a -> a = opt) args with
  | Some i when i + 1 < List.length args -> (Some (List.nth args (i + 1)), take i args @ drop (i + 2) args)
  | _ -> (None, args)

let read_int (s : string) : int =
  let t = strip s in
  let ok = t <> "" && (let r = ref true in String.iter (fun c -> if c < '0' || c > '9' then r := false) t; !r) in
  match (if ok then int_of_string_opt t else None) with Some k -> k | None -> raise (Err (Eval "Prelude.read: no parse"))

let run_cmd (args0 : string list) : int =
  let o, r1 = take_opt "--out" args0 in
  let n_opt, rest = take_opt "--n" r1 in
  match o with
  | Some o when not (List.mem o modes) ->
    line ("--out takes one of " ^ String.concat ", " modes);
    2
  | _ ->
    let p = load_files rest true in
    if p.errors <> [] then (report_errors p; 1)
    else begin
      let n = match n_opt with Some s -> Some (read_int s) | None -> None in
      match (try Ok (run_main p o n put) with Err (Print e) -> Error e) with
      | Ok _ -> 0
      | Error e -> line ("error: " ^ e); 1
    end

let translate_cmd (rest : string list) : int =
  let to_ = match position (fun a -> a = "--to") rest with Some i when i + 1 < List.length rest -> List.nth rest (i + 1) | _ -> raise (Err (Eval "--to is missing")) in
  let files = List.filter (fun x -> x <> "--to" && x <> to_) rest in
  let p = load_files files false in
  if p.errors <> [] then (report_errors p; 1)
  else begin
    if to_ = "spec" then put (spec_text p)
    else begin
      let t = bin_text p in
      put t;
      if p.doc1.local <> [] then put ("\n" ^ local_table p)
    end;
    0
  end

let is_file (x : string) : bool = Sys.file_exists x && not (Sys.is_directory x)

let query_cmd (cmd : string) (rest : string list) : int =
  let files, name, n =
    if cmd = "check" then (rest, None, None)
    else begin
      let fs = List.filter is_file rest in
      let tl = List.filter (fun x -> not (is_file x)) rest in
      if tl = [] then parse_err "a name is expected";
      let n = match tl with _ :: k :: _ -> Some (read_int k) | _ -> None in
      (fs, Some (List.hd tl), n)
    end
  in
  let p = load_files files (cmd <> "check") in
  if p.errors <> [] then (report_errors p; 1)
  else if cmd = "check" then begin
    line (Printf.sprintf "ok: %d statements checked" (List.length (user_statements p)));
    0
  end
  else begin
    let nm = spec_name p.hum (match name with Some s -> s | None -> "") in
    match (try Ok (if cmd = "text" then sfmt (machine p) (val_ p nm) else show_name p nm n) with Err (Unknown m) | Err (Print m) -> Error m) with
    | Ok s -> line s; 0
    | Error m -> line ("error: " ^ m); 1
  end

let dispatch (args : string list) : int =
  match args with
  | [] -> put usage; 0
  | ("-h" | "--help") :: _ -> put usage; 0
  | cmd :: tl ->
    let known = [ "run"; "check"; "eval"; "text"; "translate" ] in
    let cmd2, rest = if (not (List.mem cmd known)) && is_file cmd then ("run", args) else (cmd, tl) in
    (match cmd2 with
     | "run" -> run_cmd rest
     | "translate" -> translate_cmd rest
     | "check" | "eval" | "text" -> query_cmd cmd2 rest
     | _ -> put usage; 2)

let real_main (args : string list) : int =
  let code =
    try dispatch args with
    | Err e -> flush stdout; prerr_endline ("ocamimo: " ^ err_text e); 1
    | Stack_overflow -> flush stdout; prerr_endline "ocamimo: stack overflow"; 1
    | Out_of_memory -> flush stdout; prerr_endline "ocamimo: out of memory"; 1
    | Bad_utf8 e -> flush stdout; prerr_endline ("ocamimo: " ^ e); 1
    | Sys_error e -> flush stdout; prerr_endline ("ocamimo: " ^ e); 1
    | (Failure e | Invalid_argument e) -> flush stdout; prerr_endline ("ocamimo: internal error: " ^ e); 1
    | Not_found -> flush stdout; prerr_endline "ocamimo: internal error: Not_found"; 1
  in
  flush stdout;
  code

(* the host recursion (reading, checking, printing nested terms) gets the largest stack the system gives: the program starts itself again
   under  ulimit -s unlimited  (the evaluator keeps its own stack on the heap) *)
let () =
  let args = List.tl (Array.to_list Sys.argv) in
  (match Sys.getenv_opt "OCAMIMO_STACK" with
   | Some _ -> ()
   | None -> (
       try
         Unix.putenv "OCAMIMO_STACK" "1";
         Unix.execv "/bin/sh"
           (Array.of_list ("sh" :: "-c" :: "ulimit -s unlimited 2>/dev/null || ulimit -s $(ulimit -H -s) 2>/dev/null; exec \"$0\" \"$@\"" :: Sys.executable_name :: args))
       with _ -> ()));
  Gc.set { (Gc.get ()) with Gc.minor_heap_size = 4 * 1024 * 1024; space_overhead = 200 };
  exit (real_main args)
