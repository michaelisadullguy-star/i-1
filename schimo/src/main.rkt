#lang racket/base
;; main.rkt -- command line of Schimo, the Racket (Scheme) interpreter of i-1 (port of ocamimo/src/main.ml and rustimo/src/main.rs).
;;   schimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  schimo FILE...)
;;   schimo check   FILE...                                load the prelude and FILE(s), run the class checker
;;   schimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table
;;   schimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class (value, stream element N, tree, string, Bool)
;;   schimo text    FILE... NAME                           evaluate NAME as a String and print it
(require racket/list racket/match racket/set
         "base.rkt" "syntax.rkt" "layers.rkt" "hum.rkt" "types.rkt" "core.rkt" "program.rkt" "output.rkt")

(define usage
  (string-append
   "schimo -- Schimo, the Racket (Scheme) interpreter of i-1 (same commands and output as Pymo, Haskimo, Rustimo and OCamimo)\n\n"
   "  schimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  schimo FILE...)\n"
   "  schimo check   FILE...                                load the prelude and FILE(s), run the class checker\n"
   "  schimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table\n"
   "  schimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class (value, stream element N, tree, string, Bool)\n"
   "  schimo text    FILE... NAME                           evaluate NAME as a String and print it\n\n"
   "`run` prints main ∶ 𝕊 as text, a list or stream of strings line by line, and any other value as a normal-form term in the output\n"
   "notation: --out, else an `@out bin|spec|hum` line in the program, else the notation main is written in.  --n N picks the stream\n"
   "element shown for a stream (default 10), or the number of lines of a stream of strings.\n\n"
   "FILE notation follows the extension:  x.imo / x.spec.imo = spec,  x.hum.imo = human,  x.bin.imo = binary (prelude.bin.imo is trusted).\n"))

(define out (current-output-port))
(define (put s) (write-string s out) (void))
(define (line s) (write-string s out) (write-char #\newline out))

(define (load-files files build?)
  (define srcs
    (for/list ([f (in-list files)])
      (define text
        (with-handlers ([bad-utf8? (lambda (e) (raise (host-err 'parse (format "~a: hGetContents: invalid argument (~a)" f (bad-utf8-msg e)))))]
                        [exn:fail:filesystem? (lambda (e)
                                                (raise (host-err 'parse (format "~a: openFile: ~a" f
                                                                                (if (file-exists? f) (exn-message e) "does not exist (No such file or directory)")))))])
          (read-utf8 f)))
      (source-file f text)))
  (define prelude (filter (lambda (f) (ends-with? f "prelude.bin.imo")) files))
  (define p (load-program srcs prelude (null? prelude)))
  (define miss (missing p))
  (unless (null? miss) (parse-err (string-append "these symbols are used and not defined: " (string-join* miss " "))))
  (when (and build? (null? (program-errors p))) (build-machine! p))
  p)

(define (report-errors p)
  (for ([e (in-list (program-errors p))])
    (define f (car e))
    (define w (cadr e))
    (define m (caddr e))
    (line (format "error in ~a: ~a" (basename f) (if (starts-with? m w) m (string-append w ": " m))))))

;; ---------------------------------------------------------------- values of ℚ[i], as Pymo shows them: a pair of exact rationals
(define (qval m v)
  (define-values (p d) (to-pair m v))
  (define a (gi-of m p))
  (define b (gi-of m d))
  (define n (+ (* (car b) (car b)) (* (cdr b) (cdr b))))
  (when (zero? n) (eval-err "Ratio has zero denominator"))
  (cons (/ (+ (* (car a) (car b)) (* (cdr a) (cdr b))) n)
        (/ (- (* (cdr a) (car b)) (* (car a) (cdr b))) n)))

(define (show-frac r) (if (integer? r) (number->string r) (format "~a/~a" (numerator r) (denominator r))))

(define (qfmt m v)
  (define q (qval m v))
  (define re (car q))
  (define im (cdr q))
  (define s (if (zero? im) (show-frac re) (format "~a + ~a i" (show-frac re) (show-frac im))))
  (define tail (if (zero? im) "" (format " + ~a i" (fmt-g 12 (exact->inexact im)))))
  (format "~a   (≈ ~a~a)" s (fmt-g 12 (exact->inexact re)) tail))

(define (sfmt m v)
  (define o (open-output-string))
  (let loop ([cur v])
    (define c (cell-or-nil m cur))
    (when (vcons? c)
      (define q (qval m (vcons-h c)))
      (define k (let ([t (truncate (car q))]) (if (and (>= t (- (expt 2 63))) (< t (expt 2 63))) t #xfffd)))
      (write-char (cp->char k) o)
      (loop (vcons-t c))))
  (get-output-string o))

(define (tfmt p v n)
  (define m (program-machine p))
  (define left-f (val p "◀"))
  (define right-f (val p "▶"))
  (cond
    [(to-bool m (app-th m left-f (vector v)))
     (define-values (a b) (to-pair m (app-th m right-f (vector v))))
     (define sa (tfmt p a n))
     (define sb (tfmt p b n))
     (format "⟨~a, ~a⟩" sa sb)]
    [else
     (define leaf0 (app-th m right-f (vector v)))
     (define leaf (if n (stream-nth m leaf0 n) leaf0))
     (define q (qval m leaf))
     (if n
         (string-append (fmt-g 10 (exact->inexact (car q))) (if (zero? (cdr q)) "" (format " + ~a i" (fmt-g 10 (exact->inexact (cdr q))))))
         (if (zero? (cdr q)) (show-frac (car q)) (format "(~a + ~a i)" (show-frac (car q)) (show-frac (cdr q)))))]))

;; evaluate NAME and print it according to its declared class
(define (show-name p name n)
  (define c (program-checker p))
  (define m (program-machine p))
  (define cls (let ([l (hash-ref (checker-sigs c) name '())]) (if (pair? l) (norm c (car l)) (eval-err "Prelude.head: empty list"))))
  (define v (val p name))
  (define hd (if (K? cls) (K-name cls) ""))
  (cond
    [(and (K? cls) (or (equal? hd "𝔖") (equal? hd "ℝ")))
     (define k (or n 10))
     (format "element ~a of the stream:  ~a" k (qfmt m (stream-nth m v k)))]
    [(and (K? cls) (equal? hd "𝔏") (= (length (K-args cls)) 1) (K? (car (K-args cls))) (equal? (K-name (car (K-args cls))) "𝕮")) (sfmt m v)]
    [(and (K? cls) (equal? hd "𝔗") (= (length (K-args cls)) 1))
     (define streams (let ([a (car (K-args cls))]) (and (K? a) (equal? (K-name a) "𝔖"))))
     (define k (or n 10))
     (define body (tfmt p v (and streams k)))
     (string-append (if streams (format "element ~a of each leaf:  " k) "") body)]
    [(equal? hd "𝔹") (if (to-bool m v) "true" "false")]
    [(contains-sub? (show-type cls) "Ω") (show-value (printer p "hum" 10) v cls)]
    [else (qfmt m v)]))

;; ---------------------------------------------------------------- commands
;; remove  OPT value  from an argument list: (cons value-or-#f rest)
(define (take-opt opt args)
  (define i (position (lambda (a) (equal? a opt)) args))
  (if (and i (< (+ i 1) (length args)))
      (cons (list-ref args (+ i 1)) (append (take* i args) (drop* (+ i 2) args)))
      (cons #f args)))

(define (read-int s)
  (define t (strip s))
  (if (and (> (string-length t) 0) (for/and ([c (in-string t)]) (and (char>=? c #\0) (char<=? c #\9))))
      (string->number t 10)
      (eval-err "Prelude.read: no parse")))

(define (run-cmd args0)
  (define r1 (take-opt "--out" args0))
  (define o (car r1))
  (define r2 (take-opt "--n" (cdr r1)))
  (define n-opt (car r2))
  (define rest (cdr r2))
  (cond
    [(and o (not (member o modes))) (line (string-append "--out takes one of " (string-join* modes ", "))) 2]
    [else
     (define p (load-files rest #t))
     (cond
       [(pair? (program-errors p)) (report-errors p) 1]
       [else
        (define n (and n-opt (read-int n-opt)))
        (with-handlers ([(host-err-of? 'print) (lambda (e) (line (string-append "error: " (host-err-msg e))) 1)])
          (run-main p o n put)
          0)])]))

(define (translate-cmd rest)
  (define i (position (lambda (a) (equal? a "--to")) rest))
  (define to (if (and i (< (+ i 1) (length rest))) (list-ref rest (+ i 1)) (eval-err "--to is missing")))
  (define files (filter (lambda (x) (and (not (equal? x "--to")) (not (equal? x to)))) rest))
  (define p (load-files files #f))
  (cond
    [(pair? (program-errors p)) (report-errors p) 1]
    [else
     (cond
       [(equal? to "spec") (put (spec-text p))]
       [else
        (put (bin-text p))
        (when (pair? (doc1-local (program-doc1 p))) (put (string-append "\n" (local-table p))))])
     0]))

(define (file? x) (file-exists? x))

(define (query-cmd cmd rest)
  (define-values (files name n)
    (cond
      [(equal? cmd "check") (values rest #f #f)]
      [else
       (define fs (filter file? rest))
       (define tl (filter (lambda (x) (not (file? x))) rest))
       (when (null? tl) (parse-err "a name is expected"))
       (values fs (car tl) (and (pair? (cdr tl)) (read-int (cadr tl))))]))
  (define p (load-files files (not (equal? cmd "check"))))
  (cond
    [(pair? (program-errors p)) (report-errors p) 1]
    [(equal? cmd "check") (line (format "ok: ~a statements checked" (length (user-statements p)))) 0]
    [else
     (define nm (spec-name (program-hum p) (or name "")))
     (define r (with-handlers ([(lambda (e) (and (host-err? e) (memq (host-err-kind e) '(unknown print)))) (lambda (e) e)])
                 (if (equal? cmd "text") (sfmt (program-machine p) (val p nm)) (show-name p nm n))))
     (cond [(host-err? r) (line (string-append "error: " (host-err-msg r))) 1]
           [else (line r) 0])]))

(define (dispatch args)
  (cond
    [(null? args) (put usage) 0]
    [(member (car args) '("-h" "--help")) (put usage) 0]
    [else
     (define cmd (car args))
     (define known '("run" "check" "eval" "text" "translate"))
     (define-values (cmd2 rest) (if (and (not (member cmd known)) (file? cmd)) (values "run" args) (values cmd (cdr args))))
     (cond
       [(equal? cmd2 "run") (run-cmd rest)]
       [(equal? cmd2 "translate") (translate-cmd rest)]
       [(member cmd2 '("check" "eval" "text")) (query-cmd cmd2 rest)]
       [else (put usage) 2])]))

(define (real-main args)
  (define code
    (with-handlers ([host-err? (lambda (e) (flush-output out) (eprintf "schimo: ~a\n" (host-err-msg e)) 1)]
                    [bad-utf8? (lambda (e) (flush-output out) (eprintf "schimo: ~a\n" (bad-utf8-msg e)) 1)]
                    [exn:fail? (lambda (e) (flush-output out) (eprintf "schimo: internal error: ~a\n" (exn-message e)) 1)])
      (dispatch args)))
  (flush-output out)
  code)

(module+ main
  (exit (real-main (vector->list (current-command-line-arguments)))))
