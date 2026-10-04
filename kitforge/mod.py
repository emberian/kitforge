"""Juice: control signals, modulation targets, buses, sends/throws, and the processors producers reach for.

Control signals are callables evaluated once per render to a float array (one value per sample):

    from kitforge.mod import LFO, Follow, Steps, Ramp, Const
    pad.mod("lp", LFO(rate_beats=8, lo=400, hi=6000, shape="sine"))                 # tempo-synced filter sweep
    pad.mod("lp", LFO(rate_beats=1, lo=300, hi=5000, rate_mod=LFO(16, 0.5, 2.0)))   # LFO whose rate is an LFO
    hats.mod("gain", Follow("kick", lo=-6, hi=0, invert=True, release_ms=120))        # hats duck under the kick
    squeak.mod("lp", Follow("vox", lo=800, hi=9000))                                   # squeak opens when the vocal sings
    vox.mod("send:echo", Steps([0, 0, 0, 1], step="4"))                                # delay throw on beat 4 (per bar)
    vox.mod("pan", LFO(rate_beats=2, lo=-0.6, hi=0.6, shape="tri"))                    # autopan
    chords.mod("width", Ramp([(0, 0.5), (32, 1.0)]))                                   # verse 75% -> chorus full

Targets: lp, hp (Hz) · gain (dB) · pan (-1..1) · width (0 mono .. 1 full .. 2 wide) · drive (dB, tanh) · send:<name> (0..1).
Per-event envelopes (in pattern/hit kwargs): pitch_env=(semis_start, semis_end, seconds) · lp_env=(hz_start, hz_end, seconds).
Parameter locks: pattern(..., plocks={"pitch": [0, 0, 12, 7], "gain": [0, -4, 0, -2], "pan": [-.5, .5]}) rotate per hit.
Buses: song.bus("drums", ["kick", "clap", "squeak"], fx=[...]) then P(ott) / glue on the bus; sends: song.send("echo", fx=[Delay...]).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pedalboard as pb
from scipy.signal import butter, sosfilt

from . import SR


# ------------------------------------------------------------------ signals

class Signal:
    def __call__(self, song, n: int, bufs: dict | None = None) -> np.ndarray:  # pragma: no cover - interface
        raise NotImplementedError

    def __add__(self, other):
        return Mix(self, other, "add")

    def __mul__(self, other):
        return Mix(self, other, "mul")


def _beats(song, n: int) -> np.ndarray:
    return np.arange(n) / SR * song.bpm / 60.0


def _as_signal(x) -> "Signal":
    return x if isinstance(x, Signal) else Const(float(x))


@dataclass
class Const(Signal):
    value: float

    def __call__(self, song, n, bufs=None):
        return np.full(n, self.value)


@dataclass
class LFO(Signal):
    """Tempo-synced LFO between lo and hi. rate_beats = period in beats (4 = one bar). shape: sine tri saw rsaw square sh
    (sample&hold random). rate_mod / depth_mod are Signals (rate in beats; depth 0..1 scales the swing around centre).
    phase in cycles. 'sh' needs seed."""
    rate_beats: float = 4.0
    lo: float = 0.0
    hi: float = 1.0
    shape: str = "sine"
    phase: float = 0.0
    rate_mod: Signal | None = None
    depth_mod: Signal | None = None
    seed: int = 0

    def __call__(self, song, n, bufs=None):
        b = _beats(song, n)
        if self.rate_mod is None:
            ph = b / self.rate_beats + self.phase
        else:
            rate = np.maximum(self.rate_mod(song, n, bufs), 1e-3)
            ph = np.cumsum(1.0 / rate) * (b[1] - b[0] if n > 1 else 0) + self.phase  # integrate instantaneous frequency
        f = ph % 1.0
        if self.shape == "sine":
            u = 0.5 - 0.5 * np.cos(2 * np.pi * f)  # starts at lo
        elif self.shape == "tri":
            u = 1 - np.abs(2 * f - 1)
        elif self.shape == "saw":
            u = f
        elif self.shape == "rsaw":
            u = 1 - f
        elif self.shape == "square":
            u = (f < 0.5).astype(float)
        elif self.shape == "sh":
            rng = np.random.default_rng(self.seed)
            cyc = np.floor(ph).astype(int)
            vals = rng.random(int(cyc.max()) + 2)
            u = vals[cyc - cyc.min()]
        else:
            raise ValueError(self.shape)
        if self.depth_mod is not None:
            d = np.clip(self.depth_mod(song, n, bufs), 0, 1)
            u = 0.5 + (u - 0.5) * d
        return self.lo + (self.hi - self.lo) * u


@dataclass
class Follow(Signal):
    """Envelope follower of another track's buffer (pre-fx), normalized to its own peak, mapped lo..hi.
    invert=True gives ducking (loud source -> lo)."""
    track: str
    lo: float = 0.0
    hi: float = 1.0
    attack_ms: float = 3.0
    release_ms: float = 120.0
    invert: bool = False
    curve: float = 1.0

    def __call__(self, song, n, bufs=None):
        from .render import _follower
        src = bufs[self.track].mean(axis=1) if bufs and self.track in bufs else np.zeros(n)
        env = _follower(np.abs(src), self.attack_ms, self.release_ms)
        env = env / (env.max() or 1.0)
        env = env ** self.curve
        if self.invert:
            env = 1 - env
        return self.lo + (self.hi - self.lo) * env[:n]


@dataclass
class Steps(Signal):
    """Per-step value sequence (parameter-lock lane): values cycle every `step`; starts at `bar`. Smoothed by slew_ms."""
    values: list
    step: str = "16"
    bar: int = 0
    slew_ms: float = 5.0

    def __call__(self, song, n, bufs=None):
        from .render import STEP_BEATS
        b = _beats(song, n) - song.t(self.bar, 0)
        idx = np.floor(b / STEP_BEATS[self.step]).astype(int)
        vals = np.array(self.values, dtype=float)
        out = vals[np.where(idx >= 0, idx % len(vals), 0)]
        if self.slew_ms:
            k = max(1, int(SR * self.slew_ms / 1000))
            out = np.convolve(out, np.ones(k) / k, mode="same")
        return out


@dataclass
class Ramp(Signal):
    """Breakpoints [(beat, value)...], linear or 'step' hold, optional exponent for curves."""
    points: list
    mode: str = "linear"
    curve: float = 1.0

    def __call__(self, song, n, bufs=None):
        b = _beats(song, n)
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        if self.mode == "step":
            i = np.clip(np.searchsorted(xs, b, side="right") - 1, 0, len(ys) - 1)
            return np.array(ys, dtype=float)[i]
        if self.curve != 1.0:
            # piecewise: normalize within each segment then apply the curve
            out = np.interp(b, xs, ys)
            for (x0, y0), (x1, y1) in zip(self.points, self.points[1:]):
                m = (b >= x0) & (b < x1)
                u = (b[m] - x0) / max(1e-9, (x1 - x0))
                out[m] = y0 + (y1 - y0) * u ** self.curve
            return out
        return np.interp(b, xs, ys)


@dataclass
class Mix(Signal):
    a: Signal
    b: Signal
    op: str = "add"

    def __call__(self, song, n, bufs=None):
        x, y = _as_signal(self.a)(song, n, bufs), _as_signal(self.b)(song, n, bufs)
        return x + y if self.op == "add" else x * y


@dataclass
class Random(Signal):
    """Per-step random values in lo..hi (humanize / 'random sliver' moves)."""
    lo: float = 0.0
    hi: float = 1.0
    step: str = "16"
    seed: int = 1

    def __call__(self, song, n, bufs=None):
        from .render import STEP_BEATS
        b = _beats(song, n)
        idx = np.floor(b / STEP_BEATS[self.step]).astype(int)
        rng = np.random.default_rng(self.seed)
        vals = rng.uniform(self.lo, self.hi, int(idx.max()) + 2)
        return vals[idx]


# ------------------------------------------------------------------ applying signals to buffers

def apply_target(buf: np.ndarray, param: str, sig: np.ndarray, block: int = 512) -> np.ndarray:
    """Apply a per-sample control signal to a (n,2) buffer for the given target."""
    n = len(buf)
    sig = sig[:n] if len(sig) >= n else np.pad(sig, (0, n - len(sig)), mode="edge")
    if param == "gain":
        return (buf * (10 ** (sig / 20))[:, None]).astype(np.float32)
    if param == "pan":
        th = (np.clip(sig, -1, 1) + 1) * math.pi / 4
        return (buf * np.stack([np.cos(th), np.sin(th)], 1) * math.sqrt(2)).astype(np.float32)
    if param == "width":
        m = (buf[:, 0] + buf[:, 1]) / 2
        s = (buf[:, 0] - buf[:, 1]) / 2 * np.clip(sig, 0, 3)
        return np.stack([m + s, m - s], 1).astype(np.float32)
    if param == "drive":
        g = 10 ** (np.clip(sig, 0, 40) / 20)
        return (np.tanh(buf * g[:, None]) / np.tanh(np.maximum(g, 1e-3))[:, None]).astype(np.float32)
    if param in ("lp", "hp"):
        plug = pb.LowpassFilter(float(np.clip(sig[0], 20, 20000))) if param == "lp" else pb.HighpassFilter(float(np.clip(sig[0], 10, 20000)))
        out = np.empty_like(buf)
        for i in range(0, n, block):
            plug.cutoff_frequency_hz = float(np.clip(sig[i], 10, 20000))
            out[i: i + block] = plug(buf[i: i + block].T, SR, reset=False).T
        return out
    raise ValueError(f"unknown mod target {param!r}")


# ------------------------------------------------------------------ per-event envelopes

def pitch_env(a: np.ndarray, semis_start: float, semis_end: float, seconds: float) -> np.ndarray:
    """Variable-speed read: pitch glides from semis_start to semis_end over `seconds`, then holds semis_end.
    (808 pitch drops, laser 'pew' chops, tape-flutter starts.)"""
    n = len(a)
    if n < 4:
        return a
    t = np.arange(n) / SR
    semis = np.where(t < seconds, semis_start + (semis_end - semis_start) * (t / max(seconds, 1e-6)), semis_end)
    speed = 2 ** (semis / 12)
    pos = np.cumsum(speed) - speed[0]
    pos = pos[pos < n - 1]
    i = pos.astype(int)
    f = (pos - i)[:, None]
    return (a[i] * (1 - f) + a[i + 1] * f).astype(np.float32)


def lp_env(a: np.ndarray, hz_start: float, hz_end: float, seconds: float, block: int = 256) -> np.ndarray:
    """Per-hit lowpass envelope (growl opens, pluck closes)."""
    n = len(a)
    t = np.arange(0, n, block) / SR
    cur = np.where(t < seconds, hz_start * (hz_end / hz_start) ** (t / max(seconds, 1e-6)), hz_end)
    plug = pb.LowpassFilter(float(cur[0]))
    out = np.empty_like(a)
    for k, i in enumerate(range(0, n, block)):
        plug.cutoff_frequency_hz = float(np.clip(cur[k], 20, 20000))
        out[i: i + block] = plug(a[i: i + block].T, SR, reset=False).T
    return out


# ------------------------------------------------------------------ processors (use with track.process(P(fn, ...)) or on buses)

def _xover(x: np.ndarray, lo: float, hi: float):
    s1 = butter(4, lo, btype="low", fs=SR, output="sos")
    s2 = butter(4, [lo, hi], btype="band", fs=SR, output="sos")
    s3 = butter(4, hi, btype="high", fs=SR, output="sos")
    return sosfilt(s1, x, axis=0), sosfilt(s2, x, axis=0), sosfilt(s3, x, axis=0)


def ott(buf: np.ndarray, depth: float = 0.6, target_db: float = -18.0, up_ratio: float = 0.5, down_ratio: float = 0.5,
        max_up_db: float = 18.0, attack_ms: float = 8.0, release_ms: float = 90.0, lo: float = 130.0, hi: float = 2500.0,
        band_gain_db=(0.0, 0.0, 0.0)) -> np.ndarray:
    """OTT-style 3-band upward+downward compression: every band is pulled toward target_db from both sides.
    depth mixes dry/wet. The hyperpop/internet-Jersey 'everything is loud and fizzy' sound; also great on vocal chops."""
    from .render import _follower
    bands = _xover(buf, lo, hi)
    out = np.zeros_like(buf)
    tgt = 10 ** (target_db / 20)
    for k, b in enumerate(bands):
        env = _follower(np.abs(b).mean(axis=1), attack_ms, release_ms)
        env = np.maximum(env, 1e-6) * 1.4  # rms-ish
        up = np.minimum(10 ** ((max_up_db if k < 2 else min(max_up_db, 6.0)) / 20), (tgt / env) ** up_ratio)  # highs: max +6 dB
        down = (tgt / env) ** down_ratio
        g = np.where(env < tgt, up, down)
        out += b * g[:, None] * (10 ** (band_gain_db[k] / 20))
    wet = out.astype(np.float32)
    return ((1 - depth) * buf + depth * wet).astype(np.float32)


def saturate(buf: np.ndarray, drive_db: float = 6.0, kind: str = "tanh", mix: float = 1.0) -> np.ndarray:
    g = 10 ** (drive_db / 20)
    x = buf * g
    if kind == "tanh":
        y = np.tanh(x) / math.tanh(min(g, 20))
    elif kind == "soft":
        y = np.where(np.abs(x) < 1, x - x ** 3 / 3, np.sign(x) * 2 / 3) * 1.5 / g
    elif kind == "hard":
        y = np.clip(x, -1, 1) / min(g, 1.0) if g < 1 else np.clip(x, -1, 1)
    elif kind == "tape":
        y = np.tanh(x * 0.8 + 0.1 * x ** 2) / math.tanh(min(g, 20) * 0.8)
    else:
        raise ValueError(kind)
    return ((1 - mix) * buf + mix * y).astype(np.float32)


def transient(buf: np.ndarray, attack_db: float = 6.0, sustain_db: float = 0.0, fast_ms: float = 1.0, slow_ms: float = 30.0) -> np.ndarray:
    """Transient shaper: boost/cut the attack portion (difference of fast and slow envelopes)."""
    from .render import _follower
    x = np.abs(buf).mean(axis=1)
    fast = _follower(x, fast_ms, 20.0)
    slow = _follower(x, slow_ms, 120.0)
    att = np.clip((fast - slow) / (fast.max() + 1e-9), 0, 1)
    sus = 1 - att
    g = 10 ** ((attack_db * att + sustain_db * sus) / 20)
    return (buf * g[:, None]).astype(np.float32)


def width(buf: np.ndarray, amount: float = 1.5, mono_below_hz: float | None = 120.0) -> np.ndarray:
    """M/S width; optionally keeps everything under mono_below_hz centred (club rule)."""
    m = (buf[:, 0] + buf[:, 1]) / 2
    s = (buf[:, 0] - buf[:, 1]) / 2 * amount
    if mono_below_hz:
        sos = butter(2, mono_below_hz, btype="high", fs=SR, output="sos")
        s = sosfilt(sos, s)
    return np.stack([m + s, m - s], 1).astype(np.float32)


def haas(buf: np.ndarray, ms: float = 12.0, side: str = "R", level_db: float = -1.0) -> np.ndarray:
    d = int(ms * SR / 1000)
    out = buf.copy()
    ch = 1 if side == "R" else 0
    out[d:, ch] = buf[:-d, ch] * (10 ** (level_db / 20))
    out[:d, ch] = 0
    return out


def comb(buf: np.ndarray, ms: float = 8.0, feedback: float = 0.85, mix: float = 0.5) -> np.ndarray:
    """Very short delay with high feedback: metallic 'robot/quad damage' resonance on vocals."""
    d = max(1, int(ms * SR / 1000))
    y = buf.copy()
    for i in range(d, len(buf)):
        y[i] += feedback * y[i - d]
    y *= (1 - feedback)
    return ((1 - mix) * buf + mix * y).astype(np.float32)


def spit_delay(track, sample: str, bar: int, beat: float, n_words: int = 4, word_step: str = "8", slice_n: int = 8, **kw):
    """'Spit delay': the first 16th of each word repeated — re-trigger a short slice on every word position."""
    from .render import STEP_BEATS
    sb = STEP_BEATS[word_step]
    t0 = track.song.t(bar, beat)
    return [track.at(t0 + i * sb, sample, slice=(i % slice_n, slice_n), onset_slice=True, dur_beats=0.25, **kw) for i in range(n_words)]


def deess(buf: np.ndarray, freq: float = 5500.0, threshold_db: float = -30.0, ratio: float = 4.0, max_cut_db: float = 12.0,
          attack_ms: float = 1.0, release_ms: float = 60.0) -> np.ndarray:
    """Split-band de-esser: only the band above `freq` is compressed when it exceeds threshold. ESSENTIAL on
    pitched-up (nightcore) vocals — resampling +6 st moves sibilance from 6 kHz to ~9 kHz and it hurts."""
    from .render import _follower
    sos_hi = butter(4, freq, btype="high", fs=SR, output="sos")
    sos_lo = butter(4, freq, btype="low", fs=SR, output="sos")
    hi = sosfilt(sos_hi, buf, axis=0)
    lo = sosfilt(sos_lo, buf, axis=0)
    env = np.maximum(_follower(np.abs(hi).mean(axis=1), attack_ms, release_ms), 1e-7)
    env_db = 20 * np.log10(env)
    over = np.maximum(0.0, env_db - threshold_db)
    cut = np.minimum(max_cut_db, over * (1 - 1 / ratio))
    return (lo + hi * (10 ** (-cut / 20))[:, None]).astype(np.float32)


def tilt(buf: np.ndarray, high_db: float = -3.0, pivot_hz: float = 4000.0, low_db: float = 0.0, low_hz: float = 200.0) -> np.ndarray:
    """Shelving tilt: tame (or add) top end / low end in one move."""
    chain = [pb.HighShelfFilter(cutoff_frequency_hz=pivot_hz, gain_db=high_db)]
    if low_db:
        chain.append(pb.LowShelfFilter(cutoff_frequency_hz=low_hz, gain_db=low_db))
    return pb.Pedalboard(chain)(buf.T, SR).T.astype(np.float32)
