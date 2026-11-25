"""
HTTP API for the Nepali document extractor.
Mobile client posts an image, gets back fields, explanations and audio.
"""

import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

# These imports must come after sys.path is extended above.
from ocr import run_ocr                                    # noqa: E402
from classify import classify                              # noqa: E402
from extract import extract_fields, lines_from_ocr_json    # noqa: E402
from extract_notice import extract_notice                  # noqa: E402
from explain import explain, explain_notice                # noqa: E402
from speak import speak                                    # noqa: E402

app = FastAPI(title="Nepali Document Extractor")

# Wide open for local development. Narrow to the app's real origin
# before this is ever deployed publicly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API replies get their own folder, separate from experiment outputs in
# data/audio, so the cleanup below can never delete research files.
AUDIO_DIR = ROOT / "data" / "api_audio"
WEB_DIR = ROOT / "web"

MAX_UPLOAD_BYTES = 8 * 1024 * 1024          # 8 MB — a phone photo is 2-4 MB
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

Image.MAX_IMAGE_PIXELS = 50_000_000         # refuse decompression bombs

AUDIO_TTL_SECONDS = 60 * 60                 # keep spoken replies for an hour


def prune_old_audio() -> None:
    """Delete generated audio older than AUDIO_TTL_SECONDS."""
    cutoff = time.time() - AUDIO_TTL_SECONDS
    for f in AUDIO_DIR.glob("*.mp3"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
        except FileNotFoundError:
            pass  # another request already removed it


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


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


def process_document(tmp_path: Path) -> dict:
    """The slow part: OCR, extraction and speech. Runs in a worker thread."""
    ocr_json = None
    try:
        ocr_json = run_ocr(tmp_path)
        lines = lines_from_ocr_json(ocr_json)
        kind = classify(lines)

        if kind == "water_bill":
            fields = extract_fields(lines)
            explainer = explain
            if len(fields) <= 1:
                raise HTTPException(422, "No recognisable fields found")
        elif kind == "notice":
            fields = extract_notice(lines)
            explainer = explain_notice
        else:
            raise HTTPException(422, "Document type not recognised")

        prune_old_audio()
        job = uuid.uuid4().hex
        result = {"fields": fields, "explanations": {}, "audio": {}}

        for lang in ("ne", "en"):
            spoken = explainer(fields, lang)
            result["explanations"][lang] = spoken
            speak(spoken, AUDIO_DIR / f"{job}_{lang}.mp3", lang)
            result["audio"][lang] = f"/audio/{job}_{lang}.mp3"

        return result
    finally:
        if ocr_json is not None:
            ocr_json.unlink(missing_ok=True)


@app.post("/extract")
async def extract_document(file: UploadFile = File(...)):
    """Take a document photo, return fields, explanations and audio URLs."""
    tmp_path = await save_upload(file)
    try:
        return await run_in_threadpool(process_document, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


@app.get("/audio/{name}")
def get_audio(name: str):
    path = (AUDIO_DIR / name).resolve()
    if not path.is_file() or AUDIO_DIR.resolve() not in path.parents:
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="audio/mpeg")

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=200)
    fields: dict = Field(max_length=40)
    lang: Literal["ne", "en"] = "ne"


@app.post("/ask")
def ask_question(req: AskRequest):
    """Answer a user question about an already-extracted document."""
    from explain import answer_question  # noqa: E402
    spoken = answer_question(req.fields, req.question, req.lang)
    if len(spoken) > 300:
        raise HTTPException(422, "Answer too long")
    prune_old_audio()
    job = uuid.uuid4().hex
    audio_path = AUDIO_DIR / f"{job}_ask.mp3"
    speak([spoken], audio_path, req.lang)
    return {
        "answer": spoken,
        "audio": f"/audio/{job}_ask.mp3",
    }