"""A small programmatic DAW.

    from kitforge.render import Song
    s = Song("twerknation28", bpm=138, bars=8)
    kick = s.track("kick", gain=-2)
    kick.pattern("x..x..x...x.x...", "kicks/id_night_club_808")          # 16th-grid step string, repeats to fill
    vox = s.track("vox", hp=150, fx=[Reverb(room_size=0.3, wet_level=0.15)])
    vox.hit("vocals/ahhh_2k10", bar=1, beat=2.5, pitch=-3, gain=-4)       # 0-based bar, 0-based fractional beat
    vox.chop("vocals/vocal_loops/a_bay_bay_vox_loop_140bpm", pattern=[0,0,2,None,0,1,3,3], step="8", bar=4)
    s.loop("sfx/perc_loops/opera_hihat_loop_140bpm", track="hats", bars=range(0, 8))  # stretched to song bpm
    s.sidechain("vox", source="kick", amount_db=5)
    s.render("demos/jersey01")   # -> demos/jersey01.wav + report.png + report.json + spec.json

Times: `bar` and `beat` are 0-based; beats are quarter notes (4/4). Pattern strings: x=hit, X=accent,
1-9=velocity, .=rest, '|' and spaces ignored. Steps: "4" "8" "16" "32" "8t" "16t".
Pitch: semitones; mode "resample" (tape, changes length) or "formant" (rubberband, keeps length).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import librosa
import numpy as np
import pedalboard as pb
import soundfile as sf

from . import SR
from .analyze import load_manifest
from .ingest import load_norm

STEP_BEATS = {"1": 4.0, "2": 2.0, "4": 1.0, "8": 0.5, "16": 0.25, "32": 0.125, "8t": 1 / 3, "16t": 1 / 6, "4t": 2 / 3}


def _fade(a: np.ndarray, fin: int, fout: int) -> np.ndarray:
    n = len(a)
    if n == 0:
        return a
    fin = min(fin, n // 2)
    fout = min(fout, n // 2)
    if fin > 0:
        a[:fin] *= np.linspace(0, 1, fin)[:, None]
    if fout > 0:
        a[n - fout:] *= np.linspace(1, 0, fout)[:, None]
    return a


class _PyFx:
    """Wrap a python buffer function so it can sit in a Track.fx list next to pedalboard plugins."""

    def __init__(self, fn):
        self.fn = fn

    def __repr__(self):
        return f"PyFx({getattr(self.fn, '__name__', 'fn')})"


def _fit(b: np.ndarray, n: int) -> np.ndarray:
    if len(b) == n:
        return b
    if len(b) > n:
        return b[:n]
    return np.concatenate([b, np.zeros((n - len(b), b.shape[1]), b.dtype)])


def _pan_gains(pan: float) -> tuple[float, float]:
    th = (pan + 1) * math.pi / 4
    return math.cos(th), math.sin(th)


@dataclass
class Event:
    track: str
    sample: str
    time: float  # beats from song start
    gain_db: float = 0.0
    pitch: float = 0.0
    pitch_mode: str = "resample"
    start: float | None = None  # seconds into the sample
    end: float | None = None
    slice: tuple[int, int] | None = None  # (i, n): i-th of n equal slices (or onset slices if onset=True)
    onset_slice: bool = False
    reverse: bool = False
    stretch_to_bpm: float | None = None  # loop's native bpm -> stretched to song bpm
    dur_beats: float | None = None  # truncate
    fade_out_ms: float = 8.0
    pan: float = 0.0


@dataclass
class Track:
    name: str
    song: "Song"
    gain_db: float = 0.0
    pan: float = 0.0
    hp: float | None = None
    lp: float | None = None
    fx: list = field(default_factory=list)
    choke: bool = False  # new event cuts previous on this track
    mute: bool = False
    solo: bool = False
    clips: list = field(default_factory=list)  # (Clip, instrument, humanize_ms)
    automation: list = field(default_factory=list)  # (param, [(beat, value), ...]) param in hp|lp|gain

    def clip(self, clip, inst, humanize_ms: float = 0.0) -> "Track":
        """Render a note Clip with an instrument (see kitforge.synth) into this track."""
        self.clips.append((clip, inst, humanize_ms))
        return self

    def automate(self, param: str, points: list[tuple[float, float]]) -> "Track":
        """Linear automation of 'hp' / 'lp' (Hz) or 'gain' (dB) over beats: [(beat, value), ...]."""
        self.automation.append((param, sorted(points)))
        return self

    def process(self, fn) -> "Track":
        """Arbitrary buffer processor fn(buf (n,2) float32) -> buf, applied after fx (e.g. tricks.*)."""
        self.fx.append(_PyFx(fn))
        return self

    def hit(self, sample: str, bar: int = 0, beat: float = 0.0, **kw) -> Event:
        return self.at(self.song.t(bar, beat), sample, **kw)

    def at(self, time_beats: float, sample: str, **kw) -> Event:
        if "gain" in kw:
            kw["gain_db"] = kw.pop("gain") + kw.pop("gain_db", 0.0)
        ev = Event(self.name, sample, time_beats, **kw)
        self.song.events.append(ev)
        return ev

    def pattern(self, pat: str, sample: str, step: str = "16", bar: int = 0, bars: int | None = None,
                gain: float = 0.0, swing: float | None = None, **kw) -> list[Event]:
        """Repeat `pat` from `bar` for `bars` bars (default: to song end). Velocity: x/X/1-9."""
        pat = pat.replace("|", "").replace(" ", "")
        sb = STEP_BEATS[step]
        start = self.song.t(bar, 0)
        end = self.song.t(bar + bars, 0) if bars is not None else self.song.length_beats
        evs = []
        i = 0
        while True:
            t = start + i * sb
            if t >= end - 1e-9:
                break
            ch = pat[i % len(pat)]
            vel = {"x": 0.0, "X": 3.0, ".": None, "-": None, "_": None}.get(ch, None)
            if vel is None and ch.isdigit() and ch != "0":
                vel = -20 * (1 - int(ch) / 9) ** 1.5 * 1.5  # 9->0dB, 1->~-25dB
            if vel is not None:
                tt = self.song.swung(t, sb, swing)
                evs.append(self.at(tt, sample, gain_db=gain + vel + kw.pop("gain_db", 0.0), **kw))
            i += 1
        return evs

    def chop(self, sample: str, pattern: list, step: str = "8", bar: int = 0, n: int | None = None,
             onset: bool = True, gain: float = 0.0, dur_steps: float = 1.0, stretch: bool = True, **kw) -> list[Event]:
        """Place slices of `sample`: pattern is a list of slice indices (None = rest), one per step.
        onset=True slices at detected onsets (n = number of onsets kept, default all up to 16);
        onset=False slices into n equal parts (default 8). Each slice truncated to dur_steps*step."""
        sb = STEP_BEATS[step]
        t0 = self.song.t(bar, 0)
        bpm_native = self.song.native_bpm(sample) if stretch else None
        if n is None:
            n = 8 if not onset else min(16, max(1, self.song.manifest.get(sample, {}).get("onsets", 8)))
        evs = []
        for i, sl in enumerate(pattern):
            if sl is None:
                continue
            evs.append(self.at(t0 + i * sb, sample, slice=(int(sl), n), onset_slice=onset, gain_db=gain,
                               dur_beats=sb * dur_steps, stretch_to_bpm=bpm_native, **kw))
        return evs


class Song:
    def __init__(self, pack: str, bpm: float = 138.0, bars: int = 8, swing: float = 50.0, swing_grid: str = "16"):
        self.pack = pack
        self.bpm = bpm
        self.bars = bars
        self.swing = swing  # percent: 50 straight, 66.7 triplet
        self.swing_grid = swing_grid
        self.tracks: dict[str, Track] = {}
        self.events: list[Event] = []
        self.sidechains: list[dict] = []
        self.master_fx: list = []
        self.master_gain_db = 0.0
        self.limiter_db = -1.0
        self.true_peak_db = -1.0  # final static trim so intersample peaks stay under this
        self.tail_beats = 4.0
        self.manifest = load_manifest(pack)
        self._cache: dict = {}

    # ---- time helpers
    def t(self, bar: int, beat: float = 0.0) -> float:
        return bar * 4.0 + beat

    @property
    def length_beats(self) -> float:
        return self.bars * 4.0

    def beats_to_samples(self, b: float) -> int:
        return int(round(b * 60.0 / self.bpm * SR))

    def swung(self, t: float, step_beats: float, swing: float | None) -> float:
        sw = self.swing if swing is None else swing
        g = STEP_BEATS[self.swing_grid]
        if abs(sw - 50) < 1e-6:
            return t
        pos = t / g
        k = round(pos)
        if abs(pos - k) > 1e-6 or k % 2 == 0:
            return t  # only odd grid positions move
        return t + g * (sw / 50.0 - 1.0)

    def native_bpm(self, sample: str) -> float | None:
        m = self.manifest.get(sample, {})
        t = m.get("tempo", {})
        return t.get("bpm_name") or t.get("bpm_best_fit")

    # ---- building
    def track(self, name: str, **kw) -> Track:
        if "gain" in kw:
            kw["gain_db"] = kw.pop("gain")
        if name not in self.tracks:
            self.tracks[name] = Track(name, self, **kw)
        else:
            for k, v in kw.items():
                setattr(self.tracks[name], k, v)
        return self.tracks[name]

    def loop(self, sample: str, track: str = "loop", bars=None, bar: int = 0, native_bpm: float | None = None,
             stretch: bool = True, gain: float = 0.0, **kw) -> list[Event]:
        """Tile a loop every N bars (N = its bar count at native bpm) across `bars` (iterable of bar indices)."""
        tr = self.track(track)
        nb = native_bpm or self.native_bpm(sample)
        m = self.manifest.get(sample, {})
        if stretch and nb:
            bars_len = max(1, round(m.get("tempo", {}).get("bars_at_best") or (m["dur"] * nb / 240)))
        else:
            bars_len = max(1, round(m["dur"] * self.bpm / 240)) if m else 1
        if bars is None:
            bars = range(bar, self.bars)
        bars = list(bars)
        evs = []
        for b in bars[::bars_len]:
            evs.append(tr.at(self.t(b, 0), sample, stretch_to_bpm=nb if stretch else None,
                             dur_beats=bars_len * 4.0, gain_db=gain, **kw))
        return evs

    def sidechain(self, target: str, source: str = "kick", amount_db: float = 6.0, attack_ms: float = 2.0,
                  release_ms: float = 150.0):
        self.sidechains.append(dict(target=target, source=source, amount_db=amount_db, attack_ms=attack_ms, release_ms=release_ms))

    def master(self, fx: list | None = None, gain_db: float = 0.0, limiter_db: float = -1.0, true_peak_db: float = -1.0):
        self.master_fx = fx or []
        self.master_gain_db = gain_db
        self.limiter_db = limiter_db
        self.true_peak_db = true_peak_db

    # ---- sample processing
    def _slice_bounds(self, sample: str, ev: Event, n_total: int) -> tuple[int, int]:
        if ev.slice is not None:
            i, n = ev.slice
            if ev.onset_slice:
                ons = self.manifest.get(sample, {}).get("onset_times", [])
                pts = [int(o * SR) for o in ons[:n]]
                if not pts or pts[0] > SR * 0.05:
                    pts = [0] + pts
                pts = sorted(set(pts))[:n]
                pts.append(n_total)
                i = i % (len(pts) - 1)
                return pts[i], pts[i + 1]
            seg = n_total / n
            return int(i * seg), int((i + 1) * seg)
        s = int((ev.start or 0) * SR)
        e = int(ev.end * SR) if ev.end is not None else n_total
        return s, min(e, n_total)

    def _prepare(self, ev: Event) -> np.ndarray:
        key = (ev.sample, ev.pitch, ev.pitch_mode, ev.start, ev.end, ev.slice, ev.onset_slice, ev.reverse, ev.stretch_to_bpm)
        if key in self._cache:
            return self._cache[key]
        a = load_norm(self.pack, ev.sample)
        if ev.stretch_to_bpm:
            # stretch whole loop first so onset times scale consistently
            factor = self.bpm / ev.stretch_to_bpm  # >1 => faster/shorter
            if abs(factor - 1) > 1e-3:
                a = pb.time_stretch(a.T.copy(), SR, stretch_factor=factor).T.copy()
        n_total = len(a)
        s, e = self._slice_bounds(ev.sample, ev, n_total)
        if ev.stretch_to_bpm and ev.slice is not None and ev.onset_slice:
            # onset times were measured on the unstretched sample
            f = n_total / len(load_norm(self.pack, ev.sample))
            s, e = int(s * f), int(e * f)
        a = a[s:e].copy()
        if ev.reverse:
            a = a[::-1].copy()
        if abs(ev.pitch) > 1e-6:
            if ev.pitch_mode == "formant":
                a = pb.time_stretch(a.T.copy(), SR, stretch_factor=1.0, pitch_shift_in_semitones=ev.pitch).T.copy()
            else:
                ratio = 2 ** (-ev.pitch / 12)
                a = librosa.resample(a.T, orig_sr=SR, target_sr=SR * ratio, res_type="soxr_hq").T.copy()
        self._cache[key] = a
        return a

    # ---- rendering
    def render(self, out: str | Path, stems: bool = False, report: bool = True, sr_out: int = SR) -> Path:
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        total = self.beats_to_samples(self.length_beats + self.tail_beats)
        bufs: dict[str, np.ndarray] = {n: np.zeros((total, 2), np.float32) for n in self.tracks}
        last_end: dict[str, tuple[int, int]] = {}
        for ev in sorted(self.events, key=lambda e: e.time):
            tr = self.tracks[ev.track]
            if ev.sample not in self.manifest:
                raise KeyError(f"unknown sample {ev.sample!r} in pack {self.pack}")
            a = self._prepare(ev)
            pos = self.beats_to_samples(ev.time)
            if ev.dur_beats is not None:
                a = a[: self.beats_to_samples(ev.dur_beats)]
            a = a * (10 ** (ev.gain_db / 20))
            a = _fade(a.copy(), int(SR * 0.002), int(SR * ev.fade_out_ms / 1000))
            if ev.pan:
                gl, gr = _pan_gains(ev.pan)
                a = a * np.array([gl, gr], np.float32) * math.sqrt(2)
            n = min(len(a), total - pos)
            if n <= 0:
                continue
            if tr.choke and ev.track in last_end:
                ps, pe = last_end[ev.track]
                if pos < pe:
                    f = int(SR * 0.005)
                    cut0 = max(ps, pos - f)
                    bufs[ev.track][cut0:pos] *= np.linspace(1, 0, pos - cut0)[:, None]
                    bufs[ev.track][pos:pe] = 0
            bufs[ev.track][pos: pos + n] += a[:n]
            last_end[ev.track] = (pos, pos + n)
        for name, tr in self.tracks.items():
            for clip, inst, hum in tr.clips:
                from .synth import render_clip
                bufs[name] += render_clip(clip, inst, self.bpm, total, humanize_ms=hum)
        # sidechain (pre-fx, uses raw source bus)
        for sc in self.sidechains:
            src = bufs[sc["source"]].mean(axis=1)
            env = _follower(np.abs(src), sc["attack_ms"], sc["release_ms"])
            env /= (env.max() or 1.0)
            g = 10 ** (-sc["amount_db"] * env / 20)
            bufs[sc["target"]] *= g[:, None]
        # track fx
        solo = any(t.solo for t in self.tracks.values())
        mix = np.zeros((total, 2), np.float32)
        for name, tr in self.tracks.items():
            if tr.mute or (solo and not tr.solo):
                continue
            chain = []
            if tr.hp:
                chain.append(pb.HighpassFilter(cutoff_frequency_hz=tr.hp))
            if tr.lp:
                chain.append(pb.LowpassFilter(cutoff_frequency_hz=tr.lp))
            chain += list(tr.fx)
            b = bufs[name]
            if tr.automation:
                b = self._automate(b, tr)
            for plug in chain:
                b = plug.fn(b) if isinstance(plug, _PyFx) else pb.Pedalboard([plug])(b.T, SR).T
                b = _fit(b, total)  # processors may change length (halfspeed, tape_stop)
            b = b * (10 ** (tr.gain_db / 20))
            if tr.pan:
                gl, gr = _pan_gains(tr.pan)
                b = b * np.array([gl, gr], np.float32) * math.sqrt(2)
            bufs[name] = b.astype(np.float32)
            mix += bufs[name]
        chain = list(self.master_fx) + [pb.Gain(self.master_gain_db), pb.Limiter(threshold_db=self.limiter_db, release_ms=80)]
        mix = pb.Pedalboard(chain)(mix.T, SR).T
        if self.true_peak_db is not None:
            up = librosa.resample(mix.T, orig_sr=SR, target_sr=SR * 4, res_type="soxr_hq")
            tp = float(np.max(np.abs(up)))
            ceil = 10 ** (self.true_peak_db / 20)
            if tp > ceil:
                mix = mix * (ceil / tp)
        wav = out.with_suffix(".wav")
        sf.write(wav, mix, SR, subtype="PCM_24")
        if stems:
            sd = out.parent / (out.stem + "_stems")
            sd.mkdir(exist_ok=True)
            for name, b in bufs.items():
                sf.write(sd / f"{name}.wav", b, SR, subtype="FLOAT")
        self.save_spec(out.with_suffix(".spec.json"))
        if report:
            from .feedback import report as _report
            _report(wav, bpm=self.bpm, bars=self.bars, out_png=out.with_suffix(".report.png"), out_json=out.with_suffix(".report.json"))
            if stems:
                from .feedback import print_stems
                print_stems(sd)
        return wav

    def _automate(self, b: np.ndarray, tr: Track, block: int = 1024) -> np.ndarray:
        n = len(b)
        beats = np.arange(n) / SR * self.bpm / 60.0
        out = b.copy()
        for param, pts in tr.automation:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            curve = np.interp(beats, xs, ys)
            if param == "gain":
                out *= (10 ** (curve / 20))[:, None].astype(np.float32)
                continue
            plug = pb.HighpassFilter(cutoff_frequency_hz=float(curve[0])) if param == "hp" else pb.LowpassFilter(cutoff_frequency_hz=float(curve[0]))
            res = np.empty_like(out)
            for i in range(0, n, block):
                plug.cutoff_frequency_hz = float(np.clip(curve[i], 10, 20000))
                res[i: i + block] = plug(out[i: i + block].T, SR, reset=False).T
            out = res
        return out

    def save_spec(self, path: Path):
        spec = {
            "pack": self.pack, "bpm": self.bpm, "bars": self.bars, "swing": self.swing,
            "tracks": {n: {k: (v if k != "fx" else [repr(x) for x in v]) for k, v in vars(t).items() if k != "song"} for n, t in self.tracks.items()},
            "sidechains": self.sidechains,
            "events": [vars(e) for e in sorted(self.events, key=lambda e: (e.time, e.track))],
        }
        Path(path).write_text(json.dumps(spec, indent=1, default=str))


def _follower(x: np.ndarray, attack_ms: float, release_ms: float) -> np.ndarray:
    ca = math.exp(-1.0 / (SR * attack_ms / 1000))
    cr = math.exp(-1.0 / (SR * release_ms / 1000))
    return _follow_jit(x.astype(np.float64), ca, cr)


try:
    from numba import njit

    @njit(cache=True)
    def _follow_jit(x, ca, cr):
        out = np.empty_like(x)
        e = 0.0
        for i in range(len(x)):
            v = x[i]
            e = ca * e + (1 - ca) * v if v > e else cr * e + (1 - cr) * v
            out[i] = e
        return out
except ImportError:  # pragma: no cover
    def _follow_jit(x, ca, cr):
        out = np.empty_like(x)
        e = 0.0
        for i in range(len(x)):
            v = x[i]
            e = ca * e + (1 - ca) * v if v > e else cr * e + (1 - cr) * v
            out[i] = e
        return out
