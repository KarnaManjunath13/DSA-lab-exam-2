"""
trie_index.py  -  Index generation using a TRIE.

Usage:  python trie_index.py <input_text_file> <output_index_file>

Design
------
Each word is stored character by character: the path from the root to a node
spells a prefix.  A node where a complete word ends holds that word's
LineQueue (linked list of line numbers).

* Children are kept in a dict {character: node}, created only when a node gets
  its first child.  This supports ALL printable ASCII characters without
  allocating a 95-slot array per node, and leaf nodes use no dict at all.
* insert / search cost O(L) for a word of length L, independent of how many
  words are stored.
* Printing in lexicographic order is a pre-order depth-first walk that visits
  children in sorted character order.  A word is emitted before the longer
  words that extend it ("app" before "apple").  The walk uses an explicit
  stack, so there is no recursion-depth problem.
"""

from index_common import LineQueue, run_cli


class _TrieNode:
    __slots__ = ("children", "queue", "word")

    def __init__(self):
        self.children = None   # dict {char: _TrieNode} or None for a leaf
        self.queue = None      # LineQueue if a word ends here, else None
        self.word = None       # the complete word (kept to ease printing)


class TrieIndex:
    def __init__(self):
        self.root = _TrieNode()
        self._count = 0        # number of distinct words

    def insert(self, word, line_no):
        """Add one occurrence of `word` found on line `line_no`."""
        node = self.root
        for ch in word:
            children = node.children
            if children is None:
                children = node.children = {}
            nxt = children.get(ch)
            if nxt is None:                    # path does not exist yet: extend it
                nxt = children[ch] = _TrieNode()
            node = nxt
        if node.queue is None:                 # first time this word is seen
            node.queue = LineQueue()
            node.word = word
            self._count += 1
        node.queue.enqueue(line_no)            # repeated words just add a line number

    def search(self, word):
        """Return the word's LineQueue, or None if the word is not present."""
        node = self.root
        for ch in word:
            children = node.children
            if children is None:
                return None
            node = children.get(ch)
            if node is None:
                return None
        return node.queue

    def items_sorted(self):
        """Yield (word, LineQueue) in ASCII lexicographic order."""
        stack = [self.root]
        while stack:
            node = stack.pop()
            if node.queue is not None:
                yield node.word, node.queue
            if node.children:
                # push in reverse order so the smallest character is popped first
                for ch in sorted(node.children, reverse=True):
                    stack.append(node.children[ch])

    def __len__(self):
        return self._count


if __name__ == "__main__":
    run_cli(TrieIndex, "Trie")
