"""
Compare extracted fields against ground truth and report per-field accuracy.
"""

import json, sys
from pathlib import Path


def compare(extracted: dict, truth: dict) -> list[tuple[str, bool, object, object]]:
    """Check each ground-truth field against what was extracted."""
    results = []
    for key, want in truth.items():
        got = extracted.get(key)
        results.append((key, got == want, got, want))
    return results


def report(results):
    hits = sum(1 for _, ok, _, _ in results if ok)
    total = len(results)

    for key, ok, got, want in results:
        mark = "ok  " if ok else "MISS"
        print(f"{mark} {key:24} got {got!r}")
        if not ok:
            print(f"{'':29} want {want!r}")

    pct = 100 * hits / total if total else 0
    print(f"\n{hits}/{total} fields correct ({pct:.1f}%)")
    return pct


if __name__ == "__main__":
    extracted = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    truth = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    report(compare(extracted, truth))