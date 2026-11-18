"""Print the reading-order lines for one OCR output. Debugging aid."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract import lines_from_ocr_json

for i, line in enumerate(lines_from_ocr_json(Path(sys.argv[1]))):
    print(f"{i:3} {line!r}")