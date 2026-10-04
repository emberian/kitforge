"""jersey02 — internet Jersey / hyperflip, 146 bpm, 32 bars, E minor.

Built on the researched canon (recipes/GENRES.md → Jersey club + Internet Jersey; kitforge/idioms.py):
5-count kick 0,4,8,11,14 · squeak between kicks · 808 follows the kick and slides roots · single-note vocal chop
re-pitched into a melody · octave vocal stacks · velocity stutters · future-bass supersaw chords sidechained hard ·
flips every 8 bars (pitch riser, roll, reverse crash, impact, pitch drop) · crushed second drop · nightcored memes.

    cd ~/dev/kitforge && uv run python -W ignore demos/jersey02.py
"""

import pedalboard as pb

from kitforge.idioms import (JERSEY_KICK, JERSEY_CLAP_GHOST, SQUEAK_BETWEEN_SAFE, SQUEAK_DOUBLE, PitchRiser, bass_follows_kick,
                             chop_melody, crush, flip, jersey_kick, nightcore, pitch_drop, reverse_crash, stutter_delay,
                             velocity_stutter, vocal_stack)
from kitforge.render import Song
from kitforge.surge import SurgeSynth
from kitforge.synth import Clip, FMPluck, Supersaw, Synth808, chord
from kitforge.tricks import P, bitcrush, stutter, tape_stop, vinyl

BPM = 146
s = Song("twerknation28", bpm=BPM, bars=32)
KICK = "kicks/id_night_club_808"
SPB = 60 / BPM

# ------------------------------------------------------------------ sections (bars)
INTRO, DROP1, FLIP_A, DROP2, BREAK, DROP3 = range(0, 4), range(4, 12), range(12, 16), range(16, 24), range(24, 28), range(28, 32)

# ------------------------------------------------------------------ drums
kick = jersey_kick(s, KICK, bar=4, bars=8, pitch=4, gain=-6)                      # drop 1
kick.pattern(JERSEY_KICK, KICK, bar=14, bars=2, dur_beats=0.45, fade_out_ms=25, pitch=4)   # back in for the flip's last 2 bars
kick.pattern(JERSEY_KICK, KICK, bar=16, bars=8, dur_beats=0.45, fade_out_ms=25, pitch=4)   # drop 2
kick.pattern(JERSEY_KICK, KICK, bar=28, bars=4, dur_beats=0.45, fade_out_ms=25, pitch=4)   # drop 3
kick.pattern("x...x...x..x..x.|x...x...x..x.x.x", KICK, bar=20, bars=4, dur_beats=0.45, fade_out_ms=25, pitch=4)  # 2-bar pickup phrasing
click = s.track("kick_click")
click.pattern(JERSEY_KICK, "sfx/percs/snap_02", bar=14, bars=10, dur_beats=0.1)
click.pattern(JERSEY_KICK, "sfx/percs/snap_02", bar=28, bars=4, dur_beats=0.1)

clap = s.track("clap", gain=-7, fx=[pb.Reverb(room_size=0.22, wet_level=0.10, dry_level=1.0)])
for b0, n in ((4, 8), (16, 8), (28, 4)):
    clap.pattern(JERSEY_CLAP_GHOST, "sfx/percs/2018_clap", bar=b0, bars=n)
    clap.pattern("....x.......x...", "sfx/percs/snap_01", bar=b0, bars=n, gain=-8)

squeak = s.track("squeak", gain=-9, hp=500, pan=0.25)
squeak.pattern(SQUEAK_BETWEEN_SAFE, "sfx/percs/fills/bed_squeak_loop_big_o_11", bar=0, bars=4, gain=-4)   # intro tease
squeak.pattern(SQUEAK_BETWEEN_SAFE, "sfx/percs/fills/bed_squeak_loop_big_o_11", bar=4, bars=8)
squeak.pattern(SQUEAK_BETWEEN_SAFE, "sfx/percs/fills/bed_squeak_loop_big_o_12", bar=16, bars=8, pan=-0.3)
squeak.pattern(SQUEAK_DOUBLE, "sfx/percs/fills/bed_squeak_loop_big_o_11", bar=28, bars=4, gain=-3)          # Philly doubles for the last 4

hats = s.track("hats", gain=-7, hp=4000)
s.loop("sfx/perc_loops/opera_hihat_loop_140bpm", track="hats", bars=range(16, 24))

# ------------------------------------------------------------------ bass: 808 follows the kick, roots slide E -> C -> G -> D (Em / C / G / D)
bass_follows_kick(s, Synth808(decay=0.5, drive_db=10, click=0.4), root="E1", bars=range(4, 12), gain=-8)
bass_follows_kick(s, Synth808(decay=0.5, drive_db=10, click=0.4), root="E1", bars=range(16, 24), slide_to=["C1", "G1", "D2"], track="bass2", gain=-8)
bass_follows_kick(s, Synth808(decay=0.5, drive_db=12, click=0.4), root="E1", bars=range(28, 32), track="bass3", gain=-7)

# ------------------------------------------------------------------ chords: future-bass supersaws, sidechained to the kick
PROG = [("Em9", 3), ("Cmaj7", 3), ("G", 3), ("D", 3)]
chords = s.track("chords", gain=3, hp=120, lp=11000)
c = Clip()
for i, b in enumerate(list(DROP1) + list(DROP2) + list(DROP3)):
    name, octv = PROG[i % 4]
    c.chord(chord(name, octv), bar=b, beat=0, dur=3.9, vel=0.8)
    if b in DROP2 or b in DROP3:
        c.chord(chord(name, octv + 1), bar=b, beat=2.75, dur=0.5, vel=0.6)   # off-beat stab on the "a" of 3
chords.clip(c, Supersaw(voices=7, detune_cents=14, cutoff=1800, env_amount=2500, s=0.7, r=0.12, width=0.8, sub=0.0))
pad = s.track("pad", gain=-2, hp=150)
pc = Clip()
for i, b in enumerate(list(INTRO) + list(BREAK)):
    name, octv = PROG[i % 4]
    pc.chord(chord(name, octv), bar=b, beat=0, dur=4.0, vel=0.9)
pad.clip(pc, SurgeSynth("Altenberg/Pads/Alone", gain_db=14))
pad.automate("lp", [(0, 500), (16, 5000), (96, 5000), (112, 800)])

# ------------------------------------------------------------------ vocals
# the hook word on the kick rhythm; "hey" answers on the 2-and / 4-and
vox = s.track("vox", gain=2, hp=200, fx=[pb.Compressor(threshold_db=-16, ratio=3), pb.Delay(delay_seconds=SPB * 0.75, feedback=0.2, mix=0.10)])
HOOK = "vocals/back_it_up_2"
vox.pattern("x...x...x..x....", HOOK, bar=4, bars=4)
vox.pattern("x...x...x..x..x.", HOOK, bar=8, bars=4, pitch=0)
vox.pattern("......x.......x.", "vocals/hey_2", bar=6, bars=6, gain=-2, pan=0.2)
vox.hit("vocals/3_2_1_lets_go", bar=3, beat=1.5, gain=1)                      # count-in into drop 1
vox.hit("vocals/we_in_jersey_right_now", bar=11, beat=0, gain=1)
velocity_stutter(vox, HOOK, bar=11, beat=2, step="16", count=8, decay_db=-1.5)  # into the flip
# single-note chop ("ahhh" is a C3) re-pitched into an E-minor line
MELODY = ["E3", None, "D3", "B2", None, "G2", "E3", None, "D3", None, "B2", "D3", "E3", None, None, None]
vmel = s.track("vmel", gain=4, hp=180, fx=[pb.Compressor(threshold_db=-18, ratio=3), pb.Reverb(room_size=0.3, wet_level=0.12, dry_level=1.0)])
for b in (8, 10, 16, 18, 20, 22, 28, 30):
    chop_melody(vmel, "vocals/ahhh", MELODY, bar=b, step="8", gate=0.9, gain=0 if b < 16 else 2)
# octave stacks of "oh_oh" (F4 -> pulled to E) answering at the end of 4-bar phrases
for b in (7, 19, 23, 31):
    vocal_stack(vmel, "vocals/oh_oh", bar=b, beat=3.0, layers=((-13, -5.0), (-1, 0.0), (11, -8.0)), gain=-2)
# drop 2 vocals: crushed bus, pitched-up "ai" ladder and the hook an octave up (chipmunk)
vox2 = s.track("vox2", gain=-7, hp=220)
vox2.pattern("x...x...x..x..x.", HOOK, bar=16, bars=8, **nightcore(7), gain=-2)
vox2.pattern("..x.......x.....", "vocals/ai", bar=16, bars=8, pitch=-1, pitch_mode="formant", gain=-3)   # G#3 -> G3 (in key)
vox2.hit("vocals/id_famous_hey_chant", bar=20, beat=0, gain=0)
vox2.hit("vocals/bring_it_back_2_2", bar=23, beat=0, gain=1)
velocity_stutter(vox2, HOOK, bar=23, beat=2, step="32", count=12, decay_db=-1.0, **nightcore(7))
vox2.process(P(crush, drive_db=5, bits=11))
# break: the sung thing in the pack (Fred again.. acapella, Em) chopped on onsets + a spoken joke
sung = s.track("sung", gain=8, hp=150, fx=[pb.Reverb(room_size=0.6, wet_level=0.25, dry_level=1.0), pb.Delay(delay_seconds=SPB * 1.5, feedback=0.3, mix=0.15)])
FRED = "vocals/vocal_loops/fred_again_jozzy_ten_fred_again_part_1_wav_vocals_2"
sung.chop(FRED, pattern=[0, None, 1, None, 2, 3, None, 4], step="8", bar=0, stretch=False, dur_steps=1.8, pitch_mode="formant")
sung.chop(FRED, pattern=[0, None, 1, None, 2, 3, None, 4, 5, None, 6, 7, None, 8, 9, None], step="8", bar=24, stretch=False, dur_steps=1.8)
sung.chop(FRED, pattern=[0, 0, 1, 1, 2, 2, 3, 3], step="16", bar=27, stretch=False, dur_steps=0.95, pitch=12, pitch_mode="resample", gain=-3)  # chipmunk run into drop 3
joke = s.track("joke", gain=-4, hp=300)
joke.hit("vocals/pause", bar=12, beat=0, gain=2)                       # the flip: everything stops, "pause"
joke.hit("vocals/wait_a_min", bar=13, beat=0)
joke.hit("vocals/calll_securityy", bar=26, beat=0, gain=-2)
joke.process(P(stutter_delay, bpm=BPM, step="16", repeats=2, filter_hz=1200, decay_db=-5))
memes = s.track("memes", gain=-8, hp=300)
memes.hit("vocals/pac_man_sound", bar=12, beat=2, **nightcore(5))
memes.hit("vocals/dragon_ballz_sample_000_022", bar=15, beat=0, **nightcore(4), gain=-2)
memes.hit("sfx/percs/synplant_ui_glitch_part_83", bar=19, beat=3.5)
memes.hit("sfx/percs/fills/swish_buzzer", bar=27, beat=3.5, gain=-3)
memes.process(P(bitcrush, bits=9))

# ------------------------------------------------------------------ flips / transitions
flip(s, 4, KICK, riser_bars=1, impact="sfx/percs/impacts/boom")                          # into drop 1
flip(s, 16, KICK, riser_bars=2, impact="sfx/percs/impacts/bomb_kick_2", roll_pattern="x.x.x.x.xxxxxxxx")   # into drop 2
flip(s, 28, KICK, riser_bars=2, impact="sfx/percs/impacts/boom")                          # into drop 3
fx = s.track("fx", gain=-6)
fx.hit("sfx/percs/fills/reload", bar=7, beat=3.5)
fx.hit("sfx/percs/fills/reload", bar=15, beat=3.5)
fx.hit("sfx/percs/impacts/purge_siren", bar=26, beat=0, gain=-6, pitch=-3)
fx.hit("sfx/percs/whips/id_whip_crack_fx", bar=12, beat=0, gain=-2)
# the chords get pitch-dropped at the top of the flip and tape-stopped before the break
chords.process(P(pitch_drop, at_s=s.t(12, 0) * SPB - 0.02, semis=-12, length_s=0.35))
chords.process(P(tape_stop, start_s=s.t(23, 3.5) * SPB, length_s=0.45, resume_s=s.t(24, 0) * SPB))

# ------------------------------------------------------------------ dynamics
for t in ("chords", "pad", "vmel", "sung"):
    s.sidechain(t, source="kick", amount_db=10, release_ms=90)
s.sidechain("bass", source="kick", amount_db=4, release_ms=80)
s.sidechain("bass2", source="kick", amount_db=4, release_ms=80)
s.sidechain("bass3", source="kick", amount_db=4, release_ms=80)
s.master(fx=[pb.HighpassFilter(28), pb.Compressor(threshold_db=-10, ratio=1.5, attack_ms=20, release_ms=150)], gain_db=3.0, limiter_db=-1.0, true_peak_db=-1.0)

if __name__ == "__main__":
    print(s.render("demos/out/jersey02", stems=True))
