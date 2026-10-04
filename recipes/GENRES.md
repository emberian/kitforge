# Genre recipes

Step strings are 16ths unless noted (`x` hit, `X` accent, `.` rest, `|` bar line ignored). 0-based bars/beats.
Each recipe: tempo · drum grammar · how vocals are used · signature moves · arrangement skeleton · what this
pack (twerknation28) gives you for it · pitfalls. Treat these as priors, not rules: the interesting tracks
violate one constraint on purpose.

---

## Jersey club — 130–145 bpm (home: 135–140)
- **Kick:** `x..x..x...x.x...` (steps 0,3,6,10,12: "1, a-of-1, &-of-2, &-of-3, 4"). Variants: drop step 12
  on alternate bars; `x..x..x.x.x.x...` ("the bounce"); 2-bar phrasing with the second bar ending in a roll.
- **Rolls/fills:** triplet kick rolls `tricks.roll(step="16t")` into section changes; 32nd stutters of the
  vocal with `accel=0.85` (`tricks.stutter`).
- **Bed squeak:** on the "e" or "a" 16ths (`..x...x...x...x.` or `.x...x...x...x..`) or mirroring the kick an
  octave up. One squeak per 4 steps is restraint; two is Philly.
- **Claps:** 2 and 4 (`....x.......x...`), often layered clap+snap. No snare drum.
- **Hats:** sparse; the `opera_hihat_loop` or 8th-note snaps. Many Jersey tracks have *no* hats.
- **Vocals:** a 1–2 word chop repeated *on the kick rhythm* is the hook ("back it up" → `x..x..x.`), pitched up
  +2..+4 in later sections, call-and-response with chants (`hey`, `ayy`), count-ins before drops, "we in Jersey".
- **FX:** reloads on the "a" of 4 before a drop, whip cracks, sirens on the last bar of a build.
- **Arrangement (DJ friendly):** 8 bars vocal/sample intro → 8 kick+hook → 8 full → 4–8 break (kick out, vocal
  stutter build) → 16 full → 8 outro drums-only. 16-bar phrases; changes every 8.
- **Pack picks:** `id_night_club_808` (+4 st), `bed_squeak_*`, `2018_clap`+`snap_02`, `back_it_up_2`, `bring_it_back_2_2`,
  `we_in_jersey_right_now`, `id_famous_hey_chant`, `3_2_1_lets_go`, `reload`, `purge_siren`, `everybody_loop_138bpm`.
- **Pitfalls:** untruncated 808 kicks drone; the pattern's 3-step gaps are the groove — do not fill them.

## Philly club — 140–150 bpm
Jersey's faster, nastier sibling. Same 5-kick grammar but **more kicks** (`x..x..x.x.x.x.x.`), double-time
squeaks, heavy clipping on the kick (`elephant_kick_clipped`, `global_kick_3_2` at -8 dB), constant reloads and
gun foley (`galil_boltpull`, `m3_pump`), vocals chopped to syllables and pitch-laddered. Explicit vocals are the
norm here. Arrangement is shorter and more abrupt: 4-bar switches.

## Baltimore club — 125–135 bpm
- **Kick:** tresillo base `x..x..x.` + straight backbeat; common 2-bar: `x..x..x.x.x.x... | x..x..x.x...x.x.`.
- **Breaks:** the "Think" and "Sing Sing" breaks under everything (NOT in this pack — the only break here is
  `tajdrums_isolated_150` stretched down and `hat_break_break`; or build one from `2018_clap`/`stomptom`/`snap_02`).
- **Vocals:** chanted hooks repeated for 8–16 bars without variation; crowd shouts; call-and-response with a
  horn-stab replacement (use `FMPluck` or a Surge brass).
- **Pack picks:** `kick031_2`, `woop_clap`, `hu_chant_13`, `hands_3`, `pump_up_the`, `get_it`, `shake_that` (103 bpm → stretch).

## Footwork / juke — 155–165 bpm (home: 160)
- **Kick (808 toms):** polymetric; e.g. `x..x..x..x..x..x` (every 3 steps, rolls over the bar) against claps on
  2 and 4; triplet 16t tom rolls with pitch (`Synth808` glides, or `mingo_idk_808_2` re-pitched per hit).
- **Vocal:** ONE word or phrase repeated in a *different* polymeter than the kick (every 5 or 7 steps); stutter it
  into 32nds; pitch down an octave for the "ghetto" voice; leave holes — silence on the downbeat is the style.
- **Hats:** straight 8ths or 16ths, quiet; snare/clap sometimes displaced by a 16th.
- **Arrangement:** loop-based, 4-bar cells, sudden mutes, very long repetition then a flip.
- **Pack picks:** `shake_it_down_loop_160` (native 160!), `dreams_loop_160bpm`, `tajdrums_isolated_150`, `808_15`,
  `werk`, `drop_it2`, `childish_gambino_*_back` (0.21 s atom), `lemme_see_you_hit_that_footwork_like` (literally).
- **Pitfalls:** with 808 toms *and* a kick the sub band saturates; give the toms the sub (30–60) and hp the kick at 60.

## New Orleans bounce — 95–105 bpm (home: 100)
- **Beat:** "Triggerman"/"Brown Beat" lineage: busy 16th hats with open-hat offbeats, snare/clap on 2 and 4 with
  flams, kick `x..x..x...x.....`-ish syncopation, cowbell/bell ostinato (`indian_bell`, `louis_bell` on
  `x.x.xx.x.x.xx.x.`).
- **Vocals:** call-and-response chants, rapid-fire repetition, "bounce"/"shake"/"wobble" commands, a female
  "ha!"/"ay!" every bar. Take a long rap phrase and chop it into 1-beat cells, re-order.
- **Pack picks:** `love_and_affection_100bpm` (full 100 bpm track in Dm — chop or play underneath),
  `yea_2` (105), `bounce`, `bounce_2`, `50_bounce`, `keke_bounce`, `shake_that` (103), `yashae_ladies_booty_bounce_to_this`,
  `drop_to_the_floor_bounce_copy`, `butt_clap_2` (68 → halve to 136 or treat as 2 bars at 100), `hazard_go_loop` (80).
- **Pitfalls:** 100 bpm with 808 subs sounds like trap unless the hats are busy and swung (`swing=56`).

## Ballroom / vogue beats — 120–130 bpm
- **Beat:** four-on-the-floor or tresillo kicks, and **the crash on beat 4** (the "Ha" — use `id_whip_crack_fx`
  layered with `2018_clap` and a reverse-reverbed `woop_clap`): `............x...`. Dips land there.
- **Vocals:** commentator energy — "work", "pussy", "cunt", "ten", count-ins; chop to single words, repeat in 8ths.
- **Synth:** stabs on the off-beats (`FMPluck`, Surge "Plucks/…"), a sub on the root.
- **Pack picks:** `this_pussy_will_drive_you_crazy` (140 → 128), `werk`, `3_2_1_lets_go`, `hands_3`, `get_it`,
  `whips/*`, `jacksepticeye_high_five` (comedic slap-crash).

## UK garage / 2-step — 130–138 bpm, swung
- **Swing:** `Song(swing=58..64)`. Non-negotiable.
- **Kick:** `x.....x...x.....` or `x......x..x.....` (skipping, not 4/4); **snare on 2 and 4** (build it:
  `2018_clap` + `snap_03` + `stomptom` hp 150); shuffled 16th hats with the 2nd/4th 16ths ghosted (`x9x9` → use `x3x3`).
- **Vocals:** pitched-up (+3..+6, formant mode) female-style chops and time-stretched phrases; the "ahh"s
  (`ahhh_2k10`, `ahhhoo`, `oh_oh`) as pads via `pitch_ladder`; one-word "oh"/"up" hooks.
- **Bass:** sub with octave jumps (`Synth808` short decay or Surge "Basses/…" with `hp=35`), warm organ chords
  on the off-beats (`Pad` low cutoff, short).
- **Pack picks:** `kick031_2` (-2 st), `my_back_vocals` (125), `future_move_that_dope_part_1` (129, G#m), `oh_oh`, `up`, `ai`.

## Trap / club-trap — 135–150 bpm, half-time feel
- **Grid:** kick on 1 and syncopated 16ths, **snare/clap on 3** (`........x.......`), hats in 16ths with 32nd and
  triplet rolls (`tricks.roll(step="32")`), open hat on the "and" of 4.
- **808:** `Synth808` or `mingo_idk_808_2`, *glides* between root/5th/b7 (`Clip.note(glide_from=)`), long decay,
  sidechained to nothing — the 808 *is* the kick.
- **Vocals:** pitched-down ad-libs (-3..-5), a single chop as melodic hook through delay, chants doubled an octave down.
- **Pack picks:** `elephant_kick_2`, `mingo_idk_808_2`, `snap_01`, `lex_clap`, `i_tote_guns_sample`, `chrome_to_ya_dome`,
  `juicy_j_yeah_hoe_2`, `dope_yo_shyt` (112 → 140 is +25 %: too far; use at 112 half-time = 56/112/224).

## Drum & bass — 170–176 bpm
- **Two-step:** kick 1, snare 2 and 4, kick on the "&" of 3: `x.......x.x.....|x...x...x.x.....` with
  snare `....x.......x...`; ghost snares on the "e"s. Build the snare (clap+snap+stomptom, short room reverb).
- **Bass:** Reese (`Supersaw(voices=3, detune=18, cutoff=600, env_amount=800)`, lp automation) or Surge
  "Basses/…"; sub sine under it.
- **Vocals:** time-stretched phrases (`stretch_to_bpm` from 85–90 bpm halves the pitch-perceived rate), chopped
  "ahh"s with reverse_reverb, diva-style one-shots on the drop (`ahhhoo`, `eh_eh`).
- **Pack picks:** `wishyouwell_loop_188bpm` (-7 %), `elephant_man_dialtone_loop_194bpm`, `drop_it_down_loop_185bpm`,
  `oh_up_to_the_loop_185bpm`, `zoom_drops_part_1`, `tajdrums_isolated_150` (+15 % — borderline), `vybe_kick_1_1_part_1` (+7 st).

## Breakcore / digicore / hyperpop-club — 160–200 bpm
- Everything above, broken: stutters every bar (`stutter(count=16, step="32", accel=0.8, pitch_ramp=12)`), chipmunk
  vocals (`pitch=+7..+12, pitch_mode="resample"`), `bitcrush(bits=6)`, `tape_stop` at section ends, `Supersaw`
  walls sidechained hard (`sidechain(amount_db=12, release_ms=80)`), tempo lies (half-time bar, then double).
- **Pack picks:** every "weird atom", `pac_man_sound`, `dragon_ballz_sample`, `synplant_ui_glitch`, `swish_buzzer`,
  `tetete_damn`, `raspberry`, `f`, plus the 185–194 loops.

## Techno / house — 125–135 / 120–128 bpm
- **Kick:** four-on-the-floor; use `kick031_2` or `vybe_kick` truncated to 0.3 beats, pitched -1..+2, layered
  with `pop002`; hp 40. Offbeat hats (`..x...x...x...x.`) from `snap_02` lowpassed, or synthesize.
- **Vocals as texture:** one phrase through `reverse_reverb` + long delay, `gate`d in 16ths, `vinyl`ed;
  spoken fragments (`hiei_audio_msg`, `calll_securityy`, `pause`, `wait_a_min`) as deadpan hooks.
- **Pack picks:** `tick_tock` (120, Cm), `my_back_vocals` (125), `chimes_chimes`, `bass_w`, `bomb_synth` texture.

## Ghetto house / ghettotech — 130–150 bpm
Four-on-the-floor 808/909 kick, explicit chant repeated with no variation for 16 bars, TR-808 tom fills (`Synth808`
with `decay=0.25`, pitched), claps on 2/4 with a short reverb, nothing else. This pack's vocals were made for it:
`werk`, `switch_it_up`, `tang_it`, `drop_it`, `ass_*`, `big_ol_butt`, `backback`.

## Amapiano — 110–115 bpm
Log drum = `Synth808(decay=0.35, click=0.2, harmonics=0.3, drive_db=4)` playing a syncopated bassline
(`x..x..x...x.x..x` in 8ths-and-16ths across 2 bars), shakers from `snap_02` 16ths at -20 dB, sparse kick on
1 only, piano/pad stabs from Surge "Keys/…", long sung vocals (`fred_again_part_1` Em, `i_can_tell_youre_lookin_at_me`
Fm at 70 → 112 is +60 %; use `pitch_mode="formant"` and chop instead). Patience: 8-bar builds, the log drum enters late.

---

## Cross-genre moves this pack is unusually good at
- **The mashup bridge:** `love_and_affection_100bpm` (Dm) under Jersey kicks at 140 (= 100 × 1.4 — too far to
  stretch; instead play it at 100 and double-time the drums at 200/2 = *bounce at 100 with 140-style kick density*,
  or chop it into 1-beat cells and re-sequence at 140).
- **One syllable → melody:** `tricks.pitch_ladder(track, "vocals/ahhh", bar, 0, semis=[0,3,5,7,5,3,0,-2])` with
  `pitch_mode="formant"` keeps it human; `"resample"` makes it a chipmunk choir.
- **Kick as bass:** `mingo_idk_808_2` and `elephant_kick_clipped` are long enough to be 808 notes; `pitch=` per hit
  gives a bassline (resample mode shortens high notes — correct for 808s).
- **Risers from nothing:** `Riser` (noise), `purge_siren` pitched (`pitch=-5` is a dread drone), `bass_w` reversed
  (`reverse=True`), `thunder_effect` reversed with `swell`.
