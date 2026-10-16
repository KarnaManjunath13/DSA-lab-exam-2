"""
index_common.py
---------------
Code shared by all three index implementations (Trie, BST, dict).

It contains:
  * tokenize()      - splits a line of text into words
  * LineQueue       - a linked-list queue that stores the line numbers of a word
  * build_index()   - reads the input file and fills any index object
  * write_index()   - writes any index object to the output file (sorted order)
  * run_cli()       - the command-line front end used by the three scripts

Every index class (TrieIndex, BSTIndex, DictIndex) offers the same interface:
    insert(word, line_no)   add one occurrence of `word` found on `line_no`
    search(word)            return the word's LineQueue, or None if absent
    items_sorted()          yield (word, LineQueue) in ASCII (lexicographic) order
    __len__()               number of distinct words
"""

import re
import sys
import time

# A word is any run of characters that are NOT separators.
# Separators allowed by the problem statement: blank, line break, full stop,
# comma, colon, semicolon.  (Tab and carriage return are also treated as
# separators so that files written on other systems do not break the program.)
# Every other character (all printable ASCII) is part of a word.
_WORD_RE = re.compile(r"[^ \t\r\n.,:;]+")


def tokenize(line):
    """Return the list of words in `line` (empty list for a blank line)."""
    return _WORD_RE.findall(line)


class _LineNode:
    """One node of the linked list: a line number and a pointer to the next."""
    __slots__ = ("number", "next")

    def __init__(self, number):
        self.number = number
        self.next = None


class LineQueue:
    """
    Linked-list QUEUE of line numbers.

    New line numbers are added at the tail (enqueue) in O(1) time, so the
    numbers are always stored in the order in which they were found, which is
    increasing order because the file is read from top to bottom.

    If a word occurs several times on the SAME line, that line number is stored
    only once (the check is O(1): compare with the current tail).
    """
    __slots__ = ("head", "tail", "size")

    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def enqueue(self, number):
        """Append `number` unless it is already the last number stored."""
        tail = self.tail
        if tail is not None and tail.number == number:
            return False                      # same word twice on one line
        node = _LineNode(number)
        if tail is None:
            self.head = node                  # first element
        else:
            tail.next = node                  # link after the old tail
        self.tail = node
        self.size += 1
        return True

    def __iter__(self):
        node = self.head
        while node is not None:
            yield node.number
            node = node.next

    def __len__(self):
        return self.size

    def __str__(self):
        return ", ".join(map(str, self))


def build_index(index, input_path):
    """
    Read `input_path` line by line and insert every word into `index`.
    Line numbers start at 1; blank lines still count as lines.
    latin-1 is used so that any byte can be read without a decoding error and
    characters are compared in plain byte (ASCII) order.
    """
    with open(input_path, "r", encoding="latin-1") as f:
        for line_no, line in enumerate(f, start=1):
            for word in tokenize(line):
                index.insert(word, line_no)
    return index


def write_index(index, output_path):
    """
    Write the index to `output_path`, one word per line, in lexicographic
    (ASCII) order:      word 3, 17, 42
    Space and comma cannot occur inside a word, so each line is unambiguous.
    """
    with open(output_path, "w", encoding="latin-1", newline="\n") as out:
        for word, queue in index.items_sorted():
            out.write(f"{word} {queue}\n")


def run_cli(index_class, title):
    """
    Command-line front end:
        python <script>.py <input_text_file> <output_index_file>
    """
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <input_text_file> <output_index_file>",
              file=sys.stderr)
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]
    index = index_class()
    try:
        t0 = time.perf_counter()
        build_index(index, input_path)
        t1 = time.perf_counter()
        write_index(index, output_path)
        t2 = time.perf_counter()
    except OSError as err:
        print(f"File error: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"[{title}] distinct words: {len(index)}")
    print(f"[{title}] construction time: {t1 - t0:.3f} s")
    print(f"[{title}] printing time:     {t2 - t1:.3f} s")
    print(f"[{title}] index written to {output_path}")
