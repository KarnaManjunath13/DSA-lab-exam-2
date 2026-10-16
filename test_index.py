"""
test_index.py  -  Test cases for the Trie, BST and dict index implementations.

Run:   python test_index.py            (or:  python -m unittest -v test_index)

Every test is run against all three implementations, and one test checks that
the three produce identical output on a large random text.
"""

import os
import random
import string
import subprocess
import sys
import tempfile
import unittest

from index_common import tokenize, build_index, write_index, LineQueue
from trie_index import TrieIndex
from bst_index import BSTIndex
from dict_index import DictIndex

IMPLEMENTATIONS = [TrieIndex, BSTIndex, DictIndex]


def run_index(index_class, text):
    """Write `text` to a temp file, index it, return (output_text, index)."""
    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "in.txt")
        out_path = os.path.join(tmp, "out.txt")
        with open(in_path, "w", encoding="latin-1", newline="") as f:
            f.write(text)                       # newline="" keeps \r\n as given
        index = index_class()
        build_index(index, in_path)
        write_index(index, out_path)
        with open(out_path, "r", encoding="latin-1") as f:
            return f.read(), index


class TestTokenizer(unittest.TestCase):
    def test_all_separators(self):
        self.assertEqual(tokenize("a b,,c.d:e;f   g\n"), list("abcdefg"))

    def test_blank_and_separator_only_lines(self):
        self.assertEqual(tokenize("\n"), [])
        self.assertEqual(tokenize(" ,.;: \n"), [])

    def test_special_characters_stay_inside_words(self):
        self.assertEqual(tokenize("a-b #c $d x_y (z) 1/2\n"),
                         ["a-b", "#c", "$d", "x_y", "(z)", "1/2"])


class TestLineQueue(unittest.TestCase):
    def test_order_and_duplicate_of_last(self):
        q = LineQueue()
        for n in (1, 1, 3, 3, 3, 7):
            q.enqueue(n)
        self.assertEqual(list(q), [1, 3, 7])
        self.assertEqual(len(q), 3)
        self.assertEqual(str(q), "1, 3, 7")


class TestIndexes(unittest.TestCase):
    def for_all(self, text, expected):
        for cls in IMPLEMENTATIONS:
            with self.subTest(implementation=cls.__name__):
                out, _ = run_index(cls, text)
                self.assertEqual(out, expected)

    def test_simple_example(self):
        self.for_all("the cat sat\nthe dog sat\na cat ran\n",
                     "a 3\ncat 1, 3\ndog 2\nran 3\nsat 1, 2\nthe 1, 2\n")

    def test_apple_banana_with_blank_lines(self):
        text = "apple\nbanana\n\napple, banana\n\n\n\n\napple\n"
        self.for_all(text, "apple 1, 4, 9\nbanana 2, 4\n")

    def test_repeated_word_on_same_line_listed_once(self):
        self.for_all("a a a\na\n", "a 1, 2\n")

    def test_blank_lines_are_counted(self):
        self.for_all("x\n\n\nx\n", "x 1, 4\n")

    def test_ascii_order(self):
        # ASCII codes: ! 33, 1 49, A 65, B 66, _ 95, a 97, b 98, ~ 126
        self.for_all("b B a A 1 ! ~ _\n", "! 1\n1 1\nA 1\nB 1\n_ 1\na 1\nb 1\n~ 1\n")

    def test_prefix_words(self):
        self.for_all("apple app a application\n",
                     "a 1\napp 1\napple 1\napplication 1\n")

    def test_special_characters(self):
        self.for_all("a-b #c $d a-b\n", "#c 1\n$d 1\na-b 1\n")

    def test_case_sensitive(self):
        self.for_all("Word word WORD\n", "WORD 1\nWord 1\nword 1\n")

    def test_empty_file(self):
        self.for_all("", "")

    def test_only_separators(self):
        self.for_all(" ,.;:\n\n", "")

    def test_no_trailing_newline(self):
        self.for_all("a\nb", "a 1\nb 2\n")

    def test_windows_line_endings(self):
        self.for_all("a b\r\nb c\r\n", "a 1\nb 1, 2\nc 2\n")

    def test_search(self):
        for cls in IMPLEMENTATIONS:
            with self.subTest(implementation=cls.__name__):
                _, index = run_index(cls, "cat dog\ncat\nbird cat\n")
                self.assertEqual(list(index.search("cat")), [1, 2, 3])
                self.assertEqual(list(index.search("dog")), [1])
                self.assertIsNone(index.search("ca"))       # prefix only
                self.assertIsNone(index.search("cats"))
                self.assertIsNone(index.search("zebra"))
                self.assertEqual(len(index), 3)

    def test_sorted_input_does_not_break_bst(self):
        # sorted words make the BST a long chain; iterative code must cope
        words = [f"w{i:05d}" for i in range(3000)]
        text = "\n".join(words) + "\n"
        expected = "".join(f"{w} {i + 1}\n" for i, w in enumerate(words))
        self.for_all(text, expected)

    def test_three_implementations_agree_on_random_text(self):
        rng = random.Random(7)
        alphabet = string.ascii_letters + string.digits + "!#$%&'()*+-/<=>?@[]^_`{|}~\"\\"
        vocab = ["".join(rng.choices(alphabet, k=rng.randint(1, 6))) for _ in range(400)]
        separators = [" ", "  ", ",", ", ", ".", ":", ";", " ; "]
        lines = []
        for _ in range(1500):
            n = rng.randint(0, 10)
            parts = []
            for _ in range(n):
                parts.append(rng.choice(vocab))
                parts.append(rng.choice(separators))
            lines.append("".join(parts))
        text = "\n".join(lines) + "\n"
        outputs = [run_index(cls, text)[0] for cls in IMPLEMENTATIONS]
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[1], outputs[2])
        # output must be strictly increasing in ASCII order
        words = [line.split(" ")[0] for line in outputs[0].splitlines()]
        self.assertEqual(words, sorted(set(words)))


class TestCommandLine(unittest.TestCase):
    def test_scripts_run_from_command_line(self):
        here = os.path.dirname(os.path.abspath(__file__))
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "in.txt")
            with open(in_path, "w") as f:
                f.write("the cat sat\nthe dog sat\na cat ran\n")
            expected = "a 3\ncat 1, 3\ndog 2\nran 3\nsat 1, 2\nthe 1, 2\n"
            for script in ("trie_index.py", "bst_index.py", "dict_index.py"):
                out_path = os.path.join(tmp, script + ".out")
                result = subprocess.run(
                    [sys.executable, os.path.join(here, script), in_path, out_path],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                with open(out_path) as f:
                    self.assertEqual(f.read(), expected, script)

    def test_wrong_arguments_and_missing_file(self):
        here = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(here, "dict_index.py")
        r = subprocess.run([sys.executable, script], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Usage", r.stderr)
        r = subprocess.run([sys.executable, script, "no_such_file.txt", "out.txt"],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("File error", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
