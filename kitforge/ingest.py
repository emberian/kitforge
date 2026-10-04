"""Normalize a pack: every audio file -> 44.1k float32 stereo wav under packs/<slug>/norm/.

ids are `category/slug` where category is the pack-relative folder (joined with '/')
and slug is the sanitized stem. A registry (packs/<slug>/files.json) maps id -> original.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from . import PACKS, SR

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aif", ".aiff", ".flac", ".ogg", ".wma", ".aac"}


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\.(wav|mp3|m4a|aiff?|flac|ogg|wma|aac)$", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "x"


def ffprobe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_name,sample_rate,channels,bits_per_sample:format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True,
    ).stdout
    j = json.loads(out or "{}")
    st = (j.get("streams") or [{}])[0]
    return {
        "codec": st.get("codec_name"),
        "sr": int(st.get("sample_rate") or 0),
        "channels": int(st.get("channels") or 0),
        "bits": int(st.get("bits_per_sample") or 0) or None,
        "duration": float((j.get("format") or {}).get("duration") or 0),
    }


def decode(path: Path, sr: int = SR) -> np.ndarray:
    """Decode anything ffmpeg can read -> (n, 2) float32 at sr."""
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-f", "f32le",
         "-acodec", "pcm_f32le", "-ar", str(sr), "-ac", "2", "-"],
        capture_output=True,
    )
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {path}: {p.stderr.decode(errors='replace')[:400]}")
    a = np.frombuffer(p.stdout, dtype=np.float32).reshape(-1, 2)
    return np.array(a)  # writable copy


def pack_dir(slug: str) -> Path:
    return PACKS / slug


def ingest(src: Path, slug: str, force: bool = False) -> dict:
    src = src.resolve()
    pd = pack_dir(slug)
    norm = pd / "norm"
    norm.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXT)
    reg: dict[str, dict] = {}
    seen: set[str] = set()
    for p in files:
        rel = p.relative_to(src)
        cat = "/".join(slugify(x) for x in rel.parent.parts) or "root"
        base = slugify(p.name)
        sid = f"{cat}/{base}"
        n = 2
        while sid in seen:
            sid = f"{cat}/{base}_{n}"
            n += 1
        seen.add(sid)
        out = norm / (sid + ".wav")
        out.parent.mkdir(parents=True, exist_ok=True)
        info = ffprobe(p)
        if force or not out.exists():
            try:
                a = decode(p)
            except RuntimeError as e:
                print(f"SKIP {rel}: {e}", file=sys.stderr)
                continue
            sf.write(out, a, SR, subtype="FLOAT")
        reg[sid] = {
            "id": sid,
            "category": cat,
            "original": str(rel),
            "original_abs": str(p),
            "norm": str(out.relative_to(pd)),
            "orig_format": info,
        }
    (pd / "files.json").write_text(json.dumps({"source": str(src), "slug": slug, "files": reg}, indent=1))
    print(f"ingested {len(reg)} files -> {pd}")
    return reg


def load_registry(slug: str) -> dict:
    return json.loads((pack_dir(slug) / "files.json").read_text())


def load_norm(slug: str, sid: str) -> np.ndarray:
    """(n,2) float32 at SR."""
    a, sr = sf.read(pack_dir(slug) / "norm" / (sid + ".wav"), dtype="float32", always_2d=True)
    assert sr == SR
    return a


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("slug")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    ingest(Path(a.src), a.slug, a.force)
