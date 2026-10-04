"""Jersey club, 138 bpm, 16 bars. The canonical 5-kick pattern, bed squeak on the 'and's, vocal chop hook,
triplet kick roll into the drop, Surge bass doubling the kick root. Run:  uv run python demos/jersey01.py
"""

import pedalboard as pb

from kitforge.render import Song
from kitforge.synth import Clip
from kitforge.surge import SurgeSynth
from kitforge.tricks import roll, stutter, P, reverse_reverb

BPM = 138
s = Song("twerknation28", bpm=BPM, bars=16)

# --- drums
kick = s.track("kick", gain=-2.0, choke=True)
KICK = "kicks/id_night_club_808"  # sub E1 ~41.7Hz; 56ms attack, 410ms decay -> truncate or it drones
K = dict(dur_beats=0.45, fade_out_ms=25, pitch=4)  # ~195ms at 138; +4st -> G#1 ~52Hz: punchier, less sub-drone
# Jersey club: 1 . . a | . . & . | . . & . | 4 . . .   == steps 0,3,6,10,12
kick.pattern("x..x..x...x.x...", KICK, bar=2, bars=2, **K)     # pattern enters after a 2-bar vocal intro
kick.pattern("x..x..x...x.x...", KICK, bar=4, bars=8, **K)
kick.pattern("x..x..x...x.x...", KICK, bar=13, bars=2, **K)    # bar 12 = kick drop-out (breath before last 4)
roll(kick, KICK, bar=15, beat=0, pattern="x..x..x.x.x.xxxx", step="16", **K)      # fill into next section
click = s.track("click", gain=-10.0, hp=1500)                   # transient layer so the kick reads on small speakers
click.pattern("x..x..x...x.x...", "sfx/percs/snap_02", bar=2, bars=14, dur_beats=0.1)

squeak = s.track("squeak", gain=-8.0, hp=400, pan=0.2)
squeak.pattern("..x...x...x...x.", "sfx/percs/fills/bed_squeak_loop_big_o_11", bar=4, bars=12)
squeak.pattern("......x.......x.", "sfx/percs/fills/bed_squeak_loop_big_o_12", bar=8, bars=8, gain=-3, pan=-0.3)

clap = s.track("clap", gain=-6.0, fx=[pb.Reverb(room_size=0.25, wet_level=0.12, dry_level=1.0)])
clap.pattern("....x.......x...", "sfx/percs/2018_clap", bar=4, bars=12)
clap.pattern("....x.......x...", "sfx/percs/snap_01", bar=8, bars=8, gain=-6)

hats = s.track("hats", gain=-10.0, hp=3000)
s.loop("sfx/perc_loops/opera_hihat_loop_140bpm", track="hats", bars=range(8, 16))

# --- vocals
vox = s.track("vox", gain=3.0, hp=180, fx=[pb.Compressor(threshold_db=-18, ratio=3), pb.Delay(delay_seconds=60 / BPM * 0.75, feedback=0.25, mix=0.15)])
# the hook: "back it up" chopped on the kick pattern, re-pitched up for the second half
HOOK = "vocals/back_it_up_2"
vox.pattern("x..x..x.........", HOOK, bar=4, bars=4)
vox.pattern("x..x..x...x.x...", HOOK, bar=8, bars=4, pitch=0)
vox.pattern("x..x..x...x.x...", HOOK, bar=12, bars=3, pitch=2)
vox.hit("vocals/ahhh", bar=7, beat=3, gain=-2)
vox.hit("vocals/ahhh", bar=11, beat=3, gain=-2, pitch=-2)
stutter(vox, HOOK, bar=15, beat=0, step="16", count=8, accel=0.85, pitch_ramp=5, gain_ramp_db=3)

shout = s.track("shout", gain=-3.0, hp=250, fx=[pb.Reverb(room_size=0.5, wet_level=0.2, dry_level=1.0)])
shout.hit("vocals/3_2_1_lets_go", bar=0, beat=2)
shout.hit("vocals/hey_2", bar=1, beat=1.5)
shout.hit("vocals/hey_2", bar=1, beat=3.5, pitch=3)
shout.hit("vocals/bring_it_back_2_2", bar=12, beat=0, gain=2)
shout.hit("vocals/we_in_jersey_right_now", bar=6, beat=0, pitch=0)
shout.hit("vocals/id_famous_hey_chant", bar=10, beat=2.5, gain=-2)
shout.hit("vocals/hey_2", bar=13, beat=1.5)
shout.hit("vocals/hey_2", bar=13, beat=3.5, pitch=3)

# --- synth: Surge bass following the kick root (E1), octave stabs in the second half
bass = s.track("bass", gain=-4.0, hp=70, lp=2500)  # hp 70: leave the sub to the kick
c = Clip()
for b in list(range(4, 12)) + [13, 14, 15]:
    for st in (0, 6, 12):  # on the kick's 1, '&' of 2, and 4
        c.note("E2", bar=b, beat=st / 4, dur=0.4, vel=0.9)
    if b >= 8:
        c.note("G2", bar=b, beat=2.5, dur=0.2, vel=0.7)
        c.note("B2", bar=b, beat=3.5, dur=0.2, vel=0.6)
bass.clip(c, SurgeSynth("Basses/Bass 1", gain_db=10))

# --- fx
fx = s.track("fx", gain=-8.0, fx=[pb.HighpassFilter(120)])
fx.hit("sfx/percs/whips/id_whip_crack_fx", bar=3, beat=3.5)
fx.hit("sfx/percs/impacts/purge_siren", bar=14, beat=0, gain=-4)
fx.hit("sfx/percs/fills/reload", bar=7, beat=3.5)
fx.hit("sfx/percs/fills/reload", bar=11, beat=3.5)

s.sidechain("vox", source="kick", amount_db=4, release_ms=120)
s.sidechain("bass", source="kick", amount_db=6, release_ms=100)
s.master(fx=[pb.HighpassFilter(28)], gain_db=1.0, limiter_db=-1.5)

if __name__ == "__main__":
    out = s.render("demos/out/jersey01", stems=True)
    print(out)
