"""Mashup planning: key/tempo compatibility across samples (and across packs).

    from kitforge.mashup import camelot, plan, harmonic_pairs
    plan(["vocals/vocal_loops/drop_vocals_139bpm_2", "sfx/perc_loops/everybody_loop_138bpm"], bpm=140, key="Fm")
"""

from __future__ import annotations

import itertools
import math

from .analyze import load_manifest

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ENH = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
# Camelot wheel: number + A (minor) / B (major)
_CAMELOT_MINOR = {"G#m": 1, "D#m": 2, "A#m": 3, "Fm": 4, "Cm": 5, "Gm": 6, "Dm": 7, "Am": 8, "Em": 9, "Bm": 10, "F#m": 11, "C#m": 12}
_CAMELOT_MAJOR = {"B": 1, "F#": 2, "C#": 3, "G#": 4, "D#": 5, "A#": 6, "F": 7, "C": 8, "G": 9, "D": 10, "A": 11, "E": 12}


def norm_key(k: str) -> str:
    minor = k.endswith("m")
    root = k[:-1] if minor else k
    root = ENH.get(root, root)
    return root + ("m" if minor else "")


def camelot(key: str) -> str:
    k = norm_key(key)
    return f"{_CAMELOT_MINOR[k]}A" if k.endswith("m") else f"{_CAMELOT_MAJOR[k]}B"


def key_root(key: str) -> int:
    k = norm_key(key)
    return NOTES.index(k[:-1] if k.endswith("m") else k)


def compatible(k1: str, k2: str) -> bool:
    """Camelot-compatible: same, ±1 on the wheel, or relative major/minor."""
    a, b = camelot(k1), camelot(k2)
    na, la = int(a[:-1]), a[-1]
    nb, lb = int(b[:-1]), b[-1]
    if la == lb:
        return (na - nb) % 12 in (0, 1, 11)
    return na == nb


def semitones_to(src_key: str, dst_key: str) -> int:
    """Smallest signed shift that moves src root onto dst root (ignores mode)."""
    d = (key_root(dst_key) - key_root(src_key)) % 12
    return d - 12 if d > 6 else d


def stretch_ratio(src_bpm: float, dst_bpm: float) -> float:
    """Speed factor (>1 faster). Also considers half/double-time and returns the closest-to-1 option."""
    opts = [dst_bpm / src_bpm, dst_bpm / (2 * src_bpm), 2 * dst_bpm / src_bpm]
    return min(opts, key=lambda r: abs(math.log2(r)))


def plan(sample_ids: list[str], bpm: float, key: str | None = None, pack: str = "twerknation28") -> list[dict]:
    """For each sample: suggested stretch factor, semitone shift, and warnings."""
    man = load_manifest(pack)
    out = []
    for sid in sample_ids:
        r = man[sid]
        t = r.get("tempo", {})
        sb = t.get("bpm_name") or t.get("bpm_best_fit")
        ke = r.get("keyest", {})
        sk = ke.get("key") if ke.get("conf", 0) > 0.05 else None
        row = {"id": sid, "native_bpm": sb, "native_key": sk, "camelot": camelot(sk) if sk else None}
        warn = []
        if sb:
            ratio = stretch_ratio(sb, bpm)
            row["stretch"] = round(ratio, 4)
            if abs(math.log2(ratio)) > math.log2(1.15):
                warn.append(f"stretch {ratio:.2f}x is >15%: expect artifacts (consider pitch_mode=resample for an intentional chipmunk/screw)")
        if key and sk:
            st = semitones_to(sk, key)
            row["semitones"] = st
            row["compatible_unshifted"] = compatible(sk, key)
            if abs(st) > 3 and r["category"].startswith("vocals"):
                warn.append(f"{st:+d} st on a vocal will sound processed; try the relative key or pitch_mode=formant")
        row["warnings"] = warn
        out.append(row)
    return out


def harmonic_pairs(pack: str = "twerknation28", min_dur: float = 2.0, conf: float = 0.08) -> list[tuple[str, str, str, str]]:
    """Pairs of longer tonal samples whose estimated keys are Camelot-compatible."""
    man = load_manifest(pack)
    keyed = [(sid, r["keyest"]["key"]) for sid, r in man.items()
             if r.get("dur", 0) >= min_dur and r.get("keyest", {}).get("conf", 0) >= conf and r.get("keyest", {}).get("key")]
    return [(a, ka, b, kb) for (a, ka), (b, kb) in itertools.combinations(keyed, 2) if compatible(ka, kb)]
