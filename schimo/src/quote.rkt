#lang racket/base
;; quote.rkt -- the compiler side of statements (port of ocamimo/src/quote.ml and rustimo/src/quote.rs).  A statement — a relation on ℝ[i], a
;; relation or predicate about an unknown, a connective with a statement operand (types.rkt marks them TQuote) — is simplified from DEFINITIONS
;; whenever it is evaluated or output, so its checked term φ is replaced by a term that builds φ's CODE at run time:
;;   numeral / Char / String / closed number or Boolean  (𝔮ⁿ value);  symbol  (𝔮ˢ code);  unknown x  (𝔮ˢ code of x);
;;   application, λ, bound variable  (𝔮ᵃ f a) (𝔮ˡ b) (𝔮ᵛ k);  a variable bound outside φ of class Ω  its value;  prop b, decide φ, ∧Ω …  transparent
;; and the statement becomes  (simplify′ ε⌜⌝ ⌜φ⌝)  where  ε⌜⌝  is one table, for the whole program, of (code, ⌜definition⌝).
(require racket/list racket/match racket/set "base.rkt" "syntax.rkt" "layers.rkt" "types.rkt")
(provide (all-defined-out))

(define unfold '("exp" "sin" "cos" "sinh" "cosh" "log" "atan"))
(define env-name "ε⌜⌝")
(define transparent '("prop" "decide" "code_rd"))

(struct quoter (c defs prelude unknowns stmt))      ; defs: name -> (list params body class); prelude: name -> (cons params body); unknowns: ((name . k) ...); stmt: hash
;; state: the doc 1 table (codes are given in order of first use) and the symbols whose definitions go into the table
(struct qs ([doc #:mutable] [needed #:mutable]))

(define (digits text) (app "↓ᶻ" (list (TNum text))))
(define (nat k) (digits (numeral (to-digits (cons k 0)))))

(define (has-quote? t)
  (match t [(TQuote _ _) #t] [(TApp f args) (or (has-quote? f) (ormap has-quote? args))] [(TLam _ b) (has-quote? b)] [_ #f]))

;; statements of the program, resolved: a list of (cons trusted stmt-or-#f)
(define (mk-quoter c sts d0)
  (define defs (make-hash))
  (define prelude (make-hash))
  (for ([e (in-list sts)])
    (define st (cdr e))
    (when (SDef? st)
      (define n (SDef-name st))
      (cond
        [(not (car e))
         (define cls (let ([l (hash-ref (checker-sigs c) n '())]) (if (pair? l) (car l) (kk "?"))))
         (hash-set! defs n (list (SDef-params st) (SDef-body st) cls))]
        [(member n unfold) (hash-set! prelude n (cons (SDef-params st) (SDef-body st)))])))
  (define unknowns (for/list ([u (in-list (checker-unknowns c))] #:when (cdr u)) (cons (car u) (cdr u))))
  (define d1 (copy-doc1 d0))
  (for ([u (in-list unknowns)]) (doc1-code d1 (car u) #t))
  (define stmt (make-hash))
  (for ([(n d) (in-hash defs)]) (when (has-quote? (cadr d)) (hash-set! stmt n #t)))
  (values (quoter c defs prelude unknowns stmt) d1))

(define (q-code st name)
  (define real (let ([e (assoc name conn-o)]) (if e (cdr e) name)))
  (define b (doc1-code (qs-doc st) real #t))
  (digits (substring b 1 (- (string-length b) 1))))

(define (need q st name)
  (when (and (or (hash-has-key? (quoter-defs q) name) (hash-has-key? (quoter-prelude q) name) (assoc name (quoter-unknowns q)))
             (not (member name (qs-needed st))))
    (set-qs-needed! st (append (qs-needed st) (list name)))))

(define (value-class? q c0)
  (and c0
       (let ([c (norm (quoter-c q) c0)])
         (and (K? c) (or (equal? c bool-ty) (leq (quoter-c q) c num-ty))))))

(define (has-rel? q t)
  (match t
    [(TQuote _ _) #t]
    [(TVar n) (or (and (member n rel-r) #t) (conn-o? n) (hash-has-key? (quoter-stmt q) n))]
    [(TApp f args) (or (has-rel? q f) (ormap (lambda (a) (has-rel? q a)) args))]
    [(TLam _ b) (has-rel? q b)]
    [_ #f]))

(define (free-in? t names)
  (match t
    [(TVar n) (set-member? names n)]
    [(TApp f args) (or (free-in? f names) (ormap (lambda (a) (free-in? a names)) args))]
    [(TLam ps b) (free-in? b (for/fold ([r names]) ([p (in-list ps)]) (set-remove r (car p))))]
    [(TQuote e _) (free-in? e names)]
    [_ #f]))

;; the code of a term.  ib: binders inside the quote (innermost last) with their classes; outer: classes of variables bound outside
(define (q-term q st t ib outer typed)
  (define names (map car ib))
  (match t
    [(TQuote e _) (q-term q st e ib outer typed)]
    [(or (TNum _) (TChr _) (TStr _)) (app "𝔮ⁿ" (list t))]
    [(TVar n)
     (define idx (rposition (lambda (m) (equal? m n)) names))
     (cond
       [idx (app "𝔮ᵛ" (list (nat (- (length names) idx))))]
       [(loc-lookup outer n)
        => (lambda (oc)
             (cond
               [(value-class? q oc) (app "𝔮ⁿ" (list t))]
               [(is-prop? (quoter-c q) oc) (app "code_rd" (list t))]
               [else (let ([pos (or (position (lambda (m) (equal? (car m) n)) outer) 0)])
                       (app "𝔮ᵛ" (list (nat (+ (length names) 1 pos)))))]))]
       [(assoc n (quoter-unknowns q))
        (need q st n)
        (app "𝔮ˢ" (list (q-code st n)))]
       [(and typed (not (hash-has-key? (quoter-defs q) n)) (hash-has-key? (checker-sigs (quoter-c q)) n)
             (andmap (lambda (s) (value-class? q s)) (hash-ref (checker-sigs (quoter-c q)) n)))
        (app "𝔮ⁿ" (list t))]
       [else
        (define d (hash-ref (quoter-defs q) n #f))
        (cond
          [(and d (value-class? q (caddr d)) (not (hash-has-key? (quoter-stmt q) n)) (not (unknownish (quoter-c q) n)))
           (app "𝔮ⁿ" (list t))]
          [else
           (need q st n)
           (app "𝔮ˢ" (list (q-code st n)))])])]
    [(TApp f args)
     (define transparent-case
       (and typed
            (match f
              [(TVar fn_) #:when (and (member fn_ transparent) (not (member fn_ names)) (not (loc-member? outer fn_)) (= (length args) 1))
               (list (q-term q st (car args) ib outer typed))]
              [_ #f])))
     (cond
       [transparent-case (car transparent-case)]
       [else
        (define value-case
          (and typed (not (has-rel? q t))
               (let ([nameset (list->set names)])
                 (and (not (free-in? t nameset))
                      (let ([both (set-union (list->set (loc-names outer)) nameset)])
                        (and (not (mentions (quoter-c q) t both))
                             (let* ([loc (for/fold ([l outer]) ([b (in-list ib)]) (loc-insert l (car b) (or (cdr b) 'F)))]
                                    [klass (with-handlers ([class-err? (lambda (e) #f)]) (car (synth (quoter-c q) loc t)))])
                               (and (value-class? q klass) (app "𝔮ⁿ" (list t))))))))))
        (cond
          [value-case value-case]
          [else
           (for/fold ([out (q-term q st f ib outer typed)]) ([a (in-list args)])
             (let ([qa (q-term q st a ib outer typed)]) (app "𝔮ᵃ" (list out qa))))])])]
    [(TLam ps b)
     (define inner (append ib ps))
     (for/fold ([o (q-term q st b inner outer typed)]) ([_ (in-list ps)]) (app "𝔮ˡ" (list o)))]
    [(TAsc _ _) (parse-err "a statement cannot be written as a code: asc")]))

(define (definition-code q st name)
  (cond
    [(assoc name (quoter-unknowns q))
     => (lambda (u)
          (define cd (q-code st "𝔲"))
          (define kn (numeral (to-digits (cons (cdr u) 0))))
          (app "𝔮ᵃ" (list (app "𝔮ˢ" (list cd)) (app "𝔮ⁿ" (list (TNum kn))))))]
    [(hash-ref (quoter-defs q) name #f)
     => (lambda (d)
          (define params (car d))
          (define body (cadr d))
          (define-values (ps _cl)
            (for/fold ([ps '()] [cl (caddr d)] #:result (values (reverse ps) cl)) ([p (in-list params)])
              (match (norm (quoter-c q) cl)
                [(K _ (list a0 a1)) (values (cons (cons p a0) ps) a1)]
                [_ (values (cons (cons p #f) ps) 'F)])))
          (for/fold ([out (q-term q st body ps '() #t)]) ([_ (in-list params)]) (app "𝔮ˡ" (list out))))]
    [(hash-ref (quoter-prelude q) name #f)
     => (lambda (d)
          (define params (car d))
          (define ps (map (lambda (p) (cons p #f)) params))
          (for/fold ([out (q-term q st (cdr d) ps '() #f)]) ([_ (in-list params)]) (app "𝔮ˡ" (list out))))]
    [else (parse-err (format "no definition for ~a to write as a code" name))]))

;; replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝
(define (quote-replace q st t)
  (match t
    [(TQuote e loc) (app "simplify′" (list (var env-name) (q-term q st e '() loc #t)))]
    [(TApp f args)
     (define f2 (quote-replace q st f))
     (TApp f2 (for/list ([a (in-list args)]) (quote-replace q st a)))]
    [(TLam ps b) (TLam ps (quote-replace q st b))]
    [_ t]))

;; the one table of definitions for the whole program
(define (quote-table q st)
  (define entries
    (let loop ([k 0] [acc '()])
      (if (< k (length (qs-needed st)))
          (let* ([name (list-ref (qs-needed st) k)]
                 [cd (q-code st name)]
                 [dc (definition-code q st name)])
            (loop (+ k 1) (cons (cons name (app "⊗" (list cd dc))) acc)))
          (reverse acc))))
  (define unk-names (map car (quoter-unknowns q)))
  (define first-part
    (sort (for*/list ([e (in-list entries)] [i (in-value (position (lambda (u) (equal? u (car e))) unk-names))] #:when i) (cons i (cdr e)))
          < #:key car))
  (define rest (for/list ([e (in-list entries)] #:unless (member (car e) unk-names)) (cdr e)))
  (foldr (lambda (e out) (app "∷" (list e out))) (var "⊘") (append (map cdr first-part) rest)))
