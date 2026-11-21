"""
Field extraction for Khanepani water bills (reading receipts).

Each field lists every label variant seen across templates and OCR runs —
including OCR's own misreadings of the label text.
"""

WATER_BILL_FIELDS = {
    "reading_month":      ["Reading Month"],
    "reading_date_bs":    ["Reading Date"],
    "area":               ["Area", "Zone"],
    "sub_area":           ["Sub Area", "Ward", "Sub Alea"],
    "area_no":            ["Area no"],
    "customer_type":      ["Customer type"],
    "customer_id":        ["Customer ID"],
    "old_customer_id":    ["Old Customer ID"],
    "name":               ["Name"],
    "address":            ["Address"],
    "connection_date_bs": ["Connection Date"],
    "previous_unit":      ["Previous Unit", "Previouis Unit"],
    "current_unit":       ["Current Unit"],
    "consumed_unit":      ["Consumed Unit"],
    "meter_status":       ["Meter Status", "Meter Statuz"],
    "bill_amount":        ["Bill Amount", "Blll Amount", "BIII Amoun"],
    "due_amount":         ["Due Amount"],
    "outstanding_amount": ["Outstanding Amount", "Oustanding Amount"],
    "advance_amount":     ["Advance Amount", "Advance AInUUIIt"],
    "payable_amount":     ["Payable Amount"],
}
import re
import json
import sys
from pathlib import Path
from normalize import parse_amount, normalize_bs_date, clean_text, bs_to_ad
sys.path.insert(0, str(Path(__file__).parent))
from normalize import parse_amount, normalize_bs_date, clean_text, to_western_digits

NUMERIC_FIELDS = {
    "previous_unit", "current_unit", "consumed_unit",
    "bill_amount", "due_amount", "outstanding_amount",
    "advance_amount", "payable_amount",
}

DATE_FIELDS = {"reading_date_bs", "connection_date_bs"}
NULL_MARKERS = {"", "-", "NA", "N/A", "NJA", "NIA"}
from difflib import SequenceMatcher


def label_similarity(line: str, label: str) -> float:
    """How closely does the start of this line resemble the label?"""
    return SequenceMatcher(None, line[:len(label)].lower(), label.lower()).ratio()


def match_field(line: str, threshold: float = 0.7) -> tuple[str, str] | None:
    """Return (field, matched_label) for the best label match on this line."""
    best = None
    best_key = (threshold, 0)

    for field, labels in WATER_BILL_FIELDS.items():
        for label in labels:
            key = (label_similarity(line, label), len(label))
            if key > best_key:
                best_key = key
                best = (field, label)

    return best


def split_value(line: str, label: str) -> str:
    """Everything after the matched label is the value."""
    rest = line[len(label):]
    rest = re.sub(r"^[\s:ः।.\-]+", "", rest)
    return clean_text(rest)


def coerce(field: str, raw: str):
    """Convert the raw value to the right type for this field."""
    raw = to_western_digits(raw)

    if raw.strip().upper() in NULL_MARKERS:
        return None
    if field in NUMERIC_FIELDS:
        return parse_amount(raw)
    if field in DATE_FIELDS:
        return normalize_bs_date(raw)
    return raw or None


def extract_fields(lines: list[str]) -> dict:
    """Walk the reordered OCR lines and pull out whatever fields we recognise."""
    out = {"document_type": "water_bill"}

    for line in lines:
        match = match_field(line)
        if not match:
            continue

        field, label = match
        if field in out:
            continue

        value = coerce(field, split_value(line, label))
        if value is not None:
            out[field] = value
            
        if field in DATE_FIELDS:
            ad = bs_to_ad(value)
            if ad:
                out[field.replace("_bs", "_ad")] = ad

    return out


def lines_from_ocr_json(path: Path, threshold: int = 20) -> list[str]:
    """Load an OCR JSON and return its text in reading order."""
    regions = json.loads(path.read_text(encoding="utf-8"))
    regions = [r for r in regions if r["text"].strip()]

    def y_center(r):
        return sum(pt[1] for pt in r["bbox"]) / 4

    def x_left(r):
        return min(pt[0] for pt in r["bbox"])

    regions.sort(key=y_center)

    rows, current = [], []
    for r in regions:
        if not current:
            current = [r]
        elif abs(y_center(r) - y_center(current[0])) <= threshold:
            current.append(r)
        else:
            rows.append(current)
            current = [r]
    if current:
        rows.append(current)

    return [" ".join(c["text"] for c in sorted(row, key=x_left)) for row in rows]


if __name__ == "__main__":
    src = Path(sys.argv[1])
    fields = extract_fields(lines_from_ocr_json(src))

    dest = Path("data/extracted") / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(fields, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(fields, ensure_ascii=False, indent=2))
    print(f"\n{len(fields)} fields → {dest}")