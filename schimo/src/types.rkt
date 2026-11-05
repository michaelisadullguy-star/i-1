#lang racket/base
;; types.rkt -- the class checker of i-1 (port of ocamimo/src/types.ml and rustimo/src/types.rs).
;; Rules: every symbol must be DECLARED (name ∶ class) before it is defined or used; classes are terms (atoms and constructors); a symbol may
;; carry several declarations (overloads); facts (⊆ A B) subclass, (≣ A B) class equation, (↪ f) f is a canonical (widening) coercion; lambda
;; binders must be annotated; numerals get the smallest class containing their value; 'trusted' files (the prelude) have their signatures
;; recorded but their bodies are NOT checked.  A class error is raised as a class-err (the host's own exceptions are host-err).
(require racket/list racket/match racket/set "base.rkt" "syntax.rkt")
(provide (all-defined-out))

(struct class-err (msg))
(define (cerr s) (raise (class-err s)))

(define arrow "→")
(define rel-r '("≐ᴿ" "≠ᴿ" "≺ᴿ" "⩽ᴿ" "≻ᴿ" "⩾ᴿ"))
(define conn-o '(("∧Ω" . "∧") ("∨Ω" . "∨") ("¬Ω" . "¬") ("⇒Ω" . "⇒") ("⇔Ω" . "⇔")))
(define (conn-o? n) (and (assoc n conn-o) #t))
(define (coercion-cost name) (if (equal? name "decide") 2 1))
(define domains '(("ℕ" . 6) ("ℤ" . 5) ("ℚ" . 3) ("ℤ[i]" . 4) ("ℚ[i]" . 2) ("ℝ" . 1) ("ℝ[i]" . 0)))
(define prop-ty (kk "Ω"))
(define bool-ty (kk "𝔹"))
(define num-ty (kk "ℚ[i]"))

(define (flip m) (case m [(pos) 'neg] [(neg) 'pos] [else 'eq]))

;; class variable -> class, small and persistent
(define (subst-get s n) (let ([e (assoc n s)]) (and e (cdr e))))
(define (subst-insert s n t) (if (assoc n s) (map (lambda (e) (if (equal? (car e) n) (cons n t) e)) s) (append s (list (cons n t)))))

(define (chain t)
  (let loop ([t t] [acc '()])
    (match t
      [(K n (list a b)) #:when (equal? n arrow) (loop b (cons a acc))]
      [_ (values (reverse acc) t)])))

(define (mk-chain ps r) (foldr (lambda (p out) (K arrow (list p out))) r ps))

;; the same class, where the flexible class ⊥ equals anything
(define (flex-eq x y)
  (cond
    [(or (equal? x y) (eq? x 'F) (eq? y 'F)) #t]
    [else (match* (x y)
            [((K n xs) (K m ys)) (and (equal? n m) (= (length xs) (length ys)) (andmap flex-eq xs ys))]
            [(_ _) #f])]))

(define (has-var? t) (match t [(V _) #t] [(K _ a) (ormap has-var? a)] [_ #f]))

;; substitute class variables; with flex, the unbound ones become the flexible class ⊥
(define (apply-subst t s flex)
  (match t
    [(V n) (let ([r (subst-get s n)]) (cond [r r] [flex 'F] [else t]))]
    [(K n a) (K n (map (lambda (x) (apply-subst x s flex)) a))]
    [_ 'F]))

(define (comma-sep xs) (string-join* xs ", "))
(define (semi-sep xs) (string-join* xs "; "))

;; the smallest class containing the value of a numeral written in base i-1
(define (num-class text)
  (define k0 (for/first ([i (in-range (string-length text))] #:when (char=? (string-ref text i) #\.)) i))
  (define bits (if k0 (string-append (substring text 0 k0) (substring text (+ k0 1))) text))
  (define k (if k0 (- (string-length text) k0 1) 0))
  (define n (string-length bits))
  (define digits (for/vector #:length n ([i (in-range n)]) (if (char=? (string-ref bits (- n 1 i)) #\1) 1 0)))
  (define z (val-digits digits))
  ;; den = b^k, nn = |den|^2 = 2^k
  (define den (for/fold ([d (cons 1 0)]) ([_ (in-range k)]) (cons (- (+ (car d) (cdr d))) (- (car d) (cdr d)))))
  (define d0 (car den))
  (define d1 (cdr den))
  (define nn (+ (* d0 d0) (* d1 d1)))
  (define re-num (+ (* (car z) d0) (* (cdr z) d1)))
  (define im-num (- (* (cdr z) d0) (* (car z) d1)))
  (define (divisible? x) (zero? (remainder x nn)))
  (cond
    [(zero? im-num) (if (divisible? re-num) (if (>= re-num 0) (kk "ℕ") (kk "ℤ")) (kk "ℚ"))]
    [(and (divisible? re-num) (divisible? im-num)) (kk "ℤ[i]")]
    [else (kk "ℚ[i]")]))

;; ---------------------------------------------------------------- the checker
(struct checker (classes formers sigs [facts #:mutable] [fact-idx #:mutable] eqs [coercions #:mutable] cov defined overloads
                 [unknowns #:mutable] user-defined raw-taint taint))

(define (new-checker)
  (define classes (make-hash))
  (hash-set! classes "→" 2) (hash-set! classes "𝒦" 0) (hash-set! classes "𝒮" 0)
  (define cov (make-hash))
  (for ([s '("𝔏" "𝔖" "𝔗" "𝔓")]) (hash-set! cov s #t))
  (checker classes (make-hash) (make-hash) '() (make-hash) (make-hash) '() cov (make-hash) (make-hash) '() (make-hash) (make-hash) (make-hash)))

;; ------------------------------------------------------------ class terms
(define (term-to-type t)
  (match t
    [(TVar n) (if (class-var? n) (V n) (kk n))]
    [(TApp (TVar n) args) (K n (map term-to-type args))]
    [_ (cerr (string-append "not a class expression: " (repr-term t)))]))

;; ------------------------------------------------------------ classes
(define (norm c t)
  (match t
    [(K n '()) (let ([e (hash-ref (checker-eqs c) n #f)]) (if e (norm c e) t))]
    [(K n a) (K n (map (lambda (x) (norm c x)) a))]
    [_ t]))

(define (wf c t)
  (match t
    [(K name args)
     (define k (hash-ref (checker-classes c) name #f))
     (cond [(not k) (cerr (string-append "undeclared class " name))]
           [(not (= k (length args))) (cerr (format "class ~a takes ~a argument(s), got ~a" name k (length args)))]
           [else (for-each (lambda (a) (wf c a)) args)])]
    [_ (void)]))

(define (leq c a b)
  (define seen '())
  (define (leq-s a0 b0)
    (define a (norm c a0))
    (define b (norm c b0))
    (cond
      [(or (equal? a b) (eq? a 'F)) #t]
      [else
       (define s
         (match* (a b)
           [((K n xs) (K m ys)) #:when (and (equal? n m) (pair? xs) (= (length xs) (length ys)))
            (cond [(equal? n arrow) (and (leq-s (car ys) (car xs)) (leq-s (cadr xs) (cadr ys)))]
                  [(hash-ref (checker-cov c) n #f) (andmap leq-s xs ys)]
                  [else (flex-eq a b)])]
           [(_ _) #f]))
       (cond
         [s #t]
         [else
          (define supers (hash-ref (checker-fact-idx c) a #f))
          (and supers
               (for/or ([y (in-list supers)])
                 (define key (cons a y))
                 (cond
                   [(member key seen) #f]
                   [else (set! seen (cons key seen))
                         (let ([r (leq-s y b)]) (set! seen (cdr seen)) r)])))])]))
  (leq-s a b))

;; a and every class that contains it, by the declared subclass facts
(define (ups c a)
  (let loop ([todo (list (norm c a))] [out '()])
    (cond
      [(null? todo) out]
      [else
       (define x (car todo))
       (cond
         [(member x out) (loop (cdr todo) out)]
         [else
          (define supers (hash-ref (checker-fact-idx c) x '()))
          (loop (append (reverse (map (lambda (y) (norm c y)) supers)) (cdr todo)) (append out (list x)))])])))

;; the least class containing both a and b (e.g. ℤ[i] and ℚ give ℚ[i]); #f if there is none or it is not unique
(define (join c a0 b0)
  (define a (norm c a0))
  (define b (norm c b0))
  (define covcase
    (match* (a b)
      [((K n xs) (K m ys)) #:when (and (equal? n m) (hash-ref (checker-cov c) n #f) (pair? xs) (= (length xs) (length ys)))
       (let ([js (map (lambda (x y) (cond [(leq c y x) x] [(leq c x y) y] [else (join c x y)])) xs ys)])
         (if (andmap values js) (list (K n js)) (list #f)))]
      [(_ _) #f]))
  (cond
    [covcase (car covcase)]
    [else
     (define ub (ups c b))
     (define common (filter (lambda (x) (member x ub)) (ups c a)))
     (define least (filter (lambda (x) (not (ormap (lambda (d) (and (not (equal? d x)) (leq c d x))) common))) common))
     (and (= (length least) 1) (car least))]))

;; ------------------------------------------------------------ matching a pattern against an actual class
(define (first-some f l) (and (pair? l) (or (f (car l)) (first-some f (cdr l)))))

;; returns the new substitution (a list) or #f
(define (do-match c p0 a0 s mode)
  (define p (norm c p0))
  (define a (norm c a0))
  (match p
    [(V pn)
     (define b (subst-get s pn))
     (cond
       [(not b) (subst-insert s pn a)]
       [(eq? a 'F) s]
       [(eq? b 'F) (subst-insert s pn a)]
       [(eq? mode 'eq) (and (flex-eq b a) s)]
       [(leq c a b) s]
       [(leq c b a) (if (eq? mode 'pos) (subst-insert s pn a) s)]
       [(eq? mode 'pos) (let ([j (join c a b)]) (and j (subst-insert s pn j)))]
       [else #f])]
    [_
     (cond
       [(not (has-var? p))
        (cond [(eq? a 'F) s]
              [else (let ([ok (case mode [(pos) (leq c a p)] [(neg) (leq c p a)] [else (flex-eq p a)])]) (and ok s))])]
       [(eq? a 'F) s]
       [else
        (define structural
          (match* (p a)
            [((K pn pas) (K an aas)) #:when (and (equal? pn an) (= (length pas) (length aas)))
             (let loop ([ps pas] [as aas] [i 0] [cur s])
               (cond
                 [(or (null? ps) (not cur)) cur]
                 [else
                  (define m (if (equal? pn arrow) (if (zero? i) (flip mode) mode) (if (hash-ref (checker-cov c) pn #f) mode 'eq)))
                  (loop (cdr ps) (cdr as) (+ i 1) (do-match c (car ps) (car as) cur m))]))]
            [(_ _) #f]))
        (cond
          [structural structural]
          [(eq? mode 'pos)
           (define supers (hash-ref (checker-fact-idx c) a #f))
           (and supers (first-some (lambda (y) (do-match c p y s mode)) supers))]
          [else #f])])]))

;; the domain code of an unknown of class t: the first number class, in the order ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i], that contains t
(define (domain c t0)
  (define t (norm c t0))
  (and (K? t) (not (has-var? t))
       (for/first ([d (in-list domains)] #:when (and (hash-has-key? (checker-classes c) (car d)) (leq c t (kk (car d))))) (cdr d))))

;; is `name` an unknown, or a program symbol whose value needs the value of an unknown?
(define (unknownish c name)
  (cond [(assoc name (checker-unknowns c)) #t]
        [else (let ([b (hash-ref (checker-taint c) name 'none)])
                (if (eq? b 'none) (hash-has-key? (checker-raw-taint c) name) b))]))

;; does the (checked) term t mention an unknown (or a symbol that needs one) — outside quoted statements?  bound: a set of names
(define (mentions c t bound)
  (match t
    [(TVar n) (and (not (set-member? bound n)) (unknownish c n))]
    [(TApp f args) (or (mentions c f bound) (ormap (lambda (a) (mentions c a bound)) args))]
    [(TLam ps b) (mentions c b (for/fold ([bd bound]) ([p (in-list ps)]) (set-add bd (car p))))]
    [_ #f]))

(define (is-prop? c t) (equal? (norm c t) prop-ty))

;; ------------------------------------------------------------ declarations and facts
(define (declare c name t)
  (define-values (ps r) (chain t))
  (cond
    [(equal? r (kk "𝒦"))
     (when (ormap (lambda (p) (not (equal? p (kk "𝒦")))) ps) (cerr (string-append name ": a class constructor takes classes only")))
     (hash-set! (checker-classes c) name (length ps))]
    [(equal? r (kk "𝒮")) (hash-set! (checker-formers c) name #t)]
    [else
     (wf c t)
     (define old (hash-ref (checker-sigs c) name '()))
     (hash-set! (checker-sigs c) name (if (member t old) old (append old (list t))))]))

(define (reindex c)
  (define idx (make-hash))
  (for ([f (in-list (checker-facts c))])
    (define k (norm c (car f)))
    (hash-set! idx k (append (hash-ref idx k '()) (list (cdr f)))))
  (set-checker-fact-idx! c idx))

;; a declared statement: raises class-err for class errors, host-err for the exceptions of the host
(define (fact c term)
  (match term
    [(TApp (TVar h) args) #:when (hash-ref (checker-formers c) h #f)
     (define (arg i) (if (< i (length args)) (list-ref args i) (parse-err "Prelude.!!: index too large")))
     (cond
       [(or (equal? h "⊆") (equal? h "≣"))
        (define a0 (arg 0))
        (define b0 (arg 1))
        (define a (term-to-type a0))
        (define b (term-to-type b0))
        (wf c a)
        (wf c b)
        (cond
          [(equal? h "⊆") (set-checker-facts! c (append (checker-facts c) (list (cons a b)))) (reindex c)]
          [else (match a
                  [(K n '()) (hash-set! (checker-eqs c) n b) (reindex c)]
                  [_ (parse-err "class equation: left side must be an atomic class")])])]
       [(equal? h "↗")
        (match args
          [(cons (TVar n) _)
           (if (>= (hash-ref (checker-classes c) n 0) 1)
               (hash-set! (checker-cov c) n #t)
               (cerr (format "covariant: ~a is not a class constructor" n)))]
          [_ (cerr "covariant:  is not a class constructor")])]
       [(equal? h "↪")
        (match args
          [(cons (TVar f) _)
           (if (hash-has-key? (checker-sigs c) f)
               (set-checker-coercions! c (append (checker-coercions c) (list f)))
               (cerr (format "coercion ~a is not declared" f)))]
          [_ (cerr "coercion  is not declared")])]
       [else (cerr (string-append "unknown statement " h))])]
    [_ (cerr (string-append "not a declared statement: " (repr-term term)))]))

;; ------------------------------------------------------------ terms
;; candidate (symbol . class) pairs for a head symbol
(define (entries-for c hd)
  (define names (hash-ref (checker-overloads c) hd (list hd)))
  (apply append
         (for/list ([n (in-list names)])
           (define es (hash-ref (checker-sigs c) n #f))
           (unless es (cerr (string-append "undeclared symbol " n)))
           (map (lambda (e) (cons n e)) es))))

(define (sigs-of c cn) (hash-ref (checker-sigs c) cn '()))

(define (best-coercion c p a-ty s)
  (define best #f)   ; (list name class subst)
  (for ([cn (in-list (checker-coercions c))])
    (for ([ce (in-list (sigs-of c cn))])
      (define-values (cps cr) (chain ce))
      (when (and (= (length cps) 1) (leq c a-ty (car cps)))
        (define s1 (do-match c p (apply-subst cr '() #f) s 'pos))
        (when s1
          (set! best (if (not best) (list cn cr s1) (if (leq c cr (cadr best)) (list cn cr s1) best)))))))
  (and best (cons (car best) (caddr best))))

;; apply a class `entry` to args [(class . term)].  -> (list result-class new-args cost) or #f
(define (try-apply c entry args)
  (let loop ([t entry] [s '()] [cost 0] [nw '()] [args args])
    (cond
      [(null? args) (list (apply-subst t s #t) (reverse nw) cost)]
      [else
       (define a-ty (car (car args)))
       (define term (cdr (car args)))
       (match (norm c t)
         [(K n (list p r)) #:when (equal? n arrow)
          (define s2 (do-match c p a-ty s 'pos))
          (cond
            [s2 (loop r s2 cost (cons term nw) (cdr args))]
            [else
             (define bc (best-coercion c p a-ty s))
             (and bc (loop r (cdr bc) (+ cost (coercion-cost (car bc))) (cons (TApp (var (car bc)) (list term)) nw) (cdr args)))])]
         [_ #f])])))

(define (resolve-app c hd args label)
  (define ents (entries-for c hd))
  (define cands
    (for*/list ([e (in-list ents)] [r (in-value (try-apply c (cdr e) args))] #:when r) (list (car e) (cdr e) r)))
  (when (null? cands)
    (cerr (format "no declaration of ~a accepts (~a);  candidates: ~a" label
                  (comma-sep (map (lambda (a) (show-type (car a))) args))
                  (comma-sep (map (lambda (e) (string-append (car e) " ∶ " (show-type (cdr e)))) ents)))))
  (define cost-of (lambda (cd) (caddr (caddr cd))))
  (define mn (apply min (map cost-of cands)))
  (define cands2 (filter (lambda (cd) (= (cost-of cd) mn)) cands))
  (define (more-specific x y)
    (define-values (p1 _1) (chain (cadr x)))
    (define-values (p2 _2) (chain (cadr y)))
    (define n (min (length args) (length p1) (length p2)))
    (andmap (lambda (a b) (leq c a b)) (take* n p1) (take* n p2)))
  (define best (filter (lambda (x) (andmap (lambda (y) (more-specific x y)) cands2)) cands2))
  (define pool (if (null? best) cands2 best))
  (unless (= (length best) 1)
    (define sigs (remove-duplicates (map (lambda (cd) (cons (car cd) (car (caddr cd)))) pool)))
    (unless (= (length sigs) 1)
      (cerr (format "ambiguous use of ~a: ~a" label
                    (semi-sep (map (lambda (cd) (string-append (car cd) " ∶ " (show-type (cadr cd)))) cands2))))))
  (define cd (car pool))
  (values (car cd) (car (caddr cd)) (cadr (caddr cd))))

;; the checked application (name new…) of class rt — marked as a quoted statement (class Ω) when it is one
(define (statement-of c loc name rt nw)
  (define app-t (TApp (var name) nw))
  (define bound (list->set (loc-names loc)))
  (define r (norm c rt))
  (cond
    [(and (member name rel-r) (= (length nw) 2)) (cons prop-ty (TQuote app-t loc))]
    [(and (conn-o? name) (is-prop? c rt)) (cons prop-ty (TQuote app-t loc))]
    [(and (or (equal? r prop-ty) (equal? r bool-ty)) (ormap (lambda (a) (mentions c a bound)) nw)) (cons prop-ty (TQuote app-t loc))]
    [else (cons rt app-t)]))

;; returns (cons class term)
(define (synth c loc t)
  (match t
    [(TNum s) (cons (num-class s) t)]
    [(TChr _) (cons (kk "𝕮") t)]
    [(TStr _) (cons (kk "𝕊") t)]
    [(TVar n)
     (define ty (loc-lookup loc n))
     (cond
       [ty (cons ty t)]
       [else
        (define ents (entries-for c n))
        (if (= (length ents) 1)
            (cons (apply-subst (cdr (car ents)) '() #t) (var (car (car ents))))
            (cerr (format "~a is overloaded (~a declarations): use it applied to arguments" n (length ents))))])]
    [(TAsc e ty)
     (wf c ty)
     (define r (synth c loc e))
     (define fixed (fit c (cdr r) (car r) ty))
     (if fixed (cons ty fixed) (cerr (format "ascription: a term of class ~a is not in ~a" (show-type (car r)) (show-type ty))))]
    [(TLam ps body)
     (define-values (loc2 ptys)
       (for/fold ([l loc] [pt '()] #:result (values l (reverse pt))) ([p (in-list ps)])
         (define n (car p))
         (define mty (cdr p))
         (unless mty (cerr (format "binder ~a has no class: write (~a ∶ class ↦ …)" n n)))
         (wf c mty)
         (values (loc-insert l n mty) (cons mty pt))))
     (define r (synth c loc2 body))
     (cons (mk-chain ptys (car r)) (TLam ps (cdr r)))]
    [(TQuote _ _) (cons prop-ty t)]
    [(TApp f as)
     (define args (for/list ([a (in-list as)]) (synth c loc a)))
     (match f
       [(TVar h) #:when (not (loc-member? loc h))
        (define r
          (with-handlers ([class-err? (lambda (e) e)])
            (let-values ([(name rt nw) (resolve-app c h args h)]) (list name rt nw))))
        (cond
          [(class-err? r)
           (define j (join-list c loc t))
           (if j j (raise r))]
          [else (statement-of c loc (car r) (cadr r) (caddr r))])]
       [_
        (define ft+term (synth c loc f))
        (define res (try-apply c (car ft+term) args))
        (if res
            (cons (car res) (TApp (cdr ft+term) (cadr res)))
            (cerr (format "cannot apply a function of class ~a to (~a)" (show-type (car ft+term)) (comma-sep (map (lambda (a) (show-type (car a))) args)))))])]))

;; a cons chain (a list literal) whose elements are truth values and statements is a list of statements: the truth values are made
;; statements (prop).  #f when that is not the case.
(define (join-list c loc t)
  (define-values (items tl)
    (let loop ([tl t] [items '()])
      (match tl
        [(TApp (TVar h) (list x0 x1)) #:when (and (or (equal? h "∷") (equal? h "hum:cons")) (not (loc-member? loc h)))
         (loop x1 (cons x0 items))]
        [_ (values (reverse items) tl)])))
  (cond
    [(or (null? items) (not (hash-has-key? (checker-sigs c) "∷"))) #f]
    [else
     (define el (for/list ([x (in-list items)]) (synth c loc x)))
     (define tc+tt (synth c loc tl))
     (define tc (car tc+tt))
     (define list-prop (K "𝔏" (list prop-ty)))
     (cond
       [(or (not (or (ormap (lambda (e) (is-prop? c (car e))) el) (equal? (norm c tc) list-prop))) (not (leq c tc list-prop))) #f]
       [else
        ;; build from the last element outwards
        (define out
          (for/fold ([out (cdr tc+tt)]) ([e (in-list (reverse el))])
            (and out
                 (let ([cl (car e)] [x (cdr e)])
                   (cond [(is-prop? c cl) (TApp (var "∷") (list x out))]
                         [(leq c cl bool-ty) (TApp (var "∷") (list (TApp (var "prop") (list x)) out))]
                         [else #f])))))
        (and out (cons list-prop out))])]))

;; term (of class got) made to fit the class want: as it is, through one coercion, element by element for a list or pair literal, or — for a λ —
;; by fitting its body.  #f when it does not fit.
(define (fit c term got want)
  (cond
    [(leq c got want) term]
    [else
     (define g (norm c got))
     (define w (norm c want))
     ;; through one coercion (the last one that fits wins)
     (define via
       (for*/fold ([via #f]) ([cn (in-list (checker-coercions c))] [ce (in-list (sigs-of c cn))])
         (define-values (cps cr) (chain ce))
         (if (and (= (length cps) 1) (leq c got (car cps)) (leq c cr want)) (TApp (var cn) (list term)) via)))
     (cond
       [via via]
       [(and (equal? term (var "⊘")) (K? w) (equal? (K-name w) "𝔏")) term]
       [else
        ;; a list or pair literal, element by element
        (define lit
          (match* (term g w)
            [((TApp (TVar h) (list a0 a1)) (K gn gargs) (K wn wargs)) #:when (equal? gn wn)
             (or (and (equal? h "∷") (equal? gn "𝔏")
                      (let ([h2 (fit c a0 (car gargs) (car wargs))])
                        (and h2 (let ([t2 (fit c a1 got want)]) (and t2 (TApp (var "∷") (list h2 t2)))))))
                 (and (equal? h "⊗") (equal? gn "𝔓")
                      (let ([x (fit c a0 (car gargs) (car wargs))])
                        (and x (let ([y (fit c a1 (cadr gargs) (cadr wargs))]) (and y (TApp (var "⊗") (list x y))))))))]
            [(_ _ _) #f]))
        (cond
          [lit lit]
          [(TLam? term)
           (define ps (TLam-ps term))
           (define n (length ps))
           (define-values (pg rg) (chain g))
           (define-values (pw rw) (chain w))
           (and (>= (length pg) n) (>= (length pw) n) (andmap (lambda (x y) (leq c y x)) (take* n pg) (take* n pw))
                (let ([nb (fit c (TLam-body term) (mk-chain (drop* n pg) rg) (mk-chain (drop* n pw) rw))])
                  (and nb (TLam ps nb))))]
          [else #f])])]))

;; after checking: which program symbols need the value of an unknown (the least fixed point over their checked bodies)
(define (settle-taint c defs)
  (hash-clear! (checker-taint c))
  (for ([d (in-list defs)]) (hash-set! (checker-taint c) (car d) #f))
  (let loop ()
    (define changed #f)
    (for ([d (in-list defs)])
      (unless (hash-ref (checker-taint c) (car d) #f)
        (when (mentions c (caddr d) (list->set (cadr d)))
          (hash-set! (checker-taint c) (car d) #t)
          (set! changed #t))))
    (when changed (loop))))

(define (check-entry c name params body entry)
  (define-values (ps r) (chain entry))
  (when (> (length params) (length ps))
    (cerr (format "~a has ~a parameters but its class ~a has only ~a" name (length params) (show-type entry) (length ps))))
  (define loc (for/fold ([l '()]) ([p (in-list params)] [i (in-naturals)]) (loc-insert l p (list-ref ps i))))
  (define want (mk-chain (drop* (length params) ps) r))
  (define got+nb (synth c loc body))
  (define fixed (fit c (cdr got+nb) (car got+nb) want))
  (unless fixed (cerr (format "~a: the body has class ~a but ~a was declared" name (show-type (car got+nb)) (show-type want))))
  fixed)

;; ------------------------------------------------------------ statements
;; check one statement; the checker keeps the effects it has before an error and the resolved statement is returned (#f: the statement is as it was
;; written).  Class errors are raised as class-err, exceptions of the host as host-err.
(define (check-statement c st trusted)
  (match st
    [(SDecl name ty)
     (declare c name ty)
     (cond
       [(and (not trusted) (assoc name (checker-unknowns c)))
        (when (> (length (sigs-of c name)) 1)
          (cerr (format "~a is declared but never defined, so it is an unknown, and an unknown has one class" name)))
        (define k (domain c ty))
        (unless k
          (cerr (format "~a is declared but never defined, so it is an unknown; an unknown must be a number (a class below ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i] — human \\NN \\ZZ \\QQ \\Z \\Q \\RR \\CC), not ~a"
                        name (show-type ty))))
        (set-checker-unknowns! c (map (lambda (u) (if (equal? (car u) name) (cons (car u) k) u)) (checker-unknowns c)))
        #f]
       [else #f])]
    [(SFact t) (fact c t) #f]
    [(SDef name params body)
     (when (hash-has-key? (checker-defined c) name) (cerr (format "~a is defined twice" name)))
     (unless (hash-has-key? (checker-sigs c) name) (cerr (format "~a is defined before it is declared:  write  ~a ∶ <class>  first" name name)))
     (hash-set! (checker-defined c) name #t)
     (cond
       [trusted #f]
       [else
        (define entries (sigs-of c name))
        (define out #f)
        (for ([entry (in-list entries)])
          (define newbody (check-entry c name params body entry))
          (unless out
            (hash-set! (checker-taint c) name (mentions c newbody (list->set params)))
            (set! out (SDef name params newbody))))
        (or out (cerr "no declaration"))])]))
