"""ZİRVE GECESİ reel: voice FX -> timeline -> canvas frames (playwright) -> SFX/VO mix -> mp4.
Run scripts/tts.py first (in map-animation-reels/.venv). Then, with system Python:
  python scripts/render.py                 full render to out/<out>.mp4 (Turkish, data/lines.json)
  python scripts/render.py --lines data/lines_en.json   English version (combine with the flags below)
  python scripts/render.py --still 3,12.5  PNG stills at those times
  python scripts/render.py --sheet         contact sheet (1 frame / 2 s) instead of video"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FFDIR = ROOT.parent / "map-animation-reels/tools/ffmpeg/bin"
FF, FP = str(FFDIR / "ffmpeg.exe"), str(FFDIR / "ffprobe.exe")
W, H, FPS = 1080, 1920, 30
OUT = ROOT / "out"
LINES = ROOT / (sys.argv[sys.argv.index("--lines") + 1] if "--lines" in sys.argv else "data/lines.json")
LANG = json.loads(LINES.read_text(encoding="utf-8")).get("lang", "tr")
VO = ROOT / ("audio/vo" if LANG == "tr" else f"audio/vo_{LANG}")
SFX_DIR = ROOT / "audio/sfx"
NAME = json.loads(LINES.read_text(encoding="utf-8")).get("out", "zirve_gecesi")

RADIO = "highpass=f=450,lowpass=f=3200,acrusher=bits=10:mix=0.25,acompressor=threshold=0.05:ratio=6:makeup=3"
FX = {  # (filter, time stretch of word timings)
    "nar": ("highpass=f=60,equalizer=f=110:t=q:w=1.2:g=3,equalizer=f=3500:t=q:w=1.5:g=2,"
            "acompressor=threshold=0.08:ratio=3:attack=5:release=150:makeup=2,aecho=0.8:0.6:35|70:0.10|0.06", 1.0),
    "you": ("highpass=f=90,acompressor=threshold=0.1:ratio=2.5:makeup=1.6,aecho=0.8:0.5:25:0.08,volume=0.9", 1.0),
    "center": (RADIO, 1.0),
    "you_radio": (RADIO + ",volume=1.1", 1.0),
    "jak": ("lowpass=f=1700,highpass=f=120,acompressor=threshold=0.1:ratio=4:makeup=3,"
            "aecho=0.8:0.6:18|40:0.25|0.15,volume=1.5", 1.0),
    "whisper": ("highpass=f=160,equalizer=f=6000:t=q:w=1:g=6,acompressor=threshold=0.06:ratio=4:makeup=2.5,"
                "aecho=0.8:0.85:90|180|270:0.35|0.22|0.12", 1 / 0.94),
}
# kind -> (file, gain, extra filter)
SFX = {
    "wind_mtn": ("wind_mtn.wav", 0.55, ""), "wind_int": ("wind_int.wav", 0.35, ""),
    "winter": ("winter_loop.wav", 0.5, ""), "bass": ("bass.wav", 0.55, ""), "roomtone": ("roomtone.wav", 0.6, ""),
    "static": ("static.wav", 0.35, ""), "ping": ("radio_ping.wav", 0.5, ""), "noise": ("radio_noise.wav", 0.16, ""),
    "broken": ("radio_broken.wav", 0.3, ""), "knock": ("knock.wav", 1.0, ""), "lock": ("key_lock.wav", 0.7, ""),
    "pen": ("pen.wav", 0.8, ""), "page": ("page.wav", 0.6, ""), "clock": ("clock.wav", 0.55, ""),
    "heart": ("heartbeat.wav", 0.8, ""), "creak": ("creak.wav", 0.6, ""), "steps": ("snowsteps.wav", 0.35, ""),
    "impact": ("impact.wav", 0.5, ""), "sub": ("sub_drop.wav", 0.55, ""), "swish": ("swish.wav", 0.3, ""),
    "swoosh": ("swoosh.wav", 0.3, ""), "sweep": ("terror_sweep.wav", 0.45, ""), "riser": ("riser.wav", 0.25, ""),
    "glass": ("glass_hit.wav", 0.4, ""), "hit": ("horror_hit.wav", 0.5, ""), "beat": ("deep_beat.wav", 0.6, ""),
    "swell": ("swell.wav", 0.35, ""),
}


def probe(f: Path) -> float:
    return float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True, check=True).stdout)


def trlow(w: str) -> str:
    """Lowercase of a word (Turkish dotted/dotless i when LANG is tr), cut at the apostrophe (Dağı'nda -> dağı)."""
    if LANG == "tr":
        w = w.replace("İ", "i").replace("I", "ı")
    return w.lower().replace("’", "'").split("'")[0]


def voice(data: dict) -> list[dict]:
    """Apply per-voice FX; return lines with start/dur/words on the global timeline."""
    out, t = [], data["lead"]
    for ln in data["lines"]:
        src_id = ln.get("from", ln["id"])
        meta = json.loads((VO / "raw" / f"{src_id}.json").read_text(encoding="utf-8"))
        flt, stretch = FX[ln["voice"]]
        wav = VO / f"{ln['id']}.wav"
        # cut the TTS lead-in/tail silence: keep 40 ms before the first word, 120 ms (+ echo) after the last
        a, b = max(0.0, meta["words"][0]["s"] - 0.04), meta["words"][-1]["e"] + 0.12
        trim = f"atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,"
        if ln["voice"] == "whisper":
            trim += "asetrate=24000*0.94,"
        subprocess.run([FF, "-y", "-v", "error", "-i", str(VO / "raw" / f"{src_id}.mp3"), "-af",
                        trim + "aresample=48000," + flt + ",apad=pad_dur=0.25", "-ac", "1", "-ar", "48000", str(wav)],
                       check=True)
        words = [{"w": w["w"], "s": round(t + (w["s"] - a) * stretch, 3), "e": round(t + (w["e"] - a) * stretch, 3),
                  "c": ln.get("hi", {}).get(trlow(w["w"]), "")} for w in meta["words"]]
        dur = (b - a) * stretch
        out.append({"id": ln["id"], "scene": ln["scene"], "voice": ln["voice"], "q": ln.get("q", False), "say": ln["say"],
                    "start": round(t, 3), "dur": round(dur, 3), "words": words, "wav": str(wav)})
        t += dur + ln.get("gap", 0.3)
    return out


def build_html(data: dict, lines: list[dict]) -> tuple[Path, float]:
    dur = lines[-1]["start"] + lines[-1]["dur"] + data["tail"]
    scenes = []
    for ln in lines:
        if not scenes or scenes[-1]["id"] != ln["scene"]:
            scenes.append({"id": ln["scene"], "start": max(0.0, ln["start"] - 0.25)})
    scenes[0]["start"] = 0.0
    scenes.append({"id": "end", "start": lines[-1]["start"] + lines[-1]["dur"] + 0.45})
    for a, b in zip(scenes, scenes[1:] + [None]):
        a["end"] = b["start"] if b else dur
    d = {"title": data["title"], "night": data["night"], "dur": dur, "scenes": scenes, "lang": LANG,
         "anchors": data.get("anchors", {}), "ui": data.get("ui", {}),
         "lines": [{k: v for k, v in ln.items() if k != "wav"} for ln in lines]}
    html = (ROOT / "scripts/engine.html").read_text(encoding="utf-8").replace("/*__DATA__*/ null", json.dumps(d, ensure_ascii=False))
    p = OUT / f"_render_{NAME}.html"
    p.write_text(html, encoding="utf-8")
    return p, dur


SR = 48000


def load(f: str | Path) -> np.ndarray:
    raw = subprocess.run([FF, "-v", "error", "-i", str(f), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def movavg(x: np.ndarray, w: int) -> np.ndarray:
    c = np.cumsum(np.pad(x, (w // 2, w - w // 2)), dtype=np.float64)
    return ((c[w:] - c[:-w]) / w)[:len(x)].astype(np.float32)


def place(bus: np.ndarray, x: np.ndarray, t: float) -> None:
    i = int(round(t * SR))
    n = min(len(x), len(bus) - i)
    if n > 0:
        bus[i:i + n] += x[:n]


def build_audio(cues: list[dict], lines: list[dict], dur: float, out: Path) -> None:
    """Numpy mix: SFX/beds bus ducked under the voice bus, then ffmpeg loudnorm to -14 LUFS."""
    n = int(dur * SR) + SR
    sfx, vo, cache = np.zeros((n, 2), np.float32), np.zeros((n, 2), np.float32), {}
    for c in cues:
        f, gain, _ = SFX[c["kind"]]
        x = cache.setdefault(f, load(SFX_DIR / f))
        if c.get("ss"):
            x = x[int(c["ss"] * SR):]
        if c.get("dur"):
            m = int(c["dur"] * SR)
            x = np.tile(x, (m // len(x) + 1, 1))[:m] if c.get("loop") else x[:m]
        x = x * (gain * c.get("g", 1))
        fi, fo = int(c.get("fin", 0.02) * SR), int(c.get("fout", 0.15) * SR) if c.get("dur") else 0
        if fi:
            x[:fi] *= np.linspace(0, 1, min(fi, len(x)))[:, None][:len(x[:fi])]
        if fo:
            k = min(fo, len(x))
            x[-k:] *= np.linspace(1, 0, k)[:, None]
        place(sfx, x, c["t"])
    for ln in lines:
        place(vo, load(ln["wav"]) * 1.5, ln["start"])
    # sidechain duck: smoothed voice envelope pulls the SFX bus down by up to ~9 dB
    env = np.abs(vo).max(1)
    env = np.maximum(movavg(env, int(0.05 * SR)), movavg(env, int(0.3 * SR)) * 2)  # fast attack, slower release
    duck = 1 - 0.65 * np.clip(env / 0.05, 0, 1)
    mix = sfx * duck[:, None] + vo
    mix = mix[:int(dur * SR)]
    tmp = OUT / "_premix.f32"
    tmp.write_bytes(mix.astype(np.float32).tobytes())
    subprocess.run([FF, "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", str(tmp), "-af",
                    "alimiter=limit=0.95:level=false,loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR),
                    "-c:a", "pcm_s16le", str(out)], check=True)
    tmp.unlink()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads(LINES.read_text(encoding="utf-8"))
    lines = voice(data)
    html, dur = build_html(data, lines)
    print(f"duration {dur:.2f} s")
    stills = sheet = None
    if "--still" in sys.argv:
        stills = [float(x) for x in sys.argv[sys.argv.index("--still") + 1].split(",")]
    if "--sheet" in sys.argv:
        sheet = [round(x * 2.0 + 1.0, 2) for x in range(int(dur // 2))]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(html.as_uri())
        page.wait_for_function("window.READY === true", timeout=30000)
        if errors:
            sys.exit(f"JS errors: {errors}")
        stage = page.locator("#stage")
        if stills or sheet:
            shots = []
            for s in stills or sheet:
                page.evaluate(f"seek({s})")
                png = OUT / f"still_{s:05.1f}.png"
                stage.screenshot(path=str(png))
                shots.append(png)
            if errors:
                sys.exit(f"JS errors: {errors}")
            browser.close()
            if sheet:
                n = len(shots)
                lst = OUT / "_sheet.txt"
                lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in shots), encoding="utf-8")
                cols = 8
                subprocess.run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf",
                                f"scale=216:384,tile={cols}x{(n + cols - 1) // cols}", "-frames:v", "1",
                                str(OUT / f"sheet_{NAME}.jpg")], check=True)
                for s in shots:
                    s.unlink()
                print("sheet:", OUT / f"sheet_{NAME}.jpg")
            else:
                print("stills:", *shots)
            return
        n = int(round(dur * FPS))
        silent = OUT / f"_video_{NAME}.mp4"
        if "--mix" in sys.argv and silent.exists():   # audio only: reuse the frames rendered last time
            n = 0
        enc = None if n == 0 else subprocess.Popen([FF, "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                                "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                                str(silent)], stdin=subprocess.PIPE)
        for i in range(n):
            page.evaluate(f"seek({i / FPS})")
            enc.stdin.write(stage.screenshot(type="jpeg", quality=93))
            if i % 150 == 0:
                print(f"  frame {i}/{n}", flush=True)
        if enc:
            enc.stdin.close()
            enc.wait()
        cues = page.evaluate("window.CUES")
        if errors:
            sys.exit(f"JS errors: {errors}")
        browser.close()
    wav = OUT / f"_mix_{NAME}.wav"
    build_audio(cues, lines, dur, wav)
    final = OUT / f"{NAME}.mp4"
    subprocess.run([FF, "-y", "-v", "error", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    for tmp in (silent, wav):
        tmp.unlink(missing_ok=True)
    print(f"done: {final}  ({dur:.1f} s)")


if __name__ == "__main__":
    main()
