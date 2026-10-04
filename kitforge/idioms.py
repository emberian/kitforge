"""Canonical Jersey club / "internet Jersey" (hyperflip, dariacore) idioms as primitives.

Sources (2026-10-04 research, see recipes/GENRES.md "Jersey club" and "Internet Jersey" for the digest):
- r/edmproduction one-liner: Jersey Club = "K---K---K--K--K with 808 samples, gun shots, Hey vocal samples,
  Cymbals, Water Drops, bed squeeks and chopped vocal samples"  -> kick 16ths 0,4,8,11,14
- NI / plugg-supply guides: "two quarter-note kicks, two dotted eighths, then an eighth" = positions 1,5,9,12,15
  (1-based); layer sub + mid + click kicks at equal velocity; no swing; claps on 9 and 12 (1-based) i.e. 2 and 4(-ish)
  with a ghost at 11; squeak between kicks, not on them; 808 follows the kick rhythm and slides root notes;
  loop-first 8-bar arrangement.
- r/clubmuzik + r/jerseyclub producers (2014-16): chop vocals ON A SINGLE NOTE and re-pitch them to build
  melodies/chords; +/-7 st harmonizes, +/-12 for octave stacks ("layer the low-octave vocal with the original and
  a high-pitched version"); "a hint of reverb" on the kick; stutters = filtered delay (~1 kHz, 1-2 repeats) OR
  manual duplicates with falling velocity/filter; pitch-envelope risers; don't abuse squeak + water drip.
- TikTok producer tips (sleepyzen): "quick pitch drops, quick risers, glitchy stutters for transitions; 8-16 bar
  loops with frequent changes".
- Twitter/Reddit on twerknation28 / hyperflip / dariacore (leroy = Jane Remover, 2021-22): sample-collage over
  Jersey kicks, "Rustie + SOPHIE with a Gen Z twist", future-bass supersaw chords, "crushed up drops",
  nightcore-pitched pop/anime/meme vocals, jokes, flips every few bars.

Everything here is a thin layer over kitforge.render / synth / tricks so an Opus can read it and deviate.
"""

from __future__ import annotations

import math

import numpy as np
import pedalboard as pb

from . import SR
from .render import STEP_BEATS, Song, Track
from .synth import Clip, adsr, note_to_midi, osc, stereo
from .tricks import P, stutter

# ------------------------------------------------------------------ grids (16ths, 0-based)
JERSEY_KICK = "x...x...x..x..x."      # 0,4,8,11,14  — THE Jersey club kick ("K---K---K--K--K")
JERSEY_KICK_2BAR = "x...x...x..x..x.|x...x...x..x.x.x"   # bar 2 ends in a 2-kick pickup
JERSEY_BOUNCE = "x...x...x.x.x.x."    # busier variant
BMORE_KICK = "x..x..x...x.x..."       # 0,3,6,10,12 — tresillo-first: Baltimore grammar (what jersey01 used)
PHILLY_KICK = "x..x..x.x.x.x.x."
JERSEY_CLAP = "....x.......x..."      # 2 and 4
JERSEY_CLAP_GHOST = "....x.....7.x..."  # ghost before the 4 (velocity 7/9)
SQUEAK_BETWEEN = "..x...x...x...x."    # lands between kicks (0,4,8,11,14 are kicks -> 2,6,10,14 are free… 14 collides; use 13)
SQUEAK_BETWEEN_SAFE = "..x...x...x..x.."
SQUEAK_DOUBLE = ".x.x.x.x.x.x.x.x"     # Philly-ish

# ------------------------------------------------------------------ kick


def jersey_kick(song: Song, sample: str, bar: int = 0, bars: int | None = None, pattern: str = JERSEY_KICK,
                pitch: float = 4.0, dur_beats: float = 0.45, click: str | None = "sfx/percs/snap_02",
                reverb_hint: float = 0.06, gain: float = -2.0, track: str = "kick") -> Track:
    """Layered club kick: retuned 808 (truncated so the 3-step gaps breathe) + click layer + a *hint* of reverb.
    Equal velocities, no swing (the genre's mechanical evenness). Returns the kick track."""
    k = song.track(track, gain=gain, choke=True,
                   fx=[pb.Reverb(room_size=0.15, wet_level=reverb_hint, dry_level=1.0, width=0.3)] if reverb_hint else [])
    k.pattern(pattern, sample, bar=bar, bars=bars, dur_beats=dur_beats, fade_out_ms=25, pitch=pitch)
    if click:
        c = song.track(track + "_click", gain=gain - 9, hp=1500)
        c.pattern(pattern, click, bar=bar, bars=bars, dur_beats=0.1)
    return k


def bass_follows_kick(song: Song, inst, root: str = "E2", bars=range(0, 8), pattern: str = JERSEY_KICK,
                      slide_to: list[str] | None = None, track: str = "bass", gain: float = -6.0, dur: float = 0.45) -> Track:
    """808/bass playing the kick rhythm on `root`; every 4 bars optionally slides to the next root in `slide_to`
    (guide: 'F2 -> G#2 -> G2' style movement)."""
    tr = song.track(track, gain=gain, hp=35)
    roots = [root] + list(slide_to or [])
    c = Clip()
    pat = pattern.replace("|", "")
    for i, b in enumerate(bars):
        r = roots[(i // 4) % len(roots)]
        prev = roots[((i // 4) - 1) % len(roots)] if i % 4 == 0 and i > 0 else None
        for step, ch in enumerate(pat):
            if ch in "xX":
                c.note(r, bar=b, beat=step / 4, dur=dur, vel=0.9, glide_from=prev if (prev and step == 0) else None)
    tr.clip(c, inst)
    return tr


# ------------------------------------------------------------------ vocals


def sample_midi(song: Song, sample: str) -> float | None:
    """Detected pitch of a one-shot (manifest pyin median), as midi; None if unvoiced."""
    p = song.manifest.get(sample, {}).get("pitch", {})
    if p.get("f0") and p.get("voiced_frac", 0) >= 0.25:
        return 69 + 12 * math.log2(p["f0"] / 440.0)
    return None


def chop_melody(track: Track, sample: str, notes: list, bar: int = 0, beat: float = 0.0, step: str = "8",
                root_midi: float | None = None, mode: str = "formant", gain: float = 0.0, gate: float = 0.95, **kw) -> list:
    """'Chop on a single note, then pitch it': place `sample` at each note name (None = rest), transposed from its
    detected pitch (or root_midi) so the chop actually sings the melody. formant mode keeps length/vowel."""
    sb = STEP_BEATS[step]
    base = root_midi if root_midi is not None else sample_midi(track.song, sample)
    if base is None:
        raise ValueError(f"{sample} has no detected pitch; pass root_midi=")
    t0 = track.song.t(bar, beat)
    evs = []
    for i, n in enumerate(notes):
        if n is None:
            continue
        semis = note_to_midi(n) - base
        evs.append(track.at(t0 + i * sb, sample, pitch=float(semis), pitch_mode=mode, dur_beats=sb * gate, gain_db=gain, **kw))
    return evs


def vocal_stack(track: Track, sample: str, bar: int, beat: float, layers=((-12, -6.0), (0, 0.0), (12, -9.0)),
                mode: str = "formant", **kw) -> list:
    """Octave/5th harmony stack of one chop: (semitones, gain_db) per layer. Defaults = low octave + original + high."""
    t = track.song.t(bar, beat)
    base_gain = kw.pop("gain_db", 0.0) + kw.pop("gain", 0.0)
    return [track.at(t, sample, pitch=float(s), pitch_mode=mode, gain_db=g + base_gain, **kw) for s, g in layers]


def velocity_stutter(track: Track, sample: str, bar: int, beat: float, step: str = "16", count: int = 4,
                     decay_db: float = -4.0, **kw) -> list:
    """'Manual delay': duplicates with falling velocity (the scene's preferred stutter over a delay plugin)."""
    return stutter(track, sample, bar, beat, step=step, count=count, gain_ramp_db=decay_db * (count - 1), **kw)


def nightcore(semis: float = 5.0) -> dict:
    """Event kwargs for the nightcore/hyperflip vocal: resample-mode pitch up (faster, brighter, chipmunk)."""
    return dict(pitch=semis, pitch_mode="resample")


# ------------------------------------------------------------------ buffer processors (use with track.process(P(fn, ...)))


def stutter_delay(buf: np.ndarray, bpm: float, step: str = "16", repeats: int = 2, filter_hz: float = 1000.0,
                  decay_db: float = -5.0, mix: float = 1.0) -> np.ndarray:
    """Filtered echo stutter: `repeats` copies one `step` apart, each `decay_db` quieter and lowpassed at filter_hz
    ('delay with the filter around 1k, feedback low enough for one or two repetitions')."""
    d = int(STEP_BEATS[step] * 60 / bpm * SR)
    out = buf.copy()
    tap = buf.copy()
    for i in range(1, repeats + 1):
        tap = pb.Pedalboard([pb.LowpassFilter(filter_hz)])(tap.T, SR).T * (10 ** (decay_db / 20))
        out[i * d:] += tap[: len(buf) - i * d] * mix
    return out.astype(np.float32)


def pitch_drop(buf: np.ndarray, at_s: float, semis: float = -12.0, length_s: float = 0.25, hold_s: float = 0.0) -> np.ndarray:
    """Quick pitch drop at a transition: for length_s after at_s the audio is read with a speed ramp
    1 -> 2^(semis/12) (then held hold_s at that speed and faded); afterwards the original continues untouched."""
    s0 = int(at_s * SR)
    ramp, hold = int(length_s * SR), int(hold_s * SR)
    n_win = ramp + hold
    if s0 >= len(buf) - 10:
        return buf
    target = 2 ** (semis / 12)
    speed = np.concatenate([np.linspace(1.0, target, ramp), np.full(hold, target)])
    pos = np.cumsum(speed)
    seg = buf[s0:]
    pos = pos[pos < len(seg) - 1]
    i = pos.astype(int)
    f = (pos - i)[:, None]
    res = seg[i] * (1 - f) + seg[i + 1] * f
    if hold:
        res[ramp:] *= np.linspace(1, 0, len(res) - ramp)[:, None]
    out = buf.copy()
    out[s0: s0 + len(res)] = res
    return out


def crush(buf: np.ndarray, drive_db: float = 6.0, bits: float = 12.0, ceiling_db: float = -0.5) -> np.ndarray:
    """The 'crushed up drop': soft clip + light bitcrush + brickwall. Put on a drop bus, not the master."""
    g = 10 ** (drive_db / 20)
    x = np.tanh(buf * g) / math.tanh(g)
    x = pb.Pedalboard([pb.Bitcrush(bit_depth=bits), pb.Limiter(threshold_db=ceiling_db, release_ms=50)])(x.T.astype(np.float32), SR).T
    return x.astype(np.float32)


# ------------------------------------------------------------------ transition instruments / bundles


class PitchRiser:
    """Synth riser from a pitch envelope (the Sylenth 'MOD ENV -> pitch' trick): a saw/sine whose pitch climbs
    `semis` over the note, with a lowpass opening. freq = start pitch."""

    def __init__(self, semis: float = 24.0, wave: str = "saw", curve: float = 1.5, lp_start: float = 600.0, lp_end: float = 9000.0):
        self.semis, self.wave, self.curve, self.lp_start, self.lp_end = semis, wave, curve, lp_start, lp_end

    def __call__(self, freq: float, dur: float, vel: float = 1.0, glide_from=None) -> np.ndarray:
        n = int(dur * SR)
        t = np.linspace(0, 1, n) ** self.curve
        f = freq * 2 ** (self.semis * t / 12)
        x = osc(self.wave, f, n)
        from .synth import ladder
        x = ladder(x, np.geomspace(self.lp_start, self.lp_end, n), 0.3)
        env = adsr(n, 0.05, 0, 1, 0.02) * (0.3 + 0.7 * t)
        return stereo(x * env * vel, width=0.5, delay_ms=4)


def reverse_crash(track: Track, sample: str, bar: int, beat: float = 0.0, length_beats: float = 2.0, gain: float = -6.0) -> None:
    """Reversed whip/clap that swells INTO (bar, beat): the downbeat lands exactly when the reversed tail ends."""
    song = track.song
    t_end = song.t(bar, beat)
    track.at(t_end - length_beats, sample, reverse=True, dur_beats=length_beats, gain_db=gain, fade_out_ms=2)


def flip(song: Song, bar: int, kick_sample: str, riser_track: str = "riser", fx_track: str = "fx",
         crash: str = "sfx/percs/whips/id_whip_crack_fx", impact: str = "sfx/percs/impacts/boom",
         fill_sample: str | None = None, riser_bars: int = 2, roll_pattern: str = "x.x.x.x.xxxxxxxx") -> None:
    """Section switch INTO `bar`: pitch riser over the last riser_bars, kick roll in the last bar, reversed crash
    into the downbeat, impact on it. Combine with velocity_stutter on the vocal and a pitch_drop/tape_stop on the
    outgoing bus for the full internet-Jersey flip."""
    r = song.track(riser_track, gain=-14, hp=200)
    r.clip(Clip().note("A3", bar=bar - riser_bars, beat=0, dur=riser_bars * 4), PitchRiser())
    k = song.track("kick")
    from .tricks import roll
    if fill_sample or kick_sample:
        roll(k, fill_sample or kick_sample, bar - 1, 0, pattern=roll_pattern, step="16", dur_beats=0.2, pitch=4)
    f = song.track(fx_track, gain=-6)
    reverse_crash(f, crash, bar, 0, length_beats=2.0)
    f.hit(impact, bar=bar, beat=0, gain=0)
