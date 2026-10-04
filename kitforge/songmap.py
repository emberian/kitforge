"""Section maps for long source material: downbeat phase + per-bar vocal/drum energy, so an Opus can pick phrases by bar.

    uv run python -m kitforge.songmap classics cassie_me_and_u      # prints bars with vocal RMS and a sparkline
"""

from __future__ import annotations

import sys

import librosa
import numpy as np

from . import SR
from .analyze import BLOCKS, load_manifest
from .ingest import load_norm


def downbeat_phase(slug: str, song: str, bpm: float, first_beat: float) -> tuple[int, np.ndarray]:
    """Which of the 4 beat phases (0..3 after first_beat) is the downbeat: average low-band onset energy per phase
    over the whole drums stem (kicks live on 1 and 3; 1 is usually the strongest)."""
    d = load_norm(slug, f"{song}/drums").mean(axis=1)
    oenv = librosa.onset.onset_strength(y=d, sr=SR, hop_length=512, fmax=150)
    spb = 60.0 / bpm
    scores = np.zeros(4)
    counts = np.zeros(4)
    t = first_beat
    i = 0
    while t < len(d) / SR:
        f = int(t * SR / 512)
        if f < len(oenv):
            w = oenv[max(0, f - 2): f + 3].max()
            scores[i % 4] += w
            counts[i % 4] += 1
        t += spb
        i += 1
    avg = scores / np.maximum(counts, 1)
    # prefer the phase whose *pair* (phase, phase+2) is strongest, then the stronger of the two
    pair = avg + np.roll(avg, -2)
    p = int(np.argmax(pair))
    p = p if avg[p] >= avg[(p + 2) % 4] else (p + 2) % 4
    return p, avg


def song_map(slug: str, song: str, bpm: float | None = None, first_beat: float | None = None, stem: str = "vocals") -> dict:
    man = load_manifest(slug)
    mix = man[f"{song}/mix"]
    g = mix.get("grid", {})
    bpm = bpm or g.get("beat_bpm") or mix["tempo"]["bpm_best_fit"]
    fb = first_beat if first_beat is not None else g.get("first_beat", 0.0)
    phase, avg = downbeat_phase(slug, song, bpm, fb)
    downbeat = fb + phase * 60.0 / bpm
    v = load_norm(slug, f"{song}/{stem}").mean(axis=1)
    bar_s = 240.0 / bpm
    nb = int((len(v) / SR - downbeat) / bar_s)
    rms = []
    for b in range(nb):
        seg = v[int((downbeat + b * bar_s) * SR): int((downbeat + (b + 1) * bar_s) * SR)]
        rms.append(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9))
    rms = np.array(rms)
    return {"song": song, "bpm": bpm, "first_beat": fb, "downbeat": round(float(downbeat), 4), "phase": phase,
            "phase_energy": [round(float(x), 2) for x in avg], "bars": nb, "bar_rms_db": [round(float(x), 1) for x in rms]}


def print_map(m: dict):
    print(f"{m['song']}: {m['bpm']} bpm, downbeat at {m['downbeat']}s (phase {m['phase']} of first_beat {m['first_beat']}, phase energy {m['phase_energy']}), {m['bars']} bars")
    r = np.array(m["bar_rms_db"])
    top = r.max()
    for row in range(0, len(r), 32):
        chunk = r[row: row + 32]
        spark = "".join(BLOCKS[int(np.clip((x - top + 36) / 36, 0, 0.999) * 8)] for x in chunk)
        secs = f"{(m['downbeat'] + row * 240 / m['bpm']):5.1f}s"
        print(f"  bar {row:3d}-{row + len(chunk) - 1:3d} @{secs} {spark}  " + " ".join(f"{x:.0f}" for x in chunk))


if __name__ == "__main__":
    slug, song = sys.argv[1], sys.argv[2]
    print_map(song_map(slug, song, stem=sys.argv[3] if len(sys.argv) > 3 else "vocals"))


def find_repeats(slug: str, song: str, block_bars: int = 8, stem: str = "vocals", top: int = 6, thresh: float = 0.93,
                 min_energy_db: float = -32.0) -> list[dict]:
    """Chorus finder: per-bar chroma+MFCC on the stem, cosine similarity between every pair of block_bars windows
    (bar-aligned, stepping 1 bar); returns windows ranked by how many *other* windows match them (>0.85)."""
    m = song_map(slug, song, stem=stem)
    bpm, downbeat, nb = m["bpm"], m["downbeat"], m["bars"]
    v = load_norm(slug, f"{song}/{stem}").mean(axis=1)
    bar_s = 240.0 / bpm
    feats = []
    for b in range(nb):
        seg = v[int((downbeat + b * bar_s) * SR): int((downbeat + (b + 1) * bar_s) * SR)]
        if len(seg) < 2048:
            feats.append(np.zeros(48 + 8))
            continue
        # 4 chroma frames per bar (one per beat) + beat energy contour: melody shape, not timbre
        ch = librosa.feature.chroma_cqt(y=seg, sr=SR, hop_length=1024)
        q = np.array_split(ch, 4, axis=1)
        chv = np.concatenate([c.mean(axis=1) / (np.linalg.norm(c.mean(axis=1)) + 1e-9) for c in q])
        e = np.array([np.sqrt(np.mean(x ** 2)) for x in np.array_split(seg, 8)])
        feats.append(np.concatenate([chv, e / (e.max() + 1e-9)]))
    F = np.array(feats)
    W = np.array([F[i: i + block_bars].ravel() for i in range(nb - block_bars + 1)])
    W = W / (np.linalg.norm(W, axis=1, keepdims=True) + 1e-9)
    S = W @ W.T
    rows = []
    for i in range(len(W)):
        if np.mean(m["bar_rms_db"][i: i + block_bars]) < min_energy_db:
            continue
        others = [j for j in range(len(W)) if abs(j - i) >= block_bars and S[i, j] > thresh]
        rows.append({"start_bar": i, "start_s": round(downbeat + i * bar_s, 1), "matches": len(others),
                     "match_bars": [j for j in others][:8], "energy_db": round(float(np.mean(m["bar_rms_db"][i: i + block_bars])), 1)})
    rows.sort(key=lambda r: (-r["matches"], -r["energy_db"]))
    # de-duplicate overlapping winners
    out = []
    for r in rows:
        if all(abs(r["start_bar"] - o["start_bar"]) >= block_bars for o in out):
            out.append(r)
        if len(out) >= top:
            break
    return out


def plot_section(slug: str, song: str, bar0: int, bar1: int, stem: str = "vocals", out: str | None = None) -> str:
    """Mel spectrogram of bars [bar0, bar1) of a stem with bar numbers: look at it to find verses/choruses."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    m = song_map(slug, song, stem=stem)
    bpm, downbeat = m["bpm"], m["downbeat"]
    bar_s = 240.0 / bpm
    v = load_norm(slug, f"{song}/{stem}").mean(axis=1)
    t0, t1 = downbeat + bar0 * bar_s, downbeat + bar1 * bar_s
    seg = v[int(t0 * SR): int(t1 * SR)]
    M = librosa.power_to_db(librosa.feature.melspectrogram(y=seg, sr=SR, n_mels=96, fmax=8000, hop_length=512), ref=np.max)
    fig, ax = plt.subplots(figsize=(18, 5))
    ax.imshow(M, origin="lower", aspect="auto", cmap="magma", vmin=-70, vmax=0, extent=[0, len(seg) / SR, 0, 96])
    for b in range(bar0, bar1 + 1):
        x = (b - bar0) * bar_s
        ax.axvline(x, color="w", lw=1.4 if b % 4 == 0 else 0.5, alpha=0.6)
        if b % 2 == 0:
            ax.text(x + 0.05, 90, str(b), color="w", fontsize=8)
    ax.set_yticks([])
    ax.set_title(f"{song} / {stem}: bars {bar0}-{bar1} ({t0:.1f}s - {t1:.1f}s) at {bpm} bpm", fontsize=10)
    out = out or f"packs/{slug}/{song}_{stem}_{bar0}_{bar1}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=80)
    plt.close(fig)
    return out
