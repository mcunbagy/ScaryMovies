"""Narration (Turkish default, or a lines file with its own "voices" map, e.g. data/lines_en.json) with edge-tts
(run in map-animation-reels/.venv). Writes audio/vo[_<lang>]/raw/<id>.mp3 and <id>.json
(word timings in seconds from line start). Skips lines whose text+voice did not change.
  ..\\map-animation-reels\\.venv\\Scripts\\python.exe scripts\\tts.py [data/lines_en.json]"""
import asyncio
import hashlib
import json
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
LINES = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "data/lines.json")
DATA = json.loads(LINES.read_text(encoding="utf-8"))
LANG = DATA.get("lang", "tr")
RAW = ROOT / ("audio/vo/raw" if LANG == "tr" else f"audio/vo_{LANG}/raw")
VOICES = {
    "nar": ("tr-TR-AhmetNeural", "+17%", "-8Hz"),
    "you": ("tr-TR-AhmetNeural", "+2%", "+4Hz"),
    "center": ("tr-TR-EmelNeural", "+6%", "-6Hz"),
    "jak": ("tr-TR-AhmetNeural", "+16%", "+2Hz"),
    "whisper": ("tr-TR-AhmetNeural", "-8%", "-16Hz"),
}
VOICES.update({k: tuple(v) for k, v in DATA.get("voices", {}).items()})


async def synth(line: dict) -> None:
    voice, rate, pitch = VOICES[line["voice"]]
    key = hashlib.md5(f"{line['say']}|{voice}|{rate}|{pitch}".encode()).hexdigest()[:10]
    meta = RAW / f"{line['id']}.json"
    if meta.exists() and json.loads(meta.read_text(encoding="utf-8")).get("key") == key:
        return
    words, audio = [], bytearray()
    com = edge_tts.Communicate(line["say"], voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    async for ch in com.stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            s = ch["offset"] / 1e7
            words.append({"w": ch["text"], "s": round(s, 3), "e": round(s + ch["duration"] / 1e7, 3)})
    (RAW / f"{line['id']}.mp3").write_bytes(audio)
    meta.write_text(json.dumps({"key": key, "words": words}, ensure_ascii=False), encoding="utf-8")
    print(line["id"], " ".join(w["w"] for w in words))


async def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for line in DATA["lines"]:
        if line["voice"] in VOICES:
            await synth(line)


asyncio.run(main())
