"""
Normalisation helpers for Nepali document fields.

Handles the recurring problems found in OCR output:
  - mixed Devanagari and Western digits, sometimes within one number
  - decimal points dropped by OCR on thermal receipts
  - characters OCR substitutes for digits (danda for 1, Z for 2)
  - lakh-style comma grouping (2,54,000 = 254000)
"""

import re
import nepali_datetime as nd

NEP_DIGITS = "०१२३४५६७८९"
WESTERN_DIGITS = "0123456789"

DEV_TO_WEST = str.maketrans(NEP_DIGITS, WESTERN_DIGITS)
WEST_TO_DEV = str.maketrans(WESTERN_DIGITS, NEP_DIGITS)

# Characters OCR commonly substitutes for digits on thermal receipts.
# Applied only inside tokens that already contain a digit.
OCR_DIGIT_CONFUSIONS = str.maketrans({
    "।": "1", "|": "1", "l": "1", "I": "1",
    "O": "0", "o": "0", "U": "0",
    "Z": "2",
})

def bs_to_ad(bs_date: str) -> str | None:
    """Convert a 'YYYY-MM-DD' Bikram Sambat date to the Gregorian equivalent.

    Returns None for anything unparseable or outside the library's range,
    rather than raising — a bad date on one field shouldn't kill extraction.
    """
    try:
        year, month, day = (int(p) for p in bs_date.split("-"))
        return nd.date(year, month, day).to_datetime_date().isoformat()
    except Exception:
        return None
    
def to_western_digits(text: str) -> str:
    """Convert any Devanagari digits in a string to Western digits."""
    return text.translate(DEV_TO_WEST)


def to_nepali_digits(text: str) -> str:
    """Convert any Western digits in a string to Devanagari digits."""
    return text.translate(WEST_TO_DEV)


def _apply_digit_confusions(text: str) -> str:
    """Fix OCR digit confusions, but only inside tokens that already hold a digit."""
    return " ".join(
        token.translate(OCR_DIGIT_CONFUSIONS) if any(c.isdigit() for c in token) else token
        for token in text.split()
    )


def parse_amount(text: str) -> float | None:
    """Extract a number from OCR text, handling mixed scripts and lakh commas."""
    s = to_western_digits(text)
    s = _apply_digit_confusions(s)
    s = s.replace(",", "")

    match = re.search(r"\d+(?:[.\s]\d{1,2})?", s)
    if not match:
        return None

    num = match.group().replace(" ", ".")
    try:
        return float(num)
    except ValueError:
        return None


def normalize_bs_date(text: str) -> str | None:
    """Pull a BS date out of OCR text and return it as YYYY-MM-DD."""
    s = to_western_digits(text)

    match = re.search(r"(\d{4})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})", s)
    if not match:
        return None

    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def clean_text(text: str) -> str:
    """Collapse repeated whitespace and strip edges."""
    return re.sub(r"\s+", " ", text).strip()


if __name__ == "__main__":
    checks = [
        (to_western_digits("5६0.0०"), "560.00"),
        (to_nepali_digits("560.00"), "५६०.००"),
        (parse_amount("५६० ००"), 560.0),
        (parse_amount("1१०३.२०"), 1103.2),
        (parse_amount("1।03.Z0"), 1103.2),
        (parse_amount("Rs. 2,54,000.00"), 254000.0),
        (parse_amount("no digits here"), None),
        (normalize_bs_date("Reading Date: 2083-4-6 08:29"), "2083-04-06"),
        (normalize_bs_date("मिति: २०८३/०१ /१६"), "2083-01-16"),
        (normalize_bs_date("2080/09/15"), "2080-09-15"),
        (clean_text("  कक्षा   सञ्चालन  "), "कक्षा सञ्चालन"),
        (bs_to_ad("2080-09-15"), "2023-12-31"),
        (bs_to_ad("not a date"), None),
        (bs_to_ad("9999-13-45"), None),
    ]

    for got, want in checks:
        mark = "ok  " if got == want else "FAIL"
        print(f"{mark} got {got!r}, want {want!r}")