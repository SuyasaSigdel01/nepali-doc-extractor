"""
Turn extracted water bill fields into spoken-style Nepali sentences.
Template-based: the bill structure is fixed, so no LLM needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import to_nepali_digits

NEPALI_MONTHS = {
    "01": "बैशाख", "02": "जेठ", "03": "असार", "04": "श्रावण",
    "05": "भदौ", "06": "असोज", "07": "कार्तिक", "08": "मंसिर",
    "09": "पुष", "10": "माघ", "11": "फागुन", "12": "चैत",
}


def rupees(amount: float) -> str:
    """Format an amount as Nepali rupees, rounded to whole rupees for speech."""
    return "रु " + to_nepali_digits(f"{round(amount):,}")


def explain(fields: dict) -> list[str]:
    lines = []

    month = fields.get("reading_month")
    bill = fields.get("bill_amount")
    if month and bill is not None:
        lines.append(f"तपाईंको {month} महिनाको पानीको बिल {rupees(bill)} छ।")

    consumed = fields.get("consumed_unit")
    status = fields.get("meter_status", "")
    if status and "BLOCK" in status.upper():
        lines.append("मिटर बन्द भएकोले यस पटक पानीको खपत रेकर्ड भएन।")
    elif consumed is not None:
        units = to_nepali_digits(str(round(consumed)))
        lines.append(f"यस महिना {units} युनिट पानी खपत भयो।")

    due = fields.get("due_amount")
    payable = fields.get("payable_amount")
    if payable is not None:
        if due:
            lines.append(
                f"पहिलेको बाँकी {rupees(due)} सहित जम्मा {rupees(payable)} तिर्नुपर्नेछ।"
            )
        else:
            lines.append(f"जम्मा {rupees(payable)} तिर्नुपर्नेछ।")

    return lines

if __name__ == "__main__":
    import json
    fields = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for line in explain(fields):
        print(line)