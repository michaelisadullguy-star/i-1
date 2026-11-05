#lang racket/base
;; hum.rkt -- the HUMAN notation of i-1 and doc 2 (port of ocamimo/src/hum.ml and rustimo/src/hum.rs).
;; doc 2 line   <hum symbol> := <rhs> | <rhs> | ...  ; <role>          (⍝ starts a comment)
;;   rhs   a spec symbol, or a bin symbol (a numeral such as 11, or .B.)
;;   role  class | value | literal | infixl P | infixr P | infix P | prefix P
;; human statements (one per logical line):  name in Class := expr | name in Class | name(x, y) in A -> B -> C := expr | A subseteq B
(require racket/list racket/match racket/set "base.rkt" "syntax.rkt" "layers.rkt")
(provide (all-defined-out))

;; ---------------------------------------------------------------- doc 2
(struct entry (hum rhs role prec) #:transparent)          ; prec: an integer or #f
(struct doc2 (entries by-hum))                            ; by-hum: hash hum -> list of entries, in order

(define (doc2-make entries)
  (define h (make-hash))
  (for ([e (in-list entries)]) (hash-set! h (entry-hum e) (cons e (hash-ref h (entry-hum e) '()))))
  (for ([(k v) (in-hash h)]) (hash-set! h k (reverse v)))
  (doc2 entries h))

(define (doc2-parse text)
  (doc2-make
   (for/fold ([acc '()] #:result (reverse acc)) ([ln0 (in-list (split-on text "\n"))])
     (define ln1 (strip ln0))
     (cond
       [(or (string=? ln1 "") (starts-with? ln1 "⍝")) acc]
       [else
        (define ln (let ([k (find-sub ln1 " ⍝ ")]) (if k (substring ln1 0 k) ln1)))
        (define k (find-sub ln " := "))
        (unless k (parse-err (format "doc2: bad line ~a" (py-repr ln))))
        (define hd (substring ln 0 k))
        (define rest (substring ln (+ k 4)))
        (define j (rfind-sub rest " ; "))
        (define rhs (if j (substring rest 0 j) ""))
        (define role (split-ws (if j (substring rest (+ j 3)) rest)))
        (when (null? role) (parse-err "Prelude.head: empty list"))
        (cons (entry (strip hd) (map strip (split-on rhs " | ")) (car role)
                     (and (pair? (cdr role)) (string->number* (cadr role))))
              acc)]))))

(define (string->number* s)
  (define n (string->number s 10))
  (and n (exact-integer? n) n))

;; the first entry for a human symbol that has one of the roles
(define (doc2-find d hum roles)
  (for/first ([e (in-list (hash-ref (doc2-by-hum d) hum '()))] #:when (member (entry-role e) roles)) e))

(define (all-bin-chars? s) (for/and ([c (in-string s)]) (and (memv c '(#\0 #\1 #\.)) #t)))

;; key -> [spec symbols]  (bin-literal right-hand sides are handled by the reader, not listed here)
(define (overload-table d)
  (define m (make-hash))
  (for ([e (in-list (doc2-entries d))])
    (unless (member (entry-role e) '("class" "literal" "syntax"))
      (define key (if (string=? (entry-role e) "prefix") (string-append "hum:prefix " (entry-hum e)) (string-append "hum:" (entry-hum e))))
      (hash-set! m key (filter (lambda (x) (not (and (not (string=? x "")) (all-bin-chars? x)))) (entry-rhs e)))))
  m)

;; a bin symbol on the right of doc 2 means the spec symbol that doc 1 gives that code to
(define (doc2-remap d d1)
  (doc2-make
   (for/list ([e (in-list (doc2-entries d))])
     (entry (entry-hum e)
            (for/list ([x (in-list (entry-rhs e))]) (if (bin-sym? x) (hash-ref (doc1-b2s d1) x x) x))
            (entry-role e) (entry-prec e)))))

;; ---------------------------------------------------------------- lexer
(struct h-num (s) #:transparent)
(struct h-str (s) #:transparent)
(struct h-chr (c) #:transparent)
(struct h-id (s) #:transparent)
(struct h-op (s) #:transparent)

(define (show-tok t)
  (match t
    [(h-num s) (format "('NUM', ~a)" (py-repr s))]
    [(h-str s) (format "('STR', ~a)" (py-repr s))]
    [(h-chr c) (format "('CHR', ~a)" c)]
    [(h-id s) (format "('ID', ~a)" (py-repr s))]
    [(h-op s) (format "('OP', ~a)" (py-repr s))]))

(define (digit? c) (and (char>=? c #\0) (char<=? c #\9)))
(define (letter? c) (or (and (char>=? c #\a) (char<=? c #\z)) (and (char>=? c #\A) (char<=? c #\Z))))

;; the body of a quoted literal: any character but the quote and the backslash, or a backslash and any character but a newline;
;; returns (values body-with-its-backslashes index-after-the-closing-quote) or (values #f #f)
(define (quoted cs start q)
  (define n (string-length cs))
  (define out (open-output-string))
  (let loop ([i start])
    (cond
      [(>= i n) (values #f #f)]
      [else
       (define x (string-ref cs i))
       (cond
         [(char=? x q) (values (get-output-string out) (+ i 1))]
         [(char=? x #\\)
          (if (and (< (+ i 1) n) (not (char=? (string-ref cs (+ i 1)) #\newline)))
              (begin (write-char #\\ out) (write-char (string-ref cs (+ i 1)) out) (loop (+ i 2)))
              (values #f #f))]
         [else (write-char x out) (loop (+ i 1))])])))

(define (unescape s)
  (define n (string-length s))
  (define out (open-output-string))
  (let loop ([i 0])
    (when (< i n)
      (cond
        [(and (char=? (string-ref s i) #\\) (< (+ i 1) n))
         (define y (string-ref s (+ i 1)))
         (write-char (cond [(char=? y #\n) #\newline] [(char=? y #\t) #\tab] [else y]) out)
         (loop (+ i 2))]
        [else (write-char (string-ref s i) out) (loop (+ i 1))])))
  (get-output-string out))

(define two-char-ops '(":=" "|->" "->" "==" "!=" "++"))

(define (lex-hum line0)
  (define cs (let loop ([n (string-length line0)])
               (if (and (> n 0) (char-whitespace? (string-ref line0 (- n 1)))) (loop (- n 1)) (substring line0 0 n))))
  (define n (string-length cs))
  (let loop ([i 0] [out '()])
    (define i1 (let l ([i i]) (if (and (< i n) (char-whitespace? (string-ref cs i))) (l (+ i 1)) i)))
    (cond
      [(>= i1 n) (reverse out)]
      [else
       (define i i1)
       (define c (string-ref cs i))
       (define (op-or-fail)
         (define rest (substring cs i (min n (+ i 3))))
         (define op (for/first ([o (in-list two-char-ops)] #:when (starts-with? rest o)) o))
         (cond
           [op (loop (+ i (string-length op)) (cons (h-op op) out))]
           [(memv c (string->list "-+*/^(),[]")) (loop (+ i 1) (cons (h-op (string c)) out))]
           [else (parse-err (format "human notation: cannot read ~a" (py-repr (substring cs i (min n (+ i 12))))))]))
       (define (try-ident)
         (if (or (letter? c) (char=? c #\_))
             (let ([j (let l ([j i]) (if (and (< j n) (let ([x (string-ref cs j)]) (or (letter? x) (char=? x #\_) (digit? x)))) (l (+ j 1)) j))])
               (loop j (cons (h-id (substring cs i j)) out)))
             (op-or-fail)))
       (define (try-backslash)
         (if (char=? c #\\)
             (let ([j (let l ([j (+ i 1)]) (if (and (< j n) (letter? (string-ref cs j))) (l (+ j 1)) j))])
               (if (> j (+ i 1))
                   (loop j (cons (h-id (string-append "\\" (substring cs (+ i 1) j))) out))
                   (try-ident)))
             (try-ident)))
       (define (try-char)
         (if (char=? c #\')
             (let-values ([(body next) (quoted cs (+ i 1) #\')])
               (if body
                   (let ([u (unescape body)])
                     (if (= (string-length u) 1)
                         (loop next (cons (h-chr (char->integer (string-ref u 0))) out))
                         (try-backslash)))
                   (try-backslash)))
             (try-backslash)))
       (define (try-string)
         (if (char=? c #\")
             (let-values ([(body next) (quoted cs (+ i 1) #\")])
               (if body (loop next (cons (h-str (unescape body)) out)) (try-char)))
             (try-char)))
       (cond
         [(digit? c)
          (define j (let l ([j i]) (if (and (< j n) (digit? (string-ref cs j))) (l (+ j 1)) j)))
          (define ip (substring cs i j))
          (cond
            [(and (< (+ j 1) n) (char=? (string-ref cs j) #\.) (digit? (string-ref cs (+ j 1))))
             (define k (let l ([k (+ j 1)]) (if (and (< k n) (digit? (string-ref cs k))) (l (+ k 1)) k)))
             (loop k (cons (h-num (string-append ip "." (substring cs (+ j 1) k))) out))]
            [else (loop j (cons (h-num ip) out))])]
         [else (try-string)])])))

;; a logical line ends at a newline outside parentheses; `--` starts a comment
(define (hum-logical-lines text)
  (define (count ln ch) (for/sum ([c (in-string ln)]) (if (char=? c ch) 1 0)))
  (define out '())
  (define cur (open-output-string))
  (define depth 0)
  (define (flush!)
    (define s (strip (get-output-string cur)))
    (unless (string=? s "") (set! out (cons s out)))
    (set! cur (open-output-string)))
  (for ([ln0 (in-list (split-on text "\n"))])
    (define ln (if (and (contains-sub? ln0 "--") (not (for/or ([c (in-string ln0)]) (char=? c #\")))) (substring ln0 0 (find-sub ln0 "--")) ln0))
    (write-char #\space cur)
    (write-string ln cur)
    (set! depth (+ depth (- (count ln #\() (count ln #\))) (- (count ln #\[) (count ln #\]))))
    (when (<= depth 0) (flush!) (set! depth 0)))
  (flush!)
  (reverse out))

;; ---------------------------------------------------------------- parser
(struct hum (doc infix prefix))        ; infix: hash op -> (cons prec kind); prefix: hash op -> prec

(define (mk-hum d)
  (define infix (make-hash))
  (define prefix (make-hash))
  (for ([e (in-list (doc2-entries d))])
    (when (member (entry-role e) '("infixl" "infixr" "infix"))
      (hash-set! infix (entry-hum e) (cons (or (entry-prec e) 0) (entry-role e))))
    (when (string=? (entry-role e) "prefix") (hash-set! prefix (entry-hum e) (or (entry-prec e) 0))))
  (hum d infix prefix))

(define (oob) (parse-err "list index out of range"))
(define (op? t o) (and (h-op? t) (string=? (h-op-s t) o)))

;; classes
(define (class-atom h ts)
  (cond
    [(null? ts) (oob)]
    [(op? (car ts) "(")
     (define-values (c r) (class-expr h (cdr ts)))
     (if (and (pair? r) (op? (car r) ")")) (values c (cdr r)) (parse-err "missing )"))]
    [(h-id? (car ts))
     (define n (h-id-s (car ts)))
     (define e (doc2-find (hum-doc h) n '("class")))
     (unless e (parse-err (format "~a is not a class in doc 2" n)))
     (define name (car (entry-rhs e)))
     (cond
       [(class-var? name) (values (V name) (cdr ts))]
       [(and (pair? (cdr ts)) (op? (cadr ts) "("))
        (define-values (args rest) (class-args h (cddr ts)))
        (values (K name args) rest)]
       [else (values (K name '()) (cdr ts))])]
    [else (parse-err (string-append "class expected, found " (show-tok (car ts))))]))

(define (class-args h ts)
  (let loop ([r ts] [out '()])
    (define-values (a r1) (class-expr h r))
    (define out2 (cons a out))
    (cond
      [(null? r1) (oob)]
      [(op? (car r1) ",") (loop (cdr r1) out2)]
      [(op? (car r1) ")") (values (reverse out2) (cdr r1))]
      [else (parse-err "missing ) in class")])))

(define (class-expr h ts)
  (define-values (l r) (class-atom h ts))
  (cond
    [(and (pair? r) (op? (car r) "->"))
     (define-values (rt r2) (class-expr h (cdr r)))
     (values (K "→" (list l rt)) r2)]
    [else (values l r)]))

;; terms
(define (number text)
  (define k (for/first ([i (in-range (string-length text))] #:when (char=? (string-ref text i) #\.)) i))
  (cond
    [(not k) (TNum (big-numeral-text (string->number text 10)))]
    [else
     (define a (substring text 0 k))
     (define b (substring text (+ k 1)))
     (app "hum:/" (list (TNum (big-numeral-text (string->number (string-append a b) 10)))
                        (TNum (big-numeral-text (expt 10 (string-length b))))))]))

(define (op-key t) (cond [(h-op? t) (h-op-s t)] [(h-id? t) (h-id-s t)] [else #f]))

(define (atom h ts scope)
  (cond
    [(null? ts) (oob)]
    [else
     (define t (car ts))
     (cond
       [(h-num? t) (values (number (h-num-s t)) (cdr ts))]
       [(h-str? t) (values (TStr (h-str-s t)) (cdr ts))]
       [(h-chr? t) (values (TChr (h-chr-c t)) (cdr ts))]
       [(op? t "[")
        (define r0 (cdr ts))
        (define-values (items r1) (if (and (pair? r0) (op? (car r0) "]")) (values '() r0) (list-items h r0 scope)))
        (cond
          [(null? r1) (oob)]
          [(op? (car r1) "]")
           (values (for/fold ([e (var "hum:nil")]) ([a (in-list (reverse items))]) (app "hum:cons" (list a e))) (cdr r1))]
          [else (parse-err "missing ] in list")])]
       [(op? t "(")
        (define-values (e r1) (hum-expr h (cdr ts) 0 scope))
        (cond
          [(null? r1) (oob)]
          [(and (h-id? (car r1)) (string=? (h-id-s (car r1)) "in"))
           (define-values (c r3) (class-expr h (cdr r1)))
           (cond [(null? r3) (oob)]
                 [(op? (car r3) ")") (values (TAsc e c) (cdr r3))]
                 [else (parse-err "missing )")])]
          [(op? (car r1) ")") (values e (cdr r1))]
          [else (parse-err "missing )")])]
       [(h-id? t)
        (define name (h-id-s t))
        (define r (cdr ts))
        (define starts-paren (and (pair? r) (op? (car r) "(")))
        (define lit (and (not (set-member? scope name)) (not starts-paren) (doc2-find (hum-doc h) name '("literal"))))
        (cond
          [lit (values (TNum (car (entry-rhs lit))) r)]
          [else
           (define hd (if (or (set-member? scope name) (not (doc2-find (hum-doc h) name '("value")))) (var name) (var (string-append "hum:" name))))
           (cond
             [(and (pair? r) (op? (car r) "("))
              (cond
                [(and (pair? (cdr r)) (op? (cadr r) ")")) (values (TApp hd '()) (cddr r))]
                [else (let-values ([(args r2) (call-args h (cdr r) scope)]) (values (TApp hd args) r2))])]
             [else (values hd r)])])]
       [else (parse-err (string-append "unexpected " (show-tok t)))])]))

(define (list-items h ts scope)
  (let loop ([r ts] [out '()])
    (define-values (a r1) (hum-expr h r 0 scope))
    (if (and (pair? r1) (op? (car r1) ","))
        (loop (cdr r1) (cons a out))
        (values (reverse (cons a out)) r1))))

(define (call-args h ts scope)
  (let loop ([r ts] [out '()])
    (define-values (a r1) (hum-expr h r 0 scope))
    (define out2 (cons a out))
    (cond
      [(null? r1) (oob)]
      [(op? (car r1) ",") (loop (cdr r1) out2)]
      [(op? (car r1) ")") (values (reverse out2) (cdr r1))]
      [else (parse-err "missing ) in call")])))

(define (hum-expr h ts minprec scope)
  (when (null? ts) (oob))
  ;; lambda:  x in Class |-> body
  (define lam
    (and (h-id? (car ts)) (pair? (cdr ts)) (h-id? (cadr ts)) (string=? (h-id-s (cadr ts)) "in")
         (let-values ([(c r1) (class-expr h (cddr ts))])
           (and (pair? r1) (op? (car r1) "|->")
                (let ([name (h-id-s (car ts))])
                  (let-values ([(body r3) (hum-expr h (cdr r1) 0 (set-add scope name))])
                    (cons (TLam (list (cons name c)) body) r3)))))))
  (cond
    [lam (values (car lam) (cdr lam))]
    [else
     (define t0 (car ts))
     (define key (op-key t0))
     (define-values (left0 r0)
       (cond
         [(and key (hash-has-key? (hum-prefix h) key) (not (and (h-id? t0) (set-member? scope key))))
          (let-values ([(arg r1) (hum-expr h (cdr ts) (hash-ref (hum-prefix h) key) scope)])
            (values (app (string-append "hum:prefix " key) (list arg)) r1))]
         [else (atom h ts scope)]))
     (let loop ([left left0] [r r0])
       (define op (and (pair? r) (op-key (car r))))
       (define info (and op (hash-ref (hum-infix h) op #f)))
       (cond
         [(and info (>= (car info) minprec))
          (let-values ([(right r1) (hum-expr h (cdr r) (if (string=? (cdr info) "infixr") (car info) (+ (car info) 1)) scope)])
            (loop (app (string-append "hum:" op) (list left right)) r1))]
         [else (values left r)]))]))

;; statements
(define (spec-name h name)
  (define e (doc2-find (hum-doc h) name '("value")))
  (if (and e (= (length (entry-rhs e)) 1) (not (all-bin-chars? (car (entry-rhs e))))) (car (entry-rhs e)) name))

(define (type-to-term t)
  (match t
    [(V n) (var n)]
    [(K n '()) (var n)]
    [(K n a) (TApp (var n) (map type-to-term a))]
    ['F (var "⊥")]))

(define (tok-text t)
  (match t [(h-num s) s] [(h-str s) s] [(h-id s) s] [(h-op s) s] [(h-chr c) (cp->string c)]))

(define (param-list ts)
  (let loop ([r ts] [out '()])
    (cond
      [(null? r) (oob)]
      [(op? (car r) ")") (values (reverse out) (cdr r))]
      [else
       (define out2 (cons (tok-text (car r)) out))
       (define r2 (cdr r))
       (loop (if (and (pair? r2) (op? (car r2) ",")) (cdr r2) r2) out2)])))

(define (hum-statement h line)
  (define ts (lex-hum line))
  (define k (position (lambda (t) (and (h-id? t) (string=? (h-id-s t) "subseteq"))) ts))
  (cond
    [k
     (define-values (a ra) (class-expr h (take* k ts)))
     (define-values (b rb) (class-expr h (drop* (+ k 1) ts)))
     (unless (and (null? ra) (null? rb)) (parse-err "assertion failed"))
     (list (SFact (app "⊆" (list (type-to-term a) (type-to-term b)))))]
    [(and (pair? ts) (h-id? (car ts)))
     (define name (h-id-s (car ts)))
     (define r0 (cdr ts))
     (define-values (params r1) (if (and (pair? r0) (op? (car r0) "(")) (param-list (cdr r0)) (values '() r0)))
     (cond
       [(and (pair? r1) (h-id? (car r1)) (string=? (h-id-s (car r1)) "in"))
        (define-values (cls r3) (class-expr h (cdr r1)))
        (cond
          [(null? r3)
           (unless (null? params) (parse-err (format "~a: a declaration without := takes no parameters (an unknown is a number)" name)))
           (list (SDecl (spec-name h name) cls))]
          [(op? (car r3) ":=")
           (define sc (for/fold ([s (set)]) ([p (in-list params)]) (set-add s p)))
           (define-values (body r5) (hum-expr h (cdr r3) 0 sc))
           (define sp (spec-name h name))
           (when (pair? r5) (parse-err (string-append "unexpected " (show-tok (car r5)))))
           (list (SDecl sp cls) (SDef sp params body))]
          [else (parse-err "missing :=")])]
       [else (parse-err (format "declare the class first:  ~a in <Class> := …" name))])]
    [else (parse-err (format "statement must start with a name: ~a" (py-repr line)))]))

(define (hum-statements h text)
  (apply append (for/list ([l (in-list (hum-logical-lines text))]) (hum-statement h l))))
