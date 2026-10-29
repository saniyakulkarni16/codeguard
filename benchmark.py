"""Benchmark + accuracy test on synthetic submissions with known ground truth.

Unique files are randomly generated programs (random structure, not templates).
~20% of files are deliberate copies of an earlier file: identifiers renamed,
comments added, and sometimes functions reordered. We measure how many planted
copies are found (recall) and how many flagged pairs are real (precision).

Run: python benchmark.py 200
"""
import builtins
import keyword
import random
import re
import sys
import time

from codeguard.compare import compare_files

OPS = ["+", "-", "*", "//", "%"]
CMP = ["<", ">", "<=", ">=", "==", "!="]
KEEP = set(keyword.kwlist) | set(dir(builtins)) | {"self", "append"}


def name(rng):
    return "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(4, 9)))


def expr(rng, vars_):
    def atom():
        return rng.choice(vars_) if rng.random() < 0.7 else str(rng.randint(0, 99))
    e = atom()
    for _ in range(rng.randint(0, 2)):
        e = f"{e} {rng.choice(OPS)} {atom()}"
    return e


def block(rng, vars_, depth, ind):
    pad = "    " * ind
    lines = []
    for _ in range(rng.randint(2, 4)):
        c = rng.random()
        if c < 0.35 or depth == 0:
            v = rng.choice(vars_)
            lines.append(f"{pad}{v} = {expr(rng, vars_)}")
        elif c < 0.55:
            lines.append(f"{pad}if {rng.choice(vars_)} {rng.choice(CMP)} {expr(rng, vars_)}:")
            lines += block(rng, vars_, depth - 1, ind + 1)
            if rng.random() < 0.5:
                lines.append(f"{pad}else:")
                lines += block(rng, vars_, depth - 1, ind + 1)
        elif c < 0.75:
            i = name(rng)
            lines.append(f"{pad}for {i} in range({expr(rng, vars_)}):")
            lines += block(rng, vars_ + [i], depth - 1, ind + 1)
        elif c < 0.85:
            lines.append(f"{pad}{rng.choice(vars_)}.append({expr(rng, vars_)})")
        elif c < 0.95:
            lines.append(f"{pad}print({expr(rng, vars_)}, {rng.choice(vars_)})")
        else:
            lines.append(f"{pad}while {rng.choice(vars_)} {rng.choice(CMP)} {rng.randint(0, 50)}:")
            lines.append(f"{pad}    {rng.choice(vars_)} {rng.choice(['+=', '-=', '*='])} {rng.randint(1, 5)}")
    return lines


def make_unique(rng):
    funcs = []
    for _ in range(rng.randint(4, 7)):
        params = [name(rng) for _ in range(rng.randint(1, 3))]
        body = block(rng, params, 2, 1) + [f"    return {expr(rng, params)}"]
        funcs.append(f"def {name(rng)}({', '.join(params)}):\n" + "\n".join(body))
    return "\n\n".join(funcs) + "\n"


def rename(src, rng):
    mapping = {}
    def sub(m):
        w = m.group(0)
        return w if w in KEEP else mapping.setdefault(w, name(rng))
    return re.sub(r"[A-Za-z_]\w*", sub, src)


def make_copy(src, rng):
    src = rename(src, rng)
    if rng.random() < 0.5:
        src = "\n\n".join(reversed(src.strip().split("\n\n"))) + "\n"
    return "# my own solution\n" + src


def main(n=200, seed=1):
    rng = random.Random(seed)
    files, cluster = {}, {}
    for i in range(n):
        if i > 5 and rng.random() < 0.2:
            j = rng.randrange(i)
            files[f"s{i}.py"] = make_copy(files[f"s{j}.py"], rng)
            cluster[f"s{i}.py"] = cluster[f"s{j}.py"]
        else:
            files[f"s{i}.py"] = make_unique(rng)
            cluster[f"s{i}.py"] = i
    # ground truth: every pair inside a cluster is a copy pair (copies of the same original too)
    names = list(files)
    truth = {frozenset((a, b)) for ai, a in enumerate(names) for b in names[ai + 1:]
             if cluster[a] == cluster[b]}
    t0 = time.perf_counter()
    rep = compare_files(files)
    dt = time.perf_counter() - t0
    flagged = {frozenset((p["file_a"], p["file_b"])) for p in rep.pairs if p["score"] >= 0.5}
    tp = len(flagged & truth)
    precision = tp / len(flagged) if flagged else 1.0
    recall = tp / len(truth) if truth else 1.0
    print(f"files={n} pairs={rep.total_pairs} scored={rep.compared} "
          f"({100 * (1 - rep.compared / max(1, rep.total_pairs)):.0f}% skipped by inverted index) time={dt:.2f}s")
    print(f"planted copies={len(truth)} flagged={len(flagged)} precision={precision:.2f} recall={recall:.2f}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
