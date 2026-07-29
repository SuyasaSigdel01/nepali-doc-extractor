import json, easyocr
from pathlib import Path

RAW = Path("data/raw")
OUT = Path("data/ocr_out")
EXTS = {".jpg", ".jpeg", ".png"}

OUT.mkdir(parents=True, exist_ok=True)
reader = easyocr.Reader(['ne', 'en'], gpu=False, verbose=False)

for img in sorted(RAW.iterdir()):
    if img.suffix.lower() not in EXTS:
        continue

    dest = OUT / (img.stem + ".json")
    if dest.exists():
        print(f"skip   {img.name}")
        continue

    print(f"ocr    {img.name}")
    try:
        results = reader.readtext(str(img))
    except Exception as e:
        print(f"  failed: {e}")
        continue

    out = [
        {"text": text, "conf": round(float(conf), 3),
         "bbox": [[int(x), int(y)] for x, y in bbox]}
        for bbox, text, conf in results
    ]
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {len(out)} regions")