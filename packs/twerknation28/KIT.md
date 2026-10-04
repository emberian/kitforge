# twerknation28 — the kit

**Source:** `@twerknation28 2023 sample pack` (287 audio files, 209 MB). **Twerknation28 is a SoundCloud collective /
channel at the centre of the 2021–23 "internet Jersey" (hyperflip / dariacore) wave** — see `recipes/GENRES.md`
→ *Internet Jersey*. This is a working folder from that scene, not a curated library: loose vocal rips, clipped 808 kicks, bed squeaks, reloads, whip cracks,
scratch fills, sirens. Everything normalized to 44.1k float32 stereo in `norm/`; features in `manifest.json`
(`MANIFEST.md` for reading, `sheets/*.png` for looking).

Read this file, then `MANIFEST.md`, then compose with `kitforge.render` (see `../../README.md`).

## The hypervector — what this pack forces on you

Every pack is a bundle of constraints. These are twerknation28's:

1. **No melodic instruments. At all.** Zero synths, chords, pads, bass loops, melodies. Every pitched element
   must come from (a) `kitforge.synth` / Surge XT, or (b) vocal pitches (many one-shots have a clear note, see
   catalog). This is the defining constraint: the pack is *rhythm + voice + impact*.
2. **No snares, no hats to speak of.** Percussion = claps/snaps (`2018_clap`, `snap_01..04`, `woop_clap`,
   `lex_clap`), one hat loop (`opera_hihat_loop_140bpm`, 4 bars, very bright 10-16k), a triangle hat, a 1-bar
   `hat_break`. A real snare must be built (clap + snap + `stomptom` layer) or synthesized (noise burst).
3. **Every kick is an 808 boomer.** 11 kicks, all 0.45–1.15 s, sub fundamentals **A#0–F1 (29–44 Hz)**, most
   clipped on purpose (1–30 % of samples at full scale), attacks 20–60 ms. None is a tight techno/house kick.
   Consequences: **truncate** (`dur_beats≈0.4–0.5` with a 20–30 ms fade) or they drone through 3-step gaps;
   **retune** (+3..+7 st via resample mode) for 50–65 Hz punch; **layer** a click (`snap_02`, `pop002`,
   `sound_29`) for small speakers; a highpass at 28–30 Hz on the master is always right.
4. **Vocals are 60 % of the pack (174 files) and they are hype, not song.** Shouts, counts, commands, chants,
   ad-libs, a few bars of rap, several full acapellas. The register is Jersey/Philly/Baltimore club: *back it
   up, bring it back, drop it, hands up, hey, ayy, woo, 3-2-1 let's go, we in Jersey right now*. Many are
   **sexually explicit** (`ass_*`, `big_ol_butt`, `hit_dat_ass_from_the_back`, `this_pussy_*`, `dontstoppopthatpussy`,
   `i_just_wanna_fuck`, `tut_my_booty`, `these_nutz_*`) and some reference guns (`i_tote_guns`, `take_your_gun`,
   `chrome_to_ya_dome`, `bodybag`) — that is the genre; choose with intent, know what you are putting in a
   track, and keep clean alternatives in mind when the brief is not club.
5. **Fidelity is mixed and that is texture.** 53 files are mp3/aac/wma, a few are 22 kHz or 24 kHz sources
   (`hiei_audio_msg`, `m3_pump`, `galil_2`, `usp1`, `hilfiger_explosive_beep`). Lowpass at 9–11 kHz hides
   codec sizzle; or embrace it (`tricks.bitcrush`, `tricks.telephone`, `tricks.vinyl`). Several vocals have
   leading silence (`active_start` in manifest; `lead-in` note in MANIFEST) — the renderer does **not** trim
   automatically; use `start=` or accept the delay.
6. **Tempo centre of gravity is 134–140 bpm** (the Jersey club window) with outliers that are gifts:
   100 bpm (`love_and_affection_100bpm` — a full 44-bar NOLA-bounce-style preview, key Dm),
   112 (`dope_yo_shyt`, `weed_guaranteed`, `dont_get_it_twisted`), 125–129 (`my_back_vocals`, `future_move_that_dope`,
   `like_a_new_jack`), 150–160 (`tajdrums_isolated_150`, `shake_it_down_loop_160`, `dreams_loop_160bpm`,
   `birthdaaayyg_156`), 185–194 (`drop_it_down_loop_185bpm`, `oh_up_to_the_loop_185bpm`, `elephant_man_dialtone_194`,
   `wishyouwell_188`). Half/double-time relationships make 70↔140, 80↔160, 92↔185 cheap.
7. **Keys exist only in the longer vocal/perc loops** (manifest `keyest`, trust only `conf > 0.08`):
   Fm (`a_bay_bay_vox_loop_140`, `i_can_tell_youre_lookin_at_me`, `jc_perc_06`), Gm (`push_it`, `music_make_you_loop`,
   `birthdaaayyg`), Em (`fred_again_part_1`, `get_down_on_the_ground`, `these_nutz`), Am (`hazard_go`, `rocking_sample`,
   `weed_guaranteed`, `dope_yo_shyt`), Dm (`love_and_affection`, `damage_reload_loop`, `reese_back_it_up_loop`),
   Cm (`b_goodie_whip_loop`, `tick_tock`, `ntell_jordan`). One-shot vocal notes are listed per file; use them as
   pitch anchors or `tricks.pitch_ladder` them into melodies.
8. **Stereo is mostly fake.** 70 % of files are dual-mono. Width must be made: pan the squeaks, Haas the
   chants, `Pad`/`Supersaw` from `kitforge.synth` are wide by design.

## Category guide (what to reach for)

### kicks (11) — tuned, long, clipped
| id | sub | note | character |
|---|---|---|---|
| `id_night_club_808` | 41.7 Hz | E1 | the workhorse; clean sine-ish, 56 ms attack — retune +4 for Jersey |
| `kick031_2` | 39.7 Hz | D#1 | most mid energy (bands 0/-6/-17): reads as *kick* not *808* — best for techno/house/UKG |
| `vybe_kick_1_1_part_1` | 39 Hz | D#1 | fast attack, 11 dB bass band: punchy |
| `global_kick_3_2` | 43.7 Hz | F1 | peaks at **+7 dBFS** (float source) and 30 % clipped — a weapon, gain -8 |
| `808_15` | 31.6 Hz | B0/C1 | lowest; pure sub tail — layer under another kick |
| `henry_kick` | 28.9 Hz | A#0 | sub-only, almost inaudible on laptops |
| `elephant_kick_2` / `elephant_kick_clipped` | 34–35 Hz | C#1 | 21 % / 7.5 % clipped, 0.6–1.2 s: the Philly "distorted 808" sound |
| `mingo_idk_808_2` | 33 Hz | C1 | 1.15 s, +3 dBFS peak — an 808 *note* more than a kick; glide material |
| `ace_bass_kick_908_boom_kick_2` | 40.4 Hz | E1 | two-layer (908 click + boom) |
| `bass_h_1_1` | 37.7 Hz | D1 | bass note, 5.7 % clipped |

Tuning rule: pick the kick whose sub note is the song's root or fifth, or retune by resample (`pitch=` semitones,
which also shortens it — usually welcome).

### vocals (146 one-shots/phrases) — by function
- **Counts / starters:** `3_2_1_lets_go` (C4), `are_you_ready`, `pump_up_the`, `get_it`, `go`, `up`
- **"Back" family (the Jersey hook word):** `back`, `back_2`, `back_drake`, `back_it_up_2` (C5), `backback`,
  `back_to_the_back`, `bring_it_back_2_2`, `from_the_back_loop_010_014`, `hit_dat_ass_from_the_back`,
  `childish_gambino_v_3005_part_1_back` (B2, 0.21 s — a perfect stutter atom)
- **Drop / floor:** `drop_it`, `drop_it2` (C#3), `drop_it_down_sample`, `drop_sample`, `drop_to_the_floor_bounce_copy`,
  `get_down_on_the_ground_5` (12 s, Em, 82 bpm), `deep_down_low` (G2)
- **Hey / ayy / woo chants:** `hey`, `hey_2` (E4), `id_famous_hey_chant` (E5, Dm), `id_aye_chant`, `ay_sso`,
  `lil_jon_ayy_2`, `ga_go_lil_jon`, `woooo_male`, `oow`, `eh_eh` (A5), `hu_chant_13`, `spanish_heyyyy_2`,
  `russian_yell`, `yo_sample` (G5), `yea`, `yep_2`
- **Ahhs / sustained (pitch material):** `ahhh` (C3, 0.93 s), `ahhh_2k10` (D4), `ahhhoo` (E5), `haaaah_2`,
  `haaaah_part_1`, `ai` (G#3), `oh_oh` (F4), `radioo` (A2)
- **Dance commands:** `werk`, `work_loop`, `left_right`, `woo_left_and_right`, `hands_3`, `shake_that`,
  `bounce` / `bounce_2` / `bounce_tone` / `50_bounce` / `keke_bounce` / `b_goodie_px_bounce_sample`,
  `first_u_gotta_put_yo_neck_into_it` / `neck_into_it_2`, `lemme_see_you_hit_that_footwork_like`,
  `move_ur_body_jump`, `let_that_girl_loose`, `switch_it_up`, `tang_it`, `do_it_3`, `bop_it_sample_2`
- **Attitude / talk:** `wait_a_min`, `pause`, `stop`, `backoff_buster`, `cuff_yo_chick`, `my_shit_was`,
  `dont_get_it_twisted_1`, `calll_securityy`, `bestfriend_she_finna` / `bestfriend_you_bettah`, `big_girls_001`,
  `i_like_how_she`, `like_a_new_jack`, `sound_familiar` (16 s, F#)
- **Regional ID:** `we_in_jersey_right_now` (C4, Cm), `steeztheproducer_x_yeaa_hoe_cypher_jerseyclub`, `jc_vox_11/49`
- **Long rap/acapella phrases (chop or feature):** `dat_apple` (124 s!), `dope_yo_shyt` (23 s, Am, 112), `bxtches` (21 s),
  `tut_my_booty` (19 s), `birthdaaayyg_lighhh_vocals_156` (17 s, Gm), `emani` (10 s, G#m), `hiei_audio_msg` (12 s
  voice memo, lo-fi), `anais_vocals` (5.6 s), `ayeeeeee_loop` (15 s)
- **Pop-culture rips:** `dragon_ballz_sample`, `pac_man_sound` (A4, Am), `kick_the_baby_sample`, `fred_again_*`,
  `future_move_that_dope_*`, `juicy_j_yeah_hoe_2`, `childish_gambino_*`, `ntell_jordan_this_is_how_we_do_it`
  (C4, Cm, 139 bpm — "This Is How We Do It" hook)
- **Weird atoms (glitch/texture):** `f`, `tetete_damn`, `raspberry`, `weird_hit`, `eh_rip`, `vm_clubeyvox_2`,
  `tiktok_*_split_by_lalalai` (G2), `illsquad14_s_119th_mix`, `dj_r_l_crowd_motivator_09`

### vocals/vocal_loops (28) — bar-locked, stretchable
Best loop material (bpm/bars/key): `a_bay_bay_vox_loop_140bpm` 140/16, `a_bay_bay_vox_loop_2_136bpm` 136/4 (D),
`drop_vocals_139bpm_2` 139/8, `styles_hey_baby_loop_140` 140/8, `deepdownlow_loop_140` 140/19 (odd length — chop),
`push_it` 134/3 (Gm), `do_it_loop` 134/3, `shake_it_down_loop_160` 160/4, `drop_it_down_loop_185bpm` 185/4,
`oh_up_to_the_loop_185bpm` 185/4, `music_make_you_loop` 152/8 (Gm), `bestfriend_loop` 153/2, `my_back_vocals` 125/7,
`hazard_go_loop` 80/1 (Am), `rock_it_ft_jdub` 80/4, `future_move_that_dope_part_1` 129/2 (G#m, acapella),
`fred_again_part_1` 64/4 (Em, pitched vocal — the only *sung* thing here), `i_can_tell_youre_lookin_at_me` 70/8 (Fm, sung).
Three long songs for mashup fodder: `twerk_hands_up_high` (83 s, 152, A#m), `yea_2` (73 s, 105), `baby_part_1` (21 s, Bm).

### sfx/perc_loops (25) — the only drums besides kicks
`opera_hihat_loop_140bpm` (hats, 4 bars), `everybody_loop_138bpm` (full club drum+vox loop, 8 bars),
`bite_into_loop_137bpm` (8 bars, C), `bubble_break` 134/8, `tajdrums_isolated_150` (2 bars, drum break — stretch to 140–170),
`hat_break_break` 126/1, `dreams_loop_160bpm` 160/8 (C), `best_i_ever_had_loop_155bpm` 155/8 (G), `wishyouwell_loop_188bpm` 188/8 (F),
`elephant_man_dialtone_loop_194bpm` 194/8, `tick_tock` 120/2 (Cm, clock — half-time it), `butt_clap_2` 68/2 (claps),
`damage_reload_loop` 139/3 (Dm), `march` (snare march, 68), scratch loops `hilfiger_syko_scratch_*` (76 and 129),
`b_goodie_whip_loop` 90/4 (Cm), `bomb_synth` (28 s texture, 70), `crack` (38 s, 187, C#m), `aye_aye_loop` (26 s, 76).

### sfx/percs (26), fills (23), impacts (21), whips (6)
- **Claps/snaps:** `2018_clap` (0.10 s, tight), `woop_clap`, `lex_clap`, `snap_01` (B6 ring), `snap_02` (0.17 s, driest),
  `snap_03`, `snap_04`, `id_finger_snap_perc`, `tellz_e_finger_snap_2` (2 s with tail)
- **Bells/ticks:** `indian_bell` (G#6), `louis_bell` (G#6), `triangle_hat` (E4), `c4_tick_tick`, `chimes_chimes` (14 s, 140),
  `japanese` (2.6 s, F#), `pop002`, `sound_29` (80 ms click), `bubbles`
- **Bed squeaks (the Jersey signature):** `fills/bed_squeak_loop_big_o_11` (A#6, 0.16 s) and `_12` — put them on
  the "e"/"a" 16ths or double the kick pattern; hp 400; they peak at 10–12 kHz so they also act as hats
- **Reloads / gun foley:** `reload`, `reload_2`, `lituation_reload`, `galil_boltpull`, `m3_pump`, `usp1`, `galil_2`,
  `hydrolic_sample_2`, `lituation_pt_2_1_part_*`
- **Scratches:** `dj_puzzle_scratch_10` (1 bar, 185), `scratch001/4/_3/_007`, `syko_scratch`, `rock_it_scratch`, `id_scratch_perc`
- **Impacts / drops:** `purge_siren` (3.8 s, sub F1 — a riser-siren), `thunder`, `thunder_effect` (7 s), `boom`,
  `bomb_160` (2.9 s), `bomb_kick_2`, `bass_w` (2 bar sub swell), `bass_d_town_1`, `ab_pre_drop_49`, `zoom_drops_part_1`
  (1 bar, 187), `rocking_sample_echo`, `wave_out_kick_edit`, `waka_kick_edited`, `bleechers_kick`, `stomptom`, `fx_21`
- **Whips:** `id_whip_crack_fx` (clean), `gangsigns_whip`, `jacksepticeye_high_five` (comedy slap), `oh_no_lab_stem_part_6`
- **Glitch:** `synplant_ui_glitch_part_83`, `swish_buzzer`, `errt`, `ls_fx_25`, `shop_fx_new_18`, `hilfiger_explosive_beep`

## Lessons from the first renders (`demos/jersey01.py`, `demos/jersey02.py`)
- jersey01 used the *Baltimore* kick grammar (0,3,6,10,12). The Jersey 5-count is 0,4,8,11,14 (`idioms.JERSEY_KICK`).
- Render 1: kick `id_night_club_808` untruncated on the 5-kick pattern = **+27 dB at 40 Hz vs pink**, flat bar
  energy, nothing else audible. Truncating to 0.45 beats, retuning +4 st and hp 28 on master fixed it
  (+17 dB at 50 Hz, arrangement range 6 dB). *Check `stems_report` before blaming the mix.*
- pedalboard's `Limiter` adds makeup gain and clips at 0 dBFS (it is a drive, not a ceiling). The renderer now uses its
  own 4x-oversampled lookahead limiter (`render.true_peak_limit`); `master(limiter_db=-1)` is a real ceiling and the
  console prints the max gain reduction — keep it under ~6 dB unless you want the crushed sound on purpose.
- Surge patches differ wildly in level (`Basses/Bass 1` needed `gain_db=+10`); always read the stem LUFS line.
- Onset "late bias" of ~8–12 ms is the kicks' slow attack, not a timing bug. Shift kicks earlier by
  `time -= 0.01*bpm/60` beats if a track needs to snap, or layer a click.
- Vocal one-shots sit ~10 dB below the kick at equal track gain; the hook wants `gain=+3..+6` and a compressor.
- A sidechained track gets *louder* when its source stops (breakdowns): intended, but plan levels for it.
- `Track.chop(onset=True)` slices from `active_start` (lead-in silence skipped) using all detected onsets; pick `n`
  or `onset=False` for equal slices. Check the loop's onset count in the manifest before writing a slice pattern.
- Numpy synths (`Supersaw`, `Pad`) and Surge patches come out 10–20 dB quieter than samples: expect `gain=+3..+14`.
- Read `*.arrangement.png` (stems × bars) before the spectrogram: it answers "which stem is holding this bar up".
- Footwork agent (2026-10-04): `shake_it_down_loop_160`, `werk` (-12 st still clean), `childish_gambino_*_back`,
  `2018_clap`, `kick031_2` hp 60 all shone; `snap_02` as a hat needs ~+16 dB; `purge_siren` gets lost under drums.

## Mix targets that worked here
Kick stem -8..-10 LUFS, hook vocal -14..-17, claps -15, bass -18..-22, squeak/hats -19..-27, fx -20.
Master: hp 28 Hz, limiter -1.5, true peak -1 → about -10 LUFS-I for a demo (push `master(gain_db=+3)` for club loud).
