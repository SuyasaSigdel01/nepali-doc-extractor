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
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from ocr import run_ocr         # noqa  — placeholder, replaced below
from extract import extract_fields, lines_from_ocr_json
from explain import explain
from speak import speak

app = FastAPI(title="Nepali Document Extractor")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
AUDIO_DIR = ROOT / "data" / "audio"

MAX_UPLOAD_BYTES = 8 * 1024 * 1024          # 8 MB — a phone photo is 2-4 MB
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

Image.MAX_IMAGE_PIXELS = 50_000_000         # refuse decompression bombs


@app.get("/health")
def health():
    return {"status": "ok"}

WEB_DIR = ROOT / "web"


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.post("/extract")
async def save_upload(file: UploadFile) -> Path:
    """Stream an upload to disk, refusing anything oversized or not an image."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, "Unsupported file type")

    written = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        while chunk := await file.read(64 * 1024):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                tmp.close()
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(413, "File too large")
            tmp.write(chunk)

    try:
        with Image.open(tmp_path) as img:
            img.verify()
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(415, "Not a readable image")

    return tmp_path

async def extract_document(file: UploadFile = File(...)):
    """Take a document photo, return fields, explanations and audio URLs."""
async def save_upload(file: UploadFile) -> Path:
    """Stream an upload to disk, refusing anything oversized or not an image."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, "Unsupported file type")

    written = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        while chunk := await file.read(64 * 1024):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                tmp.close()
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(413, "File too large")
            tmp.write(chunk)

    try:
        with Image.open(tmp_path) as img:
            img.verify()
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(415, "Not a readable image")

    return tmp_path

    try:
        ocr_json = run_ocr(tmp_path)
        fields = extract_fields(lines_from_ocr_json(ocr_json))

        if len(fields) <= 1:
            raise HTTPException(422, "No recognisable fields found")

        job = uuid.uuid4().hex
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