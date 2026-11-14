"""
Turn Nepali explanation sentences into an audio file.

Uses gTTS (needs internet). For offline use, swap this one function
for a local engine — the rest of the pipeline doesn't change.
"""

import sys
from pathlib import Path
from gtts import gTTS

sys.path.insert(0, str(Path(__file__).parent))
from explain import explain


def speak(lines: list[str], dest: Path, lang: str = "ne") -> Path:
    """Render sentences to an mp3 file."""
    text = " ".join(lines)
    if not text.strip():
        raise ValueError("nothing to speak")

    dest.parent.mkdir(parents=True, exist_ok=True)
    gTTS(text=text, lang=lang, slow=False).save(str(dest))
    return dest


if __name__ == "__main__":
    import json

    src = Path(sys.argv[1])
    fields = json.loads(src.read_text(encoding="utf-8"))
    lines = explain(fields)

    for line in lines:
        print(line)

    out = Path("data/audio") / (src.stem + "_ne.mp3")
    speak(lines, out)
    print(f"\nsaved {out}")