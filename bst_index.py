"""
bst_index.py  -  Index generation using a BINARY SEARCH TREE (BST).

Usage:  python bst_index.py <input_text_file> <output_index_file>

Design
------
Each node holds one complete word (the key), its LineQueue (linked list of line
numbers) and left/right child pointers.  For a node with key K:
    words smaller than K are in the left subtree,
    words larger than K are in the right subtree.
Comparison uses Python string comparison, which for ASCII text is exactly
ASCII order (uppercase before lowercase, digits before letters, ...).

* insert / search take O(h) comparisons, h = height of the tree.  For random
  word order h is about log(n); for already-sorted input the tree degenerates
  into a chain (h = n).  The tree is NOT self-balancing (not required here).
* Insertion, search and printing are all iterative (no recursion), so even a
  degenerate tree cannot hit Python's recursion limit.
* Printing in lexicographic order is an in-order traversal (left, node, right)
  using an explicit stack.
"""

from index_common import LineQueue, run_cli


class _BSTNode:
    __slots__ = ("word", "queue", "left", "right")

    def __init__(self, word, line_no):
        self.word = word
        self.queue = LineQueue()
        self.queue.enqueue(line_no)
        self.left = None
        self.right = None


class BSTIndex:
    def __init__(self):
        self.root = None
        self._count = 0        # number of distinct words

    def insert(self, word, line_no):
        """Add one occurrence of `word` found on line `line_no`."""
        if self.root is None:
            self.root = _BSTNode(word, line_no)
            self._count = 1
            return
        node = self.root
        while True:
            key = node.word
            if word < key:                         # go left
                if node.left is None:
                    node.left = _BSTNode(word, line_no)
                    self._count += 1
                    return
                node = node.left
            elif word > key:                       # go right
                if node.right is None:
                    node.right = _BSTNode(word, line_no)
                    self._count += 1
                    return
                node = node.right
            else:                                  # word already present
                node.queue.enqueue(line_no)
                return

    def search(self, word):
        """Return the word's LineQueue, or None if the word is not present."""
        node = self.root
        while node is not None:
            key = node.word
            if word < key:
                node = node.left
            elif word > key:
                node = node.right
            else:
                return node.queue
        return None

    def items_sorted(self):
        """Yield (word, LineQueue) in ASCII lexicographic order (in-order walk)."""
        stack = []
        node = self.root
        while stack or node is not None:
            while node is not None:                # go as far left as possible
                stack.append(node)
                node = node.left
            node = stack.pop()
            yield node.word, node.queue            # visit the node
            node = node.right                      # then its right subtree

    def __len__(self):
        return self._count


if __name__ == "__main__":
    run_cli(BSTIndex, "BST")
