"""
Decide what kind of document this is, before deciding how to read it.

Bills have labelled fields. Notices are prose. They need different
pipelines, so this runs first.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import match_field

NOTICE_MARKERS = ("सूचना", "सुचना", "NOTICE", "Notice")


def classify(lines: list[str]) -> str:
    """Return 'water_bill', 'notice', or 'unknown'."""
    bill_hits = sum(1 for line in lines if match_field(line))
    if bill_hits >= 4:
        return "water_bill"

    text = " ".join(lines)
    if any(marker in text for marker in NOTICE_MARKERS):
        return "notice"

    return "unknown"


if __name__ == "__main__":
    from extract import lines_from_ocr_json

    for path in sorted(Path("data/ocr_out").glob("*.json")):
        print(f"{classify(lines_from_ocr_json(path)):12}  {path.stem}")

    for path in sorted(Path("experiments/fixtures").glob("*.txt")):
        lines = path.read_text(encoding="utf-8").splitlines()
        print(f"{classify(lines):12}  {path.stem}  (fixture)")