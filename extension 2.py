"""
extensions_all_in_one.py
------------------------
A single, self-contained file combining:
  1. Shared utilities (tokenize, LineQueue, build_index, write_index)
  2. All three data structures (TrieIndex, BSTIndex, DictIndex)
  3. All possible lab exam modifications controllable via flags or methods:
     - Case-insensitive indexing (--ignore-case)
     - Minimum word length filter (--min-length K)
     - Alphabetic-only filter (--alpha-only)
     - Stop-words filtering (--stop-words)
     - Allowing duplicate line numbers on the same line (--allow-dup-lines)
     - Storing (line_no, col_no) positions (--track-columns)
     - Showing total word occurrence count (--show-count)
     - Reverse lexicographic order Z -> A (--reverse)
     - Sorting by frequency instead of alphabetically (--sort-by-freq)
     - Prefix search (--prefix <str>)
     - Range search (--range <low> <high>)
     - Word deletion (--delete <word>)
     - Structure diagnostics: BST height & Trie node count (--stats)
     - Peak memory measurement using tracemalloc (--memory)

Usage Examples:
  # Standard run (exact original behavior, defaults to Dict, or choose --impl):
  python extensions_all_in_one.py input.txt output.txt --impl bst

  # Exam modification examples:
  python extensions_all_in_one.py input.txt output.txt --impl trie --ignore-case --show-count
  python extensions_all_in_one.py input.txt output.txt --impl bst --reverse --stats --memory
  python extensions_all_in_one.py input.txt output.txt --impl dict --sort-by-freq --min-length 4
  python extensions_all_in_one.py input.txt output.txt --impl trie --prefix "app"
  python extensions_all_in_one.py input.txt output.txt --impl bst --range "a" "m"
"""

import argparse
import re
import sys
import time
import tracemalloc

# ==============================================================================
# 1. TOKENIZER & FILTERING MODIFICATIONS
# ==============================================================================

# Standard regex: any run of characters except space, tab, CR, LF, ., ,, :, ;
_WORD_RE = re.compile(r"[^ \t\r\n.,:;]+")

# Modification: Strictly alphabetic words only
_ALPHA_RE = re.compile(r"[A-Za-z]+")

# Modification: Common stop words set
DEFAULT_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "from",
    "by", "for", "with", "of", "is", "are", "was", "were", "be", "been", "it",
    "this", "that", "as"
}


def tokenize(line, ignore_case=False, min_length=1, alpha_only=False, stop_words=None):
    """
    Split `line` into words with optional exam modifications:
      - ignore_case : convert words to lowercase
      - min_length  : keep only words with len(w) >= min_length
      - alpha_only  : keep only A-Z / a-z words
      - stop_words  : set of lowercase words to ignore
    """
    if ignore_case:
        line = line.lower()

    words = _ALPHA_RE.findall(line) if alpha_only else _WORD_RE.findall(line)

    if min_length > 1:
        words = [w for w in words if len(w) >= min_length]

    if stop_words:
        words = [w for w in words if w.lower() not in stop_words]

    return words


# ==============================================================================
# 2. LINKED-LIST QUEUE & COUNTING MODIFICATIONS
# ==============================================================================

class _LineNode:
    """One node of the linked list: stores a line entry and next pointer."""
    __slots__ = ("entry", "next")

    def __init__(self, entry):
        self.entry = entry
        self.next = None


class LineQueue:
    """
    Linked-list QUEUE of line numbers (or (line, col) tuples).

    Supports:
      - Standard O(1) duplicate line suppression (default)
      - Allowing duplicate line numbers (allow_duplicates=True)
      - Tracking total occurrences of the word (self.total_occurrences)
    """
    __slots__ = ("head", "tail", "size", "total_occurrences")

    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0               # number of nodes stored in queue
        self.total_occurrences = 0  # total times word was seen (including same-line repeats)

    def enqueue(self, entry, allow_duplicates=False):
        """Append `entry` to the tail in O(1) time."""
        self.total_occurrences += 1
        tail = self.tail

        # Standard behavior: suppress duplicate if same word appears twice on the same line
        if not allow_duplicates and tail is not None and tail.entry == entry:
            return False

        node = _LineNode(entry)
        if tail is None:
            self.head = node
        else:
            tail.next = node
        self.tail = node
        self.size += 1
        return True

    def __iter__(self):
        node = self.head
        while node is not None:
            yield node.entry
            node = node.next

    def __len__(self):
        return self.size

    def __str__(self):
        # Handles both plain int line_no and (line_no, col_no) tuples
        first = self.head.entry if self.head is not None else None
        if isinstance(first, tuple):
            return ", ".join(f"({line}:{col})" for line, col in self)
        return ", ".join(map(str, self))


# ==============================================================================
# 3. IMPLEMENTATION A: TRIE DATA STRUCTURE (with all extensions)
# ==============================================================================

class _TrieNode:
    __slots__ = ("children", "queue")

    def __init__(self):
        self.children = {}   # maps char -> _TrieNode
        self.queue = None    # LineQueue if a complete word ends here, else None


class TrieIndex:
    """Trie-based word index with prefix search, range search, deletion, and stats."""

    def __init__(self):
        self.root = _TrieNode()
        self._count = 0

    def insert(self, word, entry, allow_duplicates=False):
        node = self.root
        for ch in word:
            child = node.children.get(ch)
            if child is None:
                child = _TrieNode()
                node.children[ch] = child
            node = child
        if node.queue is None:
            node.queue = LineQueue()
            self._count += 1
        node.queue.enqueue(entry, allow_duplicates=allow_duplicates)

    def search(self, word):
        node = self.root
        for ch in word:
            node = node.children.get(ch)
            if node is None:
                return None
        return node.queue

    def delete(self, word):
        """Remove `word` from the Trie. Returns True if deleted, False if absent."""
        node = self.root
        path = []  # stack of (parent_node, char, child_node) for pruning empty branches
        for ch in word:
            child = node.children.get(ch)
            if child is None:
                return False
            path.append((node, ch, child))
            node = child

        if node.queue is None:
            return False

        node.queue = None
        self._count -= 1

        # Prune any leaf nodes upward that are no longer part of another word
        for parent, ch, child in reversed(path):
            if child.queue is None and not child.children:
                del parent.children[ch]
            else:
                break
        return True

    def items_sorted(self, reverse=False):
        """
        Iterative DFS traversal yielding (word, LineQueue) in ASCII order
        (or reverse ASCII order if reverse=True).
        """
        stack = [("", self.root, False)]
        while stack:
            prefix, node, visited = stack.pop()
            if visited:
                yield prefix, node.queue
                continue

            # Push children in opposite order so they are popped in desired order
            keys = sorted(node.children.keys(), reverse=not reverse)
            if reverse:
                # For reverse order (Z -> A): children first, then current node's word
                if node.queue is not None:
                    stack.append((prefix, node, True))
                for ch in keys:
                    stack.append((prefix + ch, node.children[ch], False))
            else:
                # For standard order (A -> Z): current node's word before its children
                for ch in keys:
                    stack.append((prefix + ch, node.children[ch], False))
                if node.queue is not None:
                    stack.append((prefix, node, True))

    def words_with_prefix(self, prefix, reverse=False):
        """Yield all (word, LineQueue) starting with `prefix` in O(P + K) time."""
        node = self.root
        for ch in prefix:
            node = node.children.get(ch)
            if node is None:
                return

        stack = [(prefix, node, False)]
        while stack:
            curr_word, curr_node, visited = stack.pop()
            if visited:
                yield curr_word, curr_node.queue
                continue
            keys = sorted(curr_node.children.keys(), reverse=not reverse)
            if reverse:
                if curr_node.queue is not None:
                    stack.append((curr_word, curr_node, True))
                for ch in keys:
                    stack.append((curr_word + ch, curr_node.children[ch], False))
            else:
                for ch in keys:
                    stack.append((curr_word + ch, curr_node.children[ch], False))
                if curr_node.queue is not None:
                    stack.append((curr_word, curr_node, True))

    def words_in_range(self, low, high):
        """Yield all (word, LineQueue) where low <= word <= high."""
        for word, queue in self.items_sorted():
            if low <= word <= high:
                yield word, queue
            elif word > high:
                break

    def node_count(self):
        """Diagnostic: total number of _TrieNode objects in the Trie."""
        count = 0
        stack = [self.root]
        while stack:
            node = stack.pop()
            count += 1
            stack.extend(node.children.values())
        return count

    def __len__(self):
        return self._count


# ==============================================================================
# 4. IMPLEMENTATION B: BINARY SEARCH TREE (with all extensions)
# ==============================================================================

class _BSTNode:
    __slots__ = ("word", "queue", "left", "right")

    def __init__(self, word, entry, allow_duplicates=False):
        self.word = word
        self.queue = LineQueue()
        self.queue.enqueue(entry, allow_duplicates=allow_duplicates)
        self.left = None
        self.right = None


class BSTIndex:
    """Iterative Binary Search Tree index with deletion, range/prefix search, and stats."""

    def __init__(self):
        self.root = None
        self._count = 0

    def insert(self, word, entry, allow_duplicates=False):
        if self.root is None:
            self.root = _BSTNode(word, entry, allow_duplicates)
            self._count = 1
            return
        node = self.root
        while True:
            key = node.word
            if word < key:
                if node.left is None:
                    node.left = _BSTNode(word, entry, allow_duplicates)
                    self._count += 1
                    return
                node = node.left
            elif word > key:
                if node.right is None:
                    node.right = _BSTNode(word, entry, allow_duplicates)
                    self._count += 1
                    return
                node = node.right
            else:
                # If word was previously lazy-deleted, re-initialize its queue
                if node.queue is None:
                    node.queue = LineQueue()
                    self._count += 1
                node.queue.enqueue(entry, allow_duplicates=allow_duplicates)
                return

    def search(self, word):
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

    def delete(self, word):
        """Lazy deletion: sets node.queue = None in O(h) time without recursion."""
        node = self.root
        while node is not None:
            if word < node.word:
                node = node.left
            elif word > node.word:
                node = node.right
            else:
                if node.queue is None:
                    return False
                node.queue = None
                self._count -= 1
                return True
        return False

    def items_sorted(self, reverse=False):
        """
        Iterative in-order traversal (Left-Node-Right).
        If reverse=True, performs reverse in-order traversal (Right-Node-Left).
        """
        stack = []
        node = self.root
        while stack or node is not None:
            while node is not None:
                stack.append(node)
                node = node.right if reverse else node.left
            node = stack.pop()
            if node.queue is not None:  # skip lazy-deleted nodes
                yield node.word, node.queue
            node = node.left if reverse else node.right

    def words_with_prefix(self, prefix, reverse=False):
        """Yield all (word, LineQueue) starting with `prefix`."""
        for word, queue in self.items_sorted(reverse=reverse):
            if word.startswith(prefix):
                yield word, queue
            elif not reverse and word > prefix:
                break

    def words_in_range(self, low, high):
        """Yield all (word, LineQueue) where low <= word <= high."""
        for word, queue in self.items_sorted():
            if low <= word <= high:
                yield word, queue
            elif word > high:
                break

    def height(self):
        """Diagnostic: iterative BFS computation of tree height."""
        if self.root is None:
            return 0
        level = [self.root]
        h = 0
        while level:
            h += 1
            next_level = []
            for node in level:
                if node.left is not None:
                    next_level.append(node.left)
                if node.right is not None:
                    next_level.append(node.right)
            level = next_level
        return h

    def leaf_count(self):
        """Diagnostic: count leaf nodes iteratively."""
        if self.root is None:
            return 0
        leaves = 0
        stack = [self.root]
        while stack:
            node = stack.pop()
            if node.left is None and node.right is None and node.queue is not None:
                leaves += 1
            if node.left is not None:
                stack.append(node.left)
            if node.right is not None:
                stack.append(node.right)
        return leaves

    def __len__(self):
        return self._count


# ==============================================================================
# 5. IMPLEMENTATION C: PYTHON DICTIONARY (with all extensions)
# ==============================================================================

class DictIndex:
    """Hash-table (Python dict) index with prefix/range search and deletion."""

    def __init__(self):
        self.table = {}

    def insert(self, word, entry, allow_duplicates=False):
        queue = self.table.get(word)
        if queue is None:
            queue = self.table[word] = LineQueue()
        queue.enqueue(entry, allow_duplicates=allow_duplicates)

    def search(self, word):
        return self.table.get(word)

    def delete(self, word):
        return self.table.pop(word, None) is not None

    def items_sorted(self, reverse=False):
        table = self.table
        for word in sorted(table, reverse=reverse):
            yield word, table[word]

    def words_with_prefix(self, prefix, reverse=False):
        for word, queue in self.items_sorted(reverse=reverse):
            if word.startswith(prefix):
                yield word, queue

    def words_in_range(self, low, high):
        for word, queue in self.items_sorted():
            if low <= word <= high:
                yield word, queue
            elif word > high:
                break

    def __len__(self):
        return len(self.table)


# ==============================================================================
# 6. INDEX BUILDER & WRITER (supporting all flags)
# ==============================================================================

def build_index(
    index,
    input_path,
    ignore_case=False,
    min_length=1,
    alpha_only=False,
    stop_words=None,
    allow_dup_lines=False,
    track_columns=False,
):
    """Read `input_path` and populate `index` with all chosen modifications."""
    with open(input_path, "r", encoding="latin-1") as f:
        for line_no, line in enumerate(f, start=1):
            words = tokenize(
                line,
                ignore_case=ignore_case,
                min_length=min_length,
                alpha_only=alpha_only,
                stop_words=stop_words,
            )
            if track_columns:
                for col_no, word in enumerate(words, start=1):
                    index.insert(word, (line_no, col_no), allow_duplicates=allow_dup_lines)
            else:
                for word in words:
                    index.insert(word, line_no, allow_duplicates=allow_dup_lines)
    return index


def write_index(
    index,
    output_path,
    reverse=False,
    sort_by_freq=False,
    show_count=False,
    prefix=None,
    word_range=None,
):
    """Write the index to `output_path` with all chosen formatting/query options."""
    if prefix is not None:
        items = index.words_with_prefix(prefix, reverse=reverse)
    elif word_range is not None:
        low, high = word_range
        items = index.words_in_range(low, high)
    else:
        items = index.items_sorted(reverse=reverse)

    if sort_by_freq:
        # Sort by total occurrences (or distinct lines) descending; ties stay alphabetical
        items = list(items)
        items.sort(key=lambda item: item[1].total_occurrences, reverse=True)

    with open(output_path, "w", encoding="latin-1", newline="\n") as out:
        for word, queue in items:
            if show_count:
                out.write(f"{word} (count={queue.total_occurrences}, lines={len(queue)}) {queue}\n")
            else:
                out.write(f"{word} {queue}\n")


# ==============================================================================
# 7. UNIFIED CLI RUNNER
# ==============================================================================

IMPLEMENTATIONS = {
    "trie": ("Trie", TrieIndex),
    "bst": ("BST", BSTIndex),
    "dict": ("Dict", DictIndex),
}


def main():
    parser = argparse.ArgumentParser(
        description="Unified Word Indexer (Trie, BST, Dict) with all Exam Extensions."
    )
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("output_file", help="Path to the output index file")
    parser.add_argument(
        "--impl",
        choices=["trie", "bst", "dict"],
        default="dict",
        help="Data structure to use (default: dict)",
    )

    # Filtering & Tokenization extensions
    parser.add_argument("--ignore-case", action="store_true", help="Case-insensitive indexing")
    parser.add_argument("--min-length", type=int, default=1, help="Minimum word length to index")
    parser.add_argument("--alpha-only", action="store_true", help="Index only alphabetic words (A-Z, a-z)")
    parser.add_argument("--stop-words", action="store_true", help="Ignore common English stop words")

    # Queue & Counting extensions
    parser.add_argument("--allow-dup-lines", action="store_true", help="List line numbers multiple times if word repeats on same line")
    parser.add_argument("--track-columns", action="store_true", help="Record (line:col) instead of just line number")
    parser.add_argument("--show-count", action="store_true", help="Include total occurrence and line counts in output")

    # Sorting & Query extensions
    parser.add_argument("--reverse", action="store_true", help="Print words in reverse lexicographic order (Z -> A)")
    parser.add_argument("--sort-by-freq", action="store_true", help="Sort output by word frequency (highest first)")
    parser.add_argument("--prefix", type=str, default=None, help="Only output words starting with this prefix")
    parser.add_argument("--range", nargs=2, metavar=("LOW", "HIGH"), default=None, help="Only output words in range [LOW, HIGH]")
    parser.add_argument("--delete", nargs="+", default=[], help="Delete specified word(s) before printing")

    # Diagnostics & Memory extensions
    parser.add_argument("--stats", action="store_true", help="Print structural stats (BST height/leaves or Trie node count)")
    parser.add_argument("--memory", action="store_true", help="Measure peak memory usage in MB using tracemalloc")

    args = parser.parse_args()

    title, index_cls = IMPLEMENTATIONS[args.impl]
    index = index_cls()
    stop_set = DEFAULT_STOP_WORDS if args.stop_words else None

    if args.memory:
        tracemalloc.start()

    try:
        t0 = time.perf_counter()
        build_index(
            index,
            args.input_file,
            ignore_case=args.ignore_case,
            min_length=args.min_length,
            alpha_only=args.alpha_only,
            stop_words=stop_set,
            allow_dup_lines=args.allow_dup_lines,
            track_columns=args.track_columns,
        )
        t1 = time.perf_counter()

        for w in args.delete:
            target = w.lower() if args.ignore_case else w
            removed = index.delete(target)
            print(f"[{title}] delete('{target}'): {'removed' if removed else 'not found'}")

        write_index(
            index,
            args.output_file,
            reverse=args.reverse,
            sort_by_freq=args.sort_by_freq,
            show_count=args.show_count,
            prefix=args.prefix,
            word_range=args.range,
        )
        t2 = time.perf_counter()
    except OSError as err:
        print(f"File error: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"[{title}] distinct words:    {len(index)}")
    print(f"[{title}] construction time: {t1 - t0:.3f} s")
    print(f"[{title}] printing time:     {t2 - t1:.3f} s")

    if args.stats:
        if isinstance(index, BSTIndex):
            print(f"[{title}] tree height:       {index.height()}")
            print(f"[{title}] leaf nodes:        {index.leaf_count()}")
        elif isinstance(index, TrieIndex):
            print(f"[{title}] total trie nodes:  {index.node_count()}")

    if args.memory:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"[{title}] peak memory:       {peak / (1024 * 1024):.3f} MB")

    print(f"[{title}] index written to {args.output_file}")


if __name__ == "__main__":
    main()