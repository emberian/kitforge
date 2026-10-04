"""Surge XT (open-source hybrid synth) hosted via pedalboard as a Clip instrument, plus Surge XT Effects.

    from kitforge.surge import SurgeSynth, surge_fx, list_patches
    list_patches("Bass")                            # fuzzy search factory + 3rd-party patches
    track.clip(clip, SurgeSynth("Basses/Bass 1"))   # whole clip is rendered as one MIDI performance
    track.fx.append(surge_fx("Reverb 2", output_mix=0.3))

Install (done 2026-10-03 on ember's M2 Max): VST3s in ~/Library/Audio/Plug-Ins/VST3, data in
~/Library/Application Support/Surge XT (we set SURGE_DATA_PATH so the user-level copy is found).
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pedalboard as pb

from . import SR

DATA = Path(os.environ.get("SURGE_DATA_PATH") or Path.home() / "Library/Application Support/Surge XT")
os.environ.setdefault("SURGE_DATA_PATH", str(DATA))
VST3 = Path.home() / "Library/Audio/Plug-Ins/VST3/Surge XT.vst3"
FX_VST3 = Path.home() / "Library/Audio/Plug-Ins/VST3/Surge XT Effects.vst3"


@lru_cache(maxsize=1)
def patch_index() -> dict[str, Path]:
    idx = {}
    for root in (DATA / "patches_factory", DATA / "patches_3rdparty"):
        for p in root.rglob("*.fxp"):
            idx[str(p.relative_to(root).with_suffix("")).replace("\\", "/")] = p
    return idx


def list_patches(query: str = "", limit: int = 40) -> list[str]:
    q = query.lower().split()
    out = [k for k in sorted(patch_index()) if all(w in k.lower() for w in q)]
    return out[:limit]


def resolve_patch(name: str) -> Path:
    idx = patch_index()
    if name in idx:
        return idx[name]
    hits = list_patches(name, 5)
    if not hits:
        raise KeyError(f"no Surge patch matching {name!r}")
    return idx[hits[0]]


_JUCE_TABLE = ".ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+"


def _juce_b64(data: bytes) -> str:
    """JUCE MemoryBlock::toBase64Encoding: '<size>.' + 6-bit groups packed LSB-first."""
    n = int.from_bytes(data, "little")
    nc = (len(data) * 8 + 5) // 6
    return f"{len(data)}." + "".join(_JUCE_TABLE[(n >> (6 * i)) & 63] for i in range(nc))


def wrap_state(chunk: bytes) -> bytes:
    """Wrap a Surge 'sub3' patch chunk the way pedalboard's VST3 raw_state expects it."""
    assert chunk[:4] == b"sub3", chunk[:8]
    xml = f'<VST3PluginState><IComponent>{_juce_b64(chunk)}</IComponent></VST3PluginState>'.encode() + b"\x00"
    return b"VC2!" + len(xml).to_bytes(4, "little") + xml


class SurgeSynth:
    """Clip instrument backed by Surge XT. Loads lazily; one plugin instance per patch."""

    def __init__(self, patch: str | None = None, gain_db: float = 0.0, release_tail_s: float = 1.5, params: dict | None = None):
        self.patch = patch
        self.gain_db = gain_db
        self.tail = release_tail_s
        self.params = params or {}
        self._plug = None

    def _load(self):
        if self._plug is None:
            p = pb.load_plugin(str(VST3))
            self._plug = p
            if self.patch:
                data = resolve_patch(self.patch).read_bytes()
                p.raw_state = wrap_state(data[60:])  # skip the 60-byte fxp header -> Surge 'sub3' chunk
                # Surge applies a new patch on its audio thread: run a silent warm-up so the swap lands
                for _ in range(3):
                    p([], duration=0.5, sample_rate=SR, reset=False)
                    if self.loaded_patch_name() != "Init Saw":
                        break
            for k, v in self.params.items():
                setattr(p, k, v)
            self._plug = p
        return self._plug

    def render_clip(self, clip, bpm: float, total_samples: int) -> np.ndarray:
        from mido import Message

        spb = 60.0 / bpm
        evs = []
        for n in clip.notes:
            t0 = n.time * spb
            evs.append((t0, Message("note_on", note=int(round(n.midi)), velocity=int(np.clip(n.vel * 127, 1, 127)))))
            evs.append((t0 + n.dur * spb, Message("note_off", note=int(round(n.midi)))))
        evs.sort(key=lambda e: e[0])
        msgs = []
        for t, m in evs:
            m.time = t
            msgs.append(m)
        dur = total_samples / SR
        p = self._load()
        a = p(msgs, duration=dur, sample_rate=SR, reset=False).T  # (n,2); reset=False keeps the loaded patch
        out = np.zeros((total_samples, 2), np.float32)
        n = min(len(a), total_samples)
        out[:n] = a[:n] * (10 ** (self.gain_db / 20))
        return out

    def loaded_patch_name(self) -> str | None:
        m = re.search(rb"<IComponent>([^<]+)</IComponent>", self._plug.raw_state)
        if not m:
            return None
        size, _, body = m.group(1).decode().partition(".")
        n = 0
        for i, ch in enumerate(body):
            n |= _JUCE_TABLE.index(ch) << (6 * i)
        mm = re.search(rb'<meta name="([^"]+)"', n.to_bytes(int(size), "little"))
        return mm.group(1).decode() if mm else None

    def __repr__(self):
        return f"SurgeSynth({self.patch!r})"


def surge_fx(fx_type: str, **params):
    """Surge XT Effects as a track plugin. fx_type e.g. 'Reverb 2','Delay','Distortion','Chorus','Phaser',
    'Rotary Speaker','Frequency Shifter','Ring Modulator','Vocoder','Nimbus' (granular),'Tape','Treemonster',
    'Waveshaper','Combulator','Spring Reverb','Bonsai','Airwindows' ... see surge_fx_types()."""
    p = pb.load_plugin(str(FX_VST3))
    p.fx_type = fx_type
    for k, v in params.items():
        setattr(p, k, v)
    return p


def surge_fx_types() -> list[str]:
    p = pb.load_plugin(str(FX_VST3))
    return list(p.parameters["fx_type"].valid_values)


def surge_fx_params(fx_type: str) -> dict:
    p = pb.load_plugin(str(FX_VST3))
    p.fx_type = fx_type
    return {k: str(v) for k, v in p.parameters.items()}


if __name__ == "__main__":
    import sys

    print("\n".join(list_patches(" ".join(sys.argv[1:]), 80)))
