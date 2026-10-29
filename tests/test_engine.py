from pathlib import Path

from codeguard.ast_compare import multiset_similarity, subtree_hashes
from codeguard.compare import compare_files
from codeguard.tokenizer import tokenize_source
from codeguard.winnowing import kgram_hashes, kgram_hashes_naive, winnow

S = Path(__file__).resolve().parent.parent / "samples"


def read(name):
    return (S / name).read_text()


def test_tokenizer_ignores_names_comments_and_formatting():
    a = "x = 1  # hi\nfor i in range(10):\n    x += i\n"
    b = "total=5\nfor   k in range( 99 ):\n        total+=k\n# bye\n"
    assert [t.value for t in tokenize_source(a)] == [t.value for t in tokenize_source(b)]


def test_rolling_hash_matches_naive():
    vals = ["ID", "=", "NUM", "for", "ID", "in", "ID", "(", "ID", ")"] * 5
    for k in (1, 3, 5, 8):
        assert kgram_hashes(vals, k) == kgram_hashes_naive(vals, k)


def test_winnowing_guarantee_shared_substring_found():
    # a shared run of >= w + k - 1 tokens must yield at least one shared fingerprint
    k, w = 5, 4
    shared = [f"t{i}" for i in range(w + k - 1)]
    a = ["a1", "a2", "a3"] + shared + ["a4", "a5"]
    b = ["b1", "b2"] + shared + ["b3", "b4", "b5", "b6"]
    fa = {h for h, _ in winnow(kgram_hashes(a, k), w)}
    fb = {h for h, _ in winnow(kgram_hashes(b, k), w)}
    assert fa & fb


def test_renamed_copy_detected():
    r = compare_files({"a": read("student_a.py"), "b": read("student_b_renamed.py")})
    assert r.pairs[0]["score"] > 0.9


def test_reordered_copy_detected_by_ast():
    r = compare_files({"a": read("student_a.py"), "c": read("student_c_reordered.py")})
    assert r.pairs[0]["ast_score"] > 0.9


def test_unrelated_files_low():
    r = compare_files({"a": read("student_a.py"), "d": read("student_d_original.py")})
    assert not r.pairs or r.pairs[0]["score"] < 0.2


def test_template_exclusion_removes_boilerplate():
    starter = "def solve(data):\n    result = []\n    for item in data:\n        result.append(item * 2)\n    return result\n"
    a = starter + "\ndef extra_a(n):\n    return [i ** 2 for i in range(n) if i % 3 == 0]\n"
    b = starter + "\nclass Other:\n    def run(self, q):\n        while q:\n            q.pop()\n"
    without = compare_files({"a": a, "b": b}, min_score=0.0)
    with_t = compare_files({"a": a, "b": b}, template=starter, min_score=0.0)
    assert without.pairs and without.pairs[0]["score"] > 0.3
    assert not with_t.pairs or with_t.pairs[0]["score"] < without.pairs[0]["score"]


def test_regions_point_to_matching_lines():
    r = compare_files({"a": read("student_a.py"), "b": read("student_b_renamed.py")})
    assert r.pairs[0]["regions_a"] and r.pairs[0]["regions_b"]


def test_unparsable_file_falls_back_to_token_score():
    broken = read("student_a.py") + "\ndef oops(:\n"
    r = compare_files({"a": read("student_a.py"), "bad": broken})
    assert r.pairs[0]["ast_score"] is None


def test_ast_multiset_similarity_identity():
    c = subtree_hashes(read("student_a.py"))
    assert multiset_similarity(c, c) == 1.0
