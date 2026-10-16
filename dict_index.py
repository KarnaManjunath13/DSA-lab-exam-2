"""
dict_index.py  -  Index generation using a Python DICTIONARY.

Usage:  python dict_index.py <input_text_file> <output_index_file>

Design
------
A Python dict (hash table) maps each word (the key) to its LineQueue (linked
list of line numbers).

* insert / search take O(1) time on average (hashing the word costs O(L)).
* A dict does not keep words sorted, so the printing step must sort the keys.
  sorted() on str keys compares by code point, which for ASCII is ASCII order.
  Sorting costs O(n log n), and that cost is part of the "printing" time.
"""

from index_common import LineQueue, run_cli


class DictIndex:
    def __init__(self):
        self.table = {}

    def insert(self, word, line_no):
        """Add one occurrence of `word` found on line `line_no`."""
        queue = self.table.get(word)
        if queue is None:                      # first time this word is seen
            queue = self.table[word] = LineQueue()
        queue.enqueue(line_no)                 # repeated words just add a line number

    def search(self, word):
        """Return the word's LineQueue, or None if the word is not present."""
        return self.table.get(word)

    def items_sorted(self):
        """Yield (word, LineQueue) in ASCII lexicographic order."""
        table = self.table
        for word in sorted(table):             # keys must be sorted explicitly
            yield word, table[word]

    def __len__(self):
        return len(self.table)


if __name__ == "__main__":
    run_cli(DictIndex, "Dict")
