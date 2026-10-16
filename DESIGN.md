# Index Generation – Design Description

Chanakya University, Laboratory Examination 2 project.

## 1. What the program does

It reads a text file, finds every word and writes an index file: each distinct
word on its own line, in lexicographic (ASCII) order, followed by the line
numbers where it occurs.

```
the cat sat          a 3
the dog sat    -->   cat 1, 3
a cat ran            dog 2
                     ran 3
                     sat 1, 2
                     the 1, 2
```

It is implemented three times, with the same interface, using a **Trie**, a
**Binary Search Tree** and a **Python dictionary**.

## 2. Files

| File | Purpose |
|------|---------|
| `index_common.py` | tokenizer, `LineQueue` (linked list), `build_index`, `write_index`, command-line runner |
| `trie_index.py` | Trie version (runnable) |
| `bst_index.py` | BST version (runnable) |
| `dict_index.py` | dictionary version (runnable) |
| `generate_data.py` | creates the six large test files |
| `benchmark.py` | times the three versions and plots the results with Matplotlib |
| `test_index.py` | test cases (`python test_index.py`) |

## 3. How to run

```
python trie_index.py  input.txt  output_index.txt
python bst_index.py   input.txt  output_index.txt
python dict_index.py  input.txt  output_index.txt

python test_index.py                 # test cases
python generate_data.py              # six files in ./data (1,200,000 words each)
python benchmark.py                  # timings -> ./results (CSV + PNG graphs)
python benchmark.py --show           # additionally open the Matplotlib windows
```

Only the Python standard library is needed, except Matplotlib for the graphs.

## 4. Design

**Reading words.** The file is read line by line (line numbers start at 1;
blank lines count). A word is a maximal run of characters that are not a
separator. Separators are blank, line break, full stop, comma, colon and
semicolon (tab and carriage return are also accepted). Every other printable
ASCII character belongs to a word, so `a-b`, `#x` or `(z)` are single words.
Words are case sensitive and are compared in ASCII order.

**Line numbers: linked-list queue.** Each distinct word owns a `LineQueue`:
a singly linked list with `head` and `tail` pointers. A new line number is
added at the tail in O(1), so numbers stay in increasing order. If the same
word appears twice on one line, the line number is stored once (compare with
the tail). This is how repeated words are handled: a word is never stored
twice, it only gets another line number.

**Trie.** Each node has a dict `{character: child}` (created only when the
node gets its first child) and, if a word ends there, the word's `LineQueue`.
Insert and search follow the characters of the word: O(L) for word length L.
Sorted printing is a pre-order depth-first walk visiting children in sorted
character order, so a word comes before the longer words that extend it.

**BST.** Each node holds a word, its `LineQueue`, and left/right pointers;
smaller words go left, larger go right. Insert and search cost O(h) for tree
height h (about log n for random input, n for sorted input; the tree is not
self-balancing). Sorted printing is an in-order traversal. Insert, search and
traversal are iterative, so a degenerate tree cannot cause a recursion error.

**Dictionary.** `word -> LineQueue`. Insert and search are O(1) on average.
A dict is unordered, so printing sorts the keys first: O(n log n).

| Operation | Trie | BST | Dict |
|-----------|------|-----|------|
| Insert / search | O(L) | O(L · h) | O(L) average |
| Sorted output | O(total chars) | O(n) | O(n log n) |

(L = word length; BST comparisons of strings cost up to O(L) each.)

## 5. Performance experiment

`generate_data.py` creates six files of 1,200,000 words each, with exactly
1000, 5000, 10000, 50000, 100000 and 500000 distinct words (random words of
3–9 characters over all printable ASCII, mostly lowercase letters; fixed seed).

`benchmark.py` measures, for each file and each implementation:

1. **Construction** – read file + tokenize + build the complete index with
   linked lists.
2. **Search** – 100,000 random words (90% present, 10% absent), the same
   words for all three implementations.
3. **Printing** – write the index in lexicographic order (includes sorting for
   the dictionary).

Garbage collection is disabled during each timed step and run in between.
The three output files are compared by hash to confirm they are identical.
Results go to `results/results.csv` and the graphs to `results/benchmark_*.png`.

## 6. Test cases (`test_index.py`)

Tokenizer separators and special characters; the queue; the `the cat sat`
example; apple/banana example with blank lines; same word twice on one line;
ASCII ordering (`!`, digits, uppercase, `_`, lowercase, `~`); prefix words
(`a`, `app`, `apple`); case sensitivity; empty file; separator-only file; no
trailing newline; Windows line endings; search hits and misses; 3000 sorted
words (degenerate BST); 1500 random lines compared across all three
implementations; command-line usage and error messages.

## 7. Notes

* The 500,000-distinct-word run needs roughly 500 MB of RAM (pure-Python
  nodes are large). Use `--sizes` in both scripts for a smaller test.
* Timing numbers depend on the machine; run `benchmark.py` on your own
  computer and use your own graphs in the submission.
