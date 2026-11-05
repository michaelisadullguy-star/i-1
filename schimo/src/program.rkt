#lang racket/base
;; program.rkt -- loader / driver for i-1 programs (port of ocamimo/src/program.ml and rustimo/src/program.rs).
;; A file is read in the notation chosen by its extension (x.bin.imo, x.hum.imo, x.imo = spec) or by section headers (@bin @spec @hum on a line of
;; their own).  Every section is translated to spec statements, the whole program is checked by the class checker, and the definitions are run
;; by the evaluator (lazy, call-by-need).  A symbol that the program declares and never defines is an UNKNOWN: its class must be a number class.
(require racket/list racket/match racket/set racket/file
         "base.rkt" "syntax.rkt" "layers.rkt" "hum.rkt" "types.rkt" "quote.rkt" "core.rkt" "data-gen.rkt")
(provide (all-defined-out))

(struct program (
  [doc1 #:mutable] doc2 hum
  [statements #:mutable]      ; a vector of (vector file stmt trusted)
  checker
  [resolved #:mutable]        ; a vector aligned with `statements` (#f: the statement had an error)
  [errors #:mutable]          ; a list of (list file what message)
  notation-of                 ; defined symbol -> the notation of the section that defines it
  [out-mode #:mutable]
  [pre-count #:mutable]       ; the number of statements that came from the embedded prelude (they are first, and trusted)
  [user-defs #:mutable]       ; the definitions of the program itself, erased to de Bruijn terms: a list of (cons name core)
  defined                     ; every name that is defined (prelude and program)
  [machine #:mutable]))

(struct source-file (path text))

(define (new-program)
  (define d1 (doc1-parse data-doc1))
  (define d2 (doc2-remap (doc2-parse data-doc2) d1))
  (define checker (new-checker))
  (for ([(k v) (in-hash (overload-table d2))]) (hash-set! (checker-overloads checker) k v))
  (program d1 d2 (mk-hum d2) (vector) checker (vector) '() (make-hash) #f 0 '() (make-hash) #f))

;; add the text of a file (or of a string) in the given default notation
(define (add-text! p text name trusted notation)
  (define out-mode (program-out-mode p))
  (define lines
    (for/list ([ln (in-list (split-on text "\n"))])
      (define words (split-ws ln))
      (cond
        [(and (= (length words) 2) (equal? (car words) "@out"))
         (define w (cadr words))
         (cond [(member w '("bin" "spec" "hum")) (set! out-mode w) ""]
               [else (parse-err (format "~a: @out takes bin, spec or hum, not ~a" name w))])]
        [else ln])))
  (define text2 (string-join* lines "\n"))
  (set-program-out-mode! p out-mode)
  (for ([sec (in-list (split-sections text2 notation))])
    (define mode (car sec))
    (define chunk (cdr sec))
    (define sts
      (cond [(equal? mode "spec") (parse-statements chunk)]
            [(equal? mode "bin") (parse-statements (bin-to-spec-text chunk (program-doc1 p)))]
            [else (hum-statements (program-hum p) chunk)]))
    (unless trusted (for ([st (in-list sts)]) (when (SDef? st) (hash-set! (program-notation-of p) (SDef-name st) mode))))
    (set-program-statements! p (vector-append* (program-statements p) (for/vector ([st (in-list sts)]) (vector name st trusted))))))

(define (vector-append* a b)
  (define r (make-vector (+ (vector-length a) (vector-length b)) #f))
  (vector-copy! r 0 a)
  (vector-copy! r (vector-length a) b)
  r)

;; add a file; a bin program brings its local symbol table (x.sbl next to x.bin.imo)
(define (add-file! p f trusted)
  (define path (source-file-path f))
  (define text (source-file-text f))
  (define k (rfind-sub path ".imo"))
  (define before (if k (substring path 0 k) path))
  (define (replace-all s a b) (string-join* (split-on s a) b))
  (define local (string-append (replace-all (replace-all (replace-all before ".bin" "") ".hum" "") ".spec" "") ".sbl"))
  (define uses-bin (or (equal? (default-notation path) "bin") (contains-sub? (string-append "\n" text) "\n@bin")))
  (when (and uses-bin (file-exists? local))
    (define tbl (with-handlers ([bad-utf8? (lambda (e) (raise (host-err 'parse (format "~a: ~a" local (bad-utf8-msg e)))))]) (read-utf8 local)))
    (for ([line (in-list (split-on tbl "\n"))])
      (when (and (contains-sub? line " := ") (not (starts-with? line "⍝")))
        (define parts (split-on line " := "))
        (unless (= (length parts) 2) (parse-err (format "bad line in ~a" (basename local))))
        (define a (strip (car parts)))
        (define b (strip (cadr parts)))
        (unless (hash-has-key? (doc1-s2b (program-doc1 p)) a)
          (define other (hash-ref (doc1-b2s (program-doc1 p)) b #f))
          (when other
            (parse-err (format "~a: local code ~a for ~a is already doc 1's code for ~a (doc 1 grew: regenerate the local table with  i1.py translate … --to bin)"
                               (basename local) b a other)))
          (doc1-add-local (program-doc1 p) a b)))))
  (add-text! p text path trusted (default-notation path)))

;; ------------------------------------------------------------ checking
(define (class-or-stmt? ty)
  (define r (let loop ([t ty]) (match t [(K n (list _ b)) #:when (equal? n "→") (loop b)] [_ t])))
  (or (equal? r (kk "𝒦")) (equal? r (kk "𝒮"))))

(define (refs t bound overloads)
  (match t
    [(TVar n) (cond [(set-member? bound n) (set)]
                    [(hash-ref overloads n #f) => list->set]
                    [else (set n)])]
    [(TApp f args) (for/fold ([s (refs f bound overloads)]) ([a (in-list args)]) (set-union s (refs a bound overloads)))]
    [(TLam ps b) (refs b (for/fold ([bd bound]) ([p (in-list ps)]) (set-add bd (car p))) overloads)]
    [(TAsc e _) (refs e bound overloads)]
    [_ (set)]))

;; the unknowns (declared by the program, defined nowhere), in declaration order, and a first estimate of which program definitions need their values
(define (unknowns-of! c stmts)
  (define defined (make-hash))
  (for ([e (in-vector stmts)]) (let ([s (vector-ref e 1)]) (when (SDef? s) (hash-set! defined (SDef-name s) #t))))
  (define seen (make-hash))
  (define order
    (reverse
     (for/fold ([acc '()]) ([e (in-vector stmts)])
       (define s (vector-ref e 1))
       (cond
         [(and (SDecl? s) (not (vector-ref e 2)))
          (define n (SDecl-name s))
          (cond [(or (hash-has-key? defined n) (class-or-stmt? (SDecl-ty s))) acc]
                [(hash-has-key? seen n) acc]
                [else (hash-set! seen n #t) (cons n acc)])]
         [else acc]))))
  (define user (for/list ([e (in-vector stmts)] #:when (and (SDef? (vector-ref e 1)) (not (vector-ref e 2)))) (vector-ref e 1)))
  (define uses (make-hash))
  (for ([d (in-list user)]) (hash-set! uses (SDef-name d) (refs (SDef-body d) (list->set (SDef-params d)) (checker-overloads c))))
  (define tainted
    (let loop ([tainted (list->set order)])
      (define nw (for/list ([(n u) (in-hash uses)] #:when (and (not (set-member? tainted n)) (for/or ([x (in-set u)]) (set-member? tainted x)))) n))
      (if (null? nw) tainted (loop (for/fold ([t tainted]) ([n (in-list nw)]) (set-add t n))))))
  (define order-set (list->set order))
  (set-checker-unknowns! c (map (lambda (n) (cons n #f)) order))
  (hash-clear! (checker-user-defined c))
  (for ([d (in-list user)]) (hash-set! (checker-user-defined c) (SDef-name d) #t))
  (hash-clear! (checker-raw-taint c))
  (for ([n (in-set tainted)]) (unless (set-member? order-set n) (hash-set! (checker-raw-taint c) n #t)))
  (hash-clear! (checker-taint c)))

;; program-local codes (doc 1 format) for the program's own symbols, assigned when the program is checked and in a fixed order
(define (codes-of! p)
  (define order
    (append (map car (checker-unknowns (program-checker p)))
            (for/list ([e (in-vector (program-statements p))]
                       #:when (let ([s (vector-ref e 1)])
                                (and (SDecl? s) (not (vector-ref e 2)) (not (equal? (SDecl-name s) env-name)) (hash-has-key? (checker-sigs (program-checker p)) (SDecl-name s)))))
              (SDecl-name (vector-ref e 1)))))
  (for ([n (in-list order)]) (doc1-code (program-doc1 p) n #t)))

;; replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝  and add the table of definitions
(define (quote-program! p)
  (define sts (for/list ([e (in-vector (program-statements p))] [r (in-vector (program-resolved p))]) (cons (vector-ref e 2) r)))
  (define-values (qr d1) (mk-quoter (program-checker p) sts (program-doc1 p)))
  (define st (qs d1 '()))
  (define replaced
    (for/list ([r (in-vector (program-resolved p))] [i (in-naturals)] #:when (and (SDef? r) (has-quote? (SDef-body r))))
      (cons i (SDef (SDef-name r) (SDef-params r) (quote-replace qr st (SDef-body r))))))
  (define tab (quote-table qr st))
  (for ([e (in-list replaced)]) (vector-set! (program-resolved p) (car e) (cdr e)))
  (set-program-doc1! p (qs-doc st))
  (define env-ty (K "𝔏" (list (K "𝔓" (list (kk "𝔇") (kk "𝔔"))))))
  (with-handlers ([class-err? (lambda (e) (eval-err (format "quote: ε⌜⌝ declaration: ~a" (class-err-msg e))))])
    (declare (program-checker p) env-name env-ty))
  (define at (let loop ([i 0]) (if (and (< i (vector-length (program-statements p))) (vector-ref (vector-ref (program-statements p) i) 2)) (loop (+ i 1)) i)))
  (define decl-st (SDecl env-name env-ty))
  (define def-st (SDef env-name '() tab))
  (define (ins arr x) (vector-append* (vector-append* (vector-copy* arr at) (vector x)) (vector-drop* arr at)))
  (set-program-statements! p (ins (ins (program-statements p) (vector "<quote>" def-st #f)) (vector "<quote>" decl-st #f)))
  (set-program-resolved! p (ins (ins (program-resolved p) def-st) decl-st)))

(define (vector-drop* v k) (let ([r (make-vector (- (vector-length v) k) #f)]) (vector-copy! r 0 v k) r))

;; check the program: class errors are collected in `errors`; the statements that mention a relation on ℝ[i] or an unknown are then written as codes
(define (check! p)
  (set-program-statements! p (for/vector ([e (in-vector (program-statements p))] #:unless (equal? (vector-ref e 0) "<quote>")) e))
  (define c (program-checker p))
  (unknowns-of! c (program-statements p))
  (define n (vector-length (program-statements p)))
  (define resolved (make-vector n #f))
  (define errors '())
  (for ([i (in-range n)])
    (define e (vector-ref (program-statements p) i))
    (define file (vector-ref e 0))
    (define st (vector-ref e 1))
    (define trusted (vector-ref e 2))
    (define r (with-handlers ([class-err? (lambda (x) x)]) (let ([nw (check-statement c st trusted)]) (or nw st))))
    (cond
      [(class-err? r)
       (define what (match st [(SDef n _ _) n] [(SDecl n _) n] [_ (pp-statement st)]))
       (set! errors (cons (list file what (class-err-msg r)) errors))]
      [else (vector-set! resolved i r)]))
  (define defs-for-taint
    (for/list ([e (in-vector (program-statements p))] [r (in-vector resolved)] #:when (and (not (vector-ref e 2)) (SDef? r)))
      (list (SDef-name r) (SDef-params r) (SDef-body r))))
  (settle-taint c defs-for-taint)
  (set-program-resolved! p resolved)
  (set-program-errors! p (reverse errors))
  (when (null? (program-errors p))
    (codes-of! p)
    (when (for/or ([r (in-vector (program-resolved p))]) (and (SDef? r) (has-quote? (SDef-body r)))) (quote-program! p))
    ;; the definitions of the program, in de Bruijn form (those of the embedded prelude are erased when they are first needed)
    (hash-clear! (program-defined p))
    (set-program-user-defs!
     p
     (for/list ([r (in-vector (program-resolved p))] [i (in-naturals)]
                #:when (and (SDef? r) (begin (hash-set! (program-defined p) (SDef-name r) #t) (>= i (program-pre-count p)))))
       (erase-def (SDef-name r) (SDef-params r) (SDef-body r))))))

;; ------------------------------------------------------------ building
(define (user-statements p)
  (for/list ([e (in-vector (program-statements p))] [r (in-vector (program-resolved p))] #:when (and (not (vector-ref e 2)) r)) r))

(define (spec-text p) (apply string-append (map (lambda (s) (string-append (pp-statement s) "\n")) (user-statements p))))
(define (bin-text p) (spec-statements-to-bin-text (user-statements p) (program-doc1 p) #t))
(define (local-table p) (doc1-render (program-doc1 p) '("program-local symbols (same format as doc 1)")))

;; the human name of a spec symbol (reverse doc 2; a symbol of the program is its own name)
(define (hum-name p spec)
  (define e (for/first ([e (in-list (doc2-entries (program-doc2 p)))]
                        #:when (and (member (entry-role e) '("value" "infixl" "infixr" "infix" "prefix")) (member spec (entry-rhs e))))
              e))
  (if e (entry-hum e) spec))

;; build the evaluator: the definitions of the embedded prelude are compiled when they are first needed
(define (build-machine! p)
  (define defs
    (append
     (for/list ([i (in-range (program-pre-count p))] #:when (SDef? (vector-ref (program-resolved p) i)))
       (let ([d (vector-ref (program-resolved p) i)]) (cons (SDef-name d) (src-term (SDef-params d) (SDef-body d)))))
     (for/list ([d (in-list (program-user-defs p))]) (cons (car d) (src-core (cdr d))))))
  (define extra
    (for/list ([u (in-list (checker-unknowns (program-checker p)))])
      (define h (hum-name p (car u)))
      (cons (car u)
            (th (st-fail (host-err 'unknown
                                   (format "~a is an unknown (it is declared and never defined, so it has no value); use it in a statement — a relation such as ~a == 1 — which is simplified, not evaluated" h h)))))))
  (set-program-machine! p (build defs extra)))

;; the globals that some definition of the program uses and nothing defines (checked programs only)
(define (missing p)
  (cond
    [(pair? (program-errors p)) '()]
    [else
     (define (defined? n) (or (hash-has-key? (program-defined p) n) (and (assoc n (checker-unknowns (program-checker p))) #t)))
     (define out (make-hash))
     (for ([d (in-list (program-user-defs p))])
       ;; iterative over the spine of applications to keep the native stack shallow for long numerals
       (let loop ([stack (list (cdr d))])
         (unless (null? stack)
           (define c (car stack))
           (cond
             [(CG? c) (unless (defined? (CG-g c)) (hash-set! out (CG-g c) #t)) (loop (cdr stack))]
             [(CL? c) (loop (cons (CL-b c) (cdr stack)))]
             [(CA? c) (loop (cons (CA-f c) (cons (CA-x c) (cdr stack))))]
             [else (loop (cdr stack))]))))
     (sort (hash-keys out) string<?)]))

(define (val p n) (global (program-machine p) n))

;; load the prelude and the files and check them
(define (load-program files trusted-paths with-prelude)
  (define p (new-program))
  (when with-prelude
    (for ([e (in-list lib-files)]) (add-file! p (source-file (car e) (cdr e)) #t))
    (set-program-pre-count! p (vector-length (program-statements p))))
  (for ([f (in-list files)]) (add-file! p f (and (member (source-file-path f) trusted-paths) #t)))
  (check! p)
  p)
