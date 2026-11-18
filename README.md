# Nepali Document Extractor

Photograph a Nepali utility bill and hear what it says — in Nepali or English.

Most bills and official notices in Nepal are printed in English, or in a mix of
English labels and Devanagari values. For someone who doesn't read English
comfortably, a water bill is a page of numbers with no way in. This reads the
bill aloud and says what each number means.

## What it does

1. You photograph a bill from a phone.
2. OCR reads the text and reconstructs reading order from bounding boxes.
3. Fields are matched against known label variants and normalised.
4. A plain-language explanation is generated in both Nepali and English.
5. Both versions are spoken aloud as audio.

No LLM in the extraction path. That was deliberate: field extraction here is
deterministic and auditable, and a model that hallucinates a plausible-looking
amount on someone's water bill is worse than one that says it couldn't read it.

## Results

Measured against hand-labeled ground truth, 27 fields per document:

| Document | Baseline | After extraction fixes |
|---|---|---|
| `water_bill_jestha` | 11.1% (3/27) | 48.1% (13/27) |
| `water_bill_shrawan` | 25.9% (7/27) | 59.3% (16/27) |
| **Overall** | **18.5%** | **53.7%** |

Reproduce with `python experiments/evaluate.py`.

**The eval set is two documents.** Seventeen were collected, two are labeled.
The percentages are a development signal, not a benchmark, and they're reported
here as such.

### What moved the number

Three fixes, all in the extraction layer, none in OCR:

- **Label-aware value splitting.** The parser looked for a colon or two spaces
  to separate label from value. OCR supplies neither — `'Previouis Unit ४४४ ००'`
  has one space and no colon. Since the matcher already knows which label it
  matched, it now slices the label off the front instead of guessing at
  separators. Nine fields recovered.
- **Similarity scoring on short labels.** Labels were compared against
  `line[:len(label) + 4]`, so `"Name"` was judged against eight characters and
  scored 0.667 — below the 0.7 threshold. Correct label, impossible test.
- **OCR digit confusions.** `1103.20` is read as `1।03.Z0` on thermal paper.
  A substitution table (danda → 1, Z → 2, O → 0) applied **only inside tokens
  that already contain a digit** fixes it without turning the word "no" into a
  zero.

### What's still wrong

The residual errors are character-level OCR damage, not matching logic:

| Field | Got | Want |
|---|---|---|
| `previous_unit` | `444.0` | `488.0` |
| `current_unit` | `448.0` | `488.0` |
| `reader_name` | — | `MONA SHRESTHA` (OCR: `SHIRESTHA`) |
| `reading_date_bs` | — | `2083-02-10` (OCR: `20U3`) |

Devanagari numerals on thermal receipts are where this breaks down: `४८८`
reads as `४४४`, `२०८३` as `२०४३`. An image preprocessing pass
(greyscale + 2× upscale + CLAHE) fixed some fields and regressed others, which
is what motivates the planned hybrid design — OCR for printed documents, a
vision model for thermal receipts.

## Scope

- **Printed documents only.** Handwriting is flagged for manual review rather
  than guessed at.
- **Khanepani water bills** are the only template with a field schema so far.
  Other document types return `422 No recognisable fields found` rather than
  inventing output.
- **No fraud detection, no medical documents.** Both were considered and
  dropped as unsafe to automate.

## Running it

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
pip install -r requirements.txt

python -m uvicorn api.main:app --reload
```

Open `http://127.0.0.1:8000`. To use it from a phone on the same network,
bind wider with `--host 0.0.0.0` and visit `http://<your-ip>:8000`.

Audio generation calls Google TTS, so that step needs internet. Everything
else runs locally.

### API

| Endpoint | Purpose |
|---|---|
| `GET /` | Mobile web client |
| `POST /extract` | Image in; fields, explanations and audio URLs out |
| `GET /audio/{name}` | Generated mp3 |
| `GET /health` | Liveness check |

## Layout

```
api/main.py            FastAPI service
web/index.html         Mobile client — camera capture, bilingual playback
labels/                Bilingual display labels per document type
experiments/
  ocr.py               Shared OCR entry point, model loaded once
  batch_ocr.py         Bulk OCR over the sample set
  reorder.py           Reading-order reconstruction from bounding boxes
  preprocess.py        Greyscale / upscale / CLAHE experiment
  extract.py           Label matching and field extraction
  normalize.py         Digits, amounts, BS dates, OCR confusions
  explain.py           Plain-language bilingual explanations
  speak.py             Text to speech
  score.py             Per-field comparison against ground truth
  evaluate.py          Scoring across every labeled document
  show_lines.py        Debugging aid — what the extractor actually sees
```

Sample documents and ground truth are not committed: they contain a real
customer's name, address and phone number.

## Next

- Label more of the seventeen collected documents so the eval set means something
- Vision-model path for thermal receipts
- Field schemas for electricity bills and institutional notices