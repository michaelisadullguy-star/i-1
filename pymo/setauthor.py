"""setauthor.py -- put the author's name and email into LICENSE, COMMERCIAL.md, haskimo.cabal and the README sources (they hold the placeholders
AUTHOR_NAME and AUTHOR_EMAIL), then rebuild the README.

  python3 pymo/setauthor.py "Ada Lovelace" "ada@example.org"        replaces the placeholders everywhere
  python3 pymo/setauthor.py --check                                  lists the files that still hold a placeholder (exit status 1 if any)
"""
import os, sys, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ['LICENSE', 'COMMERCIAL.md', 'haskimo.cabal', 'readme/part1.md', 'readme/part8.md', 'README.md']
def main():
    if sys.argv[1:] == ['--check']:
        left = [f for f in FILES if os.path.exists(os.path.join(ROOT, f)) and ('AUTHOR_NAME' in open(os.path.join(ROOT, f), encoding='utf-8').read() or 'AUTHOR_EMAIL' in open(os.path.join(ROOT, f), encoding='utf-8').read())]
        print('placeholders left in: ' + ', '.join(left) if left else 'no placeholder left')
        return 1 if left else 0
    if len(sys.argv) != 3 or '@' not in sys.argv[2]:
        sys.exit(__doc__)
    name, email = sys.argv[1], sys.argv[2]
    for f in FILES:
        p = os.path.join(ROOT, f)
        if not os.path.exists(p): continue
        s = open(p, encoding='utf-8').read()
        t = s.replace('AUTHOR_NAME', name).replace('AUTHOR_EMAIL', email)
        if t != s: open(p, 'w', encoding='utf-8').write(t); print('updated', f)
    return 0
if __name__ == '__main__':
    sys.exit(main())
