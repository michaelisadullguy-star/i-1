#lang racket/base
;; output.rkt -- printing values: the output side of the three notations, and the `main` entry point (port of ocamimo/src/output.ml).
;; A value is printed as a NORMAL-FORM TERM in the chosen notation.  Nothing is computed on the host: the normal forms are computed IN THE
;; LANGUAGE (⊜, showq / showc, decimals); the host walks the value as its declared class describes it, reads digit strings and turns code
;; points into characters.  main ∶ 𝕊: its text is the output; main ∶ 𝔏 𝕊 / 𝔖 𝕊: one line per element; any other class: the value as a term.
(require racket/list racket/match racket/set
         "base.rkt" "syntax.rkt" "layers.rkt" "hum.rkt" "types.rkt" "core.rkt" "program.rkt")
(provide (all-defined-out))

(define modes '("bin" "spec" "hum"))

(define undetermined
  "undetermined: this truth value is neither proved nor refuted — a statement that depends on its unknowns, or a relation on ℝ[i] that no rule decides (declare it Prop to print its simplest form instead of a Bool)")

(struct printer (p mode n))
(define (mach pr) (program-machine (printer-p pr)))
(define (chk pr) (program-checker (printer-p pr)))
(define (is-hum? pr) (equal? (printer-mode pr) "hum"))

(define (esc q s)
  (define out (open-output-string))
  (for ([c (in-string s)])
    (cond [(char=? c #\\) (write-string "\\\\" out)]
          [(char=? c #\newline) (write-string "\\n" out)]
          [(char=? c #\tab) (write-string "\\t" out)]
          [(char=? c q) (write-char #\\ out) (write-char c out)]
          [else (write-char c out)]))
  (get-output-string out))

;; take a list / string cell apart (a vcons, or 'VNil); ⍰ (an undetermined Boolean inside the text) is reported, never printed as text
(define (cell-of pr v)
  (define c (cell-or-nil (mach pr) v))
  (if (or (vcons? c) (eq? c 'VNil)) c (print-err undetermined)))

(define (boolean-of pr v)
  (define m (mach pr))
  (define r (apply-whnf m v (vector (machine-vt m) (machine-vf m))))
  (cond [(eq? r 'VT) #t] [(eq? r 'VF) #f] [else (print-err undetermined)]))

(define (call-th pr f args) (call-g (mach pr) f args))

;; a 𝕮 value (a natural numeral, as a ℚ[i] pair) -> code point; its canonical form is a pair (n, 1)
(define (char-of pr v)
  (define m (mach pr))
  (define canon (call-th pr "⊜" (vector v)))
  (define-values (z mm) (to-pair m canon))
  (define zd (to-list m z))
  (define ok-den (equal? (to-list m mm) (vector 1)))
  (define cp (let ([r (val-digits-small zd)]) (and r (zero? (cdr r)) (>= (car r) 0) (<= (car r) #x10FFFF) (car r))))
  (if (and cp ok-den) (if (and (>= cp #xD800) (<= cp #xDFFF)) #xFFFD cp) #xFFFD))

;; a 𝕊 value -> String (code point by code point)
(define (text-of pr v)
  (define out (open-output-string))
  (let loop ([cell (cell-of pr v)])
    (unless (eq? cell 'VNil)
      (write-char (cp->char (char-of pr (vcons-h cell))) out)
      (loop (cell-of pr (vcons-t cell)))))
  (get-output-string out))

(define (digits-str pr v) (numeral (to-list (mach pr) v)))
(define (is-class? pr cls name) (and (leq (chk pr) cls (kk name)) (leq (chk pr) (kk name) cls)))

(define (strip-quotes t)
  (match t
    [(TQuote e _) (strip-quotes e)]
    [(TApp f args) (TApp (strip-quotes f) (map strip-quotes args))]
    [(TLam ps b) (TLam ps (strip-quotes b))]
    [_ t]))

;; ------------------------------------------------------------ the Speller: the human spelling of the code of a statement
;; nodes: (list 'N x) (list 'S x) (list 'A f a) 'L 'Var     pieces: (list text precedence kind)
(define formula-args '("∧" "∨" "¬" "⇒" "⇔" "∧Ω" "∨Ω" "¬Ω" "⇒Ω" "⇔Ω" "prop" "decide" "code_rd"))
(define spell-transparent '("⇡" "prop" "decide" "code_rd"))
(define tight '("*" "/" "^"))
(define assoc-ops '("+" "*"))

(define (par pc need avoid)
  (if (or (< (cadr pc) need) (member (caddr pc) avoid)) (string-append "(" (car pc) ")") (car pc)))

(define (node-of pr v)
  (define m (mach pr))
  (define (not-a-code) (print-err "a statement whose code is not a code (undetermined, or not built by the simplifier)"))
  (define r (with-handlers ([host-err? (lambda (e) e)]) (apply-whnf m v (machine-code-cbs m))))
  (cond
    [(host-err? r) (if (eq? (host-err-kind r) 'unknown) (raise r) (not-a-code))]
    [(vcn? r) (list 'N (vcn-x r))]
    [(vcs? r) (list 'S (vcs-x r))]
    [(vca? r) (list 'A (vca-f r) (vca-a r))]
    [(vcl? r) 'L]
    [(vcv? r) 'Var]
    [else (not-a-code)]))

(define (symbol-name pr c)
  (define ds (trim-digits (to-list (mach pr) c)))
  (define b (string-append "." (numeral ds) "."))
  (or (hash-ref (doc1-b2s (program-doc1 (printer-p pr))) b #f)
      (print-err (format "a statement mentions the symbol code ~a, which neither doc 1 nor this program names" b))))

;; reverse doc 2: the first entry that has the spec symbol on its right
(define (rev-entry pr spec)
  (for/first ([e (in-list (doc2-entries (program-doc2 (printer-p pr))))]
              #:when (and (member (entry-role e) '("value" "infixl" "infixr" "infix" "prefix")) (member spec (entry-rhs e))))
    e))

(define (number-piece pr q)
  (define t (with-handlers ([(host-err-of? 'eval) (lambda (e) (print-err "a statement holds a value that is not a number where a number is expected"))])
              (text-of pr (call-th pr "showc" (vector q)))))
  (define p (cond [(or (contains-sub? t " + ") (contains-sub? t " - ")) 6]
                  [(or (ends-with? t "i") (contains-sub? t "/")) 7]
                  [(starts-with? t "-") 8]
                  [else 10]))
  (list t p "num"))

(define (go pr v formula)
  (define n (node-of pr v))
  (cond
    [(and (pair? n) (eq? (car n) 'N))
     (cond
       [formula
        (define m (mach pr))
        (define r (apply-whnf m (cadr n) (vector (machine-vt m) (machine-vf m))))
        (cond [(eq? r 'VT) (list "true" 10 "atom")] [(eq? r 'VF) (list "false" 10 "atom")] [else (print-err undetermined)])]
       [else (number-piece pr (cadr n))])]
    [(and (pair? n) (eq? (car n) 'S)) (app-piece pr (symbol-name pr (cadr n)) '() formula)]
    [(and (pair? n) (eq? (car n) 'A))
     ;; the spine: head and arguments
     (let loop ([args (list (caddr n))] [cur (node-of pr (cadr n))])
       (cond
         [(and (pair? cur) (eq? (car cur) 'A)) (loop (cons (caddr cur) args) (node-of pr (cadr cur)))]
         [(and (pair? cur) (eq? (car cur) 'S)) (app-piece pr (symbol-name pr (cadr cur)) args formula)]
         [else (print-err "a statement applies something that is not a symbol (a λ): it has no human spelling")]))]
    [else (print-err "a statement contains a λ or a bound variable: it has no human spelling yet")]))

(define (app-piece pr name args formula)
  (define k (length args))
  (define (arg i) (list-ref args i))
  (cond
    [(and (or (equal? name "⊤") (equal? name "⊥")) (= k 0)) (list (if (equal? name "⊤") "true" "false") 10 "atom")]
    [(and (member name spell-transparent) (= k 1)) (go pr (arg 0) (and formula (not (equal? name "⇡"))))]
    [(and (equal? name "⊘") (= k 0)) (list "[]" 10 "atom")]
    [(and (equal? name "∷") (= k 2))
     (define first (car (go pr (arg 0) #f)))
     (define items (list-loop pr (arg 1) (list first)))
     (list (string-append "[" (string-join* items ", ") "]") 10 "atom")]
    [(and (or (equal? name "∨") (equal? name "∨Ω")) (= k 2))
     (define a (go pr (arg 0) #t))
     (define b (go pr (arg 1) #t))
     (list (string-append (par a 3 '("and")) " or " (par b 2 '("and"))) 2 "or")]
    [(and (or (equal? name "∧") (equal? name "∧Ω")) (= k 2))
     (define a (go pr (arg 0) #t))
     (define b (go pr (arg 1) #t))
     (list (string-append (par a 4 '()) " and " (par b 3 '())) 3 "and")]
    [(and (or (equal? name "¬") (equal? name "¬Ω")) (= k 1))
     (define a (go pr (arg 0) #t))
     (list (string-append "not " (par a 4 '())) 4 "not")]
    [else
     (define sub (and (member name formula-args) #t))
     (define entry (rev-entry pr name))
     (define h (if entry (entry-hum entry) name))
     (define role (if entry (entry-role entry) "value"))
     (define prec (or (and entry (entry-prec entry)) 0))
     (cond
       [(and (member role '("infixl" "infixr" "infix")) (= k 2))
        (define a (go pr (arg 0) sub))
        (define b (go pr (arg 1) sub))
        (define-values (ln rn)
          (cond [(equal? h "^") (values 10 prec)]
                [(equal? role "infixl") (values prec (if (member h assoc-ops) prec (+ prec 1)))]
                [(equal? role "infixr") (values (+ prec 1) prec)]
                [else (values (+ prec 1) (+ prec 1))]))
        (define sep (if (member h tight) h (string-append " " h " ")))
        (list (string-append (par a ln '()) sep (par b rn '())) prec "op")]
       [(and (equal? role "prefix") (= k 1))
        (define a (go pr (arg 0) sub))
        (define x0 (par a prec '()))
        (define x (if (and (equal? h "-") (starts-with? x0 "-")) (string-append "(" (car a) ")") x0))
        (define first-alpha (and (> (string-length h) 0) (let ([c (string-ref h 0)]) (or (char-alphabetic? c)))))
        (list (if first-alpha (string-append h " " x) (string-append h x)) prec "op")]
       [(and (= k 0) (equal? role "value")) (list h 10 "atom")]
       [(not (equal? role "value")) (print-err (format "~a applied to ~a argument(s) has no human spelling" h k))]
       [else
        (define as (for/list ([a (in-list args)]) (car (go pr a sub))))
        (list (string-append h "(" (string-join* as ", ") ")") 10 "atom")])]))

(define (list-loop pr rest acc0)
  (define (bad) (print-err "a list code that does not end in ⊘"))
  (let loop ([cur rest] [acc acc0])
    (define n (node-of pr cur))
    (cond
      [(and (pair? n) (eq? (car n) 'S)) (if (equal? (symbol-name pr (cadr n)) "⊘") acc (bad))]
      [(and (pair? n) (eq? (car n) 'A))
       (define n2 (node-of pr (cadr n)))
       (cond
         [(and (pair? n2) (eq? (car n2) 'A))
          (define n3 (node-of pr (cadr n2)))
          (cond
            [(and (pair? n3) (eq? (car n3) 'S))
             (if (equal? (symbol-name pr (cadr n3)) "∷")
                 (loop (caddr n) (append acc (list (car (go pr (caddr n2) #f)))))
                 (bad))]
            [else (bad)])]
         [else (bad)])]
      [else (bad)])))

(define (spell pr v) (car (go pr v #t)))

;; the spec term of a human statement, read in the program's context (unknowns declared): the checker chooses ≐ or ≐ᴿ, inserts ⇡ and prop, and
;; marks statements — the marks are dropped, the term is what a reader of the output reads back
(define (reread pr text)
  (define c (chk pr))
  (define term
    (with-handlers ([(host-err-of? 'parse) (lambda (e) (print-err (format "the statement ~a cannot be read in the human notation (~a)" (py-repr text) (host-err-msg e))))])
      (let ([ts (lex-hum text)])
        (let-values ([(term rest) (hum-expr (program-hum (printer-p pr)) ts 0 (set))])
          (when (pair? rest) (parse-err (string-append "unexpected " (show-tok (car rest)))))
          term))))
  (define r (with-handlers ([class-err? (lambda (e) e)]) (synth c '() term)))
  (cond
    [(class-err? r) (print-err (format "the statement ~a does not read back in this program: ~a" (py-repr text) (class-err-msg r)))]
    [else
     (define fitted (fit c (cdr r) (car r) prop-ty))
     (if fitted
         (pp-term (strip-quotes fitted))
         (print-err (format "~a reads back as a ~a, not as a statement" (py-repr text) (show-type (car r)))))]))

(define (statement-text pr v)
  (define text (spell pr v))
  (if (is-hum? pr) text (reread pr text)))

(define (number-text pr v cls)
  (define m (mach pr))
  (cond
    [(is-hum? pr)
     (text-of pr (call-th pr (if (leq (chk pr) cls (kk "ℚ")) "showq" "showc") (vector v)))]
    [else
     (define canon (call-th pr "⊜" (vector v)))
     (define-values (z mm) (to-pair m canon))
     (define zt (digits-str pr z))
     (define mt (digits-str pr mm))
     (if (equal? mt "1") zt (format "(÷ ~a ~a)" zt mt))]))

;; the normal-form term of v (of class raw) in spec or hum notation (bin is spelled from spec)
(define (term-of pr v raw)
  (define c (chk pr))
  (define m (mach pr))
  (define hum (is-hum? pr))
  (define cls (norm c raw))
  (unless (K? cls) (print-err (format "cannot print a value whose class is not known (~a)" (show-type raw))))
  (define hd (K-name cls))
  (define args (K-args cls))
  (cond
    [(equal? cls prop-ty) (statement-text pr v)]
    [(or (is-class? pr raw "𝕊") (and (equal? hd "𝔏") (pair? args) (equal? (norm c (car args)) (kk "𝕮"))))
     (string-append "\"" (esc #\" (text-of pr v)) "\"")]
    [(leq c raw (kk "𝕮")) (string-append "'" (esc #\' (cp->string (char-of pr v))) "'")]
    [(leq c raw num-ty) (number-text pr v raw)]
    [(equal? hd "𝔹")
     (define b (boolean-of pr v))
     (cond [hum (if b "true" "false")] [b "⊤"] [else "⊥"])]
    [(equal? hd "𝔒")
     (define k (to-ord m v))
     (list-ref (if hum '("less" "same" "greater") '("⋖" "≖" "⋗")) (min k 2))]
    [(equal? hd "𝔏")
     (define el (car args))
     (cell-of pr v)
     (cond
       [(and (equal? (norm c el) bool-ty) (not hum)) (format "(◀ ~a)" (digits-str pr v))]
       [else
        (define items
          (let loop ([cell (cell-of pr v)] [acc '()])
            (if (eq? cell 'VNil)
                (reverse acc)
                (let ([x (term-of pr (vcons-h cell) el)]) (loop (cell-of pr (vcons-t cell)) (cons x acc))))))
        (if hum
            (string-append "[" (string-join* items ", ") "]")
            (for/fold ([out "⊘"]) ([x (in-list (reverse items))]) (format "(∷ ~a ~a)" x out)))])]
    [(equal? hd "𝔓")
     (define-values (a b) (to-pair m v))
     (define x (term-of pr a (car args)))
     (define y (term-of pr b (cadr args)))
     (if hum (format "pair(~a, ~a)" x y) (format "(⊗ ~a ~a)" x y))]
    [(equal? hd "𝔗")
     (define-values (tag body) (to-pair m v))
     (cond
       [(to-bool m tag)
        (define-values (a b) (to-pair m body))
        (define x (term-of pr a cls))
        (define y (term-of pr b cls))
        (if hum (format "node(~a, ~a)" x y) (format "(❁ ~a ~a)" x y))]
       [else
        (define x (term-of pr body (car args)))
        (if hum (format "leaf(~a)" x) (format "(❀ ~a)" x))])]
    [(equal? hd "𝔖") (term-of pr (stream-nth m v (printer-n pr)) (car args))]
    [(or (equal? hd "→") (equal? hd "𝔄")) (print-err (format "a value of class ~a has no normal form to print (it is a function)" (show-type raw)))]
    [else (print-err (format "cannot print a value of class ~a" (show-type raw)))]))

;; the language value of a small natural number, built from its digits (the reader's numeral expansion)
(define (lit pr k)
  (define m (mach pr))
  (call-g m "⊗" (vector (list-value m (to-digits (cons k 0))) (list-value m (vector 1)))))

;; the remark printed after a stream element (none in bin: the binary notation has no comments)
(define (comment pr v cls0)
  (define c (chk pr))
  (define m (mach pr))
  (define cls (norm c cls0))
  (cond
    [(and (K? cls) (equal? (K-name cls) "𝔖") (= (length (K-args cls)) 1) (not (equal? (printer-mode pr) "bin")))
     (define el (car (K-args cls)))
     (define mark (if (is-hum? pr) "--" "⍝"))
     (define approx
       (cond
         [(leq c el num-ty)
          (define x (stream-nth m v (printer-n pr)))
          (define re-v (call-th pr "ℜ" (vector x)))
          (define re (text-of pr (call-th pr "decimals" (vector re-v (lit pr 12)))))
          (define im (call-th pr "ℑ" (vector x)))
          (define eq0 (call-th pr "≐" (vector im (lit pr 0))))
          (cond
            [(not (to-bool m eq0))
             (define imt (text-of pr (call-th pr "decimals" (vector im (lit pr 12)))))
             (define stripped (let loop ([k 0]) (if (and (< k (string-length imt)) (char=? (string-ref imt k) #\-)) (loop (+ k 1)) (substring imt k))))
             (format ", ≈ ~a ~a ~a i" re (if (starts-with? imt "-") "-" "+") stripped)]
            [else (format ", ≈ ~a" re)])]
         [else ""]))
     (format "   ~a element ~a of the stream~a" mark (printer-n pr) approx)]
    [else ""]))

(define (show-value pr v cls)
  (define t (term-of pr v cls))
  (define t2 (if (equal? (printer-mode pr) "bin") (spec-term-to-bin t (copy-doc1 (program-doc1 (printer-p pr)))) t))
  (string-append t2 (comment pr v cls)))

;; ---------------------------------------------------------------- main
(define (output-mode p override name)
  (or override (program-out-mode p) (hash-ref (program-notation-of p) name #f) "spec"))

(define (run-main-inner p mode0 n write)
  (define c (program-checker p))
  (define cls (let ([l (hash-ref (checker-sigs c) "main" '())])
                (if (pair? l) (car l) (print-err "this program has no main:  define  main ∶ <class>  (spec),  main in <Class> := …  (hum)"))))
  (define mode (output-mode p mode0 "main"))
  (define v (val p "main"))
  (define pr (printer p mode (or n 10)))
  (define c0 (norm c cls))
  (cond
    [(leq c cls (kk "𝕊"))
     (let loop ([cell (cell-of pr v)])
       (unless (eq? cell 'VNil)
         (write (cp->string (char-of pr (vcons-h cell))))
         (loop (cell-of pr (vcons-t cell)))))
     mode]
    [(and (K? c0) (member (K-name c0) '("𝔏" "𝔖")) (= (length (K-args c0)) 1) (equal? (norm c (car (K-args c0))) (norm c (kk "𝕊"))))
     (let loop ([cell (cell-of pr v)] [k 0])
       (when (and (vcons? cell) (or (not n) (< k n)))
         (let ([s (text-of pr (vcons-h cell))])
           (write (string-append s "\n"))
           (loop (cell-of pr (vcons-t cell)) (+ k 1)))))
     mode]
    [else
     (write (string-append (show-value pr v cls) "\n"))
     mode]))

;; evaluate `main` and write its output; returns the output notation used.  An unknown whose value is needed is reported (kind print), as an
;; undetermined truth value is.
(define (run-main p mode0 n write)
  (with-handlers ([(host-err-of? 'unknown) (lambda (e) (raise (host-err 'print (host-err-msg e))))])
    (run-main-inner p mode0 n write)))
