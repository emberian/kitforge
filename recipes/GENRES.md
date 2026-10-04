# Genre recipes

Step strings are 16ths unless noted (`x` hit, `X` accent, `.` rest, `|` bar line ignored). 0-based bars/beats.
Each recipe: tempo · drum grammar · how vocals are used · signature moves · arrangement skeleton · what this
pack (twerknation28) gives you for it · pitfalls. Treat these as priors, not rules: the interesting tracks
violate one constraint on purpose.

---

## Jersey club — 130–145 bpm (home: 135–140, "sweet spot ~137")
*Researched 2026-10-04 (producer forums, NI/plugg-supply guides, scene Twitter); primitives in `kitforge/idioms.py`.*
- **Kick — the 5-count:** `x...x...x..x..x.` = 16ths **0, 4, 8, 11, 14** ("K---K---K--K--K": two quarter
  notes, two dotted eighths, an eighth). The late 14th step is the forward pull. Variants: 2-bar phrasing with a
  pickup `…x..x.x.x` in bar 2; "the bounce" `x...x...x.x.x.x.`. The tresillo-first `x..x..x...x.x...` (0,3,6,10,12)
  is **Baltimore** grammar — jersey01.py used it; it works, but it is not the Jersey signature.
  Program it mechanically: equal velocity, no swing, no humanize. Layer sub + mid + click; "a hint of reverb".
  `idioms.jersey_kick(song, sample)` does all of this.
- **Claps:** 2 and 4 (`....x.......x...`), optional ghost before the 4 (`....x.....7.x...`). No snare drum.
- **Bed squeak:** rhythmic SFX *between* the kicks, never on them (`..x...x...x..x..`); offset so the two do not
  mask. "Don't abuse the squeak and the water drip" — one per 4 steps is taste, every 8th is Philly.
- **808 / bass follows the kick** rhythm on the root, slides to new roots every 4–8 bars (F2→G#2→G2-style).
  `idioms.bass_follows_kick`. HP the kick (~30–40 Hz) if the 808 owns the sub, or the reverse.
- **Vocals are the lead instrument — rhythm made of voice.** The canon: *chop on a single note, then pitch
  the chop* to build melodies and chords (root / 5th / 10th); ±7 st harmonizes, ±12 for octave stacks
  ("layer the low octave with the original and a high-pitched version" — `idioms.vocal_stack`);
  `idioms.chop_melody` transposes from the manifest's detected pitch so the chop really sings the notes.
  Stutters: filtered delay (~1 kHz, 1–2 repeats, `idioms.stutter_delay`) or manual duplicates with falling
  velocity (`idioms.velocity_stutter`) — the scene prefers the manual one for control. One syllable repeated
  4–8 times on the 16th grid is the signature. Hooks are 1–2 words on the kick rhythm; chants (`hey`, `ayy`,
  "what") answer them. Jersey = vocal cut-ups; Bmore = chants.
- **Transitions:** quick pitch drops (`idioms.pitch_drop`), quick pitch-envelope risers (`idioms.PitchRiser`),
  glitchy stutters, reversed crash into the 1 (`idioms.reverse_crash`), reloads/gunshots on the "a" of 4,
  sirens on the last bar. `idioms.flip` bundles a section switch.
- **Arrangement:** loop-first. Build the 8-bar loop, then add/drop at 8-bar boundaries: 8 intro (kick + squeak or
  vocal only) → 8 full → 8 strip (vocals or bass out) → 8 full reload → wind-down. 16-bar DJ intro/outro for tools.
- **Mix:** kick needs physical weight and a click; squeak sits mid-high; chops bright and loud; light sidechain
  of 808 to kick; do not over-compress — the stutter energy *is* the dynamics. Clipped kicks are a feature.
- **Pack picks:** `id_night_club_808` (+4 st) or `kick031_2`, `snap_02` click, `bed_squeak_*`, `2018_clap`+`snap_01`,
  `back_it_up_2`, `bring_it_back_2_2`, `we_in_jersey_right_now`, `id_famous_hey_chant`, `hey_2`, `3_2_1_lets_go`,
  `reload`, `purge_siren`, `ahhh`/`oh_oh`/`ai` as single-note chop material, `everybody_loop_138bpm`.

## Internet Jersey / hyperflip / dariacore — 140–160 bpm (the twerknation28 house style)
Who: **Twerknation28 is a SoundCloud collective/channel (@TN28EXCLUSIVE)** at the centre of the 2021–23 online
Jersey wave — host of Jane Remover's *leroy* "Obsessed Post-Frailty Extended Jersey Mix" (2022), Lyrical Lemonade
"Get Refreshed" Jan 2022, a 166-track archive; `elxnce` (whose 100 bpm preview is in this pack) posts there.
Scene verdicts: "twerknation28 ruined a whole generation of jersey prods" (i.e. everyone copied it);
"Twerknation28 and hyperflip from 2022 still sounds like the future"; dariacore = "Rustie + SOPHIE with an
aggressively Gen Z twist", "sample collage", "crushed up drops". The pack's contents (pop/anime/meme rips, lo-fi
mp3s, Fred again.. and Future acapellas, Pac-Man, Dragon Ball) are exactly this scene's raw material.
- **Foundation:** the Jersey 5-count kick and squeak, but at 145–160 and *louder*: clipped kicks, crushed
  drop bus (`idioms.crush`), master pushed to -6..-8 LUFS.
- **Collage:** a new recognizable sample every 2–8 bars; nightcore-pitched vocals (`idioms.nightcore(+4..+7)`,
  resample mode so they speed up too); sung hooks re-pitched to the key; meme SFX as percussion
  (`pac_man_sound`, `dragon_ballz_sample`, `synplant_ui_glitch`, `swish_buzzer`, `jacksepticeye_high_five`).
- **Harmony:** future-bass supersaw chords (`Supersaw`, Surge "Pads/…", "Polysynths/…") sidechained hard to the
  kick (`sidechain(amount_db=9..12, release_ms=90)`), 7th/9th voicings, often major-key pop progressions under
  the aggressive drums. Vocal-chop melodies via `chop_melody` doubled by a pluck.
- **Flips:** every 8 bars something breaks: `idioms.flip` (riser + roll + reverse crash + impact), `pitch_drop`
  on the outgoing bus, `tape_stop`, half-time bar, a bar of silence then the sample alone, `velocity_stutter`
  accelerating into the 1 (`stutter(accel=0.8)`).
- **Texture:** `bitcrush(bits=8..10)` on a chop bus, `telephone` on a verse sample, `vinyl` for an intro, mp3
  sizzle left in on purpose; `stutter_delay` echoes on chants.
- **Jokes:** a spoken sample answering the hook (`pause`, `wait_a_min`, `calll_securityy`, `hiei_audio_msg`),
  the count-in that never drops, the Wii-Sports-style voice line.
- **Pitfalls:** maximalism without holes is mud — keep the Jersey space between kicks; keep one element the
  listener can follow across flips (usually the vocal hook or the chord loop).

## Philly club — 140–150 bpm
Jersey's faster, nastier sibling. Same 5-kick grammar but **more kicks** (`x..x..x.x.x.x.x.`), double-time
squeaks, heavy clipping on the kick (`elephant_kick_clipped`, `global_kick_3_2` at -8 dB), constant reloads and
gun foley (`galil_boltpull`, `m3_pump`), vocals chopped to syllables and pitch-laddered. Explicit vocals are the
norm here. Arrangement is shorter and more abrupt: 4-bar switches.

## Baltimore club — 125–135 bpm
- **Kick:** tresillo-first `x..x..x...x.x...` (0,3,6,10,12) and variants `x..x..x.x.x.x...`; 2-bar phrasing common.
  Compare Jersey's `x...x...x..x..x.` — Jersey front-loads straight quarters, Bmore front-loads the tresillo.
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
