"""
Normalisation helpers for Nepali document fields.

Handles the three recurring problems found in OCR output:
  - mixed Devanagari and Western digits, sometimes within one number
  - decimal points dropped by OCR on thermal receipts
  - lakh-style comma grouping (2,54,000 = 254000)
"""

import re

NEP_DIGITS = "०१२३४५६७८९"
WESTERN_DIGITS = "0123456789"

DEV_TO_WEST = str.maketrans(NEP_DIGITS, WESTERN_DIGITS)
WEST_TO_DEV = str.maketrans(WESTERN_DIGITS, NEP_DIGITS)


def to_western_digits(text: str) -> str:
    """Convert any Devanagari digits in a string to Western digits."""
    return text.translate(DEV_TO_WEST)


def to_nepali_digits(text: str) -> str:
    """Convert any Western digits in a string to Devanagari digits."""
    return text.translate(WEST_TO_DEV)


def parse_amount(text: str) -> float | None:
    """Extract a number from OCR text, handling mixed scripts and lakh commas."""
    s = to_western_digits(text)
    s = s.replace(",", "")

    match = re.search(r"\d+(?:[.\s]\d{2})?", s)
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
        (parse_amount("Rs. 2,54,000.00"), 254000.0),
        (parse_amount("no digits here"), None),
        (normalize_bs_date("Reading Date: 2083-4-6 08:29"), "2083-04-06"),
        (normalize_bs_date("मिति: २०८३/०१ /१६"), "2083-01-16"),
        (normalize_bs_date("2080/09/15"), "2080-09-15"),
        (clean_text("  कक्षा   सञ्चालन  "), "कक्षा सञ्चालन"),
    ]

    for got, want in checks:
        mark = "ok  " if got == want else "FAIL"
        print(f"{mark} got {got!r}, want {want!r}")