"""Production tricks. Two kinds:

Event generators (place many events):   stutter(track, ...), roll(track, ...), pitch_ladder(track, ...)
Buffer processors (use with track.process(fn) or on any (n,2) array):
    tape_stop, gate, halfspeed, bitcrush, telephone, vinyl, reverse_reverb, sidechain_pump, swell

All buffer processors take and return (n,2) float32 at SR. Bind params with functools.partial.
"""

from __future__ import annotations

import math
from functools import partial

import librosa
import numpy as np
import pedalboard as pb

from . import SR
from .render import STEP_BEATS, Track


# --------------------------------------------------------------------------- event generators

def stutter(track: Track, sample: str, bar: int, beat: float, step: str = "32", count: int = 8,
            gain_ramp_db: float = 0.0, pitch_ramp: float = 0.0, accel: float = 1.0, **kw) -> list:
    """Retrigger `sample` `count` times from (bar, beat). accel<1 speeds up each successive gap (buildup)."""
    sb = STEP_BEATS[step]
    t = track.song.t(bar, beat)
    base_gain = kw.pop("gain_db", 0.0) + kw.pop("gain", 0.0)
    base_pitch = kw.pop("pitch", 0.0)
    evs = []
    gap = sb
    for i in range(count):
        evs.append(track.at(t, sample, gain_db=base_gain + gain_ramp_db * i / max(1, count - 1),
                            pitch=base_pitch + pitch_ramp * i / max(1, count - 1), dur_beats=gap, **kw))
        t += gap
        gap *= accel
    return evs


def roll(track: Track, sample: str, bar: int, beat: float, pattern: str = "x.xx.x.xxxxx", step: str = "16t", **kw) -> list:
    """Jersey-style triplet kick roll / fill: a step string starting at (bar, beat)."""
    sb = STEP_BEATS[step]
    t0 = track.song.t(bar, beat)
    evs = []
    for i, ch in enumerate(pattern.replace(" ", "")):
        if ch in "xX":
            evs.append(track.at(t0 + i * sb, sample, gain_db=(3.0 if ch == "X" else 0.0) + kw.get("gain_db", 0.0),
                                **{k: v for k, v in kw.items() if k != "gain_db"}))
    return evs


def pitch_ladder(track: Track, sample: str, bar: int, beat: float, semis: list[float], step: str = "8", **kw) -> list:
    """Same chop re-pitched per step: classic vocal 'melody' from one syllable."""
    sb = STEP_BEATS[step]
    t0 = track.song.t(bar, beat)
    return [track.at(t0 + i * sb, sample, pitch=s, dur_beats=sb, **kw) for i, s in enumerate(semis) if s is not None]


# --------------------------------------------------------------------------- buffer processors

def tape_stop(buf: np.ndarray, start_s: float, length_s: float = 0.6, curve: float = 2.0, resume_s: float | None = None) -> np.ndarray:
    """Tape/turntable stop beginning at start_s: pitch and speed fall to 0 over length_s, then silence until
    resume_s (default: start_s + length_s, i.e. the original continues right after the stop)."""
    s0 = int(start_s * SR)
    n = int(length_s * SR)
    out = buf.copy()
    seg = buf[s0:]
    if len(seg) < 10:
        return out
    speed = (1 - np.linspace(0, 1, n) ** (1 / curve))  # 1 -> 0
    pos = np.cumsum(speed)
    pos = pos[pos < len(seg) - 1]
    i = pos.astype(int)
    frac = (pos - i)[:, None]
    res = seg[i] * (1 - frac) + seg[i + 1] * frac
    r0 = int(resume_s * SR) if resume_s is not None else s0 + n
    out[s0:r0] = 0
    out[s0: s0 + len(res)] = res * (speed[: len(res)] ** 0.3)[:, None]
    return out


def gate(buf: np.ndarray, bpm: float, pattern: str = "x.x.x.x.x.x.x.x.", step: str = "16", attack_ms: float = 2, release_ms: float = 20, depth_db: float = -60) -> np.ndarray:
    """Trance gate / chopped-vocal effect: amplitude pattern locked to the grid."""
    sb = STEP_BEATS[step] * 60 / bpm
    n = len(buf)
    g = np.full(n, 10 ** (depth_db / 20))
    pat = pattern.replace(" ", "").replace("|", "")
    L = int(sb * SR)
    for i in range(0, n // L + 1):
        if pat[i % len(pat)] in "xX":
            g[i * L: (i + 1) * L] = 1.0
    a, r = int(attack_ms * SR / 1000), int(release_ms * SR / 1000)
    k = np.ones(max(a, 1)) / max(a, 1)
    g = np.convolve(g, k, mode="same")
    k = np.ones(max(r, 1)) / max(r, 1)
    g = np.convolve(g, k, mode="same")
    return (buf * g[:, None]).astype(np.float32)


def halfspeed(buf: np.ndarray, factor: float = 2.0) -> np.ndarray:
    """Chopped & screwed: play at 1/factor speed (pitch drops with it)."""
    return librosa.resample(buf.T, orig_sr=SR * factor, target_sr=SR, res_type="soxr_hq").T.astype(np.float32)


def bitcrush(buf: np.ndarray, bits: float = 8, downsample: float = 1.0) -> np.ndarray:
    chain = [pb.Bitcrush(bit_depth=bits)]
    if downsample > 1:
        chain.insert(0, pb.Resample(target_sample_rate=SR / downsample, quality=pb.Resample.Quality.ZeroOrderHold))
    return pb.Pedalboard(chain)(buf.T, SR).T.astype(np.float32)


def telephone(buf: np.ndarray, lo: float = 400, hi: float = 3200, drive_db: float = 12) -> np.ndarray:
    return pb.Pedalboard([pb.HighpassFilter(lo), pb.LowpassFilter(hi), pb.Distortion(drive_db), pb.Gain(-6)])(buf.T, SR).T.astype(np.float32)


def vinyl(buf: np.ndarray, lp: float = 9000, noise_db: float = -48, wow_cents: float = 8, wow_hz: float = 0.6) -> np.ndarray:
    n = len(buf)
    t = np.arange(n) / SR
    ratio = 2 ** (wow_cents / 1200 * np.sin(2 * np.pi * wow_hz * t))
    pos = np.cumsum(ratio)
    pos = np.clip(pos, 0, n - 1.001)
    i = pos.astype(int)
    f = (pos - i)[:, None]
    w = buf[i] * (1 - f) + buf[np.minimum(i + 1, n - 1)] * f
    rng = np.random.default_rng(3)
    noise = rng.normal(0, 1, (n, 2)) * 10 ** (noise_db / 20)
    crackle = (rng.random(n) < 0.0004).astype(np.float32)[:, None] * rng.uniform(0.05, 0.4, (n, 1))
    out = pb.Pedalboard([pb.LowpassFilter(lp), pb.HighpassFilter(40)])((w + noise + crackle).T.astype(np.float32), SR).T
    return out.astype(np.float32)


def reverse_reverb(buf: np.ndarray, room: float = 0.8, wet: float = 0.5, pre_s: float = 0.0) -> np.ndarray:
    """Reverb tail that swells INTO each sound (reverse the buffer, reverb, reverse back, mix)."""
    rev = pb.Pedalboard([pb.Reverb(room_size=room, wet_level=1.0, dry_level=0.0, width=1.0)])(buf[::-1].T.copy(), SR).T[::-1]
    return (buf + wet * rev).astype(np.float32)


def sidechain_pump(buf: np.ndarray, bpm: float, step: str = "4", depth_db: float = -9, release_beats: float = 0.6, curve: float = 2.0) -> np.ndarray:
    """Fake sidechain: duck on every `step` regardless of what the kick does (pads, loops)."""
    per = STEP_BEATS[step] * 60 / bpm
    n = len(buf)
    t = np.arange(n) / SR
    phase = (t % per) / (release_beats * 60 / bpm)
    env = np.clip(phase, 0, 1) ** (1 / curve)
    g = 10 ** (depth_db * (1 - env) / 20)
    return (buf * g[:, None]).astype(np.float32)


def swell(buf: np.ndarray, start_s: float, end_s: float, from_db: float = -40) -> np.ndarray:
    """Linear-in-dB fade-in between two times (risers, reverse crash feel)."""
    n = len(buf)
    g = np.ones(n)
    a, b = int(start_s * SR), int(end_s * SR)
    g[:a] = 10 ** (from_db / 20)
    g[a:b] = 10 ** (np.linspace(from_db, 0, max(1, b - a)) / 20)
    return (buf * g[:, None]).astype(np.float32)


def P(fn, **kw):
    """partial() with a readable repr for spec.json."""
    f = partial(fn, **kw)
    f.__name__ = f"{fn.__name__}({', '.join(f'{k}={v}' for k, v in kw.items())})"
    return f
