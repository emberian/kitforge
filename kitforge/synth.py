"""Synthesis: numpy instruments + note clips, rendered into Song tracks.

    from kitforge.synth import Clip, Synth808, Supersaw, FMPluck, Pad, Riser, chord, scale
    c = Clip()
    c.note("F1", bar=0, beat=0, dur=1.5, vel=1.0, glide_from="A1")      # 808 slide
    c.chord(chord("Fm7"), bar=0, beat=0, dur=4, octave=3)
    track.clip(c, Synth808(drive=6))                                     # renders into the song

Instruments are callables: inst(freq_hz, dur_s, vel, glide_from_hz=None) -> (n,2) float32 at SR.
All envelopes in seconds. Keep instruments pure so Opuses can write new ones in a few lines.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np
import pedalboard as pb
from scipy.signal import butter, sosfilt

from . import SR

NOTE_IDX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10], "mixolydian": [0, 2, 4, 5, 7, 9, 10], "harm_minor": [0, 2, 3, 5, 7, 8, 11],
    "pent_minor": [0, 3, 5, 7, 10], "pent_major": [0, 2, 4, 7, 9], "blues": [0, 3, 5, 6, 7, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11], "chromatic": list(range(12)),
}
CHORDS = {
    "": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11], "dim": [0, 3, 6],
    "m7b5": [0, 3, 6, 10], "sus2": [0, 2, 7], "sus4": [0, 5, 7], "add9": [0, 4, 7, 14], "m9": [0, 3, 7, 10, 14],
    "9": [0, 4, 7, 10, 14], "6": [0, 4, 7, 9], "m6": [0, 3, 7, 9], "5": [0, 7], "aug": [0, 4, 8], "mmaj7": [0, 3, 7, 11],
}


def note_to_midi(n: str | int | float) -> float:
    if isinstance(n, (int, float)):
        return float(n)
    m = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d+)", n.strip())
    if not m:
        raise ValueError(f"bad note {n!r}")
    v = NOTE_IDX[m.group(1).upper()] + {"#": 1, "b": -1, "": 0}[m.group(2)] + 12 * (int(m.group(3)) + 1)
    return float(v)


def midi_to_hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def chord(name: str, octave: int = 3) -> list[int]:
    """'Fm7' -> midi numbers; 'F#maj7/A#' slash bass supported (bass an octave lower)."""
    m = re.fullmatch(r"([A-Ga-g][#b]?)([a-zA-Z0-9]*)(?:/([A-Ga-g][#b]?))?", name.strip())
    if not m:
        raise ValueError(name)
    root = int(note_to_midi(f"{m.group(1)}{octave}"))
    notes = [root + i for i in CHORDS[m.group(2)]]
    if m.group(3):
        notes = [int(note_to_midi(f"{m.group(3)}{octave - 1}"))] + notes
    return notes


def scale(root: str, mode: str = "minor", octave: int = 3, octaves: int = 1) -> list[int]:
    r = int(note_to_midi(f"{root}{octave}"))
    return [r + 12 * o + i for o in range(octaves) for i in SCALES[mode]]


# ----------------------------------------------------------------- building blocks

def adsr(n: int, a: float, d: float, s: float, r: float, curve: float = 1.0) -> np.ndarray:
    """Envelope of n samples where the note is held for n - r*SR samples."""
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    hold = max(0, n - r_n)
    env = np.zeros(n)
    a_n = min(a_n, hold)
    env[:a_n] = np.linspace(0, 1, a_n) ** curve
    d_end = min(hold, a_n + d_n)
    env[a_n:d_end] = np.linspace(1, s, d_end - a_n) ** curve if d_end > a_n else s
    env[d_end:hold] = s
    if r_n > 0 and hold < n:
        start = env[hold - 1] if hold > 0 else s
        env[hold:] = start * np.linspace(1, 0, n - hold) ** curve
    return env


def osc(kind: str, freq: np.ndarray | float, n: int, phase: float = 0.0) -> np.ndarray:
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    ph = (np.cumsum(f) / SR + phase) % 1.0
    if kind == "sine":
        return np.sin(2 * np.pi * ph)
    if kind == "saw":
        return 2 * ph - 1
    if kind == "square":
        return np.where(ph < 0.5, 1.0, -1.0)
    if kind == "tri":
        return 4 * np.abs(ph - 0.5) - 1
    if kind == "noise":
        return np.random.default_rng(int(f[0])).uniform(-1, 1, n)
    raise ValueError(kind)


def saturate(x: np.ndarray, drive_db: float) -> np.ndarray:
    g = 10 ** (drive_db / 20)
    return np.tanh(x * g) / math.tanh(min(g, 20))


def stereo(x: np.ndarray, width: float = 0.0, delay_ms: float = 0.0) -> np.ndarray:
    """mono -> (n,2); width via haas-ish delay and inverted-side noise-free decorrelation."""
    if x.ndim == 2:
        return x.astype(np.float32)
    r = x.copy()
    if delay_ms > 0:
        d = int(SR * delay_ms / 1000)
        r = np.concatenate([np.zeros(d), x[:-d]]) if d < len(x) else r
    out = np.stack([x, r], axis=1)
    if width:
        m, s = (out[:, 0] + out[:, 1]) / 2, (out[:, 0] - out[:, 1]) / 2 * (1 + width)
        out = np.stack([m + s, m - s], axis=1)
    return out.astype(np.float32)


def lowpass(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    sos = butter(order, min(cutoff, SR / 2 - 100), btype="low", fs=SR, output="sos")
    return sosfilt(sos, x)


def highpass(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    sos = butter(order, max(cutoff, 10), btype="high", fs=SR, output="sos")
    return sosfilt(sos, x)


def ladder(x: np.ndarray, cutoff_env: np.ndarray, resonance: float = 0.2, mode=pb.LadderFilter.Mode.LPF24,
           block: int = 512) -> np.ndarray:
    """Moog-style ladder (pedalboard) with a per-sample cutoff envelope, stepped per block."""
    f = pb.LadderFilter(mode=mode, cutoff_hz=float(cutoff_env[0]), resonance=resonance, drive=1.0)
    out = np.empty_like(x, dtype=np.float32)
    xs = x.astype(np.float32)
    for i in range(0, len(x), block):
        f.cutoff_hz = float(np.clip(cutoff_env[min(i, len(x) - 1)], 20, 18000))
        out[i: i + block] = f(xs[i: i + block], SR, reset=False)
    return out


# ----------------------------------------------------------------- instruments

@dataclass
class Synth808:
    """Sine-ish 808: pitch drop click, long decay, tanh drive, optional glide."""
    decay: float = 1.2
    drive_db: float = 8.0
    click: float = 0.6  # amount of initial pitch sweep
    harmonics: float = 0.15  # square blend for grit
    glide_s: float = 0.08

    def __call__(self, freq: float, dur: float, vel: float = 1.0, glide_from: float | None = None) -> np.ndarray:
        n = int((dur + 0.05) * SR)
        t = np.arange(n) / SR
        f = np.full(n, freq)
        if glide_from:
            gn = int(self.glide_s * SR)
            f[:gn] = np.geomspace(glide_from, freq, gn)
        f = f * (1 + self.click * 6 * np.exp(-t / 0.012))  # click: fast downward sweep
        x = osc("sine", f, n) * (1 - self.harmonics) + osc("square", f, n) * self.harmonics * np.exp(-t / 0.15)
        env = np.exp(-t / self.decay) * adsr(n, 0.001, 0, 1, 0.02)
        x = saturate(x * env, self.drive_db) * vel
        return stereo(lowpass(x, 3000))


@dataclass
class Supersaw:
    """Detuned saw stack through a ladder filter with an envelope. Trance/hyperpop/club lead or bass."""
    voices: int = 5
    detune_cents: float = 12.0
    cutoff: float = 2500.0
    env_amount: float = 4000.0
    resonance: float = 0.25
    a: float = 0.005
    d: float = 0.25
    s: float = 0.6
    r: float = 0.15
    width: float = 0.6
    sub: float = 0.2  # sine sub-octave

    def __call__(self, freq: float, dur: float, vel: float = 1.0, glide_from: float | None = None) -> np.ndarray:
        n = int((dur + self.r) * SR)
        L = np.zeros(n)
        R = np.zeros(n)
        for i in range(self.voices):
            c = (i - (self.voices - 1) / 2) / max(1, (self.voices - 1) / 2)
            f = freq * 2 ** (c * self.detune_cents / 1200)
            v = osc("saw", f, n, phase=i * 0.37)
            pan = (c + 1) / 2
            L += v * (1 - pan * self.width)
            R += v * (1 - (1 - pan) * self.width)
        L /= self.voices
        R /= self.voices
        env = adsr(n, self.a, self.d, self.s, self.r)
        fenv = self.cutoff + self.env_amount * adsr(n, self.a, self.d * 1.5, self.s * 0.3, self.r)
        out = np.stack([ladder(L, fenv, self.resonance), ladder(R, fenv, self.resonance)], axis=1)
        out *= env[:, None] * vel
        if self.sub:
            out += (osc("sine", freq / 2, n) * env * vel * self.sub)[:, None]
        return out.astype(np.float32)


@dataclass
class FMPluck:
    """2-op FM pluck/bell: ratio & index decay. Good for footwork/juke stabs and club bells."""
    ratio: float = 2.0
    index: float = 3.0
    index_decay: float = 0.12
    decay: float = 0.5
    bright: float = 1.0

    def __call__(self, freq: float, dur: float, vel: float = 1.0, glide_from: float | None = None) -> np.ndarray:
        n = int(max(dur, 0.05) * SR + 0.1 * SR)
        t = np.arange(n) / SR
        idx = self.index * np.exp(-t / self.index_decay) * self.bright
        mod = np.sin(2 * np.pi * freq * self.ratio * t) * idx
        x = np.sin(2 * np.pi * freq * t + mod)
        env = np.exp(-t / self.decay) * adsr(n, 0.001, 0, 1, 0.05)
        return stereo(x * env * vel, width=0.2, delay_ms=0.4)


@dataclass
class Pad:
    """Slow, wide, filtered pad: 3 detuned saws + chorus + lowpass."""
    cutoff: float = 1800.0
    a: float = 0.4
    r: float = 0.8
    detune_cents: float = 7.0
    chorus_mix: float = 0.4

    def __call__(self, freq: float, dur: float, vel: float = 1.0, glide_from: float | None = None) -> np.ndarray:
        n = int((dur + self.r) * SR)
        x = sum(osc("saw", freq * 2 ** (c / 1200), n, phase=p) for c, p in ((-self.detune_cents, 0.1), (0, 0.5), (self.detune_cents, 0.9))) / 3
        x = lowpass(x, self.cutoff, 4) * adsr(n, self.a, 0.3, 0.8, self.r)
        st = stereo(x * vel, width=0.8, delay_ms=11)
        return pb.Pedalboard([pb.Chorus(rate_hz=0.3, depth=0.35, mix=self.chorus_mix)])(st.T, SR).T.astype(np.float32)


@dataclass
class Riser:
    """Filtered noise sweep. freq is ignored; dur is the rise length. Use dur = bars*240/bpm."""
    start_hz: float = 200.0
    end_hz: float = 12000.0
    resonance: float = 0.5
    curve: float = 2.0

    def __call__(self, freq: float, dur: float, vel: float = 1.0, glide_from: float | None = None) -> np.ndarray:
        n = int(dur * SR)
        noise = osc("noise", 7, n)
        cut = np.geomspace(self.start_hz, self.end_hz, n) ** 1.0
        x = ladder(noise, cut, self.resonance, mode=pb.LadderFilter.Mode.BPF12)
        env = (np.linspace(0, 1, n) ** self.curve) * vel
        return stereo(x * env, width=0.5, delay_ms=3)


@dataclass
class Sine:
    """Plain sine with ADSR (sub layers, test tones)."""
    a: float = 0.005
    d: float = 0.1
    s: float = 0.8
    r: float = 0.05

    def __call__(self, freq: float, dur: float, vel: float = 1.0, glide_from: float | None = None) -> np.ndarray:
        n = int((dur + self.r) * SR)
        return stereo(osc("sine", freq, n) * adsr(n, self.a, self.d, self.s, self.r) * vel)


# ----------------------------------------------------------------- note clips

@dataclass
class Note:
    midi: float
    time: float  # beats
    dur: float  # beats
    vel: float = 1.0
    glide_from: float | None = None


@dataclass
class Clip:
    notes: list[Note] = field(default_factory=list)

    def note(self, n, bar: int = 0, beat: float = 0.0, dur: float = 1.0, vel: float = 1.0, glide_from=None, time=None) -> "Clip":
        t = time if time is not None else bar * 4 + beat
        self.notes.append(Note(note_to_midi(n), t, dur, vel, note_to_midi(glide_from) if glide_from is not None else None))
        return self

    def chord(self, notes: list, bar: int = 0, beat: float = 0.0, dur: float = 4.0, vel: float = 1.0, strum: float = 0.0) -> "Clip":
        for i, n in enumerate(notes):
            self.note(n, bar, beat + i * strum, dur, vel)
        return self

    def seq(self, notes: list, step: float = 0.25, bar: int = 0, beat: float = 0.0, dur: float | None = None, vel: float = 1.0) -> "Clip":
        """Step sequence: list of midi/note-name/None(rest); each occupies `step` beats."""
        for i, n in enumerate(notes):
            if n is None:
                continue
            self.note(n, bar, beat + i * step, dur or step * 0.95, vel)
        return self

    def arp(self, notes: list, step: float = 0.25, bar: int = 0, bars: int = 1, mode: str = "up", gate: float = 0.9, vel: float = 1.0) -> "Clip":
        order = {"up": notes, "down": notes[::-1], "updown": notes + notes[-2:0:-1]}[mode]
        k = int(bars * 4 / step)
        for i in range(k):
            self.note(order[i % len(order)], bar, i * step, step * gate, vel)
        return self

    def transpose(self, semis: float) -> "Clip":
        return Clip([Note(n.midi + semis, n.time, n.dur, n.vel, (n.glide_from + semis) if n.glide_from else None) for n in self.notes])

    def shift(self, beats: float) -> "Clip":
        return Clip([Note(n.midi, n.time + beats, n.dur, n.vel, n.glide_from) for n in self.notes])

    def __add__(self, other: "Clip") -> "Clip":
        return Clip(self.notes + other.notes)


def render_clip(clip: Clip, inst, bpm: float, total_samples: int, humanize_ms: float = 0.0, seed: int = 0) -> np.ndarray:
    """Render all notes to a (total_samples, 2) buffer. Instruments with .render_clip (e.g. SurgeSynth) take the whole clip."""
    if hasattr(inst, "render_clip"):
        return inst.render_clip(clip, bpm, total_samples)
    out = np.zeros((total_samples, 2), np.float32)
    rng = np.random.default_rng(seed)
    spb = 60.0 / bpm
    for nt in clip.notes:
        a = inst(midi_to_hz(nt.midi), nt.dur * spb, nt.vel, midi_to_hz(nt.glide_from) if nt.glide_from else None)
        pos = int((nt.time * spb + (rng.normal(0, humanize_ms / 1000) if humanize_ms else 0)) * SR)
        pos = max(0, pos)
        n = min(len(a), total_samples - pos)
        if n > 0:
            out[pos: pos + n] += a[:n]
    return out
