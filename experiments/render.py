"""
Render extracted fields as human-readable output in Nepali or English.
"""

import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import to_nepali_digits

NEPALI_MONTHS = {
    "01": "बैशाख", "02": "जेठ", "03": "असार", "04": "श्रावण",
    "05": "भदौ", "06": "असोज", "07": "कार्तिक", "08": "मंसिर",
    "09": "पुष", "10": "माघ", "11": "फागुन", "12": "चैत",
}


def format_value(key: str, value, lang: str) -> str:
    if value is None:
        return "—"

    if isinstance(value, float):
        s = f"{value:,.2f}"
        return to_nepali_digits(s) if lang == "ne" else s

    if key.endswith("_bs") and isinstance(value, str) and "-" in value:
        return to_nepali_digits(value) if lang == "ne" else value

    return str(value)


def render(fields: dict, labels: dict, lang: str = "ne") -> str:
    table = labels[lang]
    out = []

    for key, value in fields.items():
        if key == "document_type":
            continue
        label = table.get(key, key)
        out.append(f"{label}: {format_value(key, value, lang)}")

    return "\n".join(out)


if __name__ == "__main__":
    fields = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    labels = json.loads(Path("labels/water_bill.json").read_text(encoding="utf-8"))

    for lang in ("ne", "en"):
        print(f"\n--- {lang} ---")
        print(render(fields, labels, lang))