#lang racket/base
;; layers.rkt -- the three notation systems of i-1 and the system documents that connect them (port of ocamimo/src/layers.ml).
;;   bin   only  1 0 .  space ( ) newline;  numeral 1011  1.01;  symbol .B. (B a bit string, the code of the symbol, see doc 1);
;;         markers  . = ↦   .. = ≔   ... = ∶
;;   spec  unicode glyphs; the notation of the prelude (lib/*.imo); `⍝` starts a comment
;;   doc 1   [spec sbl] := [bin sbl]            one line per symbol
(require racket/list racket/match "base.rkt" "syntax.rkt")
(provide (all-defined-out))

;; ---------------------------------------------------------------- doc 1
(struct doc1 (s2b b2s [local #:mutable]))   ; local: program-local symbols (name . code), newest first

;; .B. with B a non-empty bit string
(define (bin-sym? s)
  (define n (string-length s))
  (and (>= n 3) (char=? (string-ref s 0) #\.) (char=? (string-ref s (- n 1)) #\.)
       (for/and ([i (in-range 1 (- n 1))]) (memv (string-ref s i) '(#\0 #\1)))))

(define (doc1-empty) (doc1 (make-hash) (make-hash) '()))
(define (copy-doc1 d) (doc1 (hash-copy (doc1-s2b d)) (hash-copy (doc1-b2s d)) (doc1-local d)))

(define (doc1-parse text)
  (define d (doc1-empty))
  (for ([ln0 (in-list (split-on text "\n"))])
    (define ln (strip ln0))
    (unless (or (string=? ln "") (starts-with? ln "⍝"))
      (define parts (split-on ln " := "))
      (unless (= (length parts) 2) (parse-err (format "doc1: bad line ~a" (py-repr ln))))
      (define a (strip (car parts)))
      (define b (strip (cadr parts)))
      (unless (bin-sym? b) (parse-err (format "doc1: bad binary symbol ~a" (py-repr b))))
      (when (or (hash-has-key? (doc1-s2b d) a) (hash-has-key? (doc1-b2s d) b)) (parse-err (format "doc1: duplicate ~a / ~a" a b)))
      (hash-set! (doc1-s2b d) a b)
      (hash-set! (doc1-b2s d) b a)))
  d)

;; the binary string without its high zeros; the larger of two; the successor
(define (bin-strip s)
  (define n (string-length s))
  (let loop ([i 0]) (if (and (< i n) (char=? (string-ref s i) #\0)) (loop (+ i 1)) (substring s i))))
(define (bin-less? a b)
  (let ([a (bin-strip a)] [b (bin-strip b)])
    (if (not (= (string-length a) (string-length b))) (< (string-length a) (string-length b)) (string<? a b))))
(define (bin-succ s)
  (define b (string-copy (bin-strip s)))
  (let loop ([i (- (string-length b) 1)])
    (cond [(and (>= i 0) (char=? (string-ref b i) #\1)) (string-set! b i #\0) (loop (- i 1))]
          [(>= i 0) (string-set! b i #\1) b]
          [else (string-append "1" b)])))

;; the next free code:  .<max + 1 in binary>.
(define (next-code d)
  (define m "")
  (for ([(b _) (in-hash (doc1-b2s d))])
    (define bits (substring b 1 (- (string-length b) 1)))
    (when (bin-less? m bits) (set! m bits)))
  (string-append "." (bin-succ m) "."))

;; the code of a symbol; a new local code is given when allowed
(define (doc1-code d name allow-new)
  (define b (hash-ref (doc1-s2b d) name #f))
  (cond
    [b b]
    [else
     (unless allow-new (parse-err (format "~a has no binary symbol in doc 1" (py-repr name))))
     (define nb (next-code d))
     (hash-set! (doc1-s2b d) name nb)
     (hash-set! (doc1-b2s d) nb name)
     (set-doc1-local! d (cons (cons name nb) (doc1-local d)))
     nb]))

;; add a symbol of a program-local table (not counted as a symbol the program created)
(define (doc1-add-local d a b) (hash-set! (doc1-s2b d) a b) (hash-set! (doc1-b2s d) b a))

;; the local table as text, in the format of doc 1
(define (doc1-render d header)
  (define out (open-output-string))
  (for ([h (in-list header)]) (write-string (format "⍝ ~a\n" h) out))
  (for ([e (in-list (reverse (doc1-local d)))]) (write-string (format "~a := ~a\n" (car e) (cdr e)) out))
  (get-output-string out))

;; ---------------------------------------------------------------- bin lexer / translators
;; tokens: 'BNl 'BOpen 'BClose (list 'BNum s) (list 'BMark s) (list 'BSym s)
(define (reserved-spec s) (cond [(string=? s ".") "↦"] [(string=? s "..") "≔"] [(string=? s "...") "∶"] [else #f]))
(define (reserved-bin s) (cond [(string=? s "↦") "."] [(string=? s "≔") ".."] [(string=? s "∶") "..."] [else #f]))

(define (lex-bin text)
  (define n (string-length text))
  (let loop ([i 0] [d 0] [out '()])
    (cond
      [(>= i n) (reverse out)]
      [else
       (define c (string-ref text i))
       (cond
         [(memv c '(#\space #\tab #\return)) (loop (+ i 1) d out)]
         [(char=? c #\newline) (loop (+ i 1) d (if (zero? d) (cons 'BNl out) out))]
         [(char=? c #\() (loop (+ i 1) (+ d 1) (cons 'BOpen out))]
         [(char=? c #\)) (loop (+ i 1) (- d 1) (cons 'BClose out))]
         [(memv c '(#\0 #\1 #\.))
          (define j (let l ([j i]) (if (and (< j n) (memv (string-ref text j) '(#\0 #\1 #\.))) (l (+ j 1)) j)))
          (define s (substring text i j))
          (define pts (for/sum ([ch (in-string s)]) (if (char=? ch #\.) 1 0)))
          (loop j d
                (cons (cond [(reserved-spec s) (list 'BMark s)]
                            [(<= pts 1) (list 'BNum s)]
                            [(bin-sym? s) (list 'BSym s)]
                            [else (parse-err (format "bad binary token ~a" (py-repr s)))])
                      out))]
         [else (parse-err (format "character ~a is not part of the binary notation" (py-repr (string c))))])])))

;; tokens to text (spaces only between atoms; newlines kept).  #f stands for a newline.
(define (render-toks toks)
  (define out (open-output-string))
  (define first? #t)
  (for ([t (in-list toks)])
    (cond
      [(not t) (write-char #\newline out) (set! first? #t)]
      [else
       (unless (or (string=? t ")") first?) (write-char #\space out))
       (write-string t out)
       (set! first? (string=? t "("))]))
  (get-output-string out))

;; bin text -> spec text, through doc 1 (and the program's local table)
(define (bin-to-spec-text text d)
  (render-toks
   (for/list ([t (in-list (lex-bin text))])
     (match t
       ['BNl #f]
       ['BOpen "("]
       ['BClose ")"]
       [(list 'BNum s) s]
       [(list 'BMark s) (reserved-spec s)]
       [(list 'BSym s) (or (hash-ref (doc1-b2s d) s #f)
                           (parse-err (format "binary symbol ~a is not defined in doc 1 (or the local table)" s)))]))))

;; the tokens of spec text re-spelled in bin notation (the shared part of the two translators)
(define (bin-of-spec-toks toks d allow-new strings-in-order)
  (define out '())
  (define (push s) (set! out (cons s out)))
  (for ([t (in-list toks)])
    (match t
      ['Open (push "(")]
      ['Close (push ")")]
      [(tk-num s) (push s)]
      [(tk-name n) (let ([r (reserved-bin n)]) (if r (push r) (push (doc1-code d n allow-new))))]
      [(tk-chr c)
       (define bc (doc1-code d "𝕔" allow-new))
       (push "(") (push bc) (push (int-numeral-text c)) (push ")")]
      [(tk-str s)
       (define cs (string->list s))
       (cond
         [strings-in-order
          (define bcons (doc1-code d "∷" allow-new))
          (define bchr (doc1-code d "𝕔" allow-new))
          (define bnil (doc1-code d "⊘" allow-new))
          (for ([ch (in-list cs)]) (push "(") (push bcons) (push "(") (push bchr) (push (int-numeral-text (char->integer ch))) (push ")"))
          (push bnil)
          (for ([_ (in-list cs)]) (push ")"))]
         [else
          (for ([ch (in-list cs)])
            (define bcons (doc1-code d "∷" allow-new))
            (define bchr (doc1-code d "𝕔" allow-new))
            (push "(") (push bcons) (push "(") (push bchr) (push (int-numeral-text (char->integer ch))) (push ")"))
          (push (doc1-code d "⊘" allow-new))
          (for ([_ (in-list cs)]) (push ")"))])]
      ['Nl (void)]))
  (reverse out))

;; the statements re-spelled in bin notation; new program-local symbols get codes in order of first use
(define (spec-statements-to-bin-text sts d allow-new)
  (render-toks
   (apply append
          (for/list ([st (in-list sts)])
            (append (bin-of-spec-toks (lex-spec (pp-statement st)) d allow-new #t) (list #f))))))

;; one spec term (as text) -> the same term in bin notation, through doc 1 (literals are expanded as the reader expands them)
(define (spec-term-to-bin text d) (render-toks (bin-of-spec-toks (lex-spec text) d #f #f)))

;; ---------------------------------------------------------------- files: default notation by extension, `@bin` `@spec` `@hum` section headers
(define (split-sections text def)
  (let loop ([lines (split-on text "\n")] [mode def] [cur '()] [acc '()])
    (cond
      [(null? lines) (reverse (if (null? cur) acc (cons (cons mode (apply-join (reverse cur))) acc)))]
      [else
       (define ln (car lines))
       (define s (strip ln))
       (if (member s '("@bin" "@spec" "@hum"))
           (loop (cdr lines) (substring s 1) '() (if (null? cur) acc (cons (cons mode (apply-join (reverse cur))) acc)))
           (loop (cdr lines) mode (cons ln cur) acc))])))
(define (apply-join lines) (string-join* lines "\n"))

(define (default-notation path)
  (cond [(ends-with? path ".bin.imo") "bin"] [(ends-with? path ".hum.imo") "hum"] [else "spec"]))
