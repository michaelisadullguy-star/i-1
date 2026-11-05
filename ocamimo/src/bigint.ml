(* bigint.ml -- arbitrary-precision integers and rationals for the host side of OCamimo (port of rustimo/src/bigint.rs).
   The language computes with digit lists; the host only does the isomorphism "digit string <-> Gaussian integer" and a few exact
   fractions.  Sign + magnitude over 30-bit limbs (little endian, no high zero limbs; zero is the empty array and not negative). *)

type t = { neg : bool; mag : int array }

let bits = 30
let base = 1 lsl bits
let mask = base - 1

let trim (a : int array) : int array =
  let n = ref (Array.length a) in
  while !n > 0 && a.(!n - 1) = 0 do decr n done;
  if !n = Array.length a then a else Array.sub a 0 !n

let cmp_mag a b =
  let la = Array.length a and lb = Array.length b in
  if la <> lb then compare la lb
  else begin
    let r = ref 0 and i = ref (la - 1) in
    while !r = 0 && !i >= 0 do
      if a.(!i) <> b.(!i) then r := compare a.(!i) b.(!i);
      decr i
    done;
    !r
  end

let add_mag a b =
  let a, b = if Array.length a >= Array.length b then a, b else b, a in
  let n = Array.length a in
  let out = Array.make (n + 1) 0 in
  let carry = ref 0 in
  for i = 0 to n - 1 do
    let s = a.(i) + (if i < Array.length b then b.(i) else 0) + !carry in
    out.(i) <- s land mask;
    carry := s lsr bits
  done;
  out.(n) <- !carry;
  trim out

(* a - b for |a| >= |b| *)
let sub_mag a b =
  let n = Array.length a in
  let out = Array.make n 0 in
  let borrow = ref 0 in
  for i = 0 to n - 1 do
    let d = a.(i) - !borrow - (if i < Array.length b then b.(i) else 0) in
    if d < 0 then (out.(i) <- d + base; borrow := 1) else (out.(i) <- d; borrow := 0)
  done;
  trim out

let mul_mag a b =
  let la = Array.length a and lb = Array.length b in
  if la = 0 || lb = 0 then [||]
  else begin
    let out = Array.make (la + lb) 0 in
    for i = 0 to la - 1 do
      let carry = ref 0 in
      for j = 0 to lb - 1 do
        let t = a.(i) * b.(j) + out.(i + j) + !carry in
        out.(i + j) <- t land mask;
        carry := t lsr bits
      done;
      out.(i + lb) <- !carry
    done;
    trim out
  end

let bit_len_mag a =
  let n = Array.length a in
  if n = 0 then 0
  else begin
    let top = a.(n - 1) in
    let l = ref 0 in
    while (top lsr !l) <> 0 do incr l done;
    (n - 1) * bits + !l
  end

let shl_mag a n =
  if Array.length a = 0 then [||]
  else begin
    let limbs = n / bits and b = n mod bits in
    let la = Array.length a in
    let out = Array.make (limbs + la + 1) 0 in
    for i = 0 to la - 1 do
      let v = a.(i) lsl b in
      out.(limbs + i) <- out.(limbs + i) lor (v land mask);
      out.(limbs + i + 1) <- out.(limbs + i + 1) lor (v lsr bits)
    done;
    trim out
  end

let shr_mag a n =
  let limbs = n / bits and b = n mod bits in
  let la = Array.length a in
  if limbs >= la then [||]
  else begin
    let m = la - limbs in
    let out = Array.make m 0 in
    for i = 0 to m - 1 do
      let lo = a.(limbs + i) lsr b in
      let hi = if i + 1 < m then (a.(limbs + i + 1) lsl (bits - b)) land mask else 0 in
      out.(i) <- lo lor hi
    done;
    trim out
  end

let bit_mag a i =
  let limb = i / bits in
  limb < Array.length a && (a.(limb) lsr (i mod bits)) land 1 = 1

(* divide by a small number (< 2^30): quotient and remainder *)
let divmod_small a d =
  let n = Array.length a in
  let q = Array.make n 0 in
  let rem = ref 0 in
  for i = n - 1 downto 0 do
    let cur = (!rem lsl bits) lor a.(i) in
    q.(i) <- cur / d;
    rem := cur mod d
  done;
  (trim q, !rem)

(* quotient and remainder of magnitudes (shift-and-subtract; the numbers of the host side are small) *)
let divrem_mag a b =
  if Array.length b = 0 then failwith "division by zero";
  if cmp_mag a b < 0 then ([||], a)
  else if Array.length b = 1 then begin
    let q, r = divmod_small a b.(0) in
    (q, if r = 0 then [||] else [| r |])
  end else begin
    let nbits = bit_len_mag a in
    let q = Array.make (Array.length a) 0 in
    let r = ref [||] in
    for i = nbits - 1 downto 0 do
      r := shl_mag !r 1;
      if bit_mag a i then begin
        if Array.length !r = 0 then r := [| 1 |] else (let c = Array.copy !r in c.(0) <- c.(0) lor 1; r := c)
      end;
      if cmp_mag !r b >= 0 then begin
        r := sub_mag !r b;
        q.(i / bits) <- q.(i / bits) lor (1 lsl (i mod bits))
      end
    done;
    (trim q, !r)
  end

let make neg mag =
  let mag = trim mag in
  { neg = neg && Array.length mag > 0; mag }

let zero = { neg = false; mag = [||] }
let one = { neg = false; mag = [| 1 |] }

let of_int (v : int) : t =
  if v = 0 then zero
  else begin
    let neg = v < 0 in
    (* |min_int| does not fit in a positive int: go through the negative side *)
    let limbs = ref [] and x = ref v in
    while !x <> 0 do
      let r = !x mod base in
      let r = if r < 0 then -r else r in
      limbs := r :: !limbs;
      x := !x / base
    done;
    make neg (Array.of_list (List.rev !limbs))
  end

let is_zero a = Array.length a.mag = 0
let is_neg a = a.neg
let sign a = if is_zero a then 0 else if a.neg then -1 else 1
let neg a = make (not a.neg) a.mag
let abs a = make false a.mag

let add a b =
  if a.neg = b.neg then make a.neg (add_mag a.mag b.mag)
  else begin
    let c = cmp_mag a.mag b.mag in
    if c = 0 then zero
    else if c > 0 then make a.neg (sub_mag a.mag b.mag)
    else make b.neg (sub_mag b.mag a.mag)
  end

let sub a b = add a (neg b)
let mul a b = make (a.neg <> b.neg) (mul_mag a.mag b.mag)
let mul_small a k = make a.neg (mul_mag a.mag [| k |])
let add_small a k = add a (of_int k)
let is_odd a = Array.length a.mag > 0 && a.mag.(0) land 1 = 1
let half_exact a = make a.neg (shr_mag a.mag 1)
let bit_length a = bit_len_mag a.mag
let shl a n = make a.neg (shl_mag a.mag n)
let shr a n = make a.neg (shr_mag a.mag n)
let bit_at a i = bit_mag a.mag i

let compare a b =
  let sa = sign a and sb = sign b in
  if sa <> sb then compare sa sb
  else if sa = 0 then 0
  else if sa = 1 then cmp_mag a.mag b.mag
  else cmp_mag b.mag a.mag

let equal a b = a.neg = b.neg && a.mag = b.mag

(* truncating division: (quotient, remainder) with the sign of the dividend on the remainder *)
let divrem a b =
  let q, r = divrem_mag a.mag b.mag in
  (make (a.neg <> b.neg) q, make a.neg r)

let gcd a b =
  let a = ref (abs a) and b = ref (abs b) in
  while not (is_zero !b) do
    let _, r = divrem !a !b in
    a := !b;
    b := r
  done;
  !a

let to_int_opt a =
  if Array.length a.mag > 3 then None
  else begin
    (* at most 90 bits: accept only what fits in 62 bits *)
    if bit_len_mag a.mag > 62 then None
    else begin
      let v = ref 0 in
      for i = Array.length a.mag - 1 downto 0 do v := (!v lsl bits) lor a.mag.(i) done;
      Some (if a.neg then - !v else !v)
    end
  end

let parse_dec (s : string) : t =
  let digits = Buffer.create (String.length s) in
  String.iter (fun c -> if c >= '0' && c <= '9' then Buffer.add_char digits c) s;
  let d = Buffer.contents digits in
  let n = String.length d in
  let r = ref zero and i = ref 0 in
  while !i < n do
    let len = min 9 (n - !i) in
    let k = int_of_string ("0" ^ String.sub d !i len) in
    let p = ref 1 in
    for _ = 1 to len do p := !p * 10 done;
    r := add_small (mul_small !r !p) k;
    i := !i + len
  done;
  !r

let pow_small b e =
  let r = ref one in
  for _ = 1 to e do r := mul_small !r b done;
  !r

let to_dec a =
  if is_zero a then "0"
  else begin
    let chunks = ref [] and cur = ref a.mag in
    while Array.length !cur > 0 do
      let q, r = divmod_small !cur 1_000_000_000 in
      chunks := r :: !chunks;
      cur := q
    done;
    let b = Buffer.create 32 in
    if a.neg then Buffer.add_char b '-';
    (match !chunks with
     | [] -> ()
     | first :: rest ->
       Buffer.add_string b (string_of_int first);
       List.iter (fun c -> Buffer.add_string b (Printf.sprintf "%09d" c)) rest);
    Buffer.contents b
  end

(* ------------------------------------------------------------------ rationals *)
type rat = { num : t; den : t }

let rat_new num den =
  let num, den = if is_neg den then (neg num, neg den) else (num, den) in
  let g = gcd num den in
  if (not (is_zero g)) && not (equal g one) then { num = fst (divrem num g); den = fst (divrem den g) }
  else { num; den }

let rat_is_zero r = is_zero r.num
let rat_is_int r = equal r.den one
let rat_truncate r = fst (divrem r.num r.den)

let low_bits_nonzero a n =
  let full = n / bits in
  let found = ref false in
  for i = 0 to min full (Array.length a.mag) - 1 do if a.mag.(i) <> 0 then found := true done;
  if !found then true
  else begin
    let rem = n mod bits in
    rem > 0 && full < Array.length a.mag && a.mag.(full) land ((1 lsl rem) - 1) <> 0
  end

(* the nearest double (ties to even), as Haskell's fromRational and Python's float(Fraction) give it *)
let rat_to_float r =
  if is_zero r.num then 0.0
  else begin
    let neg_ = is_neg r.num in
    let a = abs r.num and b = r.den in
    let shift = 55 - (bit_length a - bit_length b) in
    let n, d = if shift >= 0 then (shl a shift, b) else (a, shl b (- shift)) in
    let q, rm = divrem n d in
    let qbits = bit_length q in
    let sticky = not (is_zero rm) in
    let exp2 = ref (qbits - 1 - shift) in
    let keep = if !exp2 >= -1022 then 53 else 53 - (-1022 - !exp2) in
    if keep <= 0 then (if neg_ then -0.0 else 0.0)
    else begin
      let drop = qbits - keep in
      let q = ref q and qb = ref qbits in
      if drop > 0 then begin
        let half_bit = bit_at !q (drop - 1) in
        let below = low_bits_nonzero !q (drop - 1) || sticky in
        let m = ref (shr !q drop) in
        if half_bit && (below || is_odd !m) then m := add_small !m 1;
        if bit_length !m > keep then (m := shr !m 1; incr exp2);
        q := !m;
        qb := keep
      end;
      let mant = match to_int_opt !q with Some v -> v | None -> 0 in
      let e = !exp2 - (!qb - 1) in
      let x = ldexp (float_of_int mant) e in
      if neg_ then -. x else x
    end
  end
