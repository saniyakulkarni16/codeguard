"""Step 2: k-gram hashing (Rabin-Karp rolling hash) and winnowing (MOSS technique)."""
import zlib
from collections import deque

BASE = 257
MOD = (1 << 61) - 1


def _to_ints(values: list[str]) -> list[int]:
    # crc32 is stable across runs (Python's built-in hash() is randomized)
    return [zlib.crc32(v.encode()) for v in values]


def kgram_hashes(values: list[str], k: int) -> list[int]:
    """Rolling hash of every window of k tokens in O(n).

    h(i+1) = (h(i) - t[i] * BASE^(k-1)) * BASE + t[i+k]   (mod MOD)
    """
    n = len(values)
    if n < k:
        return []
    t = _to_ints(values)
    top = pow(BASE, k - 1, MOD)
    h = 0
    for x in t[:k]:
        h = (h * BASE + x) % MOD
    out = [h]
    for i in range(k, n):
        h = ((h - t[i - k] * top) * BASE + t[i]) % MOD
        out.append(h)
    return out


def kgram_hashes_naive(values: list[str], k: int) -> list[int]:
    """O(n*k) reference implementation, used in tests to verify the rolling hash."""
    t = _to_ints(values)
    res = []
    for i in range(len(t) - k + 1):
        h = 0
        for x in t[i:i + k]:
            h = (h * BASE + x) % MOD
        res.append(h)
    return res


def winnow(hashes: list[int], w: int) -> list[tuple[int, int]]:
    """Pick the minimum hash of every window of w hashes (rightmost on ties).

    Uses a monotonic deque so the whole pass is O(n).
    Guarantee: any shared substring of >= w + k - 1 tokens produces a shared fingerprint.
    Returns a list of (hash, position-of-k-gram).
    """
    if not hashes:
        return []
    if len(hashes) <= w:
        i = min(range(len(hashes)), key=lambda j: (hashes[j], -j))
        return [(hashes[i], i)]
    result: list[tuple[int, int]] = []
    dq: deque[int] = deque()
    last = -1
    for i, h in enumerate(hashes):
        while dq and hashes[dq[-1]] >= h:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - w:
            dq.popleft()
        if i >= w - 1:
            m = dq[0]
            if m != last:
                result.append((hashes[m], m))
                last = m
    return result


def fingerprints(values: list[str], k: int = 5, w: int = 4) -> dict[int, list[int]]:
    """hash -> list of k-gram start positions."""
    fp: dict[int, list[int]] = {}
    for h, pos in winnow(kgram_hashes(values, k), w):
        fp.setdefault(h, []).append(pos)
    return fp


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)
