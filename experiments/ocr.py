"""
Shared OCR entry point. Loads the model once and reuses it.
"""

import json
from pathlib import Path

_reader = None


def get_reader():
    """Load the EasyOCR model once, reuse it for every call."""
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(['ne', 'en'], gpu=False, verbose=False)
    return _reader


def run_ocr(image_path: Path, out_dir: Path = Path("data/ocr_out")) -> Path:
    """OCR an image, write the regions as JSON, return the JSON path."""
    results = get_reader().readtext(str(image_path))

    regions = [
        {"text": text, "conf": round(float(conf), 3),
         "bbox": [[int(x), int(y)] for x, y in bbox]}
        for bbox, text, conf in results
    ]

    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / (Path(image_path).stem + ".json")
    dest.write_text(json.dumps(regions, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest