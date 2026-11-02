import sys, json
from faster_whisper import WhisperModel
import os
os.environ.setdefault('HF_HOME', 'D:/memo-app/map-animation-reels/models/hf')
m = WhisperModel(sys.argv[2] if len(sys.argv) > 2 else 'small', device='cpu', compute_type='int8')
import soundfile as sf
audio, _ = sf.read(sys.argv[1], dtype='float32')
segs, info = m.transcribe(audio, language='tr', word_timestamps=True)
out = []
for s in segs:
    print(f"{s.start:6.2f}-{s.end:6.2f} {s.text}")
    out += [dict(w=w.word, s=w.start, e=w.end) for w in s.words]
json.dump(out, open(sys.argv[1] + '.words.json', 'w', encoding='utf-8'), ensure_ascii=False)
