# kitforge

Turn a sample pack into a **kit** a Claude can compose with: ingest → analyze → compose (programmatic DAW with
synths and real plugins) → render → **critique with spectrograms and numbers** → iterate. No ears required.

```
uv run python -m kitforge.ingest  "/path/to/pack" <slug>     # normalize to packs/<slug>/norm, ids = category/slug
uv run python -m kitforge.analyze <slug>                      # manifest.json, MANIFEST.md, sheets/*.png
uv run python demos/jersey01.py                               # a composition -> demos/out/*.wav + .report.png/.json
uv run python -m kitforge.feedback some.wav --bpm 138 --bars 16
uv run python -m kitforge.surge bass                          # search Surge XT patches
```

Genre idioms as code: `kitforge/idioms.py` (Jersey 5-count kick, chop melodies, vocal stacks, stutters, flips).
Packs live in `packs/<slug>/` with a hand-written **`KIT.md`** — the pack's *hypervector of constraints*: what it
has, what it lacks, what that forces. Start there. Genre priors: `recipes/GENRES.md`.

## Composing (the API an Opus writes against)

```python
import pedalboard as pb
from kitforge.render import Song
from kitforge.synth import Clip, Synth808, Supersaw, FMPluck, Pad, Riser, chord, scale
from kitforge.surge import SurgeSynth, surge_fx, list_patches
from kitforge.tricks import stutter, roll, pitch_ladder, P, gate, tape_stop, reverse_reverb, halfspeed, bitcrush
from kitforge.idioms import jersey_kick, chop_melody, vocal_stack, velocity_stutter, stutter_delay, flip, crush, nightcore, JERSEY_KICK

s = Song("twerknation28", bpm=138, bars=16, swing=50)           # swing 50 straight, 58-64 UKG, 66.7 triplet
k = s.track("kick", gain=-2, choke=True)                          # choke: each hit cuts the previous
k.pattern("x...x...x..x..x.", "kicks/id_night_club_808", bar=0, bars=16, dur_beats=0.45, pitch=4)  # Jersey 5-count
c = s.track("clap", gain=-6, fx=[pb.Reverb(room_size=0.3, wet_level=0.1)])
c.pattern("....x.......x...", "sfx/percs/2018_clap")              # repeats to the end of the song
v = s.track("vox", gain=3, hp=180, fx=[pb.Compressor(threshold_db=-18, ratio=3)])
v.hit("vocals/ahhh", bar=3, beat=2.5, pitch=-2, gain=-3)          # 0-based bar, fractional beat
v.chop("vocals/vocal_loops/drop_vocals_139bpm_2", pattern=[0,0,2,None,0,1,3,3], step="8", bar=4)  # onset slices
stutter(v, "vocals/back_it_up_2", bar=7, beat=2, step="32", count=8, accel=0.85, pitch_ramp=5)
pitch_ladder(v, "vocals/ahhh", bar=8, beat=0, semis=[0,3,5,7], step="8", pitch_mode="formant")
s.loop("sfx/perc_loops/opera_hihat_loop_140bpm", track="hats", bars=range(8, 16))   # stretched to 138
b = s.track("bass", gain=-6, hp=35)
b.clip(Clip().seq(["E1", None, "E1", "G1"], step=0.5, bar=0).note("B1", bar=1, beat=2, dur=1.5, glide_from="E1"),
       Synth808(decay=0.9, drive_db=8))
p = s.track("pad", gain=-14).clip(Clip().chord(chord("Em7", 3), bar=0, dur=16), SurgeSynth("Altenberg/Pads/Alone"))
p.automate("lp", [(0, 400), (32, 6000)])                          # beat -> Hz
p.process(P(gate, bpm=138, pattern="x.x.x.xx"))                  # python buffer fx after plugin fx
s.sidechain("pad", source="kick", amount_db=8, release_ms=140)
s.master(fx=[pb.HighpassFilter(28)], gain_db=2, limiter_db=-1.5, true_peak_db=-1)
s.render("demos/out/mytrack", stems=True)   # .wav, _stems/, .spec.json, .report.png, .report.json + stem table
```

Then **Read the `.report.png`** (waveform · mel spectrogram · 20–300 Hz zoom with note lines · bar RMS/LUFS ·
1/3-octave spectrum vs pink · onset deviation from the 16th grid) and the printed stem table, change the
script, render again. Three passes is normal.

### Time and pitch
- Beats are quarter notes, 0-based. `Song.t(bar, beat)`; patterns take `step` in `4 8 16 32 8t 16t`.
- `pitch` in semitones. `pitch_mode="resample"` (default: tape — shorter and brighter when up; right for drums and
  808s) or `"formant"` (Rubber Band — keeps length and vowels; right for vocals within ±4 st).
- Loops with a known bpm (`manifest.tempo.bpm_name`/`bpm_best_fit`) are stretched to the song automatically by
  `Song.loop` and `Track.chop(stretch=True)`; pass `stretch_to_bpm=` on any event to force it.
- `dur_beats` truncates (with `fade_out_ms`), `start`/`end` crop in seconds, `slice=(i, n)` takes the i-th of n
  equal or onset-based slices, `reverse=True`.

### Instruments
- `kitforge.synth`: `Synth808`, `Supersaw`, `FMPluck`, `Pad`, `Riser`, `Sine` — pure numpy/pedalboard; copy one and
  edit to invent more. `Clip` holds notes: `.note .chord .seq .arp .transpose .shift`, `+` to merge.
- `kitforge.surge.SurgeSynth("Category/Name")`: Surge XT with ~3000 factory + community patches, searched with
  `list_patches("pluck")`. Plus `surge_fx("Reverb 2" | "Tape" | "Nimbus" | "Frequency Shifter" | "Vocoder" | ...)`
  as a track effect (29 types, incl. Airwindows).
- Any pedalboard plugin in `fx=[...]`: Reverb, Delay, Chorus, Phaser, Distortion, Bitcrush, Compressor,
  Limiter, LadderFilter, PeakFilter, shelves, Convolution, plus `pb.load_plugin("...vst3")` for anything else.

### Feedback vocabulary (report.json)
`lufs_i`, `true_peak_db`, `crest_db`, `stereo_corr`, `side_mid_db`, `bands` (sub<60 / kick 60–120 / mud 200–400 /
presence 2–5k / air>10k, dB vs pink), `third_oct_rel_pink`, `bar_rms_db`, `arrangement_range_db`,
`onset_dev_ms` (mean/p90/late bias vs 16th grid), `flags`. `feedback.stems_report(dir)` per track.

## Juice: modulation, buses, throws (`kitforge/mod.py`)
Control signals — `LFO`, `Follow(track)`, `Steps`, `Ramp`, `Random` — evaluate per sample and can modulate each other
(`LFO(rate_mod=LFO(...))`). Targets via `track.mod(param, signal)`: `lp hp gain pan width drive send:<name>`.
Per-hit envelopes `pitch_env=(st0, st1, s)`, `lp_env=(hz0, hz1, s)`; parameter locks `pattern(..., plocks={"pitch": [...]})`.
`song.bus(name, tracks, process=[P(ott), P(saturate)...])`, `song.send("echo", fx=[...])` + `track.send(...)` or a
`Steps` throw. Processors: `ott`, `saturate`, `transient`, `width`, `haas`, `comb`, `deess`, `tilt`, `spit_delay`.
Canonical uses (scene sources in the module docstring): hats `Follow` the kick inverted; filters ramp open into
choruses; width 0.75 in verses → full in choruses; delay throws on phrase ends; OTT on music buses (gently).

## Remixing songs (`packs/classics`, `kitforge/songmap.py`, `demos/jersey03.py`)
`yt-dlp -x --audio-format wav` → `demucs -n htdemucs -d mps` (vocals/drums/bass/other) → ingest as a pack with
`<song>/<stem>` ids → `python -m kitforge.songmap classics <song>` (beat-tracked tempo, kick-phase downbeat, per-bar
vocal energy; `find_repeats` for choruses, `plot_section` to look) → `song.song_section(sample, src_bar, bars, bar=...,
src_bpm=, first_beat=, nightcore=True|False)`. `nightcore=True` is the sped-up edit (pure resample so the source's bars
land on ours); otherwise formant stretch. Use `Song(..., extra_packs=["classics"])` and ids like `classics:pony/vocals`.
Sources are for local, personal remix work only: `sources/` and `packs/*/norm/` are gitignored; do not publish renders.

## Loudness and pain (learned the hard way on jersey03)
- Sped-up vocals move sibilance to 8–12 kHz: always `deess` + a small `tilt` on nightcored vocals; never ladder chops
  above about +7 st in resample mode.
- OTT lifts highs: keep vocal-bus depth ≤ 0.15 and cap the high band.
- A track that sits at one RMS for minutes is a wall. Automate section levels (verses 2–4 dB under choruses),
  open verses half-time, and keep limiter gain reduction ≤ ~5 dB. -10..-11 LUFS is a fine demo level.
- The critic now flags: `HARSH` (5–10 kHz vs pink), `fizzy` (>10 kHz), `fatiguing`, `WALL OF SOUND`, hf-spike bars,
  crushed+loud, and limiter GR > 6 dB. A clean flag list is necessary, not sufficient — ember's ears are the judge.

## Layout
```
kitforge/   ingest.py analyze.py render.py synth.py surge.py tricks.py idioms.py mod.py songmap.py mashup.py feedback.py
packs/<slug>/  KIT.md  MANIFEST.md  manifest.json  files.json  norm/  sheets/      (norm/ is gitignored)
recipes/GENRES.md       demos/*.py -> demos/out/
```

## Environment notes (ember's M2 Max, 2026-10)
- Python env via `uv` (librosa 1.0, pedalboard 0.9.25, pyloudnorm, mido). System: sox, ffmpeg, rubberband, csound, faust, fluidsynth.
- Surge XT 1.3.4 extracted from the Homebrew cask pkg without sudo into `~/Library/Audio/Plug-Ins/{VST3,Components}`
  and `~/Library/Application Support/Surge XT` (`SURGE_DATA_PATH` is set by `kitforge.surge`). Patches are loaded by
  wrapping the `.fxp` body in JUCE's VST3 state framing (`surge.wrap_state`); Surge applies them asynchronously, so
  the wrapper warms the plugin up and never `reset`s it afterwards.
- Apple's built-in AUs (`/System/Library/Components/CoreAudio.component`) hang pedalboard on load — do not try.
- Adding another pack: `ingest` + `analyze`, then write its `KIT.md` by reading `MANIFEST.md` and the sheets.
