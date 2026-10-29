"""Step 4: the full pipeline: fingerprints -> inverted index -> scores -> highlights."""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations

from .ast_compare import multiset_similarity, subtree_hashes
from .tokenizer import Token, tokenize_source
from .winnowing import fingerprints


@dataclass
class FileAnalysis:
    name: str
    source: str
    tokens: list[Token]
    fp: dict[int, list[int]]
    ast: Counter | None
    k: int = 5
    keys: frozenset = frozenset()


def analyze_file(name: str, source: str, k: int = 5, w: int = 4,
                 template: "FileAnalysis | None" = None) -> FileAnalysis:
    tokens = tokenize_source(source)
    fp = fingerprints([t.value for t in tokens], k, w)
    ast_c = subtree_hashes(source)
    if template is not None:  # boilerplate exclusion: starter code is never "plagiarism"
        fp = {h: p for h, p in fp.items() if h not in template.fp}
        if ast_c is not None and template.ast is not None:
            ast_c = ast_c - template.ast  # Counter subtraction keeps positive counts only
    return FileAnalysis(name, source, tokens, fp, ast_c, k, frozenset(fp))


def _line_ranges(lines: set[int]) -> list[list[int]]:
    """{3,4,5,9,10} -> [[3,5],[9,10]]"""
    ranges: list[list[int]] = []
    for ln in sorted(lines):
        if ranges and ln == ranges[-1][1] + 1:
            ranges[-1][1] = ln
        else:
            ranges.append([ln, ln])
    return ranges


def matching_regions(a: FileAnalysis, b: FileAnalysis) -> tuple[list, list]:
    """Lines covered by k-grams whose fingerprint appears in both files."""
    shared = set(a.fp) & set(b.fp)

    def lines_of(f: FileAnalysis) -> set[int]:
        out: set[int] = set()
        for h in shared:
            for pos in f.fp[h]:
                for tok in f.tokens[pos:pos + f.k]:
                    out.add(tok.line)
        return out

    return _line_ranges(lines_of(a)), _line_ranges(lines_of(b))


def verdict(score: float) -> str:
    return "high" if score >= 0.7 else "medium" if score >= 0.4 else "low"


@dataclass
class Report:
    names: list[str]
    pairs: list[dict] = field(default_factory=list)
    matrix: list[list[float]] = field(default_factory=list)
    compared: int = 0     # pairs actually scored
    total_pairs: int = 0  # N(N-1)/2

    def to_dict(self) -> dict:
        return self.__dict__


def compare_files(files: dict[str, str], template: str | None = None,
                  k: int = 5, w: int = 4, token_weight: float = 0.6,
                  min_score: float = 0.2, max_df: float = 0.2,
                  min_shared: int = 3, ast_gate: float = 0.1) -> Report:
    tmpl = analyze_file("<template>", template, k, w) if template else None
    analyses = {n: analyze_file(n, s, k, w, tmpl) for n, s in files.items()}
    names = list(analyses)
    idx = {n: i for i, n in enumerate(names)}

    # Inverted index: fingerprint -> files containing it. Only files that share
    # fingerprints can be similar, so most pairs are never scored.
    # Two noise filters (same idea as MOSS):
    #   - ignore fingerprints present in too many files (common idioms like `ID = ID + ID`)
    #   - require a minimum number of shared fingerprints to become a candidate pair
    inverted: dict[int, list[str]] = defaultdict(list)
    for n_, a in analyses.items():
        for h in a.fp:
            inverted[h].append(n_)
    max_owners = max(10, int(max_df * len(names)))
    shared_count: Counter = Counter()
    for owners in inverted.values():
        if 1 < len(owners) <= max_owners:
            shared_count.update(combinations(sorted(owners), 2))
    candidates = {
        (x, y) for (x, y), c in shared_count.items()
        if c >= min(min_shared, len(analyses[x].fp), len(analyses[y].fp))
    }

    n = len(names)
    report = Report(names=names, total_pairs=n * (n - 1) // 2, compared=len(candidates))
    report.matrix = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

    for x, y in candidates:
        a, b = analyses[x], analyses[y]
        tok = len(a.keys & b.keys) / len(a.keys | b.keys)
        st = None
        if tok < ast_gate:
            # negligible token overlap: skip the (more expensive) AST comparison
            score = token_weight * tok
        elif a.ast is not None and b.ast is not None:
            st = multiset_similarity(a.ast, b.ast)
            score = token_weight * tok + (1 - token_weight) * st
        else:  # a file failed to parse -> fall back to the token score alone
            score = tok
        i, j = idx[x], idx[y]
        report.matrix[i][j] = report.matrix[j][i] = round(score, 4)
        if score < min_score:
            continue
        ra, rb = matching_regions(a, b)
        report.pairs.append({
            "file_a": x, "file_b": y,
            "token_score": round(tok, 4),
            "ast_score": None if st is None else round(st, 4),
            "score": round(score, 4),
            "verdict": verdict(score),
            "regions_a": ra, "regions_b": rb,
        })
    report.pairs.sort(key=lambda p: p["score"], reverse=True)
    return report
