"""Per-sample feature extraction -> packs/<slug>/manifest.json, MANIFEST.md, sheets/*.png"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import librosa
import numpy as np
import pyloudnorm as pyln

from . import SR
from .ingest import load_norm, load_registry, pack_dir

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
BLOCKS = "▁▂▃▄▅▆▇█"

# Krumhansl-Schmuckler key profiles
MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

BANDS = [("sub", 20, 60), ("bass", 60, 200), ("lowmid", 200, 800), ("mid", 800, 3000), ("hi", 3000, 10000), ("air", 10000, 20000)]


def db(x: float, floor: float = -120.0) -> float:
    return float(max(floor, 20 * math.log10(x))) if x > 0 else floor


def hz_to_note(f: float) -> tuple[str, float]:
    midi = 69 + 12 * math.log2(f / 440.0)
    n = int(round(midi))
    cents = (midi - n) * 100
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 1}", round(cents, 1)


def parse_bpm_from_name(name: str) -> int | None:
    s = name.lower()
    m = re.search(r"(\d{2,3})\s*bpm", s) or re.search(r"bpm\s*(\d{2,3})", s)
    if m:
        return int(m.group(1))
    m = re.search(r"[\s_(\-](1\d\d)(?:[)\s_\-.]|$)", s)  # bare 100-199 token
    if m:
        return int(m.group(1))
    return None


def active_region(mono: np.ndarray, thresh_db: float = -45.0) -> tuple[int, int]:
    """First/last sample above threshold (relative to peak)."""
    peak = np.max(np.abs(mono)) or 1.0
    env = np.abs(mono) / peak
    idx = np.where(env > 10 ** (thresh_db / 20))[0]
    if len(idx) == 0:
        return 0, len(mono)
    return int(idx[0]), int(idx[-1]) + 1


def envelope_sketch(mono: np.ndarray, cols: int = 24) -> str:
    n = len(mono)
    if n < cols:
        return ""
    seg = np.array_split(mono, cols)
    rms = np.array([np.sqrt(np.mean(s ** 2)) + 1e-9 for s in seg])
    r = rms / rms.max()
    lv = 20 * np.log10(r)  # 0 .. -inf
    q = np.clip((lv + 36) / 36, 0, 1)  # -36dB..0 -> 0..1
    return "".join(BLOCKS[min(7, int(v * 7.999))] for v in q)


def band_energies(mono: np.ndarray) -> dict:
    S = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
    f = np.fft.rfftfreq(len(mono), 1 / SR)
    tot = S.sum() + 1e-12
    out = {}
    for name, lo, hi in BANDS:
        out[name] = round(10 * math.log10((S[(f >= lo) & (f < hi)].sum() + 1e-12) / tot), 1)
    return out


def key_estimate(mono: np.ndarray) -> dict:
    chroma = librosa.feature.chroma_cqt(y=mono, sr=SR, hop_length=1024)
    c = chroma.mean(axis=1)
    if c.sum() <= 0:
        return {"key": None, "conf": 0.0}
    best = []
    for i in range(12):
        for name, prof in (("maj", MAJ), ("min", MIN)):
            r = np.corrcoef(np.roll(prof, i), c)[0, 1]
            best.append((float(r), f"{NOTE_NAMES[i]}{'m' if name == 'min' else ''}"))
    best.sort(reverse=True)
    conf = best[0][0] - best[1][0]
    return {"key": best[0][1], "key_alt": best[1][1], "key_corr": round(best[0][0], 3), "conf": round(conf, 3)}


def pitch_estimate(mono: np.ndarray, fmin: float, fmax: float) -> dict:
    try:
        f0, voiced, prob = librosa.pyin(mono, fmin=fmin, fmax=fmax, sr=SR, frame_length=2048, hop_length=256)
    except Exception:
        return {"f0": None, "voiced_frac": 0.0}
    vf = f0[voiced & np.isfinite(f0)]
    if len(vf) == 0:
        return {"f0": None, "voiced_frac": 0.0}
    med = float(np.median(vf))
    note, cents = hz_to_note(med)
    return {
        "f0": round(med, 1), "note": note, "cents": cents,
        "voiced_frac": round(float(np.mean(voiced)), 2),
        "f0_range": [round(float(np.percentile(vf, 10)), 1), round(float(np.percentile(vf, 90)), 1)],
    }


def kick_fundamental(mono: np.ndarray) -> dict:
    """Pitch of the sub tail (after the click/pitch-drop): FFT peak of the last 70% of the active region, 25-250Hz."""
    a, b = active_region(mono, -40)
    seg = mono[a + (b - a) * 3 // 10: b]
    if len(seg) < 2048:
        seg = mono[a:b]
    if len(seg) < 512:
        return {}
    n = max(len(seg), 1 << 16)
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n))
    f = np.fft.rfftfreq(n, 1 / SR)
    m = (f >= 25) & (f <= 250)
    i = np.argmax(S[m])
    fpk = float(f[m][i])
    note, cents = hz_to_note(fpk)
    return {"sub_hz": round(fpk, 1), "sub_note": note, "sub_cents": cents}


def tempo_estimates(mono: np.ndarray, dur: float, name_bpm: int | None) -> dict:
    oenv = librosa.onset.onset_strength(y=mono, sr=SR, hop_length=512)
    try:
        tempo_fn = librosa.feature.tempo
    except AttributeError:  # pragma: no cover
        tempo_fn = librosa.beat.tempo
    t = tempo_fn(onset_envelope=oenv, sr=SR, hop_length=512, aggregate=None, start_bpm=140, std_bpm=1.5)
    hist = np.round(t).astype(int)
    vals, counts = np.unique(hist, return_counts=True)
    est = int(vals[np.argmax(counts)])
    cands = {est, est * 2, est // 2, round(est * 4 / 3), round(est * 3 / 4)}
    if name_bpm:
        cands.add(name_bpm)
    def fit(c):
        bars = dur * c / 240.0
        return abs(bars - round(bars)), c, round(bars, 3)

    fits = [fit(c) for c in sorted(x for x in cands if 60 <= x <= 220)]
    good = [f for f in fits if f[0] < 0.03 and round(f[2]) >= 1]
    if name_bpm and fit(name_bpm)[0] < 0.06:
        best_err, best_bpm, best_bars = fit(name_bpm)  # the producer told us; trust it
    elif good:
        # among exact-ish fits, prefer closest to the estimator, nudged toward the 100-180 club prior
        def score(f):
            return abs(math.log2(f[1] / est)) + (0.0 if 100 <= f[1] <= 180 else 0.5)
        best_err, best_bpm, best_bars = min(good, key=score)
    else:
        best_err, best_bpm, best_bars = min(fits)
    return {
        "bpm_name": name_bpm,
        "bpm_est": est,
        "bpm_best_fit": best_bpm,
        "bars_at_best": best_bars,
        "fit_err": round(best_err, 3),
        "loopable": bool(best_err < 0.03 and round(best_bars) >= 1),
    }


def analyze_one(sid: str, entry: dict, slug: str) -> dict:
    a = load_norm(slug, sid)
    mono = a.mean(axis=1)
    n = len(mono)
    dur = n / SR
    peak = float(np.max(np.abs(a))) if n else 0.0
    s, e = active_region(mono)
    act = mono[s:e]
    rms = float(np.sqrt(np.mean(act ** 2))) if len(act) else 0.0
    cat = entry["category"]
    r: dict = {
        "id": sid,
        "category": cat,
        "original": entry["original"],
        "dur": round(dur, 3),
        "active_start": round(s / SR, 3),
        "active_dur": round((e - s) / SR, 3),
        "peak_db": round(db(peak), 1),
        "rms_db": round(db(rms), 1),
        "crest_db": round(db(peak) - db(rms), 1),
        "clip_frac": round(float(np.mean(np.abs(a) >= 0.999)), 4),
        "orig": entry["orig_format"],
    }
    # stereo
    if n > 1:
        l, rr = a[:, 0], a[:, 1]
        denom = (np.std(l) * np.std(rr))
        corr = float(np.mean((l - l.mean()) * (rr - rr.mean())) / denom) if denom > 0 else 1.0
        r["stereo_corr"] = round(corr, 3)
        r["mono"] = bool(np.allclose(l, rr, atol=1e-4) or corr > 0.995)
    # loudness
    if dur >= 1.0:
        try:
            r["lufs"] = round(float(pyln.Meter(SR).integrated_loudness(a)), 1)
        except Exception:
            pass
    # spectral
    if len(act) > 2048:
        cent = librosa.feature.spectral_centroid(y=act, sr=SR)[0]
        roll = librosa.feature.spectral_rolloff(y=act, sr=SR, roll_percent=0.85)[0]
        flat = librosa.feature.spectral_flatness(y=act)[0]
        r["centroid_hz"] = int(np.median(cent))
        r["rolloff_hz"] = int(np.median(roll))
        r["flatness"] = round(float(np.median(flat)), 3)
        r["bands_db"] = band_energies(act)
    # onsets / transient
    on = librosa.onset.onset_detect(y=mono, sr=SR, units="time", backtrack=False, hop_length=256)
    r["onsets"] = int(len(on))
    r["onset_times"] = [round(float(x), 3) for x in on[:64]]
    if len(act):
        pk = int(np.argmax(np.abs(act)))
        r["attack_ms"] = round(pk / SR * 1000, 1)
        # decay: time from peak to -30dB (of peak) on smoothed env
        env = np.abs(act[pk:])
        if len(env) > 100:
            k = 441
            sm = np.convolve(env, np.ones(k) / k, mode="same")
            below = np.where(sm < (np.max(sm) * 10 ** (-30 / 20)))[0]
            r["decay30_ms"] = round((below[0] if len(below) else len(env)) / SR * 1000, 1)
    r["env"] = envelope_sketch(mono)
    # tempo
    name_bpm = parse_bpm_from_name(entry["original"])
    if dur >= 1.2:
        r["tempo"] = tempo_estimates(mono, dur, name_bpm)
    elif name_bpm:
        r["tempo"] = {"bpm_name": name_bpm}
    # beat grid for long material: beat times -> first downbeat estimate + beat-interval stability
    if dur >= 8.0:
        try:
            bpm_hint = r["tempo"]["bpm_best_fit"]
            tempo_bt, beats = librosa.beat.beat_track(y=mono, sr=SR, start_bpm=bpm_hint, tightness=100, units="time", hop_length=512)
            if len(beats) >= 8:
                iv = np.diff(beats)
                # downbeat: of the first 4 beats, the one with the strongest low-frequency onset energy
                oenv = librosa.onset.onset_strength(y=mono, sr=SR, hop_length=512, fmax=200)
                frames = librosa.time_to_frames(beats[:4], sr=SR, hop_length=512)
                db_i = int(np.argmax(oenv[np.clip(frames, 0, len(oenv) - 1)]))
                r["grid"] = {"first_beat": round(float(beats[0]), 4), "first_downbeat_guess": round(float(beats[db_i]), 4),
                             "beat_bpm": round(float(60 / np.median(iv)), 2), "beat_jitter_ms": round(float(np.std(iv) * 1000), 1),
                             "n_beats": int(len(beats))}
                if np.std(iv) * 1000 < 30 and dur >= 20:
                    # long material with a steady beat: the tracked tempo beats the bar-fit heuristic
                    r["tempo"]["bpm_best_fit"] = r["grid"]["beat_bpm"]
                    r["tempo"]["bars_at_best"] = round(dur * r["grid"]["beat_bpm"] / 240.0, 2)
                    r["tempo"]["source"] = "beat_track"
        except Exception as e:  # pragma: no cover
            r["grid"] = {"error": repr(e)}
    # pitch / key
    is_kick = cat.startswith("kicks") or "impact" in cat
    if is_kick:
        r["kick"] = kick_fundamental(mono)
    if dur <= 2.5 and len(act) > 1024:
        r["pitch"] = pitch_estimate(act, 30 if is_kick else 60, 400 if is_kick else 2000)
    if dur >= 0.5:
        r["keyest"] = key_estimate(mono)
    # role guess
    if dur < 1.2 or (r["onsets"] <= 2 and dur < 2.5):
        role = "oneshot"
    elif r.get("tempo", {}).get("loopable"):
        role = "loop"
    elif dur > 20:
        role = "song"
    else:
        role = "phrase"
    r["role"] = role
    return r


def contact_sheets(slug: str, man: dict, per_sheet: int = 30):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = pack_dir(slug) / "sheets"
    out.mkdir(exist_ok=True)
    bycat = defaultdict(list)
    for sid, r in man.items():
        bycat[r["category"]].append(sid)
    for cat, ids in bycat.items():
        ids.sort()
        for si in range(0, len(ids), per_sheet):
            chunk = ids[si: si + per_sheet]
            cols = 5
            rows = math.ceil(len(chunk) / cols)
            fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.6, rows * 2.2), squeeze=False)
            for ax in axes.flat:
                ax.axis("off")
            for ax, sid in zip(axes.flat, chunk):
                a = load_norm(slug, sid).mean(axis=1)
                a = a[: SR * 8]
                M = librosa.feature.melspectrogram(y=a, sr=SR, n_mels=64, fmax=16000, hop_length=512)
                Md = librosa.power_to_db(M, ref=np.max)
                ax.imshow(Md, origin="lower", aspect="auto", cmap="magma", vmin=-70, vmax=0)
                r = man[sid]
                t = r.get("tempo", {})
                tag = f"{r['dur']:.2f}s"
                if t.get("bpm_best_fit") and r["role"] in ("loop", "phrase"):
                    tag += f" ~{t['bpm_best_fit']}bpm/{t['bars_at_best']:.1f}b"
                if r.get("pitch", {}).get("note") and r["pitch"].get("voiced_frac", 0) > 0.3:
                    tag += f" {r['pitch']['note']}"
                if r.get("kick", {}).get("sub_note"):
                    tag += f" sub:{r['kick']['sub_note']}"
                ax.set_title(f"{sid.split('/')[-1][:34]}\n{tag}", fontsize=6.5, loc="left")
                ax.axis("on")
                ax.set_xticks([])
                ax.set_yticks([])
            fig.suptitle(f"{slug} :: {cat} ({si + 1}-{si + len(chunk)} of {len(ids)}) — mel spectrograms, first 8s", fontsize=9)
            fig.tight_layout()
            name = cat.replace("/", "_") + (f"_{si // per_sheet + 1}" if len(ids) > per_sheet else "")
            fig.savefig(out / f"{name}.png", dpi=110)
            plt.close(fig)
    print(f"sheets -> {out}")


def write_markdown(slug: str, man: dict):
    lines = [f"# {slug} manifest", "", f"{len(man)} samples. Columns: dur s · role · peak/rms dBFS · tempo (name→best-fit bpm / bars) · pitch/key · bands (sub/bass/lowmid/mid/hi/air dB rel) · envelope", ""]
    bycat = defaultdict(list)
    for sid, r in man.items():
        bycat[r["category"]].append(r)
    for cat in sorted(bycat):
        rows = sorted(bycat[cat], key=lambda r: r["id"])
        lines += [f"## {cat} ({len(rows)})", "", "| id | dur | role | pk/rms | tempo | pitch/key | bands | env | notes |", "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            t = r.get("tempo", {})
            tempo = ""
            if t:
                nb = t.get("bpm_name")
                bf = t.get("bpm_best_fit")
                tempo = (f"{nb}→" if nb else "") + (f"{bf} /{t.get('bars_at_best')}b" if bf else "") + (" ✓" if t.get("loopable") else "")
            pk = ""
            p = r.get("pitch", {})
            if p.get("note") and p.get("voiced_frac", 0) >= 0.25:
                pk = f"{p['note']} ({p['voiced_frac']:.0%})"
            k = r.get("kick", {})
            if k.get("sub_note"):
                pk = (pk + " " if pk else "") + f"sub {k['sub_note']} {k['sub_hz']}Hz"
            ke = r.get("keyest", {})
            if ke.get("key") and r["dur"] >= 1.0 and ke.get("conf", 0) > 0.05:
                pk = (pk + " " if pk else "") + f"key {ke['key']}"
            b = r.get("bands_db", {})
            bands = "/".join(str(int(b[n])) for n, _, _ in BANDS) if b else ""
            notes = []
            if r["clip_frac"] > 0.001:
                notes.append(f"clips {r['clip_frac']:.1%}")
            if r.get("mono"):
                notes.append("mono")
            if r["active_start"] > 0.05:
                notes.append(f"lead-in {r['active_start']:.2f}s")
            if r["orig"]["codec"] not in ("pcm_s16le", "pcm_s24le", "pcm_f32le"):
                notes.append(r["orig"]["codec"])
            if r["orig"]["sr"] and r["orig"]["sr"] < 44100:
                notes.append(f"{r['orig']['sr']}Hz src")
            lines.append(
                f"| `{r['id'].split('/')[-1]}` | {r['dur']:.2f} | {r['role']} | {r['peak_db']:.0f}/{r['rms_db']:.0f} | {tempo} | {pk} | {bands} | `{r['env']}` | {', '.join(notes)} |"
            )
        lines.append("")
    (pack_dir(slug) / "MANIFEST.md").write_text("\n".join(lines))


def analyze_pack(slug: str, limit: int | None = None, sheets: bool = True):
    reg = load_registry(slug)["files"]
    man = {}
    ids = sorted(reg)
    if limit:
        ids = ids[:limit]
    for i, sid in enumerate(ids):
        try:
            man[sid] = analyze_one(sid, reg[sid], slug)
        except Exception as e:  # keep going; record failure
            print(f"FAIL {sid}: {e!r}", file=sys.stderr)
            man[sid] = {"id": sid, "category": reg[sid]["category"], "original": reg[sid]["original"], "error": repr(e), "role": "?", "dur": 0, "peak_db": 0, "rms_db": 0, "clip_frac": 0, "active_start": 0, "orig": reg[sid]["orig_format"], "env": ""}
        if i % 25 == 0:
            print(f"{i}/{len(ids)} {sid}", file=sys.stderr)
    (pack_dir(slug) / "manifest.json").write_text(json.dumps(man, indent=1))
    write_markdown(slug, man)
    if sheets:
        contact_sheets(slug, {k: v for k, v in man.items() if "error" not in v})
    print(f"manifest -> {pack_dir(slug)}")
    return man


def load_manifest(slug: str) -> dict:
    return json.loads((pack_dir(slug) / "manifest.json").read_text())


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-sheets", action="store_true")
    a = ap.parse_args()
    analyze_pack(a.slug, a.limit, not a.no_sheets)
