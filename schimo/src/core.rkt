#lang racket/base
;; core.rkt -- the lazy evaluator of i-1 (port of ocamimo/src/core.ml and rustimo/src/core.rs).
;; A definition is an untyped lambda term in de Bruijn form.  Evaluation is call-by-need, on an explicit stack, so that the depth of a
;; computation is limited by memory:  every term is compiled once to code with FLAT closures (a lambda captures exactly the variables it
;; uses, a delayed argument too; a frame is the captured values followed by the arguments of the call); a chain of applications is one call,
;; a chain of lambdas one lambda of arity n; every closed application is evaluated at most once; the decoders apply a language value to
;; builder constants of the host (markers, list and pair builders, ...) and read what comes back.
(require racket/list racket/match "base.rkt" "syntax.rkt")
(provide (all-defined-out))

;; ---------------------------------------------------------------- values
(struct th ([st #:mutable]))
;; states: (st-done value) (st-delayed info caps) (st-clo info caps) (st-pap base held) (st-lazy idx) (st-prim p) 'running (st-fail err)
(struct st-done (val))
(struct st-delayed (info caps))
(struct st-clo (info caps))
(struct st-pap (base held))
(struct st-lazy (idx))
(struct st-prim (p))
(struct st-fail (err))
;; values: (fun th) 'VT 'VF 'VNil (vcons h t) (vpair a b) (vint k) (vcn x) (vcs x) (vca f a) (vcl x) (vcv x)
(struct fun (t))
(struct vcons (h t))
(struct vpair (a b))
(struct vint (k))
(struct vcn (x))
(struct vcs (x))
(struct vca (f a))
(struct vcl (x))
(struct vcv (x))
;; code
(struct x-var (i))
(struct x-const (t))
(struct x-lam (info))
(struct x-app (f args))
(struct x-call (g args))
(struct x-callvar (i args))
(struct x-pap (spec))
(struct a-var (i))
(struct a-const (t))
(struct a-lam (info))
(struct a-delay (info))
(struct a-pap (spec))
(struct papspec (g args))
(struct laminfo (arity caps body))
(struct thunkinfo (caps body))

(define (mk st) (th st))
(define (done v) (th (st-done v)))
(define dummy (th 'running))
(define no-caps (vector))

(define (prim-arity p) (if (memq p '(PCons PPair PCodeA)) 2 1))
(define (run-prim p a)
  (case p
    [(PCons) (vcons (vector-ref a 0) (vector-ref a 1))]
    [(PPair) (vpair (vector-ref a 0) (vector-ref a 1))]
    [(PCodeN) (vcn (vector-ref a 0))]
    [(PCodeS) (vcs (vector-ref a 0))]
    [(PCodeA) (vca (vector-ref a 0) (vector-ref a 1))]
    [(PCodeL) (vcl (vector-ref a 0))]
    [else (vcv (vector-ref a 0))]))

(define (describe v)
  (cond [(fun? v) "function"] [(eq? v 'VT) "true"] [(eq? v 'VF) "false"] [(vcons? v) "cons cell"] [(eq? v 'VNil) "nil"]
        [(vpair? v) "pair"] [(vint? v) (number->string (vint-k v))] [(vcn? v) "number code"] [(vcs? v) "symbol code"]
        [(vca? v) "application code"] [(vcl? v) "lambda code"] [else "variable code"]))

;; ---------------------------------------------------------------- compiling de Bruijn terms
;; a term with the levels (absolute binder depths) of its free variables
(struct n-v (level))
(struct n-g (name))
(struct n-l (arity body fv))
(struct n-a (f x fv))

(define (fv-of a) (cond [(n-l? a) (n-l-fv a)] [(n-a? a) (n-a-fv a)] [else '()]))
(define (free-levels a) (cond [(n-v? a) (list (n-v-level a))] [(n-g? a) '()] [else (fv-of a)]))
(define (closed? a) (cond [(n-v? a) #f] [(n-g? a) #t] [else (null? (fv-of a))]))

(define (union-sorted a b)
  (cond [(null? a) b] [(null? b) a]
        [(< (car a) (car b)) (cons (car a) (union-sorted (cdr a) b))]
        [(< (car b) (car a)) (cons (car b) (union-sorted a (cdr b)))]
        [else (cons (car a) (union-sorted (cdr a) (cdr b)))]))

;; annotate a term at binder depth `depth`; a run of lambdas becomes one lambda of that arity
(define (annotate t depth)
  (cond
    [(CV? t) (n-v (- depth (CV-k t)))]
    [(CG? t) (n-g (CG-g t))]
    [(CL? t)
     (let loop ([cur t] [n 0])
       (if (CL? cur)
           (loop (CL-b cur) (+ n 1))
           (let* ([body (annotate cur (+ depth n))]
                  [fv (filter (lambda (l) (< l depth)) (free-levels body))])
             (n-l n body fv))))]
    [else
     (let* ([fa (annotate (CA-f t) depth)] [xa (annotate (CA-x t) depth)])
       (n-a fa xa (union-sorted (free-levels fa) (free-levels xa))))]))

;; level -> slot of the frame being compiled for
(define (scope-new) (make-hasheqv))
(define (scope-slot sc level)
  (or (hash-ref sc level #f) (error "i-1: internal error: a free variable is not in the frame")))

(struct linker (globals arities))

;; the chain of applications of an open application, as its head and its arguments in order; a closed inner application is the head
;; (it is shared), not part of the chain
(define (spine a)
  (let loop ([cur a] [args '()] [first #t])
    (if (and (n-a? cur) (or first (not (closed? cur))))
        (loop (n-a-f cur) (cons (n-a-x cur) args) #f)
        (values cur args))))

(define (link-global lk g)
  (or (hash-ref (linker-globals lk) g #f)
      (mk (st-fail (host-err 'eval (format "i-1: ~a has no compiled body" g))))))

(define (gen-lam lk a depth sc)
  (define arity (n-l-arity a))
  (define fv (n-l-fv a))
  (define caps (list->vector (map (lambda (l) (scope-slot sc l)) fv)))
  (define inner (scope-new))
  (for ([l (in-list fv)] [j (in-naturals)]) (hash-set! inner l j))
  (for ([p (in-range arity)]) (hash-set! inner (+ depth p) (+ (length fv) p)))
  (laminfo arity caps (gen lk (n-l-body a) (+ depth arity) inner #f)))

;; the code of a delayed argument: a frame of its own free variables
(define (gen-thunk lk a depth sc)
  (define fv (fv-of a))
  (define caps (list->vector (map (lambda (l) (scope-slot sc l)) fv)))
  (define inner (scope-new))
  (for ([l (in-list fv)] [j (in-naturals)]) (hash-set! inner l j))
  (thunkinfo caps (gen lk a depth inner #t)))

;; a closed term as a shared value: a closure is made now, an application is a thunk evaluated at most once
(define (shared lk a depth)
  (if (n-l? a)
      (mk (st-clo (gen-lam lk a depth (scope-new)) no-caps))
      (mk (st-delayed (thunkinfo (vector) (gen lk a depth (scope-new) #t)) no-caps))))

(define (known-arity lk g) (hash-ref (linker-arities lk) g #f))

(define (gen-arg lk a depth sc)
  (cond
    [(n-v? a) (a-var (scope-slot sc (n-v-level a)))]
    [(n-g? a) (a-const (link-global lk (n-g-name a)))]
    [(closed? a) (a-const (shared lk a depth))]
    [(n-l? a) (a-lam (gen-lam lk a depth sc))]
    [else
     ;; a known function applied to too few arguments is a value: build it now instead of delaying the work
     (define-values (head args) (spine a))
     (define n (and (n-g? head) (known-arity lk (n-g-name head))))
     (if (and n (< (length args) n))
         (a-pap (gen-pap lk (n-g-name head) args depth sc))
         (a-delay (gen-thunk lk a depth sc)))]))

(define (gen-pap lk g args depth sc)
  (papspec (link-global lk g) (list->vector (map (lambda (x) (gen-arg lk x depth sc)) args))))

;; `root`: the term is the body of a thunk or of a global (it is evaluated once, so it is not floated out again)
(define (gen lk a depth sc root)
  (cond
    [(n-v? a) (x-var (scope-slot sc (n-v-level a)))]
    [(n-g? a) (x-const (link-global lk (n-g-name a)))]
    [(n-l? a) (if (closed? a) (x-const (shared lk a depth)) (x-lam (gen-lam lk a depth sc)))]
    [(and (not root) (closed? a)) (x-const (shared lk a depth))]
    [else
     (define-values (cur args) (spine a))
     (define (gargs) (list->vector (map (lambda (x) (gen-arg lk x depth sc)) args)))
     (define n (and (n-g? cur) (known-arity lk (n-g-name cur))))
     (cond
       [n (if (>= (length args) n)
              (x-call (link-global lk (n-g-name cur)) (gargs))
              (x-pap (gen-pap lk (n-g-name cur) args depth sc)))]
       [(n-v? cur) (let ([slot (scope-slot sc (n-v-level cur))]) (x-callvar slot (gargs)))]
       [else (let ([head (gen lk cur depth sc #f)]) (x-app head (gargs)))])]))

;; the state of a global definition: a closed lambda is a function value at once, anything else a delayed expression
(define (gen-def lk c)
  (define a (annotate c 0))
  (if (n-l? a)
      (st-clo (gen-lam lk a 0 (scope-new)) no-caps)
      (st-delayed (thunkinfo (vector) (gen lk a 0 (scope-new) #t)) no-caps)))

;; ---------------------------------------------------------------- the machine
(struct k-update (t))
(struct k-arg (t))

;; where the code of a global comes from: (src-core c), or (src-term params term) -- a checked definition to erase when it is first needed
(struct src-core (c))
(struct src-term (ps term))

(define (term-lams t)
  (match t
    [(TLam ps b) (+ (length ps) (term-lams b))]
    [(TAsc e _) (term-lams e)]
    [(TQuote e _) (term-lams e)]
    [_ 0]))
(define (term-arity ps body) (+ (length ps) (term-lams body)))
(define (core-arity c) (let loop ([c c] [n 0]) (if (CL? c) (loop (CL-b c) (+ n 1)) n)))

(struct machine (globals arities lazy-src [conts #:mutable] [ntop #:mutable] [frame #:mutable]
                 vt vf vnil cons-cb pair-cb ints code-cbs [app-infos #:mutable]))

(define (push! m k)
  (when (>= (machine-ntop m) (vector-length (machine-conts m)))
    (let ([n (make-vector (max 64 (* 2 (vector-length (machine-conts m)))) #f)])
      (vector-copy! n 0 (machine-conts m) 0 (machine-ntop m))
      (set-machine-conts! m n)))
  (vector-set! (machine-conts m) (machine-ntop m) k)
  (set-machine-ntop! m (+ (machine-ntop m) 1)))

(define (pop! m)
  (define i (- (machine-ntop m) 1))
  (set-machine-ntop! m i)
  (define k (vector-ref (machine-conts m) i))
  (vector-set! (machine-conts m) i #f)
  k)

;; how many further arguments (at most `want`) are waiting on the stack above `base`
(define (waiting m base want)
  (let loop ([n 0])
    (if (and (< n want) (> (machine-ntop m) (+ base n)) (k-arg? (vector-ref (machine-conts m) (- (machine-ntop m) 1 n))))
        (loop (+ n 1))
        n)))

(define (pick frame idx)
  (define n (vector-length idx))
  (if (zero? n)
      no-caps
      (let ([r (make-vector n #f)])
        (let loop ([i 0]) (when (< i n) (vector-set! r i (vector-ref frame (vector-ref idx i))) (loop (+ i 1))))
        r)))

;; the value of an argument: a variable and a global are passed as they are, a lambda is built at once, a partial application of a known
;; function too, anything else is delayed
(define (make-arg a frame)
  (cond
    [(a-var? a) (vector-ref frame (a-var-i a))]
    [(a-const? a) (a-const-t a)]
    [(a-delay? a) (let ([info (a-delay-info a)]) (th (st-delayed info (pick frame (thunkinfo-caps info)))))]
    [(a-lam? a) (let ([info (a-lam-info a)]) (th (st-clo info (pick frame (laminfo-caps info)))))]
    [else (make-pap (a-pap-spec a) frame)]))

(define (make-pap spec frame)
  (define args (papspec-args spec))
  (define n (vector-length args))
  (define held (make-vector n #f))
  (let loop ([i 0]) (when (< i n) (vector-set! held i (make-arg (vector-ref args i) frame)) (loop (+ i 1))))
  (th (st-pap (papspec-g spec) held)))

(define (build defs extra)
  (define globals (make-hash))
  ;; the ready values first (they win over a definition of the same name), then the placeholders: definitions refer to each other (and to
  ;; themselves) through them, and are compiled when they are first needed
  (for ([e (in-list extra)]) (hash-set! globals (car e) (cdr e)))
  (define arities (make-hash))
  (define last (make-hash))
  (for ([d (in-list defs)] [i (in-naturals)]) (hash-set! last (car d) i))   ; a later definition of the same name wins
  (define lazy-src (make-vector (length defs) #f))
  (for ([d (in-list defs)] [i (in-naturals)])
    (define n (car d))
    (define src (cdr d))
    (when (and (= (hash-ref last n) i) (not (hash-has-key? globals n)))
      (define ar (if (src-core? src) (core-arity (src-core-c src)) (term-arity (src-term-ps src) (src-term-term src))))
      (when (> ar 0) (hash-set! arities n ar))
      (hash-set! globals n (th (st-lazy i)))
      (vector-set! lazy-src i src)))
  (define (prim p) (th (st-prim p)))
  (machine globals arities lazy-src (make-vector 1024 #f) 0 (vector)
           (done 'VT) (done 'VF) (done 'VNil) (prim 'PCons) (prim 'PPair)
           (vector (done (vint 0)) (done (vint 1)) (done (vint 2)))
           (vector (prim 'PCodeN) (prim 'PCodeS) (prim 'PCodeA) (prim 'PCodeL) (prim 'PCodeV))
           (vector)))

;; compile a global that has not been needed before
(define (compile-global m idx)
  (define src (vector-ref (machine-lazy-src m) idx))
  (vector-set! (machine-lazy-src m) idx #f)
  (cond
    [(src-core? src) (gen-def (linker (machine-globals m) (machine-arities m)) (src-core-c src))]
    [(src-term? src)
     (with-handlers ([host-err? (lambda (e) (st-fail e))])
       (let ([c (cdr (erase-def "" (src-term-ps src) (src-term-term src)))])
         (gen-def (linker (machine-globals m) (machine-arities m)) c)))]
    [else (st-fail (host-err 'eval "i-1: internal error: a global was compiled twice"))]))

(define (global m g)
  (or (hash-ref (machine-globals m) g #f) (eval-err (format "i-1: ~a is not defined" g))))
(define (has-global? m g) (hash-has-key? (machine-globals m) g))

;; the lazy application of f to args: a thunk that is evaluated when it is needed
(define (app-th m f args)
  (define n (vector-length args))
  (when (<= (vector-length (machine-app-infos m)) n)
    (define old (vector-length (machine-app-infos m)))
    (define infos
      (for/vector #:length (+ n 1) ([k (in-range (+ n 1))])
        (if (< k old)
            (vector-ref (machine-app-infos m) k)
            ;; frame: [f, a1 .. ak]; body: f a1 .. ak
            (thunkinfo (for/vector #:length (+ k 1) ([i (in-range (+ k 1))]) i)
                       (if (zero? k) (x-var 0) (x-app (x-var 0) (for/vector #:length k ([i (in-range k)]) (a-var (+ i 1)))))))))
    (set-machine-app-infos! m infos))
  (define caps (make-vector (+ n 1) f))
  (vector-copy! caps 1 args)
  (th (st-delayed (vector-ref (machine-app-infos m) n) caps)))

;; apply a lambda (`clo` is the thunk that holds it; `held` the arguments of the partial application it may be inside):
;; returns (values code #f) to evaluate in the new frame, or (values #f value)
(define (call-clo m base info caps held clo first)
  (define nh (vector-length held))
  (define need (- (laminfo-arity info) nh))
  (define extra (waiting m base (- need 1)))
  (cond
    [(< (+ extra 1) need)
     ;; not enough arguments yet: a partial application
     (define h (make-vector (+ nh 1 extra) first))
     (vector-copy! h 0 held)
     (for ([k (in-range 1 (+ extra 1))]) (vector-set! h (+ nh k) (k-arg-t (pop! m))))
     (values #f (fun (th (st-pap clo h))))]
    [else
     (define nc (vector-length caps))
     (define fr (make-vector (+ nc nh need) first))
     (vector-copy! fr 0 caps)
     (vector-copy! fr nc held)
     (vector-set! fr (+ nc nh) first)
     (for ([k (in-range 1 need)]) (vector-set! fr (+ nc nh k) (k-arg-t (pop! m))))
     (set-machine-frame! m fr)
     (values (laminfo-body info) #f)]))

(define (call-prim m base p held prim-v first)
  (define nh (vector-length held))
  (define need (- (prim-arity p) nh))
  (define extra (waiting m base (- need 1)))
  (define args (make-vector (+ nh 1 extra) first))
  (vector-copy! args 0 held)
  (for ([k (in-range 1 (+ extra 1))]) (vector-set! args (+ nh k) (k-arg-t (pop! m))))
  (if (< (+ extra 1) need)
      (fun (th (st-pap prim-v args)))
      (run-prim p args)))

;; evaluate  start args  to weak head normal form
(define (run m start args)
  (define base (machine-ntop m))
  (for ([k (in-range (- (vector-length args) 1) -1 -1)]) (push! m (k-arg (vector-ref args k))))
  (define (force t)
    (define st (th-st t))
    (cond
      [(st-done? st) (deliver (st-done-val st))]
      [(or (st-clo? st) (st-pap? st) (st-prim? st)) (deliver (fun t))]
      [(eq? st 'running) (eval-err "<<loop>>")]
      [(st-fail? st) (raise (st-fail-err st))]
      [(st-lazy? st) (set-th-st! t (compile-global m (st-lazy-idx st))) (force t)]
      [else ; delayed
       (set-th-st! t 'running)
       (set-machine-frame! m (st-delayed-caps st))
       (push! m (k-update t))
       (eval (thunkinfo-body (st-delayed-info st)))]))
  (define (eval-var t)
    (define st (th-st t))
    (cond
      [(st-done? st) (deliver (st-done-val st))]
      [(or (st-clo? st) (st-pap? st) (st-prim? st)) (deliver (fun t))]
      [else (force t)]))
  (define (eval code)
    (cond
      [(x-var? code) (eval-var (vector-ref (machine-frame m) (x-var-i code)))]
      [(x-const? code) (eval-var (x-const-t code))]
      [(x-lam? code) (let ([info (x-lam-info code)]) (deliver (fun (th (st-clo info (pick (machine-frame m) (laminfo-caps info)))))))]
      [(x-call? code)
       (define g (x-call-g code))
       (define args (x-call-args code))
       (let ([st (th-st g)]) (when (st-lazy? st) (set-th-st! g (compile-global m (st-lazy-idx st)))))
       (define st (th-st g))
       (define fr (machine-frame m))
       (cond
         [(and (st-clo? st) (<= (laminfo-arity (st-clo-info st)) (vector-length args)))
          (define info (st-clo-info st))
          (define n (laminfo-arity info))
          (for ([k (in-range (- (vector-length args) 1) (- n 1) -1)]) (push! m (k-arg (make-arg (vector-ref args k) fr))))
          (define nf (make-vector n #f))
          (let loop ([k 0]) (when (< k n) (vector-set! nf k (make-arg (vector-ref args k) fr)) (loop (+ k 1))))
          (set-machine-frame! m nf)
          (eval (laminfo-body info))]
         [else
          (for ([k (in-range (- (vector-length args) 1) -1 -1)]) (push! m (k-arg (make-arg (vector-ref args k) fr))))
          (force g)])]
      [(x-callvar? code)
       (define t (vector-ref (machine-frame m) (x-callvar-i code)))
       (define args (x-callvar-args code))
       (define st (th-st t))
       (define fr (machine-frame m))
       (cond
         [(and (st-clo? st) (= (laminfo-arity (st-clo-info st)) (vector-length args)))
          (define caps (st-clo-caps st))
          (define nc (vector-length caps))
          (define na (vector-length args))
          (define nf (make-vector (+ nc na) #f))
          (vector-copy! nf 0 caps)
          (let loop ([k 0]) (when (< k na) (vector-set! nf (+ nc k) (make-arg (vector-ref args k) fr)) (loop (+ k 1))))
          (set-machine-frame! m nf)
          (eval (laminfo-body (st-clo-info st)))]
         [else
          (for ([k (in-range (- (vector-length args) 1) -1 -1)]) (push! m (k-arg (make-arg (vector-ref args k) fr))))
          (eval-var t)])]
      [(x-pap? code) (deliver (fun (make-pap (x-pap-spec code) (machine-frame m))))]
      [else ; x-app
       (define args (x-app-args code))
       (define fr (machine-frame m))
       (for ([k (in-range (- (vector-length args) 1) -1 -1)]) (push! m (k-arg (make-arg (vector-ref args k) fr))))
       (eval (x-app-f code))]))
  ;; deliver the value to what is waiting for it
  (define (deliver x)
    (cond
      [(<= (machine-ntop m) base) x]
      [else
       (define k (pop! m))
       (cond
         [(k-update? k) (set-th-st! (k-update-t k) (st-done x)) (deliver x)]
         [else
          (define first (k-arg-t k))
          (unless (fun? x) (eval-err (string-append "a value that is not a function was applied: " (describe x))))
          (define f (fun-t x))
          (define st (th-st f))
          (cond
            [(st-clo? st)
             (let-values ([(code v) (call-clo m base (st-clo-info st) (st-clo-caps st) no-caps f first)])
               (if code (eval code) (deliver v)))]
            [(st-prim? st) (deliver (call-prim m base (st-prim-p st) no-caps f first))]
            [else ; a partial application
             (define b (st-pap-base st))
             (define held (st-pap-held st))
             (let ([bs (th-st b)]) (when (st-lazy? bs) (set-th-st! b (compile-global m (st-lazy-idx bs)))))
             (define bs (th-st b))
             (cond
               [(st-clo? bs)
                (let-values ([(code v) (call-clo m base (st-clo-info bs) (st-clo-caps bs) held b first)])
                  (if code (eval code) (deliver v)))]
               [else (deliver (call-prim m base (st-prim-p bs) held b first))])])])]))
  (with-handlers ([host-err? (lambda (e)
                               ;; an error: the thunks under evaluation keep it (evaluating them again gives the same error), the rest of the work is dropped
                               (let loop ()
                                 (when (> (machine-ntop m) base)
                                   (let ([k (pop! m)]) (when (k-update? k) (set-th-st! (k-update-t k) (st-fail e))))
                                   (loop)))
                               (raise e))])
    (force start)))

(define (whnf m v) (run m v (vector)))
(define (apply-whnf m f args) (run m f args))

;; ---------------------------------------------------------------- decoding
(define (to-bool m v) (eq? (apply-whnf m v (vector (machine-vt m) (machine-vf m))) 'VT))

;; the truth value that a Boolean selects between the markers: 'true, 'false, or #f for anything else (⍰)
(define (tri m v)
  (define r (apply-whnf m v (vector (machine-vt m) (machine-vf m))))
  (cond [(eq? r 'VT) 'true] [(eq? r 'VF) 'false] [else #f]))

;; take a list cell apart: a vcons, 'VNil, or (for an undetermined value) something else
(define (cell-or-nil m v) (apply-whnf m v (vector (machine-cons-cb m) (machine-vnil m))))

;; an ordering (lib/bounded.imo): a Scott value with three alternatives, read as 0, 1 or 2
(define (to-ord m v)
  (define r (apply-whnf m v (machine-ints m)))
  (if (vint? r) (vint-k r) (eval-err "an ordering was expected")))

;; a list of booleans (digits, least significant first), as a vector of 0 and 1
(define (to-list m v)
  (let loop ([cur v] [out '()])
    (define c (cell-or-nil m cur))
    (cond
      [(vcons? c) (loop (vcons-t c) (cons (if (to-bool m (vcons-h c)) 1 0) out))]
      [(eq? c 'VNil) (list->vector (reverse out))]
      [else (eval-err "a list was expected")])))

(define (to-pair m v)
  (define r (apply-whnf m v (vector (machine-pair-cb m))))
  (if (vpair? r) (values (vpair-a r) (vpair-b r)) (eval-err "a pair was expected")))

;; element n (from 0) of a stream
(define (stream-nth m v n)
  (let loop ([cur v] [k n])
    (define c (cell-or-nil m cur))
    (cond
      [(vcons? c) (if (zero? k) (vcons-h c) (loop (vcons-t c) (- k 1)))]
      [else (eval-err "a stream was expected")])))

;; the digit list (LSB first) as a language value
(define (list-value m ds)
  (define tv (global m "⊤"))
  (define fv (global m "⊥"))
  (define cons-g (global m "∷"))
  (for/fold ([acc fv]) ([i (in-range (- (vector-length ds) 1) -1 -1)])
    (app-th m cons-g (vector (if (zero? (vector-ref ds i)) fv tv) acc))))

;; the lazy application of the global f to the arguments
(define (call-g m f args) (app-th m (global m f) args))

;; the Gaussian integer of a digit-list value
(define (gi-of m v) (val-digits (to-list m v)))
