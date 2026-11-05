#lang racket/base
;; syntax.rkt -- the SPEC notation reader of i-1 (port of ocamimo/src/syntax.ml and rustimo/src/syntax.rs).
;; spec text -> statements:  SDef name params body | SDecl name type | SFact term.
;; Classes: (K name args) class constructor application, (V name) class variable, 'F the flexible class; "→" is the constructor of functions.
(require racket/list racket/match "base.rkt")
(provide (all-defined-out))

(struct K (name args) #:transparent)
(struct V (name) #:transparent)

(struct TNum (s) #:transparent)
(struct TChr (c) #:transparent)
(struct TStr (s) #:transparent)
(struct TVar (n) #:transparent)
(struct TApp (f args) #:transparent)
(struct TLam (ps body) #:transparent)          ; ps: list of (cons name class-or-#f)
(struct TAsc (e ty) #:transparent)
(struct TQuote (e loc) #:transparent)          ; a statement (class Ω) with the classes of the variables bound outside it

(struct SDef (name params body) #:transparent)
(struct SDecl (name ty) #:transparent)
(struct SFact (term) #:transparent)

;; the runtime term in de Bruijn form
(struct CV (k) #:transparent)
(struct CL (b) #:transparent)
(struct CA (f x) #:transparent)
(struct CG (g) #:transparent)

(define (kk n) (K n '()))
(define (app f xs) (TApp (TVar f) xs))
(define (var n) (TVar n))

;; loc: an insertion-ordered association list name -> class
(define (loc-insert loc n t)
  (if (assoc n loc) (map (lambda (e) (if (equal? (car e) n) (cons n t) e)) loc) (append loc (list (cons n t)))))
(define (loc-lookup loc n) (let ([e (assoc n loc)]) (and e (cdr e))))
(define (loc-member? loc n) (and (assoc n loc) #t))
(define (loc-names loc) (map car loc))

(define class-vars '("α" "β" "γ" "δ" "ε"))
(define (class-var? n) (and (member n class-vars) #t))

;; ---------------------------------------------------------------- Haskell-style `show` (the messages of Haskimo quote it)
(define hs-names
  (vector "NUL" "SOH" "STX" "ETX" "EOT" "ENQ" "ACK" "a" "b" "t" "n" "v" "f" "r" "SO" "SI" "DLE" "DC1" "DC2" "DC3" "DC4"
          "NAK" "SYN" "ETB" "CAN" "EM" "SUB" "ESC" "FS" "GS" "RS" "US"))

(define (hs-show-str s)
  (define n (string-length s))
  (define out (open-output-string))
  (write-char #\" out)
  (for ([i (in-range n)])
    (define u (char->integer (string-ref s i)))
    (define next (and (< (+ i 1) n) (char->integer (string-ref s (+ i 1)))))
    (cond
      [(= u 34) (write-string "\\\"" out)]
      [(= u 92) (write-string "\\\\" out)]
      [(< u 32)
       (write-char #\\ out)
       (write-string (vector-ref hs-names u) out)
       (when (and (= u 14) (eqv? next 72)) (write-string "\\&" out))]
      [(= u 127) (write-string "\\DEL" out)]
      [(> u 126)
       (write-string (format "\\~a" u) out)
       (when (and next (>= next 48) (<= next 57)) (write-string "\\&" out))]
      [else (write-char (string-ref s i) out)]))
  (write-char #\" out)
  (get-output-string out))

(define (hs-show-list-str xs) (string-append "[" (string-join* (map hs-show-str xs) ",") "]"))

(define (hs-show-ty t)
  (match t
    [(V n) (string-append "V " (hs-show-str n))]
    ['F "F"]
    [(K n args) (format "K ~a [~a]" (hs-show-str n) (string-join* (map hs-show-ty args) ","))]))

;; ---------------------------------------------------------------- lexer
;; tokens: 'Nl 'Open 'Close  (tk-num s) (tk-chr c) (tk-str s) (tk-name s)
(struct tk-num (s) #:transparent)
(struct tk-chr (c) #:transparent)
(struct tk-str (s) #:transparent)
(struct tk-name (s) #:transparent)

(define (hs-show-tok t)
  (match t
    ['Nl "TNL"] ['Open "TOpen"] ['Close "TClose"]
    [(tk-num s) (string-append "TkNum " (hs-show-str s))]
    [(tk-chr c) (format "TkChr ~a" c)]
    [(tk-str s) (string-append "TkStr " (hs-show-str s))]
    [(tk-name s) (string-append "TkName " (hs-show-str s))]))

(define (delim? c) (memv c '(#\space #\tab #\return #\newline #\( #\) #\0 #\1 #\. #\' #\")))

(define comment-sign (string (integer->char #x235D)))

(define (lex-spec text)
  (define n (string-length text))
  (let loop ([i 0] [d 0] [out '()])
    (cond
      [(>= i n) (reverse out)]
      [else
       (define c (string-ref text i))
       (cond
         [(memv c '(#\space #\tab #\return)) (loop (+ i 1) d out)]
         [(char=? c #\newline) (loop (+ i 1) d (if (zero? d) (cons 'Nl out) out))]
         [(char=? c #\() (loop (+ i 1) (+ d 1) (cons 'Open out))]
         [(char=? c #\)) (loop (+ i 1) (- d 1) (cons 'Close out))]
         [(memv c '(#\0 #\1 #\.))
          (define j (let l ([j i]) (if (and (< j n) (memv (string-ref text j) '(#\0 #\1 #\.))) (l (+ j 1)) j)))
          (define s (substring text i j))
          (define dots (for/sum ([ch (in-string s)]) (if (char=? ch #\.) 1 0)))
          (when (> dots 1) (parse-err (format "bad numeral ~a (spec notation allows one radix point)" (py-repr s))))
          (loop j d (cons (tk-num s) out))]
         [(memv c '(#\' #\"))
          ;; literal: up to the closing quote; a backslash escapes the next character (n, t as in Python)
          (define body (open-output-string))
          (define-values (j blen first)
            (let l ([j (+ i 1)] [blen 0] [first #f])
              (when (>= j n) (parse-err "unterminated literal"))
              (define x (string-ref text j))
              (cond
                [(char=? x c) (values (+ j 1) blen first)]
                [(char=? x #\\)
                 (when (>= (+ j 1) n) (parse-err "string index out of range"))
                 (define y0 (string-ref text (+ j 1)))
                 (define y (cond [(char=? y0 #\n) #\newline] [(char=? y0 #\t) #\tab] [else y0]))
                 (write-char y body)
                 (l (+ j 2) (+ blen 1) (or first y))]
                [else (write-char x body) (l (+ j 1) (+ blen 1) (or first x))])))
          (cond
            [(char=? c #\')
             (if (= blen 1)
                 (loop j d (cons (tk-chr (char->integer first)) out))
                 (parse-err (format "char literal needs exactly one character: ~a" (py-repr (get-output-string body)))))]
            [else (loop j d (cons (tk-str (get-output-string body)) out))])]
         [else
          (define j (let l ([j i]) (if (and (< j n) (not (delim? (string-ref text j)))) (l (+ j 1)) j)))
          (define name (substring text i j))
          (cond
            [(string=? name comment-sign)
             (define k (let l ([k j]) (if (and (< k n) (not (char=? (string-ref text k) #\newline))) (l (+ k 1)) k)))
             (loop k d out)]
            [else (loop j d (cons (tk-name name) out))])])])))

;; token trees: an atom (a token) or a parenthesised group (a list)
(struct grp (items) #:transparent)

(define (hs-show-tt t)
  (match t
    [(grp xs) (string-append "Grp [" (string-join* (map hs-show-tt xs) ",") "]")]
    [k (let ([s (hs-show-tok k)]) (if (for/or ([ch (in-string s)]) (char=? ch #\space)) (string-append "Atom (" s ")") (string-append "Atom " s)))]))

;; token list (one line, no Nl) -> token trees
(define (trees ts)
  (define v (list->vector ts))
  (define n (vector-length v))
  (define i 0)
  (define (go)
    (let loop ([out '()])
      (cond
        [(>= i n) (reverse out)]
        [else
         (define t (vector-ref v i))
         (cond
           [(eq? t 'Open)
            (set! i (+ i 1))
            (define inner (go))
            (cond [(and (< i n) (eq? (vector-ref v i) 'Close)) (set! i (+ i 1)) (loop (cons (grp inner) out))]
                  [else (parse-err "missing )")])]
           [(eq? t 'Close) (reverse out)]
           [else (set! i (+ i 1)) (loop (cons t out))])])))
  (define r (go))
  (when (< i n) (parse-err "unexpected )"))
  r)

;; the logical lines (split at top-level newlines) of a token stream, each as a list of token trees
(define (logical-lines toks)
  (define lines
    (let loop ([ts toks] [cur '()] [acc '()])
      (cond [(null? ts) (reverse (cons (reverse cur) acc))]
            [(eq? (car ts) 'Nl) (loop (cdr ts) '() (cons (reverse cur) acc))]
            [else (loop (cdr ts) (cons (car ts) cur) acc)])))
  (let loop ([ls lines] [out '()])
    (cond [(null? ls) (reverse out)]
          [else (let ([tt (trees (car ls))]) (loop (cdr ls) (if (null? tt) out (cons tt out))))])))

;; ---------------------------------------------------------------- terms
(define (name-is? t n) (and (tk-name? t) (string=? (tk-name-s t) n)))

(define s-arrow "→")
(define s-mapsto "↦")
(define s-colon "∶")
(define s-assign "≔")

(define (parse-item t)
  (match t
    [(tk-num s) (TNum s)]
    [(tk-chr c) (TChr c)]
    [(tk-str s) (TStr s)]
    [(tk-name n) (TVar n)]
    [(grp inner)
     (define k (rposition (lambda (x) (name-is? x s-mapsto)) inner))
     (if k
         (TLam (parse-binders (take* k inner)) (parse-seq (drop* (+ k 1) inner)))
         (parse-seq inner))]
    [k (parse-err (string-append "unexpected " (hs-show-tok k)))]))

(define (parse-binders ts)
  (cond
    [(null? ts) '()]
    [(tk-name? (car ts))
     (define name (tk-name-s (car ts)))
     (cond
       [(and (pair? (cdr ts)) (name-is? (cadr ts) s-colon))
        (define-values (ty rest) (parse-type-atom (cddr ts)))
        (cons (cons name ty) (parse-binders rest))]
       [else (cons (cons name #f) (parse-binders (cdr ts)))])]
    [else (parse-err (string-append "bad binder " (hs-show-tt (car ts))))]))

(define (parse-seq ts)
  (cond
    [(null? ts) (parse-err "empty application")]
    [(null? (cdr ts)) (parse-item (car ts))]
    [else (let* ([f (parse-item (car ts))] [args (map parse-item (cdr ts))]) (TApp f args))]))

;; ---------------------------------------------------------------- types
(define (parse-type-atom ts)
  (cond
    [(null? ts) (parse-err "list index out of range")]
    [(tk-name? (car ts)) (let ([n (tk-name-s (car ts))]) (values (if (class-var? n) (V n) (K n '())) (cdr ts)))]
    [(grp? (car ts)) (values (parse-type-seq (grp-items (car ts))) (cdr ts))]
    [else (parse-err (string-append "bad type " (hs-show-tt (car ts))))]))

(define (type-atoms ts)
  (if (null? ts)
      '()
      (let-values ([(a r) (parse-type-atom ts)]) (cons a (type-atoms r)))))

(define (parse-type-seq inner)
  (cond
    [(null? inner) (parse-err "empty type")]
    [(name-is? (car inner) s-arrow)
     (define a (type-atoms (cdr inner)))
     (if (= (length a) 2) (K s-arrow a) (parse-err "→ takes two classes"))]
    [else
     (define k (position (lambda (x) (name-is? x s-arrow)) inner))
     (cond
       [k (let* ([l (parse-type-seq (take* k inner))] [r (parse-type-seq (drop* (+ k 1) inner))]) (K s-arrow (list l r)))]
       [else
        (define-values (hd r) (parse-type-atom inner))
        (define args (type-atoms r))
        (cond [(null? args) hd]
              [(and (K? hd) (null? (K-args hd))) (K (K-name hd) args)]
              [else (parse-err (string-append "bad class application " (hs-show-ty hd)))])])]))

(define (show-type t)
  (match t
    [(V n) n]
    ['F "⊥"]
    [(K n (list a b)) #:when (string=? n s-arrow)
     (let* ([l (show-type a)] [l (if (and (K? a) (string=? (K-name a) s-arrow)) (string-append "(" l ")") l)])
       (string-append l " → " (show-type b)))]
    [(K n '()) n]
    [(K n args)
     (string-append "(" n " "
                    (string-join* (map (lambda (a) (if (and (K? a) (string=? (K-name a) s-arrow)) (string-append "(" (show-type a) ")") (show-type a))) args) " ")
                    ")")]))

;; ---------------------------------------------------------------- statements
(define (has-assign? t)
  (match t [(grp xs) (ormap has-assign? xs)] [(tk-name n) (string=? n s-assign)] [_ #f]))

(define (statement ln)
  (cond
    [(ormap has-assign? ln)
     (define k (position (lambda (t) (name-is? t s-assign)) ln))
     (unless k (parse-err "assertion failed"))
     (define hd (take* k ln))
     (define body (drop* (+ k 1) ln))
     (define names (for/list ([t hd] #:when (tk-name? t)) (tk-name-s t)))
     (when (or (null? hd) (not (= (length names) (length hd)))) (parse-err (string-append "bad definition head " (hs-show-list-str names))))
     (SDef (car names) (cdr names) (parse-seq body))]
    [(and (>= (length ln) 3) (name-is? (cadr ln) s-colon))
     (if (tk-name? (car ln))
         (SDecl (tk-name-s (car ln)) (parse-type-seq (cddr ln)))
         (parse-err "assertion failed"))]
    [else (SFact (parse-seq ln))]))

(define (parse-statements text)
  (map statement (logical-lines (lex-spec text))))

;; ---------------------------------------------------------------- erasure to the runtime (de Bruijn) term
(define g-false (CG "⊥"))
(define g-true (CG "⊤"))
(define g-cons (CG "∷"))
(define g-nil (CG "⊘"))
(define g-pair (CG "⊗"))

(define (int-ast s)
  (for/fold ([r g-false]) ([ch (in-string s)])
    (CA (CA g-cons (if (char=? ch #\1) g-true g-false)) r)))

;; the reader's expansion of a numeral: the pair (digits, denominator), digits LSB first
(define (num-ast s)
  (define (pair a b) (CA (CA g-pair a) b))
  (define k (for/first ([i (in-range (string-length s))] #:when (char=? (string-ref s i) #\.)) i))
  (cond
    [(not k) (pair (int-ast s) (int-ast "1"))]
    [else
     (define x (substring s 0 k))
     (define y (substring s (+ k 1)))
     (define bits (string-append x y))
     (when (string=? bits "") (parse-err "empty numeral"))
     (pair (int-ast bits) (int-ast (string-append "1" (make-string (string-length y) #\0))))]))

;; scope: the binders in scope, innermost FIRST
(define (erase scope t)
  (match t
    [(TNum s) (num-ast s)]
    [(TChr c) (num-ast (int-numeral-text c))]
    [(TStr s)
     (for/fold ([r g-nil]) ([ch (in-list (reverse (string->list s)))])
       (CA (CA g-cons (num-ast (int-numeral-text (char->integer ch)))) r))]
    [(TVar nm) (let ([idx (position (lambda (x) (string=? x nm)) scope)]) (if idx (CV (+ idx 1)) (CG nm)))]
    [(TApp f args) (for/fold ([acc (erase scope f)]) ([a (in-list args)]) (CA acc (erase scope a)))]
    [(TLam ps b)
     (define scope2 (for/fold ([sc scope]) ([p (in-list ps)]) (cons (car p) sc)))
     (for/fold ([body (erase scope2 b)]) ([_ (in-list ps)]) (CL body))]
    [(TAsc e _) (erase scope e)]
    [(TQuote e _) (erase scope e)]))

(define (erase-def name params body)
  (define scope (for/fold ([sc '()]) ([n (in-list params)]) (cons n sc)))
  (cons name (for/fold ([c (erase scope body)]) ([_ (in-list params)]) (CL c))))

;; ---------------------------------------------------------------- pretty printer (spec text)
(define (pp-type t)
  (match t
    [(V n) n]
    ['F "⊥"]
    [(K n (list a b)) #:when (string=? n s-arrow) (format "(→ ~a ~a)" (pp-type a) (pp-type b))]
    [(K n '()) n]
    [(K n args) (format "(~a ~a)" n (string-join* (map pp-type args) " "))]))

(define (esc-with s q)
  (define out (open-output-string))
  (for ([ch (in-string s)])
    (cond [(char=? ch #\\) (write-string "\\\\" out)]
          [(char=? ch #\newline) (write-string "\\n" out)]
          [(char=? ch q) (write-char #\\ out) (write-char ch out)]
          [else (write-char ch out)]))
  (get-output-string out))

(define (pp-term t)
  (match t
    [(TNum s) s]
    [(TChr c) (string-append "'" (esc-with (cp->string c) #\') "'")]
    [(TStr s) (string-append "\"" (esc-with s #\") "\"")]
    [(TVar n) n]
    [(TApp f args) (string-append "(" (string-join* (cons (pp-term f) (map pp-term args)) " ") ")")]
    [(TLam ps b)
     (define p (map (lambda (e) (if (cdr e) (string-append (car e) " ∶ " (pp-type (cdr e))) (car e))) ps))
     (string-append "(" (string-join* p " ") " ↦ " (pp-term b) ")")]
    [(TAsc e _) (pp-term e)]
    [(TQuote e _) (pp-term e)]))

(define (pp-statement s)
  (match s
    [(SDef n ps b) (string-append (string-join* (cons n ps) " ") " ≔ " (pp-term b))]
    [(SDecl n ty) (string-append n " ∶ " (pp-type ty))]
    [(SFact t) (pp-term t)]))

;; ---------------------------------------------------------------- Python repr of the tuple form of a term (for error messages)
(define (tuple-of xs)
  (cond [(null? xs) "()"] [(null? (cdr xs)) (string-append "(" (car xs) ",)")] [else (string-append "(" (string-join* xs ", ") ")")]))

(define (repr-ty t)
  (match t
    [(V n) (format "('V', ~a)" (py-repr n))]
    ['F "('F', '⊥')"]
    [(K n args) (format "('K', ~a, ~a)" (py-repr n) (tuple-of (map repr-ty args)))]))

(define (repr-term t)
  (define (tup xs) (string-append "(" (string-join* xs ", ") ")"))
  (match t
    [(TNum s) (tup (list "'num'" (py-repr s)))]
    [(TChr c) (tup (list "'chr'" (number->string c)))]
    [(TStr s) (tup (list "'str'" (py-repr s)))]
    [(TVar n) (tup (list "'var'" (py-repr n)))]
    [(TApp f args) (tup (list "'app'" (repr-term f) (string-append "[" (string-join* (map repr-term args) ", ") "]")))]
    [(TLam ps b)
     (tup (list "'lam'"
                (string-append "[" (string-join* (map (lambda (e) (tup (list (py-repr (car e)) (if (cdr e) (repr-ty (cdr e)) "None")))) ps) ", ") "]")
                (repr-term b)))]
    [(TAsc e ty) (tup (list "'asc'" (repr-term e) (repr-ty ty)))]
    [(TQuote e _) (tup (list "'quote'" (repr-term e)))]))
