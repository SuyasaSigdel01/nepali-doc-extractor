"""
Score field extraction across every hand-labeled document.
Reads existing OCR output — does not re-run OCR.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract import extract_fields, lines_from_ocr_json
from score import compare, report

ROOT = Path(__file__).resolve().parent.parent
OCR_DIR = ROOT / "data" / "ocr_out"
TRUTH_DIR = ROOT / "data" / "ground_truth"


def main():
    scores = []

    for truth_path in sorted(TRUTH_DIR.glob("*.json")):
        name = truth_path.stem
        ocr_path = OCR_DIR / f"{name}.json"

        if not ocr_path.is_file():
            print(f"-- {name}: no OCR output, skipped")
            continue

        print(f"\n=== {name} ===")
        fields = extract_fields(lines_from_ocr_json(ocr_path))
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        scores.append(report(compare(fields, truth)))

    if scores:
        avg = sum(scores) / len(scores)
        print(f"\nOverall: {avg:.1f}% across {len(scores)} documents")


if __name__ == "__main__":
    main()