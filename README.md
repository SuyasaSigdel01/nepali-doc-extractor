# Nepali Document Extractor

Photograph a Nepali bill or notice, and get back what it says — as structured
data, as plain-language sentences, and as spoken audio in Nepali or English.

## Why

Many documents Nepali households receive are printed in English, or in dense
formal Nepali. A Khanepani water bill reports `Meter Status: METER BLOCKED` and
`Payable Amount: 1103.20` — the two lines that matter most — in a language a
large share of its recipients cannot read.

The output of this project is not a JSON blob. It is a sentence:

> तपाईंको श्रावण महिनाको पानीको बिल रु ५६० छ।
> मिटर बन्द भएकोले यस पटक पानीको खपत रेकर्ड भएन।
> पहिलेको बाँकी रु ५४३ सहित जम्मा रु १,१०३ तिर्नुपर्नेछ।

and the same thing read aloud, for someone who cannot read at all.

## Pipeline

```
photo → preprocess → OCR → reading-order → field extraction
                                              ↓
                              normalise (digits, dates, amounts)
                                              ↓
                          explanation templates (Nepali / English)
                                              ↓
                                      text + audio
```

| Stage | File | What it does |
|---|---|---|
| OCR | `experiments/ocr.py` | EasyOCR (`ne`+`en`), model loaded once and reused |
| Batch OCR | `experiments/batch_ocr.py` | Runs across `data/raw/`, resumable |
| Preprocess | `experiments/preprocess.py` | Greyscale, 2x upscale, CLAHE |
| Reading order | `experiments/reorder.py` | Rebuilds rows from bounding boxes |
| Normalise | `experiments/normalize.py` | Devanagari↔Western digits, amounts, BS dates |
| Extract | `experiments/extract.py` | Fuzzy label matching → structured fields |
| Explain | `experiments/explain.py` | Fields → Nepali/English sentences |
| Speak | `experiments/speak.py` | Sentences → mp3 |
| Score | `experiments/score.py` | Field-level accuracy against ground truth |
| API | `api/main.py` | FastAPI: upload image, get fields + text + audio |

## Dataset

No public dataset exists for Nepali document field extraction. The public
Nepali OCR resources are character-level handwriting sets, which do not help
with "find the total on this bill."

So the evaluation set was collected by hand: **17 documents** spanning six
print formats — thermal receipt, dot-matrix carbon copy, printed tax invoice,
institutional notice, printed ledger, and handwritten shop bill. Both numeral
systems appear across the set.

The documents are not committed. They carry real names, addresses, customer
IDs and phone numbers.

## What the data showed

Findings from the sample set, in full in `experiments/NOTES.md`:

**Schema drift within one issuer.** Two Khanepani receipts, same customer, two
months apart: one prints `Zone` / `Ward`, the other prints `Area` / `Sub Area`
for the same fields. A parser matching literal label text breaks silently when
the template changes. This is the argument for fuzzy matching over regex.

**Two numeral systems, sometimes inside one value.** Notices print `२०८३`,
receipts print `2083`, and after preprocessing a single amount came back as
`5६0.0०` — Latin and Devanagari digits interleaved. Normalisation has to work
character by character, not per-string.

**OCR confidence tracks length, not correctness.** A 28-character Devanagari
line scored 0.41 and was completely correct; a 2-character line scored 1.00.
Every extra character is another chance for the model to be unsure. A naive
confidence threshold would flag correct long text and pass short text unchecked.

**Bounding boxes are load-bearing.** EasyOCR returns regions in detection
order, not reading order — one word arrived 59th of 61 despite belonging to a
table row two-thirds up the page. Grouping regions by vertical centre and
sorting by x recovers both the reading order and the table columns.

**Preprocessing helps, partially.** Greyscale + 2x upscale + CLAHE corrected a
wrong year (2043 → 2083), the customer ID, and most lost decimal points — but
did not fix the meter readings (488 read as 484 and 448), and one field that
had been correct regressed. Conclusion: route by document type rather than
applying one pipeline to everything.

**Handwriting fails per-cell, not per-document.** On handwritten shop bills the
printed structure reads fine and only the written-in cells fail. The system
flags those cells for manual entry instead of rejecting the document.

## Status

Working end to end for Khanepani water bills: upload a photo to the API, get
fields, bilingual explanations, and two audio files back.

**Not yet measured.** Ground truth exists for two water bills; the scorer is
written but has not been run. There is no accuracy figure in this README
because there is not yet an honest one to report.

## Limitations

- Field extraction covers one document type (Khanepani water bills)
- Thermal receipts misread meter readings even after preprocessing
- Handwritten content is detected and flagged, never transcribed
- Row grouping merges logos into header rows when they sit at the same height
- The row threshold is hardcoded in pixels and is resolution-dependent
- BS→AD date conversion is not implemented (dates are normalised, not converted)
- TTS uses gTTS, which requires internet — this conflicts with the offline goal

## Running it

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows
pip install -r requirements.txt

# single document
python experiments/first_ocr.py data/raw/<image>.jpg
python experiments/reorder.py data/ocr_out/<image>.json

# API
python -m uvicorn api.main:app --reload
# then open http://127.0.0.1:8000/docs
```

`data/` is gitignored, so a fresh clone has no images. Populate `data/raw/`
before running the batch scripts.