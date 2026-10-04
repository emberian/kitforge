"""Footwork / juke, 160 bpm, 32 bars (8 four-bar cells). F minor.

808 toms (Synth808, per-hit pitch) on a 3-step cycle against claps on 2 and 4; "werk" on a 7-step cycle;
"shake it down" chopped on the 16th grid; Surge Rhodes stabs on a 5-step cycle; holes on the downbeats;
flip at bar 16 (toms go to a 16t-flavoured 5-step cycle, werk drops an octave, Rhodes moves to Db).
Run:  uv run python -W ignore demos/footwork01.py
"""

import pedalboard as pb

from kitforge.render import Song
from kitforge.synth import Clip, Synth808, chord
from kitforge.surge import SurgeSynth
from kitforge.tricks import stutter, P, tape_stop

BPM = 160
BARS = 32
s = Song("twerknation28", bpm=BPM, bars=BARS)


def poly(cycle, bar0, bars, offset=0, holes=lambda g: g % 16 == 0):
    """Global 16th indices hit every `cycle` steps from bar0 (+offset), skipping `holes` (default: every downbeat)."""
    g0 = bar0 * 16
    return [g for g in range(g0 + offset, (bar0 + bars) * 16, cycle) if not holes(g)]


def beats(g):
    return g / 4.0


# sudden mutes (beats, half-open): the drums drop out and leave the stutter alone
MUTES = [(15 * 4 + 2, 15 * 4 + 3), (19 * 4 + 2, 20 * 4)]
BREAK_CLAP_OFF = (24 * 4, 26 * 4)


def in_mute(t, windows=MUTES):
    return any(a <= t < b for a, b in windows)


# ----------------------------------------------------------------- 808 toms: carry the sub
toms = s.track("toms", gain=-3.0, hp=28)
TOM = Synth808(decay=0.14, drive_db=6, click=0.35, harmonics=0.25)
A_PITCH = ["F1", "F1", "Ab1", "C2", "C1", "Eb2", "C2", "Eb1"]       # 8-long pitch cycle over a 3-step hit cycle
B_PITCH = ["Db2", "Db1", "Db2", "Ab1", "Bb1", "F1"]                  # flip: Db colour
tc = Clip()
for cell in range(1, 8):
    b0 = cell * 4
    if cell == 6:  # breakdown cell: only rolls
        continue
    flip = b0 >= 16
    steps = [g for g in poly(5 if flip else 3, b0, 4, offset=1 if flip else 0) if not in_mute(beats(g))]
    pitches = B_PITCH if flip else A_PITCH
    for i, g in enumerate(steps):
        tc.note(pitches[i % len(pitches)], time=beats(g), dur=0.6, vel=0.95 if i % 2 == 0 else 0.8)
# 16t tom rolls with falling pitch into cell changes
for bar in (7, 15, 27, 31):
    for i, n in enumerate(["F2", "Eb2", "C2", "Ab1", "F1", "Eb1"]):
        tc.note(n, bar=bar, beat=3 + i / 6, dur=0.3, vel=0.7 + 0.05 * i)
# breakdown cell: bars 24-25 tom-less; 26-27 a 16t pitch ladder that grows into the last cell
for bar in (26, 27):
    for i, n in enumerate(["F1", "Ab1", "C2", "Eb2", "F2", "Ab2"][: 4 + 2 * (bar - 26)]):
        tc.note(n, bar=bar, beat=1.5 + i / 6, dur=0.25, vel=0.45 + 0.08 * i)
toms.clip(tc, TOM)

# ----------------------------------------------------------------- kick: punch only, sub given to toms
kick = s.track("kick", gain=-4.0, hp=60, choke=True)
KICK = "kicks/kick031_2"
K = dict(dur_beats=0.4, fade_out_ms=20, pitch=3)
for cell in range(1, 8):
    if cell == 6:
        continue
    pat = "...x..x...x..x.." if cell < 4 else "...x.....x..x..."
    kick.pattern(pat, KICK, bar=cell * 4, bars=4, **K)

# ----------------------------------------------------------------- claps on 2 and 4, displaced a 16th at cell ends
clap = s.track("clap", gain=-5.0, fx=[pb.Reverb(room_size=0.2, wet_level=0.1, dry_level=1.0)])
for cell in range(8):
    b0 = cell * 4
    if cell == 0:
        clap.pattern("....x.......x...", "sfx/percs/2018_clap", bar=2, bars=2)
        continue
    clap.pattern("....x.......x...", "sfx/percs/2018_clap", bar=b0, bars=3)
    clap.pattern("....x........x..", "sfx/percs/2018_clap", bar=b0 + 3, bars=1)
snap = s.track("snap", gain=-8.0, hp=800)
snap.pattern("....x.......x...", "sfx/percs/snap_02", bar=4, bars=28)

# quiet straight 16th hats
hats = s.track("hats", gain=-4.0, hp=5000, pan=0.15)
hats.pattern("5373537353735373", "sfx/percs/snap_02", bar=8, bars=16, dur_beats=0.2)
hats.pattern("5373537353735373", "sfx/percs/snap_02", bar=28, bars=4, dur_beats=0.2)
air = s.track("air", gain=-6.0, hp=7000, pan=-0.2)
s.loop("sfx/perc_loops/opera_hihat_loop_140bpm", track="air", bars=list(range(16, 24)) + list(range(28, 32)))

# ----------------------------------------------------------------- vocal chop: shake it down (native 160)
chop = s.track("chop", gain=8.0, hp=200, fx=[pb.Compressor(threshold_db=-20, ratio=3)])
LOOP = "vocals/vocal_loops/shake_it_down_loop_160"
CHOP_A = [None, None, 1, 2, None, 3, 4, None, 1, 1, 2, None, 5, None, None, None]
CHOP_B = [None, 1, 1, 1, None, 2, 3, 4, None, 5, None, 1, 2, None, 5, None]
for bar in list(range(0, 4)) + list(range(8, 12)) + list(range(20, 24)) + list(range(28, 31)):
    chop.chop(LOOP, pattern=CHOP_B if bar >= 16 else CHOP_A, step="16", bar=bar, n=16, gain=-7 if bar < 2 else -4 if bar < 4 else 0)

# ----------------------------------------------------------------- ONE word: "werk" on a 7-step cycle
werk = s.track("werk", gain=5.0, hp=150, fx=[pb.Compressor(threshold_db=-18, ratio=3)])
WERK = "vocals/werk"
for cell in (1, 2, 3, 4, 5, 7):
    b0 = cell * 4
    flip = b0 >= 16
    for g in poly(7, b0, 4, offset=2):
        werk.at(beats(g), WERK, dur_beats=0.5, pitch=-12 if flip else 0, gain=-2 if flip else 0)
# 32nd stutters into the flip and at cell ends
stutter(werk, WERK, bar=15, beat=2, step="32", count=16, accel=1.0, pitch_ramp=7, gain_ramp_db=4)
stutter(werk, "vocals/childish_gambino_v_3005_part_1_back", bar=11, beat=3, step="32", count=8)
stutter(werk, "vocals/childish_gambino_v_3005_part_1_back", bar=23, beat=3, step="32", count=8, pitch_ramp=-5)

# bar 19's hole: hand-rolled pitched 32nd stutter (tricks.stutter cannot take a base pitch)
for i in range(8):
    werk.at(19 * 4 + 3 + i / 8, "vocals/childish_gambino_v_3005_part_1_back", pitch=-7 - i, dur_beats=1 / 8, gain=-1 + i * 0.5)

# ----------------------------------------------------------------- Surge Rhodes stabs, 5-step cycle
keys = s.track("keys", gain=-6.0, hp=120, fx=[pb.Delay(delay_seconds=60 / BPM * 0.75, feedback=0.3, mix=0.2)])
kc = Clip()
for cell in (2, 3, 4, 5, 6, 7):
    b0 = cell * 4
    ch = ["Fm9", "Fm9", "Dbmaj7", "Ebsus4"] if b0 < 16 else ["Dbmaj7", "Bbm7", "Fm9", "C7"]
    for g in poly(5, b0, 4, offset=3):
        bar_in_cell = (g // 16) - b0
        kc.chord(chord(ch[bar_in_cell], 3), bar=0, beat=beats(g), dur=0.35, vel=0.8)
keys.clip(kc, SurgeSynth("Bluelight/Keys/Treated Rhodes", gain_db=6))
keys.automate("gain", [(0, 0), (24 * 4, 0), (24 * 4 + 0.01, -5), (28 * 4, -1), (28 * 4 + 0.01, 0)])
keys.automate("lp", [(0, 20000), (24 * 4, 20000), (24 * 4 + 0.01, 500), (28 * 4, 9000), (28 * 4 + 0.01, 20000)])

# ----------------------------------------------------------------- fx
fx = s.track("fx", gain=-10.0, hp=150)
fx.hit("sfx/percs/whips/id_whip_crack_fx", bar=15, beat=3.5)
fx.hit("sfx/percs/impacts/purge_siren", bar=22, beat=0, gain=-4)
fx.hit("sfx/percs/whips/id_whip_crack_fx", bar=27, beat=3.5)

# apply sudden mutes / breakdown clap drop to the sample tracks (Track.mute is whole-track only)
s.events = [e for e in s.events if not (
    (e.track in ("kick", "clap", "snap", "hats") and in_mute(e.time))
    or (e.track in ("clap", "snap") and in_mute(e.time, [BREAK_CLAP_OFF])))]

s.sidechain("keys", source="kick", amount_db=6, release_ms=110)
s.sidechain("chop", source="toms", amount_db=3, release_ms=90)
s.sidechain("toms", source="kick", amount_db=4, release_ms=80)
s.master(fx=[pb.HighpassFilter(28), pb.Compressor(threshold_db=-14, ratio=2, attack_ms=15, release_ms=120)], gain_db=7.0, limiter_db=-1.0, true_peak_db=-1)

if __name__ == "__main__":
    print(s.render("demos/out/footwork01", stems=True))
