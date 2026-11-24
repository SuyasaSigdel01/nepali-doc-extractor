"""
Turn extracted water bill fields into spoken-style Nepali sentences.
Template-based: the bill structure is fixed, so no LLM needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import to_nepali_digits
NEPALI_DAY_SUFFIX = "गते"


def explain_notice(fields: dict, lang: str = "ne") -> list[str]:
    """A short spoken summary of a notice: who, when, what about.

    Deliberately does not read the body. Notice bodies contain tables and
    footer mottos that are meaningless as speech — the summary says what
    the notice is, and the reader can look at the detail on screen.
    """
    ne = lang == "ne"
    issuer = fields.get("issuer")
    subject = fields.get("subject")
    bs = fields.get("date_bs")
    ad = fields.get("date_ad")

    lines = []

    when = ""
    if bs:
        year, month, day = bs.split("-")
        name = NEPALI_MONTHS.get(month, "")
        if ne:
            when = f"{to_nepali_digits(year)} साल {name} {to_nepali_digits(str(int(day)))} {NEPALI_DAY_SUFFIX}"
        elif ad:
            when = format_ad_for_speech(ad)
    if issuer and subject:
        if ne:
            lines.append(
                f"{issuer}ले {when + ' ' if when else ''}{subject} जारी गरेको छ।"
            )
        else:
            lines.append(
                f"{issuer} issued a notice{' on ' + when if when else ''}: {subject}"
            )
    elif subject:
        lines.append(subject)

    return lines
NEPALI_MONTHS = {
    "01": "बैशाख", "02": "जेठ", "03": "असार", "04": "श्रावण",
    "05": "भदौ", "06": "असोज", "07": "कार्तिक", "08": "मंसिर",
    "09": "पुष", "10": "माघ", "11": "फागुन", "12": "चैत",
}


def rupees(amount: float) -> str:
    """Format an amount as Nepali rupees, rounded to whole rupees for speech."""
    return "रु " + to_nepali_digits(f"{round(amount):,}")


def explain(fields: dict, lang: str = "ne") -> list[str]:
    ne = lang == "ne"
    money = rupees if ne else (lambda a: f"Rs {round(a):,}")
    num = (lambda n: to_nepali_digits(str(n))) if ne else str

    lines = []

    month = fields.get("reading_month")
    bill = fields.get("bill_amount")
    if month and bill is not None:
        lines.append(
            f"तपाईंको {month} महिनाको पानीको बिल {money(bill)} छ।" if ne
            else f"Your water bill for {month} is {money(bill)}."
        )

    consumed = fields.get("consumed_unit")
    status = fields.get("meter_status", "")
    if status and "BLOCK" in status.upper():
        lines.append(
            "मिटर बन्द भएकोले यस पटक पानीको खपत रेकर्ड भएन।" if ne
            else "The meter was blocked, so no usage was recorded this time."
        )
    elif consumed is not None:
        u = num(round(consumed))
        lines.append(
            f"यस महिना {u} युनिट पानी खपत भयो।" if ne
            else f"You used {u} units of water this month."
        )

    due = fields.get("due_amount")
    payable = fields.get("payable_amount")
    if payable is not None:
        if due:
            lines.append(
                f"पहिलेको बाँकी {money(due)} सहित जम्मा {money(payable)} तिर्नुपर्नेछ।" if ne
                else f"Including {money(due)} carried over, the total payable is {money(payable)}."
            )
        else:
            lines.append(
                f"जम्मा {money(payable)} तिर्नुपर्नेछ।" if ne
                else f"The total payable is {money(payable)}."
            )

    return lines

if __name__ == "__main__":
    import json
    fields = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for lang in ("ne", "en"):
        print(f"\n--- {lang} ---")
        for line in explain(fields, lang):
            print(line)

    MONTHS_EN = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]


def format_ad_for_speech(iso: str) -> str:
    """'2026-04-29' -> '29 April 2026'. ISO is for storage, not for speaking."""
    try:
        year, month, day = iso.split("-")
        return f"{int(day)} {MONTHS_EN[int(month) - 1]} {year}"
    except (ValueError, IndexError):
        return iso

def answer_question(fields: dict, question: str, lang: str = "ne") -> str:
    ne = lang == "ne"
    q = question.lower().strip()
    payable = fields.get("payable_amount")
    due = fields.get("due_amount")
    bill = fields.get("bill_amount")
    consumed = fields.get("consumed_unit")
    name = fields.get("customer_name") or fields.get("name")
    meter = fields.get("meter_status", "")
    month = fields.get("reading_month")

    # Order matters: first match wins.
    # "kati"/"कति" appears in many questions, so topics that pair with it
    # (due, units, meter) are checked before payable. Name/month words often
    # appear inside payable questions ("yo mahina kati tirnu?"), so they go after.

    if any(w in q for w in ["due", "baaki", "baki", "outstanding",
                            "बाँकी", "बाकी", "बक्यौता"]):
        if due is not None:
            return f"{'बाँकी रकम' if ne else 'Due amount'}: {'रू ' if ne else 'Rs '}{round(due):,}"
        return "बाँकी रकम छैन।" if ne else "No due amount found."

    if any(w in q for w in ["unit", "khapat", "consum",
                            "युनिट", "खपत"]):
        if consumed is not None:
            return f"{'खपत' if ne else 'Consumed'}: {round(consumed)} {'युनिट' if ne else 'units'}"
        return "खपत विवरण भेटिएन।" if ne else "Consumption data not found."

    if any(w in q for w in ["meter", "miṭar", "block", "status",
                            "मिटर", "मीटर", "स्थिति"]):
        return f"{'मिटर स्थिति' if ne else 'Meter status'}: {meter or ('अज्ञात' if ne else 'unknown')}"

    if any(w in q for w in ["tir", "pay", "jamma", "total", "kitti", "kati",
                            "तिर", "कति", "जम्मा"]):
        if payable is not None:
            return f"{'जम्मा तिर्नुपर्ने रकम' if ne else 'Total payable'}: {'रू ' if ne else 'Rs '}{round(payable):,}"
        elif bill is not None:
            return f"{'बिल रकम' if ne else 'Bill amount'}: {'रू ' if ne else 'Rs '}{round(bill):,}"

    if any(w in q for w in ["name", "naam", "customer",
                            "नाम"]):
        return f"{'नाम' if ne else 'Name'}: {name or ('भेटिएन' if ne else 'not found')}"

    if any(w in q for w in ["month", "mahina", "mahena",
                            "महिना", "मैना"]):
        return f"{'महिना' if ne else 'Month'}: {month or ('भेटिएन' if ne else 'not found')}"

    return ("माफ गर्नुस्, यो प्रश्नको जवाफ दिन सकिएन।" if ne
            else "Sorry, I could not answer that question from the bill.")