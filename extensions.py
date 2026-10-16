"""
extensions.py  -  Practice solutions for the extensions an exam may ask for.

This file does NOT replace your project files.  It imports them and adds the
new features on top, so you can study each feature in isolation.  In the real
exam you would edit your own files directly; the comment "EXAM EDIT" in each
section tells you where that edit would go.

Run   python extensions.py    for a small demo of every feature.

Contents
  A. Reading words        make_tokenizer, build_index_with, build_index_with_positions
  B. Line-number queues   CountedLineQueue, AllOccurrencesQueue, DoublyLineQueue,
                          use_queue_class
  C. BST extras           BSTIndexExt   (height, nodes, min/max, reverse, range,
                                         delete, balanced rebuild, search_steps)
  D. Trie extras          TrieIndexExt  (prefix, count, longest word, common
                                         prefix, delete, wildcard, search_steps)
  E. Dict extras          DictIndexExt  (delete, reverse order)
  F. Works on any index   most_frequent_word, longest_word, by_frequency,
                          anagram_groups, search_info, search_many
  G. Output / command line  write_index_reverse, write_index_per_occurrence,
                          write_index_with_counts, run_cli_with_query
  H. Timing               time_deletions
"""

import re
import sys
import time

import trie_index
import bst_index
import dict_index
from index_common import LineQueue, _LineNode, tokenize, write_index
from trie_index import TrieIndex
from bst_index import BSTIndex, _BSTNode
from dict_index import DictIndex


# ===========================================================================
# A. READING WORDS
# ===========================================================================

def make_tokenizer(separators=" \t\r\n.,:;", lowercase=False,
                   min_length=1, stop_words=()):
    """
    Build a tokenizer with your own rules.

      separators  characters that split words (add "?!-" to treat them as separators)
      lowercase   True  -> "The" and "the" become the same word   (case-insensitive)
      min_length  ignore words shorter than this
      stop_words  words to ignore completely, e.g. ("the", "a", "an")

    EXAM EDIT: the same changes go inside tokenize() in index_common.py:
        line = line.lower()                                  # case-insensitive
        _WORD_RE = re.compile(r"[^ \\t\\r\\n.,:;?!-]+")        # more separators
        words = [w for w in words if len(w) >= 3]            # ignore short words
    """
    pattern = re.compile("[^" + re.escape(separators) + "]+")
    stop = frozenset(w.lower() if lowercase else w for w in stop_words)

    def tokenizer(line):
        if lowercase:
            line = line.lower()
        return [w for w in pattern.findall(line)
                if len(w) >= min_length and w not in stop]

    return tokenizer


def build_index_with(index, input_path, tokenizer=tokenize):
    """
    Like build_index() but uses any tokenizer and RETURNS THE TOTAL NUMBER OF
    WORDS read.  Distinct words = len(index).
    """
    total = 0
    with open(input_path, "r", encoding="latin-1") as f:
        for line_no, line in enumerate(f, start=1):
            words = tokenizer(line)
            total += len(words)
            for word in words:
                index.insert(word, line_no)
    return total


_WORD_PATTERN = re.compile(r"[^ \t\r\n.,:;]+")


def build_index_with_positions(index, input_path):
    """
    Store (line, column) for every occurrence instead of just the line.
    Columns start at 1.  No change to the index classes is needed because the
    queue stores whatever value it is given; a tuple is never equal to the
    previous tuple, so every occurrence is kept.
    """
    with open(input_path, "r", encoding="latin-1") as f:
        for line_no, line in enumerate(f, start=1):
            for match in _WORD_PATTERN.finditer(line):
                index.insert(match.group(), (line_no, match.start() + 1))
    return index


# ===========================================================================
# B. LINE-NUMBER QUEUES
# ===========================================================================

class CountedLineQueue(LineQueue):
    """
    Adds a field `occurrences`: how many times the word occurred (every
    occurrence counts, even a second one on the same line).  The line list
    itself is unchanged.

    EXAM EDIT: add the field to LineQueue itself.  All three structures store a
    LineQueue, so ONE edit changes the Trie, BST and dict together:
        self.occurrences = 0              # in __init__
        self.occurrences += 1             # first line of enqueue()
    """
    __slots__ = ("occurrences",)

    def __init__(self):
        super().__init__()
        self.occurrences = 0

    def enqueue(self, number):
        self.occurrences += 1
        return super().enqueue(number)


class AllOccurrencesQueue(LineQueue):
    """Keeps a line number every time: 'a a a' on line 1 gives 1, 1, 1."""
    __slots__ = ()

    def enqueue(self, number):
        node = _LineNode(number)
        if self.tail is None:
            self.head = node
        else:
            self.tail.next = node
        self.tail = node
        self.size += 1
        return True


class _DNode:
    __slots__ = ("number", "next", "prev")

    def __init__(self, number):
        self.number = number
        self.next = None
        self.prev = None


class DoublyLineQueue:
    """
    Doubly linked queue: every node knows its next AND previous node.
    That makes these easy and O(1):
        reverse_iter()   walk from tail to head (line numbers in reverse order)
        dequeue()        remove and return the FIRST number
        remove_last()    remove and return the LAST number
    Same interface as LineQueue, so it can be plugged into the indexes.
    """
    __slots__ = ("head", "tail", "size")

    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def enqueue(self, number):
        if self.tail is not None and self.tail.number == number:
            return False
        node = _DNode(number)
        if self.tail is None:
            self.head = self.tail = node
        else:
            node.prev = self.tail          # new node points back to old tail
            self.tail.next = node          # old tail points forward to new node
            self.tail = node
        self.size += 1
        return True

    def dequeue(self):
        """Remove and return the first number (None if empty)."""
        node = self.head
        if node is None:
            return None
        self.head = node.next
        if self.head is None:              # queue became empty
            self.tail = None
        else:
            self.head.prev = None
        self.size -= 1
        return node.number

    def remove_last(self):
        """Remove and return the last number (None if empty)."""
        node = self.tail
        if node is None:
            return None
        self.tail = node.prev
        if self.tail is None:
            self.head = None
        else:
            self.tail.next = None
        self.size -= 1
        return node.number

    def __iter__(self):
        node = self.head
        while node is not None:
            yield node.number
            node = node.next

    def reverse_iter(self):
        node = self.tail
        while node is not None:
            yield node.number
            node = node.prev

    def __len__(self):
        return self.size

    def __str__(self):
        return ", ".join(map(str, self))

    def reverse_str(self):
        return ", ".join(map(str, self.reverse_iter()))


class use_queue_class:
    """
    Context manager for experiments: while active, the Trie, BST and dict
    create queues of the given class.

        with use_queue_class(CountedLineQueue):
            idx = TrieIndex(); build_index(idx, "in.txt")

    (In the exam you edit the LineQueue class itself instead.)
    """
    _modules = (trie_index, bst_index, dict_index)

    def __init__(self, queue_class):
        self.queue_class = queue_class
        self._saved = []

    def __enter__(self):
        self._saved = [(m, m.LineQueue) for m in self._modules]
        for m in self._modules:
            m.LineQueue = self.queue_class
        return self

    def __exit__(self, *exc):
        for m, old in self._saved:
            m.LineQueue = old
        return False


def frequency(queue):
    """Occurrences if the queue counts them, otherwise the number of lines."""
    return getattr(queue, "occurrences", len(queue))


# ===========================================================================
# C. BST EXTRAS
# ===========================================================================

class BSTIndexExt(BSTIndex):

    def height(self):
        """Number of nodes on the longest root-to-leaf path (empty tree: 0)."""
        if self.root is None:
            return 0
        best = 0
        stack = [(self.root, 1)]                       # (node, depth)
        while stack:
            node, depth = stack.pop()
            best = max(best, depth)
            if node.left is not None:
                stack.append((node.left, depth + 1))
            if node.right is not None:
                stack.append((node.right, depth + 1))
        return best

    def node_count(self):
        """Count nodes by walking the whole tree (must equal len(index))."""
        count = 0
        stack = [self.root] if self.root is not None else []
        while stack:
            node = stack.pop()
            count += 1
            if node.left is not None:
                stack.append(node.left)
            if node.right is not None:
                stack.append(node.right)
        return count

    def minimum(self):
        """Smallest word: keep going left."""
        node = self.root
        if node is None:
            return None
        while node.left is not None:
            node = node.left
        return node.word

    def maximum(self):
        """Largest word: keep going right."""
        node = self.root
        if node is None:
            return None
        while node.right is not None:
            node = node.right
        return node.word

    def items_reverse(self):
        """Reverse in-order: right subtree, node, left subtree -> descending."""
        stack = []
        node = self.root
        while stack or node is not None:
            while node is not None:
                stack.append(node)
                node = node.right
            node = stack.pop()
            yield node.word, node.queue
            node = node.left

    def range_query(self, low, high):
        """
        Yield (word, queue) for every word with low <= word <= high, in order.
        Skips subtrees that cannot contain answers:
          node.word < low  -> it and its whole left subtree are too small
          node.word > high -> it and everything after it (in order) is too big
        """
        stack = []
        node = self.root
        while True:
            while node is not None:
                if node.word < low:
                    node = node.right
                else:
                    stack.append(node)
                    node = node.left
            if not stack:
                return
            node = stack.pop()
            if node.word > high:
                return
            yield node.word, node.queue
            node = node.right

    def delete(self, word):
        """
        Remove `word`.  Returns True if it was present.
        Three cases for the node to remove:
          1. leaf               -> remove it
          2. one child          -> the child takes its place
          3. two children       -> copy the in-order SUCCESSOR (smallest word of
                                   the right subtree) into this node, then
                                   remove the successor (it has no left child,
                                   so it falls under case 1 or 2)
        """
        parent = None
        node = self.root
        while node is not None and node.word != word:      # find the node
            parent = node
            node = node.left if word < node.word else node.right
        if node is None:
            return False

        if node.left is not None and node.right is not None:   # case 3
            succ_parent, succ = node, node.right
            while succ.left is not None:
                succ_parent, succ = succ, succ.left
            node.word, node.queue = succ.word, succ.queue
            parent, node = succ_parent, succ                    # now remove succ

        child = node.left if node.left is not None else node.right  # cases 1, 2
        if parent is None:
            self.root = child
        elif parent.left is node:
            parent.left = child
        else:
            parent.right = child
        self._count -= 1
        return True

    def rebuild_balanced(self):
        """
        Rebuild the tree so that its height is about log2(n): take the sorted
        words, make the MIDDLE one the root, and build the left and right
        halves the same way.  (Recursion depth is only about log2(n).)
        """
        items = list(self.items_sorted())

        def build(lo, hi):
            if lo > hi:
                return None
            mid = (lo + hi) // 2
            word, queue = items[mid]
            node = _BSTNode(word, 0)
            node.queue = queue                  # keep the existing line numbers
            node.left = build(lo, mid - 1)
            node.right = build(mid + 1, hi)
            return node

        self.root = build(0, len(items) - 1)

    def search_steps(self, word):
        """Return (queue or None, number of nodes compared)."""
        steps = 0
        node = self.root
        while node is not None:
            steps += 1
            if word < node.word:
                node = node.left
            elif word > node.word:
                node = node.right
            else:
                return node.queue, steps
        return None, steps


# ===========================================================================
# D. TRIE EXTRAS
# ===========================================================================

class TrieIndexExt(TrieIndex):

    def _walk(self, start):
        """Pre-order walk from `start`: yields (word, queue) in sorted order."""
        stack = [start]
        while stack:
            node = stack.pop()
            if node.queue is not None:
                yield node.word, node.queue
            if node.children:
                for ch in sorted(node.children, reverse=True):
                    stack.append(node.children[ch])

    def _find_node(self, prefix):
        node = self.root
        for ch in prefix:
            if node.children is None or ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def words_with_prefix(self, prefix):
        """All (word, queue) that start with `prefix`, in sorted order."""
        node = self._find_node(prefix)
        if node is None:
            return iter(())
        return self._walk(node)

    def count_with_prefix(self, prefix):
        return sum(1 for _ in self.words_with_prefix(prefix))

    def longest_word(self):
        """Longest word (the alphabetically first one on a tie)."""
        best = None
        for word, _ in self._walk(self.root):
            if best is None or len(word) > len(best):
                best = word
        return best

    def longest_common_prefix(self):
        """
        Longest prefix shared by ALL words: follow the path from the root while
        the node has exactly one child and no word ends there.
        """
        node = self.root
        prefix = []
        while node.children and len(node.children) == 1 and node.queue is None:
            (ch, node), = node.children.items()
            prefix.append(ch)
        return "".join(prefix)

    def node_count(self):
        """Number of nodes (excluding the root)."""
        count = 0
        stack = [self.root]
        while stack:
            node = stack.pop()
            if node.children:
                count += len(node.children)
                stack.extend(node.children.values())
        return count

    def height(self):
        """Length of the longest path from the root = length of longest word."""
        best = 0
        stack = [(self.root, 0)]
        while stack:
            node, depth = stack.pop()
            best = max(best, depth)
            if node.children:
                for child in node.children.values():
                    stack.append((child, depth + 1))
        return best

    def delete(self, word):
        """
        Remove `word`.  Returns True if it was present.
        1. Walk down, remembering (parent, character) for every step.
        2. Un-mark the final node (it no longer ends a word).
        3. Walk back up deleting nodes that are now useless: no children and no
           word ending there.  Stop at the first node that is still needed
           (it has another child, or another word ends there).
        """
        path = []
        node = self.root
        for ch in word:
            if node.children is None or ch not in node.children:
                return False
            path.append((node, ch))
            node = node.children[ch]
        if node.queue is None:                       # prefix only, not a word
            return False
        node.queue = None
        node.word = None
        self._count -= 1
        while path and node.queue is None and not node.children:
            parent, ch = path.pop()
            del parent.children[ch]
            if not parent.children:
                parent.children = None
            node = parent
        return True

    def wildcard_search(self, pattern):
        """
        '?' matches exactly one character, '*' matches any number (also zero).
        Returns a sorted list of (word, queue).
        (A word that itself contains '?' or '*' can only be found by exact
        search, because those two characters act as wildcards here.)
        """
        found = {}
        seen = set()                                  # (node id, pattern position)
        stack = [(self.root, 0)]
        while stack:
            node, pos = stack.pop()
            state = (id(node), pos)
            if state in seen:
                continue
            seen.add(state)
            if pos == len(pattern):
                if node.queue is not None:
                    found[node.word] = node.queue
                continue
            c = pattern[pos]
            if c == "*":
                stack.append((node, pos + 1))         # '*' matches nothing
                if node.children:
                    for child in node.children.values():
                        stack.append((child, pos))    # '*' swallows one character
            elif node.children:
                if c == "?":
                    for child in node.children.values():
                        stack.append((child, pos + 1))
                else:
                    child = node.children.get(c)
                    if child is not None:
                        stack.append((child, pos + 1))
        return sorted(found.items())

    def items_reverse(self):
        return reversed(list(self.items_sorted()))

    def search_steps(self, word):
        """Return (queue or None, number of characters followed)."""
        steps = 0
        node = self.root
        for ch in word:
            if node.children is None or ch not in node.children:
                return None, steps
            node = node.children[ch]
            steps += 1
        return node.queue, steps


# ===========================================================================
# E. DICT EXTRAS
# ===========================================================================

class DictIndexExt(DictIndex):

    def delete(self, word):
        """Remove `word`; True if it was present."""
        return self.table.pop(word, None) is not None

    def items_reverse(self):
        for word in sorted(self.table, reverse=True):
            yield word, self.table[word]


# ===========================================================================
# F. FUNCTIONS THAT WORK ON ANY OF THE THREE INDEXES
#    (they only use items_sorted(), so one version serves all structures)
# ===========================================================================

def most_frequent_word(index):
    """(word, frequency) with the highest frequency; alphabetically first on a tie."""
    best = None
    for word, queue in index.items_sorted():           # sorted -> first wins ties
        f = frequency(queue)
        if best is None or f > best[1]:
            best = (word, f)
    return best


def most_lines_word(index):
    """(word, number of different lines) - the word on the most lines."""
    best = None
    for word, queue in index.items_sorted():
        if best is None or len(queue) > best[1]:
            best = (word, len(queue))
    return best


def longest_word(index):
    best = None
    for word, _ in index.items_sorted():
        if best is None or len(word) > len(best):
            best = word
    return best


def by_frequency(index):
    """List of (word, frequency): most frequent first, ties alphabetical."""
    pairs = [(word, frequency(queue)) for word, queue in index.items_sorted()]
    pairs.sort(key=lambda p: -p[1])                    # stable sort keeps alphabetical ties
    return pairs


def anagram_groups(index):
    """
    Groups of words made of the same letters ('listen', 'silent', 'enlist').
    Key idea: two words are anagrams exactly when their sorted letters match.
    """
    groups = {}
    for word, _ in index.items_sorted():
        groups.setdefault("".join(sorted(word)), []).append(word)
    result = [g for g in groups.values() if len(g) >= 2]
    result.sort(key=lambda g: g[0])
    return result


def search_info(index, word):
    """Everything about one word: found?, line numbers, how many lines, occurrences."""
    queue = index.search(word)
    if queue is None:
        return {"found": False, "lines": [], "num_lines": 0, "occurrences": 0}
    return {"found": True, "lines": list(queue), "num_lines": len(queue),
            "occurrences": frequency(queue)}


def search_many(index, query_file):
    """Search every word listed in `query_file`; returns {word: [line numbers]}."""
    results = {}
    with open(query_file, "r", encoding="latin-1") as f:
        for line in f:
            for word in tokenize(line):
                queue = index.search(word)
                results[word] = list(queue) if queue is not None else []
    return results


# ===========================================================================
# G. OUTPUT AND COMMAND LINE
# ===========================================================================

def write_index_reverse(index, output_path):
    """Same format as write_index but words in REVERSE order (Z..A)."""
    with open(output_path, "w", encoding="latin-1", newline="\n") as out:
        for word, queue in index.items_reverse():
            out.write(f"{word} {queue}\n")


def write_index_per_occurrence(index, output_path):
    """One line per (word, line number):  'cat 1' then 'cat 3'."""
    with open(output_path, "w", encoding="latin-1", newline="\n") as out:
        for word, queue in index.items_sorted():
            for number in queue:
                out.write(f"{word} {number}\n")


def write_index_with_counts(index, output_path):
    """'cat (3 times): 1, 3, 7' - needs a queue that counts (CountedLineQueue)."""
    with open(output_path, "w", encoding="latin-1", newline="\n") as out:
        for word, queue in index.items_sorted():
            out.write(f"{word} ({frequency(queue)} times): {queue}\n")


def run_cli_with_query(index_class, title):
    """
    python script.py <input> <output> <query_word>
    Builds the index, writes it, then prints the line numbers of <query_word>.
    """
    from index_common import build_index
    if len(sys.argv) != 4:
        print(f"Usage: python {sys.argv[0]} <input_file> <output_file> <query_word>",
              file=sys.stderr)
        sys.exit(1)
    in_path, out_path, query = sys.argv[1:4]
    index = index_class()
    build_index(index, in_path)
    write_index(index, out_path)
    queue = index.search(query)
    if queue is None:
        print(f"[{title}] '{query}' not found")
    else:
        print(f"[{title}] '{query}' found on lines: {queue}")


# ===========================================================================
# H. TIMING
# ===========================================================================

def time_deletions(index, words):
    """Time how long it takes to delete every word in `words`; returns seconds."""
    start = time.perf_counter()
    for word in words:
        index.delete(word)
    return time.perf_counter() - start


# ===========================================================================
# DEMO
# ===========================================================================

def _demo():
    import os
    import tempfile
    from index_common import build_index

    text = ("the cat sat\nthe dog sat\na cat ran\n"
            "listen silent enlist cat cat\ncar card care\n")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "demo.txt")
        with open(path, "w") as f:
            f.write(text)

        print("TEXT:\n" + text)

        bst = BSTIndexExt(); build_index(bst, path)
        trie = TrieIndexExt(); build_index(trie, path)
        dct = DictIndexExt(); build_index(dct, path)

        print("BST height:", bst.height(), "| nodes:", bst.node_count(),
              "| min:", bst.minimum(), "| max:", bst.maximum())
        print("BST range 'car'..'dog':", [w for w, _ in bst.range_query("car", "dog")])
        print("BST reverse:", [w for w, _ in bst.items_reverse()])
        bst.rebuild_balanced()
        print("BST height after balancing:", bst.height())
        print("BST delete 'cat':", bst.delete("cat"), "->", bst.search("cat"))
        print("BST search_steps('sat'):", bst.search_steps("sat")[1], "comparisons")

        print("Trie words with prefix 'ca':", [w for w, _ in trie.words_with_prefix("ca")])
        print("Trie count prefix 'car':", trie.count_with_prefix("car"))
        print("Trie longest word:", trie.longest_word(), "| height:", trie.height(),
              "| nodes:", trie.node_count())
        print("Trie wildcard 'ca?':", [w for w, _ in trie.wildcard_search("ca?")])
        print("Trie wildcard 'c*d':", [w for w, _ in trie.wildcard_search("c*d")])
        print("Trie delete 'car':", trie.delete("car"),
              "| 'card' still there:", trie.search("card") is not None)

        print("Anagram groups:", anagram_groups(dct))
        print("Most lines:", most_lines_word(dct), "| longest:", longest_word(dct))

        with use_queue_class(CountedLineQueue):
            counted = DictIndexExt(); build_index(counted, path)
        print("Most frequent (occurrences):", most_frequent_word(counted))
        print("By frequency (top 3):", by_frequency(counted)[:3])


if __name__ == "__main__":
    _demo()
