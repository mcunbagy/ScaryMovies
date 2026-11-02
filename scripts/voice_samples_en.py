"""Five ~20 s English narrator samples for the US version (run in map-animation-reels/.venv).
Chatterbox take is made separately by map-animation-reels/scripts/claimcheck/tts.py (.venv_tts)."""
import asyncio
from pathlib import Path

import edge_tts

TEXT = ("You're the night watchman at a snow station on Donner Pass. The same pass that trapped the Donner Party. "
        "An avalanche just closed I-80. The nearest person is nine miles down the mountain. "
        "At 2 AM, every light in the town below goes out. All at once.")
OUT = Path(__file__).resolve().parents[1] / "voice_samples/raw"
EDGE = {  # id: (voice, rate, pitch)
    "1_christopher": ("en-US-ChristopherNeural", "-6%", "-6Hz"),
    "2_andrew": ("en-US-AndrewNeural", "-4%", "+0Hz"),
    "3_brian": ("en-US-BrianNeural", "-6%", "+0Hz"),
    "4_ava": ("en-US-AvaNeural", "-8%", "+0Hz"),
}


async def main() -> None:
    for k, (v, r, p) in EDGE.items():
        await edge_tts.Communicate(TEXT, v, rate=r, pitch=p).save(str(OUT / f"{k}.mp3"))
        print("wrote", k)


asyncio.run(main())
