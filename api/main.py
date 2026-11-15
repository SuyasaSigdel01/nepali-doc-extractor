"""
HTTP API for the Nepali document extractor.
Mobile client posts an image, gets back fields, explanations and audio.
"""

import json
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from ocr import run_ocr         # noqa  — placeholder, replaced below
from extract import extract_fields, lines_from_ocr_json
from explain import explain
from speak import speak

app = FastAPI(title="Nepali Document Extractor")

AUDIO_DIR = ROOT / "data" / "audio"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract_document(file: UploadFile = File(...)):
    """Take a document photo, return fields, explanations and audio URLs."""
    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        ocr_json = run_ocr(tmp_path)
        fields = extract_fields(lines_from_ocr_json(ocr_json))

        if len(fields) <= 1:
            raise HTTPException(422, "No recognisable fields found")

        job = uuid.uuid4().hex[:8]
        result = {"fields": fields, "explanations": {}, "audio": {}}

        for lang in ("ne", "en"):
            lines = explain(fields, lang)
            result["explanations"][lang] = lines
            speak(lines, AUDIO_DIR / f"{job}_{lang}.mp3", lang)
            result["audio"][lang] = f"/audio/{job}_{lang}.mp3"

        return result
    finally:
        tmp_path.unlink(missing_ok=True)


@app.get("/audio/{name}")
def get_audio(name: str):
    path = (AUDIO_DIR / name).resolve()
    if not path.is_file() or AUDIO_DIR.resolve() not in path.parents:
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="audio/mpeg")