"""kitforge — turn a sample pack into a kit Claudes can compose with.

Pipeline:
  ingest   normalize any audio file to 44.1k float32 stereo, stable ids
  analyze  per-sample features -> packs/<slug>/manifest.json + MANIFEST.md + contact sheets
  render   programmatic DAW: Song/Track/Event -> wav (+ stems)
  feedback render -> spectrogram PNG + numeric critique
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKS = ROOT / "packs"
SR = 44100
