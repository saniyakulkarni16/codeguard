"""Usage: python -m codeguard.cli <dir> [--template starter.py] [--min-score 0.3] [--json out.json]"""
import argparse
import json
import time
from pathlib import Path

from .compare import compare_files
from .loader import load_dir


def main() -> None:
    ap = argparse.ArgumentParser(description="CodeGuard plagiarism detector")
    ap.add_argument("directory")
    ap.add_argument("--template", help="starter/boilerplate file to ignore")
    ap.add_argument("--min-score", type=float, default=0.3)
    ap.add_argument("--json", help="write full report to this file")
    args = ap.parse_args()

    files = load_dir(args.directory)
    template = Path(args.template).read_text() if args.template else None
    t0 = time.perf_counter()
    report = compare_files(files, template=template, min_score=args.min_score)
    dt = time.perf_counter() - t0

    print(f"{len(files)} files | scored {report.compared}/{report.total_pairs} pairs | {dt:.3f}s\n")
    for p in report.pairs:
        print(f"[{p['verdict'].upper():6}] {p['score']:.2f}  "
              f"(token {p['token_score']:.2f}, ast {p['ast_score']})  "
              f"{p['file_a']}  <->  {p['file_b']}")
    if args.json:
        Path(args.json).write_text(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
