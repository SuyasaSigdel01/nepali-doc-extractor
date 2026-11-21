"""
Notice extraction.

Notices are prose, not labelled fields, so this pulls out the few things
that are structurally identifiable — issuer, date, subject — and keeps the
rest as body text to be read aloud. Heuristic by nature.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import normalize_bs_date, bs_to_ad, clean_text

MARKERS = ("सूचना", "सुचना")
DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def _strip_latin_noise(line: str) -> str:
    """Drop stray Latin tokens from a line that is mostly Devanagari.

    Reading-order grouping sweeps logo text and certification badges into
    header lines (NOTES.md finding 5). On a predominantly Devanagari line,
    isolated Latin tokens are almost always logo fragments.
    """
    tokens = line.split()
    if not tokens:
        return ""
    dev = [t for t in tokens if DEVANAGARI.search(t)]
    if len(dev) < len(tokens) / 2:
        return clean_text(line)
    return clean_text(" ".join(dev))


def extract_notice(lines: list[str]) -> dict:
    clean = [clean_text(l) for l in lines if l.strip()]
    out = {"document_type": "notice"}
    if not clean:
        return out

    out["issuer"] = _strip_latin_noise(clean[0]) or clean[0]

    for line in clean:
        bs = normalize_bs_date(line)
        if bs:
            out["date_bs"] = bs
            ad = bs_to_ad(bs)
            if ad:
                out["date_ad"] = ad
            break

    marker_at = next(
        (i for i, l in enumerate(clean) if any(m in l for m in MARKERS)),
        None,
    )

    if marker_at is None:
        out["body"] = " ".join(clean[1:])
        return out

    # The heading often wraps, with the word सूचना alone on its own line.
    parts = [clean[marker_at]]
    prev = clean[marker_at - 1] if marker_at > 0 else ""
    if prev and len(prev) < 45 and not normalize_bs_date(prev):
        parts.insert(0, prev)

    out["subject"] = " ".join(parts)
    out["body"] = " ".join(clean[marker_at + 1:])
    return out


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 \
        else Path("experiments/fixtures/kec_notice.txt")
    lines = path.read_text(encoding="utf-8").splitlines()
    print(json.dumps(extract_notice(lines), ensure_ascii=False, indent=2))