# Findings — Nepali Document Extractor

Lab notebook. Each entry: what was tried, what happened, what it means for the design.

## Sample set

17 documents, collected July 2026. No public Nepali document dataset exists, so
all samples were gathered by hand.

| Format | Examples |
|---|---|
| Thermal receipt | water_bill_shrawan, water_bill_jestha |
| Dot-matrix carbon | water_bill_2076 |
| Printed tax invoice | phone_bill, college_bill |
| Institutional notice | class_start_notice_kec, examcenter_ioe, retotaling_notice_ioe |
| Printed ledger | CH_group_bill |
| Handwritten shop bill | (stationery bills, printed structure + handwritten cells) |

Regions detected per document range from 31 (water_bill_2076) to 298
(result_notice_iom) — a ~10x spread that argues for per-document-type handling
rather than one generic extractor.

---

## 1. Schema drift within a single issuer

**Observed:** Two Khanepani receipts, same customer, two months apart.

```
जेठ 2083:     Zone: 04      Ward: 01
श्रावण 2083:   Area: 04      Sub Area: 01
```

Identical fields, renamed labels. The values also differ legitimately
(Due 0.00 vs 543.20), so this is a genuine template change, not a misread.

**Why it matters:** Any parser that searches for the literal string "Zone"
returns nothing after the template changes, and fails silently. This is the
argument for extracting by meaning rather than by matching label text.

---

## 2. Two numeral systems, sometimes inside one value

**Observed:** Devanagari numerals on institutional notices, Western digits on
utility receipts.

```
KEC notice:      मिति: २०८३/०१/१६
Khanepani:       Reading Date: 2083-4-6
```

Worse, after preprocessing, single values came back mixed:

```
5६0.0०     Latin 5, Devanagari ६, Latin 0, decimal, Latin 0, Devanagari ०
२0८0       Devanagari २, Latin 0, Devanagari ८, Latin 0
```

`०` and `0` are near-identical glyphs, so OCR flips between them
unpredictably.

**Why it matters:** Normalisation cannot detect the script once and convert the
whole string. It has to work character by character.

---

## 3. Confidence correlates with length, not correctness

**Observed:** on class_start_notice_kec.

| Text | Chars | Confidence | Correct? |
|---|---|---|---|
| यस | 2 | 1.00 | yes |
| तपशील | 5 | 1.00 | yes |
| काठमाण्डौं इन्जिनियरिङ्ग कलेज | 28 | 0.41 | **yes** |
| काठमाडौं इन्जिनियरिङ्ग कलेजमा अध्ययनरत... | ~70 | 0.54 | mostly |

The college name scored 0.41 and is completely correct. Every additional
character is another opportunity for uncertainty, so long strings score low
regardless of accuracy.

**Why it matters:** A naive "flag anything below 0.6 for review" rule would
flag correct long text and pass short text unchecked. Needs length-normalised
scoring, per-character confidence, or validation against expected field shapes
instead.

---

## 4. Reading order requires bounding boxes

**Observed:** EasyOCR returns regions in detection order, not reading order.
On class_start_notice_kec, the word `बैशाख` arrived among the final six of 61
regions despite belonging to a table row two-thirds up the page. Its cell was
split across three separate detections:

```
"२०८३"                        x 416–488    y-centre 1200.00
"बैशाख"                       x 485–566    y-centre 1199.25
"२९ गते सोमबार बिहान ९०० बजेदेखि"  x 567–989    y-centre 1202.50
```

Same vertical band, contiguous x-ranges. Sorting by vertical centre and
grouping into rows reassembled the cell correctly.

Note that `बैशाख`'s bbox corners are not square — EasyOCR runs a second pass
for rotated text and appends those results at the end. Every trailing region on
this document was skewed.

**Why the vertical *centre* rather than the top edge:** `बैशाख`'s top edge is
8px from its neighbour's, but its centre is under 1px away. Averaging the four
corner y-values cancels out box tilt.

**Columns are recoverable the same way:**

```
column 1 (व्याच)         x 115–195
column 2 (वर्ष / खण्ड)    x 228–365
column 3 (मिति र समय)    x 414–991
```

**Why it matters:** Which batch year pairs with which date is the entire
meaning of that table, and it exists only in the x-coordinate. Discard the
bbox and the document becomes a bag of unordered strings.

---

## 5. Known limitation — y-band grouping over-merges

**Observed:** the same row-grouping that fixes tables breaks on page headers.

```
ENG काठमाण्डौं इन्जिनियरिङ्ग कलेज
(त्रि.वि बाट सम्बन्धन प्राप्त ACM
Certified Colleze
```

`ENG` and `Colleze` are fragments of the college logo on the far left; `ACM` is
a certification badge on the far right. They sit at the same height as the
title text, so the grouping swept them in.

The algorithm cannot distinguish "same line of text" from "same distance down
the page."

**Fix, identified but not implemented:** split a row when the horizontal gap
between consecutive regions exceeds a threshold. `ENG` ends at x=140 and the
title begins at x=315 — a 175px void, far wider than any gap between real table
cells.

**Second known limitation:** the row threshold is a hardcoded 20px, tuned to
the current image resolution. Row spacing on this document is ~40px and
intra-row spread is ~5px, so 20 sits safely between — but the same document
photographed at higher resolution would break it. Fix: derive from median box
height x 0.6.

---

## 6. Preprocessing experiment — partial success

**Tried:** greyscale, 2x bicubic upscale, CLAHE (clipLimit=3.0,
tileGridSize=8x8) before OCR.
**On:** water_bill_shrawan.jpg (creased thermal receipt).

| Field | Truth | Raw OCR | Preprocessed |
|---|---|---|---|
| Reading Date | 2083-4-6 | `२०४३ 4-6` | `२083 4 6` |
| Customer ID | 493-11846 | `४93-11846` | `493-11846` |
| Area no | 04-01-135 | `04 0।-1३५` | `04 01-135` |
| Bill Amount | 560.00 | `५६० ००` | `5६0.0०` |
| Payable Amount | 1103.20 | `1१०३ २०` | `1१०३.२०` |
| Previous Unit | 488.00 | `४४४` (444) | `४८४` (484) |
| Current Unit | 488.00 | `४४८` (448) | `४४8` (448) |
| Reader Mobile | 9847165143 | `9847165143` | `98471 65(42` |

**Gains:** the reading date went from a wrong year (2043) to correct (2083).
Customer ID and area code became exactly right. Decimal points were recovered
across most amount fields.

**Losses:** the two meter readings remain wrong — 488 read as 484 and 448.
The reader's phone number regressed from correct to mangled. Script mixing
inside individual numbers got worse.

**Conclusion:** keep preprocessing (free, offline, measurably better), but it
does not reach reliable extraction on thermal receipts. Route by document type:
OCR for printed documents, vision model for low-contrast receipts.

---

## 7. Decimal points vanish on thermal receipts

**Observed:** consistently, on raw OCR of water_bill_shrawan.

```
488.00   ->  ४४४ ००
560.00   ->  ५६० ००
1103.20  ->  1१०३ २०
```

The period becomes a space every time. Preprocessing recovered most of these.

**Why it matters:** unrecoverable downstream. Once `560.00` is `५६० ००`, there
is no way to tell whether the original was 560.00 or 56000.

---

## 8. Handwriting failure is localised, not document-wide

**Observed:** on handwritten shop bills, the printed structure (shop name, PAN,
column headers क्र.सं. / विवरण / परिमाण / दर / जम्मा, serial numbers) reads
fine. Only the handwritten cell contents fail.

**Why it matters:** the system does not need to reject these documents. It can
extract the structure and mark individual cells as requiring manual entry.
Field-level flagging rather than document-level rejection.

---

## Open questions

- Does preprocessing help the printed notices, or only low-contrast receipts?
  (Only tested on one thermal receipt so far.)
- Is there a confidence signal that actually tracks correctness?
- Can the horizontal-gap fix be applied without breaking wide table columns?