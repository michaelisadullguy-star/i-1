(* base.ml -- reference arithmetic of the base b = i-1 with digits {0,1}, errors of the host, UTF-8 and the Python look-alikes
   (port of rustimo/src/base.rs). *)

(* ---------------------------------------------------------------- errors of the host *)
type err = Parse of string | Unknown of string | Print of string | Eval of string
exception Err of err

let err_text = function Parse m | Unknown m | Print m | Eval m -> m
let parse_err m = raise (Err (Parse m))
let print_err m = raise (Err (Print m))

(* ---------------------------------------------------------------- UTF-8 *)
(* the code points of a (valid) UTF-8 string *)
let decode (s : string) : int array =
  let n = String.length s in
  let out = Array.make n 0 in
  let k = ref 0 and i = ref 0 in
  while !i < n do
    let c = Char.code s.[!i] in
    let len, init =
      if c < 0x80 then (1, c)
      else if c < 0xE0 then (2, c land 0x1F)
      else if c < 0xF0 then (3, c land 0x0F)
      else (4, c land 0x07)
    in
    let v = ref init in
    for j = 1 to len - 1 do
      if !i + j < n then v := (!v lsl 6) lor (Char.code s.[!i + j] land 0x3F)
    done;
    out.(!k) <- !v;
    incr k;
    i := !i + len
  done;
  Array.sub out 0 !k

let add_cp (b : Buffer.t) (c : int) : unit =
  let c = if c < 0 || c > 0x10FFFF || (c >= 0xD800 && c <= 0xDFFF) then 0xFFFD else c in
  if c < 0x80 then Buffer.add_char b (Char.chr c)
  else if c < 0x800 then begin
    Buffer.add_char b (Char.chr (0xC0 lor (c lsr 6)));
    Buffer.add_char b (Char.chr (0x80 lor (c land 0x3F)))
  end else if c < 0x10000 then begin
    Buffer.add_char b (Char.chr (0xE0 lor (c lsr 12)));
    Buffer.add_char b (Char.chr (0x80 lor ((c lsr 6) land 0x3F)));
    Buffer.add_char b (Char.chr (0x80 lor (c land 0x3F)))
  end else begin
    Buffer.add_char b (Char.chr (0xF0 lor (c lsr 18)));
    Buffer.add_char b (Char.chr (0x80 lor ((c lsr 12) land 0x3F)));
    Buffer.add_char b (Char.chr (0x80 lor ((c lsr 6) land 0x3F)));
    Buffer.add_char b (Char.chr (0x80 lor (c land 0x3F)))
  end

let string_of_cp (c : int) : string =
  let b = Buffer.create 4 in
  add_cp b c;
  Buffer.contents b

(* the string of the code points a.(lo) .. a.(hi-1) *)
let string_of_cps (a : int array) (lo : int) (hi : int) : string =
  let b = Buffer.create (hi - lo) in
  for i = lo to hi - 1 do add_cp b a.(i) done;
  Buffer.contents b

let cp_length (s : string) : int = Array.length (decode s)

(* is s valid UTF-8?  if not, the position of the first bad byte *)
let utf8_error (s : string) : int option =
  let n = String.length s in
  let i = ref 0 and bad = ref None in
  while !bad = None && !i < n do
    let c = Char.code s.[!i] in
    let cont k = !i + k < n && Char.code s.[!i + k] land 0xC0 = 0x80 in
    if c < 0x80 then incr i
    else if c >= 0xC2 && c < 0xE0 && cont 1 then i := !i + 2
    else if c >= 0xE0 && c < 0xF0 && cont 1 && cont 2 then begin
      let c1 = Char.code s.[!i + 1] in
      if (c = 0xE0 && c1 < 0xA0) || (c = 0xED && c1 >= 0xA0) then bad := Some !i else i := !i + 3
    end else if c >= 0xF0 && c < 0xF5 && cont 1 && cont 2 && cont 3 then begin
      let c1 = Char.code s.[!i + 1] in
      if (c = 0xF0 && c1 < 0x90) || (c = 0xF4 && c1 >= 0x90) then bad := Some !i else i := !i + 4
    end else bad := Some !i
  done;
  !bad

(* ---------------------------------------------------------------- Gaussian integers *)
type gi = Bigint.t * Bigint.t

(* multiply by the base i-1:  (a + bi)(-1 + i) = (-a - b) + (a - b)i *)
let times_b ((a, b) : gi) : gi = (Bigint.neg (Bigint.add a b), Bigint.sub a b)

(* the Gaussian integer with the digits ds (least significant first) *)
let val_digits (ds : int array) : gi =
  let s = ref (Bigint.zero, Bigint.zero) and p = ref (Bigint.one, Bigint.zero) in
  Array.iter
    (fun d ->
       if d <> 0 then s := (Bigint.add (fst !s) (fst !p), Bigint.add (snd !s) (snd !p));
       p := times_b !p)
    ds;
  !s

(* the same for digit lists short enough for native arithmetic (None when they are not) *)
let val_digits_small (ds : int array) : (int * int) option =
  let e = ref (Array.length ds) in
  while !e > 0 && ds.(!e - 1) = 0 do decr e done;
  if !e > 100 then None
  else begin
    let sa = ref 0 and sb = ref 0 and pa = ref 1 and pb = ref 0 in
    for i = 0 to !e - 1 do
      if ds.(i) <> 0 then (sa := !sa + !pa; sb := !sb + !pb);
      let na = - !pa - !pb and nb = !pa - !pb in
      pa := na;
      pb := nb
    done;
    Some (!sa, !sb)
  end

(* Penney: the canonical least-significant-first digit list of a Gaussian integer *)
let to_digits ((x0, y0) : gi) : int array =
  let x = ref x0 and y = ref y0 and out = ref [] in
  while not (Bigint.is_zero !x && Bigint.is_zero !y) do
    let d = Bigint.is_odd (Bigint.add !x !y) in
    let x1 = if d then Bigint.sub !x Bigint.one else !x in
    let nx = Bigint.half_exact (Bigint.add (Bigint.neg x1) !y) in
    let ny = Bigint.half_exact (Bigint.sub (Bigint.neg x1) !y) in
    out := (if d then 1 else 0) :: !out;
    x := nx;
    y := ny
  done;
  Array.of_list (List.rev !out)

(* the same with native integers (the values must stay far from the overflow) *)
let to_digits_native (x0 : int) (y0 : int) : int array =
  let x = ref x0 and y = ref y0 and out = ref [] in
  while not (!x = 0 && !y = 0) do
    let d = (!x + !y) land 1 = 1 in
    let x1 = if d then !x - 1 else !x in
    let nx = (- x1 + !y) / 2 and ny = (- x1 - !y) / 2 in
    out := (if d then 1 else 0) :: !out;
    x := nx;
    y := ny
  done;
  Array.of_list (List.rev !out)

(* most significant digit first ("0" for zero) *)
let numeral (ds : int array) : string =
  let n = Array.length ds in
  if n = 0 then "0" else String.init n (fun i -> if ds.(n - 1 - i) <> 0 then '1' else '0')

(* the numeral text of a natural number (a code point, a digit count, ...), as the reader writes it *)
let int_numeral_text (n : int) : string = numeral (to_digits_native n 0)

let big_numeral_text (n : Bigint.t) : string = numeral (to_digits (n, Bigint.zero))

(* the digits without the most significant zeros *)
let trim_digits (ds : int array) : int array =
  let e = ref (Array.length ds) in
  while !e > 0 && ds.(!e - 1) = 0 do decr e done;
  Array.sub ds 0 !e

(* ---------------------------------------------------------------- Python look-alikes *)
let py_printable (c : int) : bool =
  if c = 0x20 then true
  else if c < 0x20 || (c >= 0x7F && c <= 0x9F) then false
  else if c = 0x85 || c = 0xA0 || c = 0x1680 || (c >= 0x2000 && c <= 0x200A) || c = 0x2028 || c = 0x2029 || c = 0x202F || c = 0x205F || c = 0x3000 then false
  else not
      (c = 0xAD || (c >= 0x600 && c <= 0x605) || c = 0x61C || c = 0x6DD || c = 0x70F || c = 0x180E || (c >= 0x200B && c <= 0x200F)
       || (c >= 0x202A && c <= 0x202E) || (c >= 0x2060 && c <= 0x2064) || (c >= 0x2066 && c <= 0x206F) || c = 0xFEFF
       || (c >= 0xFFF9 && c <= 0xFFFB) || (c >= 0xE000 && c <= 0xF8FF) || (c >= 0xF0000 && c <= 0x10FFFF))

(* Python's repr() of a str *)
let py_repr (s : string) : string =
  let cs = decode s in
  let has_sq = Array.exists (fun c -> c = 39) cs and has_dq = Array.exists (fun c -> c = 34) cs in
  let q = if has_sq && not has_dq then 34 else 39 in
  let b = Buffer.create (String.length s + 2) in
  Buffer.add_char b (Char.chr q);
  Array.iter
    (fun c ->
       if c = q then (Buffer.add_char b '\\'; Buffer.add_char b (Char.chr c))
       else if c = 92 then Buffer.add_string b "\\\\"
       else if c = 10 then Buffer.add_string b "\\n"
       else if c = 13 then Buffer.add_string b "\\r"
       else if c = 9 then Buffer.add_string b "\\t"
       else if py_printable c then add_cp b c
       else if c < 0x100 then Buffer.add_string b (Printf.sprintf "\\x%02x" c)
       else if c < 0x10000 then Buffer.add_string b (Printf.sprintf "\\u%04x" c)
       else Buffer.add_string b (Printf.sprintf "\\U%08x" c))
    cs;
  Buffer.add_char b (Char.chr q);
  Buffer.contents b

(* Python's format(x, '.<p>g') of a float *)
let fmt_g (p : int) (x : float) : string =
  if x = 0.0 then (if 1.0 /. x < 0.0 then "-0" else "0")
  else if x = infinity then "inf"
  else if x = neg_infinity then "-inf"
  else if x <> x then "nan"
  else Printf.sprintf "%.*g" p x

(* ---------------------------------------------------------------- string helpers *)
let is_ws (c : int) : bool =
  (c >= 9 && c <= 13) || c = 0x20 || c = 0x85 || c = 0xA0 || c = 0x1680 || (c >= 0x2000 && c <= 0x200A)
  || c = 0x2028 || c = 0x2029 || c = 0x202F || c = 0x205F || c = 0x3000

(* Python's s.strip() *)
let strip (s : string) : string =
  let cs = decode s in
  let lo = ref 0 and hi = ref (Array.length cs) in
  while !lo < !hi && is_ws cs.(!lo) do incr lo done;
  while !hi > !lo && is_ws cs.(!hi - 1) do decr hi done;
  string_of_cps cs !lo !hi

let basename (p : string) : string =
  match String.rindex_opt p '/' with Some i -> String.sub p (i + 1) (String.length p - i - 1) | None -> p

let starts_with (s : string) (p : string) : bool =
  String.length s >= String.length p && String.sub s 0 (String.length p) = p

let ends_with (s : string) (p : string) : bool =
  let ls = String.length s and lp = String.length p in
  ls >= lp && String.sub s (ls - lp) lp = p

let contains_sub (s : string) (p : string) : bool =
  let ls = String.length s and lp = String.length p in
  let r = ref false and i = ref 0 in
  while (not !r) && !i + lp <= ls do
    if String.sub s !i lp = p then r := true;
    incr i
  done;
  !r

(* the position of the first occurrence of p in s *)
let find_sub (s : string) (p : string) : int option =
  let ls = String.length s and lp = String.length p in
  let r = ref None and i = ref 0 in
  while !r = None && !i + lp <= ls do
    if String.sub s !i lp = p then r := Some !i;
    incr i
  done;
  !r

(* split at every occurrence of the separator *)
let split_on (s : string) (sep : string) : string list =
  let ls = String.length s and lp = String.length sep in
  let out = ref [] and start = ref 0 and i = ref 0 in
  while !i + lp <= ls do
    if String.sub s !i lp = sep then (out := String.sub s !start (!i - !start) :: !out; i := !i + lp; start := !i)
    else incr i
  done;
  out := String.sub s !start (ls - !start) :: !out;
  List.rev !out

(* read a whole file; a file that is not valid UTF-8 is an error carrying the message of Python's decoder *)
exception Bad_utf8 of string

let read_file (path : string) : string =
  let ic = open_in_bin path in
  let n = in_channel_length ic in
  let s = really_input_string ic n in
  close_in ic;
  s

let read_utf8 (path : string) : string =
  let s = read_file path in
  match utf8_error s with
  | None -> s
  | Some at -> raise (Bad_utf8 (Printf.sprintf "cannot decode byte sequence starting from %d (position %d)" (Char.code s.[at]) at))
