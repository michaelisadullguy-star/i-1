# Encodings and checksums (`lib/encode.imo`)

Twenty-two functions on bytes and text, written in the human notation (`libsrc/encode.hum.imo`) and translated into spec notation by `libsrc/build.sh`.  **Bytes are lists of natural
numbers below 256.**  A function that can fail returns a list of at most one element: `[]` when the input is not valid, `[x]` otherwise (the convention of `rxprefix` and `lookup`).

## Binary operations on naturals

The language's own `band`, `bor`, `bxor`, `shl` and `shr` act on the digits of the base *i*−1, which is what the arithmetic is built on.  The usual operations on the *binary* digits of a
natural number are separate functions:

| function | class | meaning |
|:--|:--|:--|
| `binand a b`, `binor a b`, `binxor a b` | ℕ → ℕ → ℕ | the bitwise and, or, exclusive or (`&`, `\|`, `^`) |
| `binshl a k`, `binshr a k` | ℕ → ℕ → ℕ | `a · 2ᵏ` and `⌊a / 2ᵏ⌋` |
| `graycode n`, `fromgray g` | ℕ → ℕ | the reflected binary Gray code `n xor ⌊n/2⌋` and its inverse |

## Text and bytes

| function | class | meaning |
|:--|:--|:--|
| `utf8bytes s` | 𝕊 → 𝔏 ℕ | the UTF-8 bytes of a string (`s.encode('utf-8')`) |
| `utf8string bs` | 𝔏 ℕ → 𝔏 𝕊 | the string of valid UTF-8 bytes, strict like Python: no overlong forms, no surrogates, nothing above U+10FFFF; `[]` otherwise |
| `hexencode bs`, `hexdecode s` | 𝔏 ℕ → 𝕊, 𝕊 → 𝔏 (𝔏 ℕ) | lower-case hexadecimal; decoding takes either case and fails on an odd length or a character that is not a digit |
| `base64encode bs`, `base64decode s` | 𝔏 ℕ → 𝕊, 𝕊 → 𝔏 (𝔏 ℕ) | RFC 4648 with padding; decoding is strict (`validate=True` of Python): the length is a multiple of 4, `=` only at the end |
| `percentencode s`, `percentdecode s` | 𝕊 → 𝕊, 𝕊 → 𝔏 𝕊 | percent-encoding of the UTF-8 bytes; the letters, digits and `- . _ ~` stay (`quote(s, safe='')`); decoding fails on a bad escape, on a character above 127 and on bytes that are not UTF-8 (`+` is not a space) |
| `vigenere key s`, `unvigenere key s` | 𝕊 → 𝕊 → 𝕊 | the Vigenère cipher on the ASCII letters of `s` (case kept, other characters stay, the key advances on letters only); the key is made of ASCII letters |
| `numwords n` | ℕ → 𝕊 | the English name: `numwords(123)` is `one hundred twenty-three`, for `n` below 10²¹ |

## Checksums

| function | class | meaning |
|:--|:--|:--|
| `adler32 bs` | 𝔏 ℕ → ℕ | the Adler-32 of zlib (`zlib.adler32`) |
| `crc32 bs` | 𝔏 ℕ → ℕ | the CRC-32 of zlib, gzip and PNG (`zlib.crc32`): the register is a list of 32 Booleans and the polynomial is applied bit by bit |
| `luhncheck s` | 𝕊 → 𝔹 | the check of Luhn for a non-empty string of ASCII digits |
| `luhndigit s` | 𝕊 → ℕ | the check digit that completes `s` |

`tests/test_encode.py` compares all of them with `base64`, `binascii`, `urllib.parse`, `zlib` and the plain textbook algorithms on random input, including every kind of invalid input that Python rejects.
