"""
HTTP API for the Nepali document extractor.
Mobile client posts an image, gets back fields, explanations and audio.
"""

from fastapi import FastAPI

app = FastAPI(title="Nepali Document Extractor")


@app.get("/health")
def health():
    return {"status": "ok"}