"""Render critique: a PNG a Claude can Read, plus numbers.

    uv run python -m kitforge.feedback demos/x.wav --bpm 138 --bars 16

Panels: waveform w/ bar lines · mel spectrogram · low-end zoom (20-300Hz) · per-bar RMS + short-term LUFS
        · long-term spectrum (1/3 oct, relative to pink) · onset deviation from 16th grid.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import librosa
import numpy as np
import pyloudnorm as pyln
import soundfile as sf

from . import SR

THIRD_OCT = [25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000,
             2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000]


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-9))


def true_peak_db(a: np.ndarray) -> float:
    up = librosa.resample(a.T, orig_sr=SR, target_sr=SR * 4, res_type="soxr_hq")
    return float(db(np.max(np.abs(up))))


def third_octave_rel_pink(mono: np.ndarray) -> list[float]:
    n = 1 << 15
    S = np.zeros(n // 2 + 1)
    hop = n // 2
    w = np.hanning(n)
    cnt = 0
    for i in range(0, max(1, len(mono) - n), hop):
        S += np.abs(np.fft.rfft(mono[i: i + n] * w)) ** 2
        cnt += 1
    S /= max(cnt, 1)
    f = np.fft.rfftfreq(n, 1 / SR)
    out = []
    for fc in THIRD_OCT:
        lo, hi = fc / 2 ** (1 / 6), fc * 2 ** (1 / 6)
        m = (f >= lo) & (f < hi)
        p = S[m].sum() if m.any() else 1e-12
        out.append(10 * math.log10(p + 1e-12))  # pink noise => equal energy per 1/3 oct => flat
    out = np.array(out)
    return list(np.round(out - np.median(out[4:20]), 1))  # relative to the 63Hz-2kHz median


def sosfilt_band(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(4, [lo, hi], btype="band", fs=SR, output="sos"), x)


def third_octave_abs(mono: np.ndarray) -> list[float]:
    """1/3-octave band energies in dB relative to pink at 0 dBFS RMS overall — comparable across stems."""
    n = 1 << 15
    S = np.zeros(n // 2 + 1)
    hop = n // 2
    w = np.hanning(n)
    cnt = 0
    for i in range(0, max(1, len(mono) - n), hop):
        S += np.abs(np.fft.rfft(mono[i: i + n] * w)) ** 2
        cnt += 1
    S /= max(cnt, 1)
    f = np.fft.rfftfreq(n, 1 / SR)
    tot = S.sum() + 1e-12
    out = []
    for fc in THIRD_OCT:
        lo, hi = fc / 2 ** (1 / 6), fc * 2 ** (1 / 6)
        m = (f >= lo) & (f < hi)
        p = S[m].sum() if m.any() else 1e-12
        out.append(10 * math.log10(p / tot * len(THIRD_OCT) + 1e-12) + 20 * math.log10(np.sqrt(np.mean(mono ** 2)) + 1e-9))
    return list(np.round(out, 1))


def analyze(wav: Path, bpm: float | None, bars: int | None) -> dict:
    a, sr = sf.read(wav, dtype="float32", always_2d=True)
    assert sr == SR, sr
    mono = a.mean(axis=1)
    dur = len(mono) / SR
    meter = pyln.Meter(SR)
    r: dict = {"file": str(wav), "dur": round(dur, 2), "bpm": bpm}
    r["lufs_i"] = round(float(meter.integrated_loudness(a)), 1) if dur > 1 else None
    r["true_peak_db"] = round(true_peak_db(a), 2)
    r["sample_peak_db"] = round(float(db(np.max(np.abs(a)))), 2)
    rms = float(np.sqrt(np.mean(mono ** 2)))
    r["rms_db"] = round(float(db(rms)), 1)
    r["crest_db"] = round(r["sample_peak_db"] - r["rms_db"], 1)
    l, rr = a[:, 0], a[:, 1]
    r["stereo_corr"] = round(float(np.corrcoef(l, rr)[0, 1]), 3) if np.std(l) > 0 and np.std(rr) > 0 else 1.0
    side = np.sqrt(np.mean(((l - rr) / 2) ** 2))
    mid = np.sqrt(np.mean(((l + rr) / 2) ** 2))
    r["side_mid_db"] = round(float(db(side) - db(mid)), 1)
    # short-term loudness curve (3s window, 1s hop) and momentary (400ms, 100ms hop)
    def curve(win, hop):
        W, H = int(win * SR), int(hop * SR)
        vals = []
        for i in range(0, max(1, len(a) - W), H):
            seg = a[i: i + W]
            vals.append(float(meter.integrated_loudness(seg)) if len(seg) >= int(0.4 * SR) else -70)
        return vals
    r["lufs_short"] = [round(v, 1) for v in curve(3.0, 1.0)] if dur >= 3 else []
    mom = curve(0.4, 0.1) if dur >= 0.5 else []
    r["lufs_momentary_max"] = round(max(mom), 1) if mom else None
    r["plr_db"] = round(r["true_peak_db"] - r["lufs_i"], 1) if r["lufs_i"] is not None else None
    # spectrum
    r["third_oct_rel_pink"] = third_octave_rel_pink(mono)
    f3 = dict(zip(THIRD_OCT, r["third_oct_rel_pink"]))
    r["bands"] = {
        "sub<60": round(float(np.mean([f3[31.5], f3[40], f3[50]])), 1),  # 25 Hz excluded: the 28 Hz master hp owns it
        "kick 60-120": round(float(np.mean([f3[63], f3[80], f3[100]])), 1),
        "mud 200-400": round(float(np.mean([f3[200], f3[250], f3[315], f3[400]])), 1),
        "presence 2-5k": round(float(np.mean([f3[2000], f3[2500], f3[3150], f3[4000], f3[5000]])), 1),
        "harsh 5-10k": round(float(np.mean([f3[5000], f3[6300], f3[8000], f3[10000]])), 1),
        "air >10k": round(float(np.mean([f3[10000], f3[12500], f3[16000]])), 1),
    }
    # fatigue: how much of the time the 5-10k band is within 6 dB of its own peak (constant fizz) and overall density
    hb = librosa.feature.rms(y=sosfilt_band(mono, 5000, 10000), frame_length=2048, hop_length=1024)[0]
    fb = librosa.feature.rms(y=mono, frame_length=2048, hop_length=1024)[0]
    act = fb > fb.max() * 10 ** (-30 / 20)
    r["hf_ratio_db"] = round(float(np.median(20 * np.log10((hb[act] + 1e-9) / (fb[act] + 1e-9)))), 1) if act.any() else None
    # per-bar energy
    if bpm:
        bar_s = 240.0 / bpm
        nb = bars or int(dur / bar_s)
        per = []
        for b in range(nb):
            seg = mono[int(b * bar_s * SR): int((b + 1) * bar_s * SR)]
            per.append(round(float(db(np.sqrt(np.mean(seg ** 2)) if len(seg) else 1e-9)), 1))
        r["bar_rms_db"] = per
        loud = [x for x in per if x > max(per) - 6]
        r["loud_bar_spread_db"] = round(float(np.std(loud)), 2) if len(loud) >= 8 else None
        r["loud_bar_share"] = round(len(loud) / max(1, len(per)), 2)
        hb = sosfilt_band(mono, 5000, 12000)
        hper = [float(db(np.sqrt(np.mean(hb[int(b * bar_s * SR): int((b + 1) * bar_s * SR)] ** 2)) + 1e-9)) for b in range(nb)]
        r["hf_bar_db"] = [round(x, 1) for x in hper]
        med = float(np.median([x for x in hper if x > -60])) if any(x > -60 for x in hper) else -60
        r["harsh_bars"] = [int(i) for i in np.argsort(hper)[::-1][:8] if hper[i] > med + 3]
        r["arrangement_range_db"] = round(max(per) - min(p for p in per if p > -60) if any(p > -60 for p in per) else 0, 1)
        # onsets vs 16th grid
        ons = librosa.onset.onset_detect(y=mono, sr=SR, units="time", hop_length=128, backtrack=False)
        g16 = 60.0 / bpm / 4
        grids = {"16": g16, "32": g16 / 2, "16t": g16 * 2 / 3}
        dev16 = np.array([(o / g16 - round(o / g16)) * g16 * 1000 for o in ons])
        # per onset: deviation from the finest grid it is closest to (so 32nds / triplets are not "errors")
        best = []
        which = []
        for o in ons:
            cands = {k: (o / g - round(o / g)) * g * 1000 for k, g in grids.items()}
            k = min(cands, key=lambda k: abs(cands[k]))
            best.append(cands[k])
            which.append(k)
        dev = np.array(best)
        r["onsets"] = int(len(ons))
        r["onset_grid_share"] = {k: round(which.count(k) / max(1, len(which)), 2) for k in grids}
        r["onset_dev_ms"] = {"mean_abs": round(float(np.mean(np.abs(dev))), 1) if len(dev) else None,
                             "p90_abs": round(float(np.percentile(np.abs(dev), 90)), 1) if len(dev) else None,
                             "late_bias": round(float(np.mean(dev)), 1) if len(dev) else None,
                             "note": "detector marks the energy peak, so slow-attack samples read late; see manifest attack_ms / Track.latency_ms"}
        r["_onsets"] = ons
        r["_dev"] = dev
    # flags
    flags = []
    if r["true_peak_db"] > -0.3:
        flags.append("true peak hot (>-0.3 dBTP)")
    if r["lufs_i"] is not None and r["lufs_i"] < -14:
        flags.append(f"quiet for club ({r['lufs_i']} LUFS; -6..-9 typical for club masters, -10..-12 for a comfy demo)")
    if r["bands"]["mud 200-400"] > 4:
        flags.append("200-400Hz mud high")
    if r["bands"]["kick 60-120"] < -4:
        flags.append("kick band weak")
    if r["bands"]["sub<60"] > 8:
        flags.append("sub excessive")
    if r["bands"]["presence 2-5k"] > 6:
        flags.append("harsh 2-5k")
    if r["bands"]["harsh 5-10k"] > -3.5:
        flags.append(f"HARSH: 5-10 kHz at {r['bands']['harsh 5-10k']:+.1f} dB vs pink (club mixes sit -6..-10). De-ess pitched-up vocals, tilt highs, check squeaks/hats")
    if r["bands"]["air >10k"] > -4:
        flags.append(f"fizzy: >10 kHz at {r['bands']['air >10k']:+.1f} dB vs pink (aim -6..-12)")
    if r.get("hf_ratio_db") is not None and r["hf_ratio_db"] > -16:
        flags.append(f"fatiguing: 5-10 kHz is only {abs(r['hf_ratio_db']):.0f} dB under the full-band level most of the time (aim >= 18 dB under)")
    if r.get("loud_bar_spread_db") is not None and (bars or 0) >= 48 and r["loud_bar_spread_db"] < 1.0 and r["loud_bar_share"] > 0.6:
        flags.append(f"WALL OF SOUND: {r['loud_bar_share']:.0%} of bars sit within {r['loud_bar_spread_db']:.1f} dB of each other — no verse/chorus contrast; automate section levels (verses 2-4 dB under choruses), thin the drums somewhere")
    if r.get("harsh_bars"):
        flags.append(f"hf spikes (5-12 kHz > 3 dB over the track median) at bars {sorted(r['harsh_bars'])}: check stems there (pitched-up chops, stutters)")
    if r["lufs_i"] is not None and r["lufs_i"] > -9.5 and r["crest_db"] < 8.5:
        flags.append("crushed + loud (crest < 8.5 dB above -9.5 LUFS): it will hurt at volume; back off master gain / limiter GR")
    if r["stereo_corr"] < 0.2:
        flags.append("stereo correlation low (mono compatibility)")
    if r["stereo_corr"] > 0.98:
        flags.append("effectively mono (corr > 0.98): pan, Haas, or widen something")
    if r.get("arrangement_range_db", 0) < 3 and (bars or 0) >= 16:
        flags.append("arrangement flat (<3 dB bar-to-bar range over 16+ bars)")
    r["flags"] = flags
    return r


def plot(wav: Path, r: dict, out_png: Path, bpm: float | None, bars: int | None):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    a, _ = sf.read(wav, dtype="float32", always_2d=True)
    mono = a.mean(axis=1)
    dur = len(mono) / SR
    fig, axes = plt.subplots(6, 1, figsize=(16, 17), gridspec_kw={"height_ratios": [1, 2.2, 1.6, 1, 1.2, 0.8]})
    bar_s = 240.0 / bpm if bpm else None

    def barlines(ax, alpha=0.35):
        if not bar_s:
            return
        for b in range(int(dur / bar_s) + 1):
            ax.axvline(b * bar_s, color="w" if ax in (axes[1], axes[2]) else "k", lw=0.9 if b % 4 else 1.6, alpha=alpha)

    t = np.arange(len(mono)) / SR
    axes[0].plot(t[::8], a[::8, 0], lw=0.3, color="#3a7", alpha=0.9)
    axes[0].plot(t[::8], -np.abs(a[::8, 1]), lw=0.3, color="#36c", alpha=0.6)
    axes[0].set_ylim(-1, 1)
    axes[0].set_title(f"{wav.name} — L up / R down · {r['lufs_i']} LUFS-I · TP {r['true_peak_db']} dBTP · crest {r['crest_db']} dB · corr {r['stereo_corr']}", fontsize=10)
    barlines(axes[0])
    axes[0].set_xlim(0, dur)

    M = librosa.power_to_db(librosa.feature.melspectrogram(y=mono, sr=SR, n_mels=128, fmax=18000, hop_length=512), ref=np.max)
    axes[1].imshow(M, origin="lower", aspect="auto", cmap="magma", vmin=-80, vmax=0, extent=[0, dur, 0, 128])
    mel_ticks = [100, 250, 500, 1000, 2000, 4000, 8000, 16000]
    axes[1].set_yticks([librosa.hz_to_mel(f) / librosa.hz_to_mel(18000) * 128 for f in mel_ticks])
    axes[1].set_yticklabels([f"{f}" for f in mel_ticks], fontsize=7)
    axes[1].set_ylabel("mel (Hz)")
    barlines(axes[1])

    D = librosa.amplitude_to_db(np.abs(librosa.stft(mono, n_fft=8192, hop_length=1024)), ref=np.max)
    f = librosa.fft_frequencies(sr=SR, n_fft=8192)
    m = f <= 300
    axes[2].imshow(D[m], origin="lower", aspect="auto", cmap="magma", vmin=-70, vmax=0, extent=[0, dur, 0, 300])
    for note_hz, name in [(32.7, "C1"), (41.2, "E1"), (49, "G1"), (65.4, "C2"), (98, "G2"), (130.8, "C3"), (196, "G3")]:
        axes[2].axhline(note_hz, color="c", lw=0.4, alpha=0.5)
        axes[2].text(dur * 0.995, note_hz + 2, name, color="c", fontsize=6, ha="right")
    axes[2].set_ylabel("low end Hz (20-300)")
    barlines(axes[2])

    if r.get("bar_rms_db"):
        per = r["bar_rms_db"]
        axes[3].bar([(i + 0.5) * bar_s for i in range(len(per))], [p + 60 for p in per], width=bar_s * 0.9, bottom=-60, color="#888")
        axes[3].set_ylim(-45, 0)
        axes[3].set_ylabel("bar RMS dB")
        if r.get("lufs_short"):
            axes[3].plot([i + 1.5 for i in range(len(r["lufs_short"]))], r["lufs_short"], color="#c33", lw=1.2, label="LUFS short-term")
            axes[3].legend(fontsize=7, loc="lower right")
        axes[3].set_xlim(0, dur)
        barlines(axes[3])

    x = np.arange(len(THIRD_OCT))
    y = r["third_oct_rel_pink"]
    axes[4].bar(x, y, color=["#c33" if v > 6 else "#36c" if v < -10 else "#3a7" for v in y])
    axes[4].set_xticks(x)
    axes[4].set_xticklabels([str(int(f)) if f >= 100 else str(f) for f in THIRD_OCT], fontsize=7, rotation=45)
    axes[4].axhline(0, color="k", lw=0.6)
    axes[4].set_ylabel("1/3-oct dB vs pink")
    axes[4].set_title("long-term spectrum relative to pink noise (0 = pink-flat; club mixes sit roughly +3..+8 in 40-100Hz and slope to ~-6..-12 at 10k+)", fontsize=8)

    if "_dev" in r and len(r["_dev"]):
        axes[5].scatter(r["_onsets"], r["_dev"], s=6, color="#555")
        axes[5].axhline(0, color="k", lw=0.5)
        axes[5].set_ylim(-60, 60)
        axes[5].set_ylabel("onset dev\nfrom 16th (ms)")
        axes[5].set_xlim(0, dur)
        barlines(axes[5])
    axes[5].set_xlabel("seconds")
    fig.tight_layout()
    fig.savefig(out_png, dpi=90)
    plt.close(fig)


def report(wav: str | Path, bpm: float | None = None, bars: int | None = None, out_png=None, out_json=None, quiet=False) -> dict:
    wav = Path(wav)
    r = analyze(wav, bpm, bars)
    out_png = Path(out_png or wav.with_suffix(".report.png"))
    plot(wav, r, out_png, bpm, bars)
    r.pop("_onsets", None)
    r.pop("_dev", None)
    Path(out_json or wav.with_suffix(".report.json")).write_text(json.dumps(r, indent=1))
    if not quiet:
        print(f"{wav.name}: {r['lufs_i']} LUFS-I, TP {r['true_peak_db']}, crest {r['crest_db']}, corr {r['stereo_corr']}, bands {r['bands']}")
        if r.get("onset_dev_ms"):
            print(f"  onsets {r['onsets']} dev {r['onset_dev_ms']}  arrangement range {r.get('arrangement_range_db')} dB")
        for fl in r["flags"]:
            print("  ! " + fl)
        print(f"  -> {out_png}")
    return r


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--bars", type=int)
    a = ap.parse_args()
    report(a.wav, a.bpm, a.bars)


def stems_report(stems_dir: str | Path, bpm: float | None = None, bars: int | None = None, heatmap_png: str | Path | None = None) -> list[dict]:
    """Per-stem loudness, peak, centroid and the 1/3-oct bands where the stem is loudest IN ABSOLUTE terms (dB vs
    pink, same reference as the mix), plus a stems x bars RMS matrix (and heatmap PNG) when bpm is given."""
    stems_dir = Path(stems_dir)
    rows = []
    meter = pyln.Meter(SR)
    mats = []
    names = []
    for w in sorted(stems_dir.glob("*.wav")):
        a, _ = sf.read(w, dtype="float32", always_2d=True)
        mono = a.mean(axis=1)
        if np.max(np.abs(mono)) < 1e-6:
            rows.append({"stem": w.stem, "silent": True})
            continue
        third = third_octave_abs(mono)
        peaks = sorted(zip(third, THIRD_OCT), reverse=True)[:3]
        if bpm:
            bar_s = 240.0 / bpm
            nb = bars or int(len(mono) / (bar_s * SR))
            per = [float(db(np.sqrt(np.mean(mono[int(b * bar_s * SR): int((b + 1) * bar_s * SR)] ** 2)) or 1e-9)) for b in range(nb)]
            mats.append(per)
            names.append(w.stem)
        C = librosa.feature.spectral_centroid(y=mono, sr=SR)[0]
        E = librosa.feature.rms(y=mono)[0]
        act = E > E.max() * 10 ** (-40 / 20)  # centroid over active frames only
        cent = float(np.median(C[act])) if act.any() else 0.0
        rows.append({
            "stem": w.stem,
            "lufs": round(float(meter.integrated_loudness(a)), 1) if len(a) > SR else None,
            "peak_db": round(float(db(np.max(np.abs(a)))), 1),
            "centroid_hz": int(cent),
            "top_bands": [f"{int(f) if f >= 100 else f}Hz:{v:+.0f}" for v, f in peaks],
            "bar_rms_db": mats[-1] if bpm else None,
        })
    if bpm and mats and heatmap_png:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        M = np.array(mats)
        fig, ax = plt.subplots(figsize=(max(8, 0.35 * M.shape[1] + 3), 0.45 * len(names) + 1.5))
        im = ax.imshow(M, aspect="auto", cmap="magma", vmin=-50, vmax=-6)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=8)
        ax.set_xticks(range(M.shape[1]))
        ax.set_xticklabels([str(i) for i in range(M.shape[1])], fontsize=7)
        ax.set_xlabel("bar")
        ax.set_title("arrangement: stem RMS per bar (dBFS, pre-master)", fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.02)
        fig.tight_layout()
        fig.savefig(heatmap_png, dpi=100)
        plt.close(fig)
    return rows


def print_stems(stems_dir, bpm=None, bars=None, heatmap_png=None):
    for r in stems_report(stems_dir, bpm=bpm, bars=bars, heatmap_png=heatmap_png):
        if r.get("silent"):
            print(f"  {r['stem']:>10}: silent")
        else:
            print(f"  {r['stem']:>10}: {r['lufs']} LUFS  pk {r['peak_db']}  cent {r['centroid_hz']}Hz  peaks {' '.join(r['top_bands'])}")
