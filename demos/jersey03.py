"""jersey03 — a 4-minute Jersey club DJ edit through four classics, 140 bpm, 140 bars.

    INTRO   0-7     Imogen Heap "Hide and Seek" cold open (free time), squeak tease
    A       8-39    Cassie "Me & U"      (99.4 -> 140 as a sped-up edit, +5.9 st): verse, pre, chorus, chopped chorus
    B      40-71    Ciara "1, 2 Step"    (112.4 -> 140, +3.8 st): "automatic, supersonic", verse, chorus, chopped
    BREAK  72-87    "Hide and Seek" bridge (mmm whatcha say), no kick, build
    C      88-119   Ginuwine "Pony"      (143.6 -> 140, formant stretch): riff, verse, chorus, chopped
    D     120-135   Beyoncé "Crazy in Love" (+5.9 st): horns, chorus
    OUTRO 136-139   tape stop + tag

Sources live in packs/classics (yt-dlp -> demucs htdemucs stems; see README "Remixing songs"). Each song keeps its own
bass/melodic stems so the harmony stays intact; key changes happen across drum-only flips. Juice (kitforge.mod):
filter LFOs and ramps on the music stems, width opening into choruses, delay throws at phrase ends, hats and squeaks
following other tracks, per-hit pitch envelopes on chops, OTT on the music bus, tape saturation + transients on drums.

    cd ~/dev/kitforge && uv run python -W ignore demos/jersey03.py
"""

import math

import pedalboard as pb

from kitforge.idioms import (bass_follows_kick, JERSEY_BOUNCE, JERSEY_CLAP_GHOST, JERSEY_KICK, JERSEY_KICK_2BAR, SQUEAK_BETWEEN_SAFE, SQUEAK_DOUBLE,
                             PitchRiser, crush, flip, pitch_drop, reverse_crash, stutter_delay, velocity_stutter)
from kitforge.mod import LFO, Follow, Ramp, Steps, deess, haas, ott, saturate, tilt, transient, width
from kitforge.render import Song
from kitforge.synth import Clip, Sine, Synth808
from kitforge.tricks import P, bitcrush, roll, tape_stop, vinyl

BPM = 140
s = Song("twerknation28", bpm=BPM, bars=140, extra_packs=["classics"])
SPB = 60 / BPM
KICK = "kicks/id_night_club_808"
K = dict(dur_beats=0.45, fade_out_ms=25, pitch=4)

# source grids (kitforge.songmap): tempo from the beat tracker, downbeat from kick-phase voting
GRID = {
    "cassie": ("classics:cassie_me_and_u", dict(src_bpm=99.38, first_beat=4.4234), True),
    "ciara": ("classics:ciara_1_2_step", dict(src_bpm=112.35, first_beat=1.6834), True),
    "pony": ("classics:ginuwine_pony", dict(src_bpm=143.55, first_beat=0.1741), False),   # near-native: formant stretch
    "bey": ("classics:beyonce_crazy_in_love", dict(src_bpm=99.38, first_beat=2.1479), True),
}
IMOGEN = "classics:imogen_heap_hide_and_seek/mix"


def sec(song, stem, src_bar, bars, bar, beat=0.0, track=None, **kw):
    """Place `bars` bars of a source stem, from its bar src_bar, at our (bar, beat)."""
    base, grid, nc = GRID[song]
    return s.song_section(f"{base}/{stem}", src_bar, bars, track=track or f"{song}_{stem}", bar=bar, beat=beat,
                          nightcore=nc, **grid, **kw)


def chop(song, stem, src_bar, src_beat, beats, bar, beat, track=None, **kw):
    """A short chop: `beats` beats of the source starting at (src_bar, src_beat)."""
    return sec(song, stem, src_bar + src_beat / 4, beats / 4, bar, beat, track=track or f"{song}_chop", **kw)


def chop_pattern(song, stem, src_bar, src_beat, beats, bar, bars, pattern=JERSEY_KICK, pitches=(0,), gains=(0,), **kw):
    """The Jersey hook move: one chop re-triggered on a 16th pattern, pitch/gain rotating per hit."""
    pat = pattern.replace("|", "")
    h = 0
    for b in range(bar, bar + bars):
        for i, ch in enumerate(pat[(b - bar) * 16 % len(pat):][:16] if len(pat) > 16 else pat):
            if ch in "xX":
                chop(song, stem, src_bar, src_beat, beats, b, i / 4, pitch=pitches[h % len(pitches)],
                     gain=gains[h % len(gains)] + kw.get("gain", 0), **{k: v for k, v in kw.items() if k != "gain"})
                h += 1


# ====================================================================== DRUMS
kick = s.track("kick", gain=-8, choke=True, fx=[pb.Reverb(room_size=0.15, wet_level=0.06, dry_level=1.0, width=0.3)])
click = s.track("kick_click", gain=-15, hp=1500)


def kicks(bar, bars, pattern=JERSEY_KICK):
    kick.pattern(pattern, KICK, bar=bar, bars=bars, **K)
    click.pattern(pattern, "sfx/percs/snap_02", bar=bar, bars=bars, dur_beats=0.1)


kicks(8, 4, "x.......x.......")  # A: verse opens half-time
kicks(12, 4)
kicks(16, 7, JERSEY_KICK_2BAR)    # A: pre (bar 23 = fill)
kicks(24, 8)                      # A: chorus
kicks(32, 7, JERSEY_BOUNCE)       # A: chopped chorus, busier
kicks(40, 4, "x.......x.......")  # B opens half-time
kicks(44, 4)
kicks(48, 7, JERSEY_KICK_2BAR)
kicks(56, 8)
kicks(64, 7, JERSEY_BOUNCE)
kicks(84, 3)                      # break: kick returns for the last bars of the build
kicks(88, 4, "x.......x.......")  # C opens half-time
kicks(92, 4)
kicks(96, 7, JERSEY_KICK_2BAR)
kicks(104, 8)
kicks(112, 7, JERSEY_BOUNCE)
kicks(120, 4, "x.......x.......")  # D: horns over half-time
kicks(124, 4)
kicks(128, 7, JERSEY_BOUNCE)
kicks(136, 2)

clap = s.track("clap", gain=-8, fx=[pb.Reverb(room_size=0.22, wet_level=0.10, dry_level=1.0)])
for b0, n in ((16, 24), (40, 32), (80, 8), (88, 32), (120, 16)):
    clap.pattern(JERSEY_CLAP_GHOST, "sfx/percs/2018_clap", bar=b0, bars=n)
    clap.pattern("....x.......x...", "sfx/percs/snap_01", bar=b0, bars=n, gain=-8)

squeak = s.track("squeak", gain=-15, hp=500, lp=12000, pan=0.25)
squeak.pattern(SQUEAK_BETWEEN_SAFE, "sfx/percs/fills/bed_squeak_loop_big_o_11", bar=4, bars=4, gain=-4)
for b0, n in ((8, 24), (40, 24), (88, 24), (120, 8)):
    squeak.pattern(SQUEAK_BETWEEN_SAFE, "sfx/percs/fills/bed_squeak_loop_big_o_11", bar=b0, bars=n,
                   plocks={"pitch": [0, 0, 2, 0, 0, -2, 0, 3], "pan": [-0.4, 0.4]})
for b0, n in ((32, 8), (64, 8), (112, 8), (128, 8)):   # chopped sections: Philly doubles
    squeak.pattern(SQUEAK_DOUBLE, "sfx/percs/fills/bed_squeak_loop_big_o_12", bar=b0, bars=n, gain=-3,
                   plocks={"gain": [0, -5, -2, -5], "pitch": [0, 0, 0, 5]})

hats = s.track("hats", gain=-11, hp=4500, lp=15000)
for b0, n in ((24, 16), (56, 16), (104, 16), (120, 16)):
    s.loop("sfx/perc_loops/opera_hihat_loop_140bpm", track="hats", bars=range(b0, b0 + n))
hats.mod("gain", Follow("kick", lo=-7, hi=0, invert=True, release_ms=90))        # hats duck under the kick: bounce

s.bus("drums", ["kick", "kick_click", "clap", "squeak", "hats"], process=[P(transient, attack_db=1.5), P(saturate, drive_db=1.5, kind="tape")])

# ====================================================================== INTRO (0-7): Hide and Seek cold open
im = s.track("imogen", gain=-1, hp=120)
im.at(s.t(0, 0), IMOGEN, start=1.1, end=1.1 + 8 * 4 * SPB, dur_beats=32, fade_out_ms=200)
im.at(s.t(72, 0), IMOGEN, start=172.0, end=172.0 + 16 * 4 * SPB, dur_beats=64, fade_out_ms=400)     # the bridge, for the break
im.mod("lp", Ramp([(0, 900), (24, 9000), (32, 14000), (288, 14000), (288.01, 2500), (320, 9000), (344, 16000)]))  # opens in the intro and again across the break
im.mod("width", Ramp([(0, 0.6), (32, 1.2), (288, 0.8), (352, 1.5)]))
s.send("verb", fx=[pb.Reverb(room_size=0.8, wet_level=1.0, dry_level=0.0, width=1.0), pb.HighpassFilter(300)], gain_db=-8)
s.send("echo", fx=[pb.Delay(delay_seconds=SPB * 0.75, feedback=0.45, mix=1.0), pb.HighpassFilter(500), pb.LowpassFilter(5000)], gain_db=-6)
im.send("verb", 0.35)
vinyl_t = s.track("crackle", gain=-22, hp=800)                                  # dust layer keyed to the squeak in the intro
vinyl_t.at(s.t(0, 0), "vocals/hiei_audio_msg", start=0.2, end=10.0, dur_beats=32)
vinyl_t.process(P(vinyl, noise_db=-30, lp=6000))
shout = s.track("shout", gain=-11, hp=250, lp=9000, fx=[pb.Reverb(room_size=0.4, wet_level=0.15, dry_level=1.0)])
shout.hit("vocals/3_2_1_lets_go", bar=7, beat=1.5, gain=2)

# ====================================================================== A (8-39): Cassie — Me & U
for stem, g in (("vocals", 3), ("other", -3), ("bass", -4)):
    sec("cassie", stem, 7, 8, 8, gain=g)       # verse
    sec("cassie", stem, 15, 8, 16, gain=g)     # pre-chorus
    sec("cassie", stem, 23, 8, 24, gain=g)     # chorus
# chopped chorus (32-39): the first beat-and-a-half of the chorus on the kick rhythm, pitch rotating; full line returns in bar 36
chop_pattern("cassie", "vocals", 23, 0, 1.0, 32, 4, pattern=JERSEY_KICK, pitches=(0, 0, 0, 3, -2), gain=2, track="cassie_vocals")
sec("cassie", "vocals", 23, 3, 36, gain=3)
chop_pattern("cassie", "vocals", 25, 0, 0.5, 39, 1, pattern="x.x.x.x.xxxxxxxx", pitches=(0, 0, 0, 0, 2, 2, 3, 3, 5, 5, 7, 7), gain=0, track="cassie_vocals")
sec("cassie", "other", 23, 8, 32, gain=-3)
sec("cassie", "bass", 23, 8, 32, gain=-4)
s.track("cassie_vocals", hp=160, lp=15000, fx=[pb.Compressor(threshold_db=-18, ratio=3)]).process(P(deess, freq=5500, threshold_db=-36, ratio=5)).process(P(tilt, high_db=-2.0, pivot_hz=5000))
s.track("cassie_other", hp=140)
s.track("cassie_bass", hp=40, lp=400)
# the source has no bass under the verse/pre: an 808 on F (B + 5.9 st) follows the kick there
bass_follows_kick(s, Synth808(decay=0.45, drive_db=9, click=0.3), root="F1", bars=range(8, 23), track="cassie_808", gain=-9)

# ====================================================================== B (40-71): Ciara — 1, 2 Step
for stem, g in (("vocals", 5), ("other", 6), ("bass", -1)):
    sec("ciara", stem, 6, 8, 40, gain=g)       # "this beat is automatic, supersonic, hypnotic, funky fresh"
    sec("ciara", stem, 14, 8, 48, gain=g)      # verse
    sec("ciara", stem, 23, 8, 56, gain=g)      # chorus
chop_pattern("ciara", "vocals", 23, 0, 1.0, 64, 4, pattern=JERSEY_BOUNCE, pitches=(0, 0, 2, 0, 0, -3, 0), gain=4, track="ciara_vocals")
sec("ciara", "vocals", 27, 3, 68, gain=5)
chop_pattern("ciara", "vocals", 27, 0, 0.5, 71, 1, pattern="x.x.x.x.xxxxxxxx", pitches=(0, 0, 0, 0, -2, -2, -3, -3, -5, -5, -7, -7), gain=1, track="ciara_vocals")
sec("ciara", "other", 23, 8, 64, gain=6)
sec("ciara", "bass", 23, 8, 64, gain=-2)
s.track("ciara_vocals", hp=160, lp=15000, fx=[pb.Compressor(threshold_db=-18, ratio=3)]).process(P(deess, freq=5500, threshold_db=-36, ratio=5)).process(P(tilt, high_db=-2.0, pivot_hz=5000))
s.track("ciara_other", hp=140)
s.track("ciara_bass", hp=40, lp=400)
shout.hit("vocals/we_in_jersey_right_now", bar=47, beat=2, gain=0)
shout.pattern("......x.......x.", "vocals/hey_2", bar=56, bars=8, gain=-3, plocks={"pan": [-0.5, 0.5], "pitch": [0, 0, 0, 3]})
shout.hit("vocals/id_famous_hey_chant", bar=63, beat=2, gain=-1)

# ====================================================================== BREAK (72-87): Hide and Seek bridge
sub = s.track("sub", gain=-12, lp=200)
sub.clip(Clip().note("A1", bar=72, dur=32, vel=0.8).note("E1", bar=80, dur=16, vel=0.8).note("A1", bar=84, dur=16, vel=0.9), Sine(a=1.5, d=0.5, s=0.9, r=1.0))
squeak.pattern("..x.......x.....", "sfx/percs/fills/bed_squeak_loop_big_o_11", bar=76, bars=8, gain=-6, plocks={"pitch": [0, 5, 7, 12]})
velocity_stutter(shout, "vocals/back_it_up_2", bar=86, beat=0, step="16", count=16, decay_db=0.2, pitch=0)   # rising stutter into C
velocity_stutter(shout, "vocals/back_it_up_2", bar=87, beat=0, step="32", count=24, decay_db=0.1, pitch=5)

# ====================================================================== C (88-119): Ginuwine — Pony
for stem, g in (("other", 9), ("bass", -2)):
    sec("pony", stem, 0, 8, 88, gain=g)        # the riff
    sec("pony", stem, 16, 8, 96, gain=g)
    sec("pony", stem, 29, 8, 104, gain=g)
    sec("pony", stem, 29, 8, 112, gain=g)
sec("pony", "vocals", 0, 8, 88, gain=9)
sec("pony", "vocals", 16, 8, 96, gain=9)       # verse 1
sec("pony", "vocals", 29, 8, 104, gain=9)      # chorus: "if you're horny, let's do it, ride it, my pony"
chop_pattern("pony", "vocals", 29, 0, 1.0, 112, 4, pattern=JERSEY_KICK, pitches=(0, 0, 0, -12, 0), gain=9, track="pony_vocals")
sec("pony", "vocals", 31, 3, 116, gain=9)
chop_pattern("pony", "vocals", 31, 0, 0.5, 119, 1, pattern="x.x.x.x.xxxxxxxx", pitches=(0, -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -12), gain=4, track="pony_vocals")
s.track("pony_vocals", hp=140, lp=12000, fx=[pb.Compressor(threshold_db=-20, ratio=3)]).process(P(deess, freq=6000, threshold_db=-36, ratio=4))
s.track("pony_other", hp=120)
s.track("pony_bass", hp=35, lp=500)

# ====================================================================== D (120-135): Beyoncé — Crazy in Love
for stem, g in (("vocals", 8), ("other", 5), ("bass", 1)):
    sec("bey", stem, 0, 8, 120, gain=g)        # the horns
    sec("bey", stem, 19, 8, 128, gain=g)       # chorus
s.track("bey_vocals", hp=160, lp=15000, fx=[pb.Compressor(threshold_db=-18, ratio=3)]).process(P(deess, freq=5500, threshold_db=-36, ratio=5)).process(P(tilt, high_db=-2.0, pivot_hz=5000))
s.track("bey_other", hp=120)
s.track("bey_bass", hp=40, lp=400)
shout.pattern("......x.......x.", "vocals/hey_2", bar=128, bars=8, gain=-3, plocks={"pan": [0.5, -0.5]})

# ====================================================================== OUTRO (136-139)
chop_pattern("bey", "vocals", 19, 0, 1.0, 136, 2, pattern=JERSEY_KICK, pitches=(0, -2, -4, -7, -12), gain=4, track="bey_vocals")
shout.hit("vocals/pause", bar=138, beat=0, gain=4)
im.at(s.t(138, 2), IMOGEN, start=1.1, end=1.1 + 6 * SPB, dur_beats=6, fade_out_ms=300)

# ====================================================================== JUICE: buses, modulation, throws
MUSIC = ["cassie_other", "cassie_bass", "ciara_other", "ciara_bass", "pony_other", "pony_bass", "bey_other", "bey_bass"]
VOX = ["cassie_vocals", "ciara_vocals", "pony_vocals", "bey_vocals"]
s.bus("music", MUSIC, process=[P(ott, depth=0.25, band_gain_db=(0, 0, -2)), P(width, amount=1.25)], gain_db=8)
s.bus("vox", VOX, process=[P(ott, depth=0.12, lo=200, hi=3500, band_gain_db=(0, 0, -2))], gain_db=7)
s.sidechain("music", source="kick", amount_db=6, release_ms=95)
s.sidechain("vox", source="kick", amount_db=2.5, release_ms=80)
s.sidechain("imogen", source="kick", amount_db=6, release_ms=120)
# verses filtered, choruses open (per song): lowpass ramps on the melodic stems
s.tracks["cassie_other"].mod("lp", Ramp([(32, 1200), (64, 3000), (96, 14000), (160, 14000)]))
s.tracks["ciara_other"].mod("lp", Ramp([(160, 2500), (192, 5000), (224, 15000), (288, 15000)]))
s.tracks["pony_other"].mod("lp", LFO(rate_beats=16, lo=1800, hi=12000, shape="sine", phase=0.0))    # the riff breathes every 4 bars
s.tracks["bey_other"].mod("lp", Ramp([(480, 4000), (496, 16000)]))
# chopped sections: the melodic stem gets a tempo-synced filter wobble whose rate speeds up
for name, b0 in (("cassie_other", 32), ("ciara_other", 64), ("pony_other", 112)):
    s.tracks[name].mod("gain", Ramp([(b0 * 4 - 0.01, 0.0), (b0 * 4, -3.0), ((b0 + 8) * 4, -3.0), ((b0 + 8) * 4 + 0.01, 0.0)], mode="step"))
# delay throws: last half-bar of every 4th bar on each lead vocal; long reverb throw on the last word before each flip
THROW = Steps([0] * 30 + [1, 1], step="8")
for v in VOX:
    s.tracks[v].mod("send:echo", THROW)
    s.tracks[v].send("verb", 0.10)
    s.tracks[v].mod("pan", LFO(rate_beats=32, lo=-0.12, hi=0.12, shape="sine"))
shout.send("echo", 0.25)
# drums-only flips get tape stops / pitch drops on the outgoing music
s.tracks["cassie_other"].process(P(tape_stop, start_s=s.t(39, 3) * SPB, length_s=SPB, resume_s=s.t(40, 0) * SPB))
s.tracks["ciara_other"].process(P(pitch_drop, at_s=s.t(71, 2) * SPB, semis=-12, length_s=SPB * 2))
s.tracks["pony_other"].process(P(tape_stop, start_s=s.t(119, 3) * SPB, length_s=SPB, resume_s=s.t(120, 0) * SPB))
s.tracks["bey_other"].process(P(tape_stop, start_s=s.t(137, 2) * SPB, length_s=SPB * 2, resume_s=s.t(140, 0) * SPB))

# flips: riser + roll + reverse crash + impact into each section
for b, imp in ((8, "sfx/percs/impacts/boom"), (24, "sfx/percs/impacts/bomb_kick_2"), (40, "sfx/percs/impacts/boom"), (56, "sfx/percs/impacts/bomb_kick_2"),
               (88, "sfx/percs/impacts/boom"), (104, "sfx/percs/impacts/bomb_kick_2"), (120, "sfx/percs/impacts/boom")):
    flip(s, b, KICK, riser_bars=2 if b in (8, 40, 88, 120) else 1, impact=imp)
fx = s.track("fx", gain=-7)
for b in (15, 31, 47, 63, 95, 111, 127):
    fx.hit("sfx/percs/fills/reload", bar=b, beat=3.5)
fx.hit("sfx/percs/impacts/purge_siren", bar=86, beat=0, gain=-5, pitch=-3)
fx.hit("sfx/percs/whips/id_whip_crack_fx", bar=72, beat=0, gain=-2)
fx.send("verb", 0.3)
s.track("riser", gain=-15)

# MACRO-DYNAMICS: verses sit under choruses; chopped sections in between. (beat, dB) steps per section.
def levels(verse, pre, chorus, chopped):
    pts = []
    for b0 in (8, 40, 88):   # A, B, C: verse / pre / chorus / chopped, 8 bars each
        pts += [(b0 * 4, verse), ((b0 + 8) * 4, pre), ((b0 + 16) * 4, chorus), ((b0 + 24) * 4, chopped)]
    pts += [(120 * 4, pre), (128 * 4, chorus), (136 * 4, verse)]
    return Ramp(sorted([(0, 0.0)] + pts), mode="step")


for t in ("kick", "clap"):
    s.tracks[t].mod("gain", levels(-4.0, -2.5, 0.0, -1.5))
for t in MUSIC:
    s.tracks[t].mod("gain", levels(-3.0, -1.5, 0.0, -2.0))
for t in VOX:
    s.tracks[t].mod("gain", levels(-1.5, -1.0, 0.0, -1.0))

s.master(fx=[pb.HighpassFilter(28), pb.HighShelfFilter(cutoff_frequency_hz=11000, gain_db=1.0)], gain_db=-3.0, limiter_db=-1.0)

if __name__ == "__main__":
    print(s.render("demos/out/jersey03", stems=True))
