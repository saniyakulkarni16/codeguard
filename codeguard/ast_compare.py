"""Step 3: structural comparison with AST subtree hashing.

Every subtree gets a hash made from its node type and the hashes of its children.
Names and constant values are ignored, so renamed code hashes the same.
Comparing multisets of subtree hashes (not one big tree) means reordered
functions/statements still match.
"""
import ast
import hashlib
from collections import Counter


def _digest(text: str) -> str:
    return hashlib.blake2b(text.encode(), digest_size=8).hexdigest()


def subtree_hashes(source: str, min_size: int = 6) -> Counter | None:
    """Multiset of subtree hashes with at least `min_size` nodes, or None if unparsable."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return None

    counter: Counter = Counter()

    def visit(node: ast.AST) -> tuple[str, int]:
        hashes, size = [], 1
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr_context):
                continue
            h, s = visit(child)
            hashes.append(h)
            size += s
        h = _digest(f"{type(node).__name__}({','.join(hashes)})")
        if size >= min_size:
            counter[h] += 1
        return h, size

    try:
        visit(tree)
    except RecursionError:
        return None
    return counter


def multiset_similarity(a: Counter, b: Counter) -> float:
    """sum(min counts) / sum(max counts): Jaccard for multisets.

    Iterates only the smaller counter; the union follows from
    sum(max) = sum(a) + sum(b) - sum(min).
    """
    if len(a) > len(b):
        a, b = b, a
    inter = sum(min(c, b[k]) for k, c in a.items() if k in b)
    union = sum(a.values()) + sum(b.values()) - inter
    return inter / union if union else 0.0
