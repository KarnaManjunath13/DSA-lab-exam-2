"""
generate_data.py  -  Create the six large test files for the benchmark.

Usage:
    python generate_data.py                       # six files, 1,200,000 words each
    python generate_data.py --total-words 50000 --sizes 100 500   # small quick test

Each file contains `--total-words` words (default 1,200,000, i.e. more than a
million) made of exactly D DISTINCT words, for D in 1000, 5000, 10000, 50000,
100000, 500000.  Every distinct word is guaranteed to appear at least once; the
remaining positions are filled with random repeats.

Words are 3-9 characters long.  Most characters are lowercase letters, but all
printable ASCII characters (except the separators  space . , : ;  ) can appear,
so the files also exercise the "all printable ASCII" requirement.  Words are
separated by blanks, commas, full stops, colons or semicolons, and some lines
are blank.  A fixed random seed makes the files reproducible.
"""

import argparse
import os
import random

DEFAULT_SIZES = [1000, 5000, 10000, 50000, 100000, 500000]

SEPARATOR_CHARS = " .,:;"
# printable ASCII (33..126) without the separator characters
_SPECIAL = [chr(c) for c in range(33, 127) if chr(c) not in SEPARATOR_CHARS]
_LOWER = [chr(c) for c in range(ord("a"), ord("z") + 1)]
# lowercase letters are repeated so that they make up most (~85%) of each word
_POOL = _LOWER * 20 + _SPECIAL

_JOINERS = [" ", " ", " ", "  ", ", ", ". ", ": ", "; "]


def data_filename(out_dir, distinct):
    return os.path.join(out_dir, f"words_{distinct}.txt")


def make_vocabulary(distinct, rng):
    """Return a list of exactly `distinct` different random words."""
    vocab = set()
    while len(vocab) < distinct:
        length = rng.randint(3, 9)
        vocab.add("".join(rng.choices(_POOL, k=length)))
    vocab = sorted(vocab)          # sort first so the result does not depend on set order
    rng.shuffle(vocab)
    return vocab


def write_file(path, distinct, total_words, seed):
    rng = random.Random(seed + distinct)
    vocab = make_vocabulary(distinct, rng)
    # every distinct word at least once, the rest are random repeats
    words = vocab + rng.choices(vocab, k=total_words - distinct)
    rng.shuffle(words)

    with open(path, "w", encoding="latin-1", newline="\n") as f:
        pos = 0
        while pos < len(words):
            n = rng.randint(5, 15)                     # words on this line
            chunk = words[pos:pos + n]
            pos += n
            parts = []
            for i, w in enumerate(chunk):
                parts.append(w)
                if i < len(chunk) - 1:
                    parts.append(rng.choice(_JOINERS))
            f.write("".join(parts) + "\n")
            if rng.random() < 0.02:                    # occasional blank line
                f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Generate benchmark text files.")
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--total-words", type=int, default=1_200_000)
    parser.add_argument("--sizes", type=int, nargs="+", default=DEFAULT_SIZES,
                        help="numbers of distinct words (one file for each)")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    for d in args.sizes:
        if d > args.total_words:
            raise SystemExit(f"distinct words ({d}) cannot exceed total words")
        path = data_filename(args.out_dir, d)
        print(f"Generating {path}  ({args.total_words} words, {d} distinct) ...")
        write_file(path, d, args.total_words, args.seed)
    print("Done.")


if __name__ == "__main__":
    main()
