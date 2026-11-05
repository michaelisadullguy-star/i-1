#lang racket/base
;; base.rkt -- reference arithmetic of the base b = i-1 with digits {0,1}, errors of the host, and the Python look-alikes
;; (port of ocamimo/src/base.ml and rustimo/src/base.rs).  Racket has exact integers and rationals, so no big-number module is needed.
(require racket/list racket/string racket/math)
(provide (all-defined-out))

;; ---------------------------------------------------------------- errors of the host
;; kind: 'parse 'unknown 'print 'eval
(struct host-err (kind msg))
(define (parse-err m) (raise (host-err 'parse m)))
(define (print-err m) (raise (host-err 'print m)))
(define (eval-err m) (raise (host-err 'eval m)))
(define (host-err-of? kind) (lambda (e) (and (host-err? e) (eq? (host-err-kind e) kind))))

;; ---------------------------------------------------------------- characters
;; a code point as a Racket character (a surrogate or a value beyond U+10FFFF becomes U+FFFD)
(define (cp->char c)
  (if (or (< c 0) (> c #x10FFFF) (and (>= c #xD800) (<= c #xDFFF))) (integer->char #xFFFD) (integer->char c)))
(define (cp->string c) (string (cp->char c)))

;; is s valid UTF-8?  if not, the position of the first bad byte
(define (utf8-error bs)
  (define n (bytes-length bs))
  (let loop ([i 0])
    (if (>= i n)
        #f
        (let ([c (bytes-ref bs i)])
          (define (cont k) (and (< (+ i k) n) (= (bitwise-and (bytes-ref bs (+ i k)) #xC0) #x80)))
          (cond
            [(< c #x80) (loop (+ i 1))]
            [(and (>= c #xC2) (< c #xE0) (cont 1)) (loop (+ i 2))]
            [(and (>= c #xE0) (< c #xF0) (cont 1) (cont 2))
             (let ([c1 (bytes-ref bs (+ i 1))])
               (if (or (and (= c #xE0) (< c1 #xA0)) (and (= c #xED) (>= c1 #xA0))) i (loop (+ i 3))))]
            [(and (>= c #xF0) (< c #xF5) (cont 1) (cont 2) (cont 3))
             (let ([c1 (bytes-ref bs (+ i 1))])
               (if (or (and (= c #xF0) (< c1 #x90)) (and (= c #xF4) (>= c1 #x90))) i (loop (+ i 4))))]
            [else i])))))

;; a file that is not valid UTF-8 raises bad-utf8 with the message of Python's decoder
(struct bad-utf8 (msg))
(define (read-file path)
  (call-with-input-file path (lambda (in) (let ([b (read-bytes (max 1 (file-size path)) in)]) (if (eof-object? b) #"" b)))))
(define (read-utf8 path)
  (define bs (read-file path))
  (define at (utf8-error bs))
  (if at
      (raise (bad-utf8 (format "cannot decode byte sequence starting from ~a (position ~a)" (bytes-ref bs at) at)))
      (bytes->string/utf-8 bs)))

;; ---------------------------------------------------------------- Gaussian integers: (cons re im) of exact integers
(define (times-b g) (let ([a (car g)] [b (cdr g)]) (cons (- (+ a b)) (- a b))))

;; the Gaussian integer with the digits ds (a vector of 0/1, least significant first)
(define (val-digits ds)
  (let loop ([i 0] [sa 0] [sb 0] [pa 1] [pb 0])
    (if (>= i (vector-length ds))
        (cons sa sb)
        (let* ([d (vector-ref ds i)]
               [sa2 (if (zero? d) sa (+ sa pa))]
               [sb2 (if (zero? d) sb (+ sb pb))])
          (loop (+ i 1) sa2 sb2 (- (+ pa pb)) (- pa pb))))))

;; the same, or #f when the digit list is longer than the native arithmetic of the other cores would take
(define (val-digits-small ds)
  (let ([e (let loop ([e (vector-length ds)]) (if (and (> e 0) (zero? (vector-ref ds (- e 1)))) (loop (- e 1)) e))])
    (if (> e 100) #f (val-digits (vector-copy* ds e)))))
(define (vector-copy* v n) (let ([r (make-vector n 0)]) (for ([i (in-range n)]) (vector-set! r i (vector-ref v i))) r))

;; Penney: the canonical least-significant-first digit list of a Gaussian integer
(define (to-digits g)
  (let loop ([x (car g)] [y (cdr g)] [out '()])
    (if (and (zero? x) (zero? y))
        (list->vector (reverse out))
        (let* ([d (odd? (+ x y))]
               [x1 (if d (- x 1) x)]
               [nx (quotient (+ (- x1) y) 2)]
               [ny (quotient (- (- x1) y) 2)])
          (loop nx ny (cons (if d 1 0) out))))))

;; most significant digit first ("0" for zero)
(define (numeral ds)
  (let ([n (vector-length ds)])
    (if (zero? n) "0" (build-string n (lambda (i) (if (zero? (vector-ref ds (- n 1 i))) #\0 #\1))))))

(define (int-numeral-text n) (numeral (to-digits (cons n 0))))
(define (big-numeral-text n) (numeral (to-digits (cons n 0))))

(define (trim-digits ds)
  (vector-copy* ds (let loop ([e (vector-length ds)]) (if (and (> e 0) (zero? (vector-ref ds (- e 1)))) (loop (- e 1)) e))))

;; ---------------------------------------------------------------- Python look-alikes
(define (py-printable c)
  (cond
    [(= c 32) #t]
    [(or (< c 32) (and (>= c #x7F) (<= c #x9F))) #f]
    [(and (< c #x110000) (not (and (>= c #xD800) (<= c #xDFFF))) (char-whitespace? (integer->char c))) #f]
    [else
     (not (or (= c #xAD) (and (>= c #x600) (<= c #x605)) (= c #x61C) (= c #x6DD) (= c #x70F) (= c #x180E)
              (and (>= c #x200B) (<= c #x200F)) (and (>= c #x202A) (<= c #x202E)) (and (>= c #x2060) (<= c #x2064))
              (and (>= c #x2066) (<= c #x206F)) (= c #xFEFF) (and (>= c #xFFF9) (<= c #xFFFB))
              (and (>= c #xE000) (<= c #xF8FF)) (and (>= c #xF0000) (<= c #x10FFFF))))]))

(define (hex-pad n width) (let ([s (number->string n 16)]) (string-append (make-string (max 0 (- width (string-length s))) #\0) s)))

;; Python's repr() of a str
(define (py-repr s)
  (define has-sq (for/or ([ch (in-string s)]) (char=? ch #\')))
  (define has-dq (for/or ([ch (in-string s)]) (char=? ch #\")))
  (define q (if (and has-sq (not has-dq)) #\" #\'))
  (define out (open-output-string))
  (write-char q out)
  (for ([ch (in-string s)])
    (define c (char->integer ch))
    (cond
      [(char=? ch q) (write-char #\\ out) (write-char ch out)]
      [(= c 92) (write-string "\\\\" out)]
      [(= c 10) (write-string "\\n" out)]
      [(= c 13) (write-string "\\r" out)]
      [(= c 9) (write-string "\\t" out)]
      [(py-printable c) (write-char ch out)]
      [(< c #x100) (write-string (string-append "\\x" (hex-pad c 2)) out)]
      [(< c #x10000) (write-string (string-append "\\u" (hex-pad c 4)) out)]
      [else (write-string (string-append "\\U" (hex-pad c 8)) out)]))
  (write-char q out)
  (get-output-string out))

;; Python's  format(x, '.<p>g')  of a float: p significant digits, trailing zeros removed, exponent form outside [1e-4, 10^p)
(define (fmt-g p x)
  (cond
    [(and (eqv? x 0.0)) "0"]
    [(eqv? x -0.0) "-0"]
    [(eqv? x +inf.0) "inf"]
    [(eqv? x -inf.0) "-inf"]
    [(not (= x x)) "nan"]
    [else
     (define neg (< x 0.0))
     (define r (abs (inexact->exact x)))
     ;; e: the decimal exponent of r (10^e <= r < 10^(e+1)); digits: r rounded to p significant digits, half to even
     (define e0 (let loop ([e (- (string-length (number->string (floor r))) 1)])
                  (cond [(< r (expt 10 e)) (loop (- e 1))] [(>= r (expt 10 (+ e 1))) (loop (+ e 1))] [else e])))
     (define (digits-at e) (round (/ r (expt 10 (- e (- p 1))))))   ; round is half to even on exact rationals
     (define d0 (digits-at e0))
     (define-values (e d) (if (>= d0 (expt 10 p)) (values (+ e0 1) (digits-at (+ e0 1))) (values e0 d0)))
     (define ds (number->string d))          ; exactly p digits
     (define sign (if neg "-" ""))
     (define (trim-zeros s) (let loop ([n (string-length s)]) (if (and (> n 0) (char=? (string-ref s (- n 1)) #\0)) (loop (- n 1)) (substring s 0 n))))
     (cond
       [(or (< e -4) (>= e p))
        (define t (trim-zeros (substring ds 1)))
        (define m (if (string=? t "") (substring ds 0 1) (string-append (substring ds 0 1) "." t)))
        (define ex (abs e))
        (string-append sign m "e" (if (< e 0) "-" "+") (if (< ex 10) "0" "") (number->string ex))]
       [(>= e 0)
        (define ip (substring ds 0 (+ e 1)))
        (define fp (trim-zeros (substring ds (+ e 1))))
        (string-append sign (if (string=? fp "") ip (string-append ip "." fp)))]
       [else
        (define fp (trim-zeros (string-append (make-string (- (- e) 1) #\0) ds)))
        (string-append sign "0." fp)])]))

;; ---------------------------------------------------------------- string helpers
(define (strip s)
  (let* ([n (string-length s)]
         [lo (let loop ([i 0]) (if (and (< i n) (char-whitespace? (string-ref s i))) (loop (+ i 1)) i))]
         [hi (let loop ([i n]) (if (and (> i lo) (char-whitespace? (string-ref s (- i 1)))) (loop (- i 1)) i))])
    (substring s lo hi)))

(define (basename p)
  (let loop ([i (- (string-length p) 1)])
    (cond [(< i 0) p] [(char=? (string-ref p i) #\/) (substring p (+ i 1))] [else (loop (- i 1))])))

(define (starts-with? s p) (and (>= (string-length s) (string-length p)) (string=? (substring s 0 (string-length p)) p)))
(define (ends-with? s p) (let ([ls (string-length s)] [lp (string-length p)]) (and (>= ls lp) (string=? (substring s (- ls lp)) p))))

;; the position of the first occurrence of p in s at or after start, or #f
(define (find-sub s p [start 0])
  (define ls (string-length s))
  (define lp (string-length p))
  (cond
    [(zero? lp) (and (<= start ls) start)]
    [else
     (define c0 (string-ref p 0))
     (let loop ([i start])
       (cond
         [(> (+ i lp) ls) #f]
         [(and (char=? (string-ref s i) c0)
               (let inner ([k 1]) (or (= k lp) (and (char=? (string-ref s (+ i k)) (string-ref p k)) (inner (+ k 1))))))
          i]
         [else (loop (+ i 1))]))]))
(define (contains-sub? s p) (and (find-sub s p) #t))
(define (rfind-sub s p)
  (define ls (string-length s))
  (define lp (string-length p))
  (let loop ([i (- ls lp)])
    (cond [(< i 0) #f]
          [(string=? (substring s i (+ i lp)) p) i]
          [else (loop (- i 1))])))

;; split at every occurrence of the separator (the pieces between, empty ones included)
(define (split-on s sep)
  (define lp (string-length sep))
  (let loop ([start 0] [out '()])
    (define k (find-sub s sep start))
    (if k
        (loop (+ k lp) (cons (substring s start k) out))
        (reverse (cons (substring s start) out)))))

;; Python's s.split(): the pieces between runs of white space
(define (split-ws s)
  (define n (string-length s))
  (let loop ([i 0] [start #f] [out '()])
    (cond
      [(>= i n) (reverse (if start (cons (substring s start n) out) out))]
      [(char-whitespace? (string-ref s i)) (loop (+ i 1) #f (if start (cons (substring s start i) out) out))]
      [else (loop (+ i 1) (or start i) out)])))

(define (split-lines s) (split-on s "\n"))

(define (take* n l) (if (or (<= n 0) (null? l)) '() (cons (car l) (take* (- n 1) (cdr l)))))
(define (drop* n l) (if (or (<= n 0) (null? l)) l (drop* (- n 1) (cdr l))))
(define (position pred l) (let loop ([l l] [i 0]) (cond [(null? l) #f] [(pred (car l)) i] [else (loop (cdr l) (+ i 1))])))
(define (rposition pred l) (let loop ([l l] [i 0] [last #f]) (cond [(null? l) last] [else (loop (cdr l) (+ i 1) (if (pred (car l)) i last))])))

(define (string-join* l sep)
  (cond [(null? l) ""] [else (apply string-append (car l) (map (lambda (x) (string-append sep x)) (cdr l)))]))
