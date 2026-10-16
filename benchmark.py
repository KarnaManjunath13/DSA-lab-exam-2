"""
benchmark.py  -  Compare Trie, BST and dict implementations (time).

Usage:
    python generate_data.py          # once, creates data/words_<D>.txt
    python benchmark.py              # runs all six files, saves plots + CSV
    python benchmark.py --show       # also opens the Matplotlib windows

For every test file and every implementation three times are measured:
    1. construction : read the file, tokenize it and build the complete index
                      (including the linked lists of line numbers)
    2. search       : look up 100,000 random words (90% present, 10% absent)
    3. printing     : write the index to a file in lexicographic order
                      (for the dict this includes sorting the keys)

Fairness notes:
  * all three implementations use the same tokenizer, file reading and queue
  * the same 100,000 query words are used for the three implementations
  * Python's garbage collector is switched off while a step is being timed
    (it would otherwise add random pauses when millions of objects are created)
    and a full collection is done between runs
  * the three output files are compared by hash to prove they are identical

Results are saved to results.csv and to PNG graphs.
"""

import argparse
import csv
import gc
import hashlib
import os
import random
import sys
import time

from index_common import build_index, write_index, tokenize
from trie_index import TrieIndex
from bst_index import BSTIndex
from dict_index import DictIndex
from generate_data import DEFAULT_SIZES, data_filename

IMPLEMENTATIONS = [("Trie", TrieIndex), ("BST", BSTIndex), ("Dict", DictIndex)]
ACTIONS = [("build", "Construction time"),
           ("search", "Search time (100000 words)"),
           ("print", "Printing time (sorted order)")]


def load_vocabulary(path):
    """All distinct words of the file (done outside the timed sections)."""
    vocab = set()
    with open(path, "r", encoding="latin-1") as f:
        for line in f:
            vocab.update(tokenize(line))
    return sorted(vocab)


def make_queries(vocab, count, rng, miss_ratio=0.1):
    """
    `count` random query words.  About `miss_ratio` of them are words that are
    NOT in the file: a DEL character (not printable, so never in the files) is
    appended to a real word.
    """
    queries = []
    for _ in range(count):
        word = rng.choice(vocab)
        if rng.random() < miss_ratio:
            word += "\x7f"
        queries.append(word)
    return queries


def timed(func):
    """Run func() with the garbage collector off; return (result, seconds)."""
    gc.collect()
    gc.disable()
    try:
        start = time.perf_counter()
        result = func()
        elapsed = time.perf_counter() - start
    finally:
        gc.enable()
    return result, elapsed


def measure(index_class, input_path, output_path, queries):
    index = index_class()
    _, t_build = timed(lambda: build_index(index, input_path))

    def do_search():
        found = 0
        for word in queries:
            if index.search(word) is not None:
                found += 1
        return found

    found, t_search = timed(do_search)
    _, t_print = timed(lambda: write_index(index, output_path))
    distinct = len(index)
    del index
    gc.collect()
    return {"build": t_build, "search": t_search, "print": t_print,
            "distinct": distinct, "found": found}


def file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def draw(ax, results, sizes, key, title):
    for name, _ in IMPLEMENTATIONS:
        ys = [results[(name, n)][key] for n in sizes]
        ax.plot(sizes, ys, marker="o", label=name)
    ax.set_xscale("log")
    ax.set_xlabel("Number of distinct words in the file")
    ax.set_ylabel("Time (seconds)")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()


def make_plots(results, sizes, out_dir, show):
    import matplotlib
    if not show:
        matplotlib.use("Agg")           # no window needed, just save PNG files
    import matplotlib.pyplot as plt

    # one figure with the three graphs side by side
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    for ax, (key, title) in zip(axes, ACTIONS):
        draw(ax, results, sizes, key, title)
    fig.tight_layout()
    combined = os.path.join(out_dir, "benchmark_all.png")
    fig.savefig(combined, dpi=150)
    print(f"Saved {combined}")

    # and one separate figure per action
    for key, title in ACTIONS:
        fig2, ax2 = plt.subplots(figsize=(6.5, 4.8))
        draw(ax2, results, sizes, key, title)
        fig2.tight_layout()
        path = os.path.join(out_dir, f"benchmark_{key}.png")
        fig2.savefig(path, dpi=150)
        print(f"Saved {path}")
        if not show:
            plt.close(fig2)
    if show:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Benchmark Trie / BST / dict indexes.")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--out-dir", default="results", help="folder for CSV, PNG, index files")
    parser.add_argument("--sizes", type=int, nargs="+", default=DEFAULT_SIZES)
    parser.add_argument("--queries", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--show", action="store_true", help="open the plot windows")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    rng = random.Random(args.seed)
    results = {}
    done_sizes = []

    for d in args.sizes:
        path = data_filename(args.data_dir, d)
        if not os.path.exists(path):
            sys.exit(f"Missing {path}. Run generate_data.py first.")
        print(f"\n=== {path} ===")
        vocab = load_vocabulary(path)
        queries = make_queries(vocab, args.queries, rng)

        hashes = {}
        for name, cls in IMPLEMENTATIONS:
            out_path = os.path.join(args.out_dir, f"index_{name.lower()}_{d}.txt")
            res = measure(cls, path, out_path, queries)
            results[(name, d)] = res
            hashes[name] = file_hash(out_path)
            print(f"{name:5s} distinct={res['distinct']:7d} found={res['found']:6d}  "
                  f"build={res['build']:8.3f}s  search={res['search']:7.3f}s  "
                  f"print={res['print']:7.3f}s")
        if len(set(hashes.values())) != 1:
            print("WARNING: the three implementations produced DIFFERENT index files!")
        else:
            print("Check: all three index files are identical.")
        done_sizes.append(d)

    csv_path = os.path.join(args.out_dir, "results.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["distinct_words", "implementation", "build_s", "search_s", "print_s"])
        for d in done_sizes:
            for name, _ in IMPLEMENTATIONS:
                r = results[(name, d)]
                w.writerow([d, name, f"{r['build']:.4f}", f"{r['search']:.4f}", f"{r['print']:.4f}"])
    print(f"\nSaved {csv_path}")

    make_plots(results, done_sizes, args.out_dir, args.show)


if __name__ == "__main__":
    main()
