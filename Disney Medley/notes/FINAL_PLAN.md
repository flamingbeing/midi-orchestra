# FINAL PLAN: Disney Medley, final render (draft 7)

Paths: S = /tmp/claude-0/-home-user-hi/93e23b1f-ff00-5890-a39f-1bbff28a4ed8/scratchpad, P = S/pipeline.
Input: S/work/draft3_input.mid (= 10_prepared.mid + the user's +5% tempo from Beauty and the Beast to Reflection; keep it).
Base engine: **S/render_v6.py + S/mix_v6.py**, not v4. v6 contains the clarinet octave fix (the draft-5 dealbreaker), cello +3.5 dB at 130-152 s, harp HPF and EQ, and the hall send increase. Port the scout-2 technique switches from P/work/technique/lib.py into a copy of v6. Do not restart from v4.

**Export (the user's standing instruction): Ogg Vorbis, `ffmpeg -i master.wav -c:a libvorbis -q:a 9 out.ogg`.** This replaces the m4a/AAC line in USER_FEEDBACK.md. Every A/B and preview file uses the same setting.

## 1. Lead spot-checks (done by me)

| Claim | Check | Result |
|---|---|---|
| The tonejs harp is a mono, normalised copy of VCSL/VSCO KSHarp mf | F4: tonejs vs VCSL KSHarp_F4_mf1, same length (478363 samples) | Normalised xcorr 0.9993. VCSL is stereo (L/R corr 0.96) with a natural peak of -20.3 dBFS; tonejs peaks at -3.0. **Confirmed.** The swap keeps the timbre the user likes. |
| The synthetic IR has no early structure and uncorrelated channels | P/work/hall_ir.wav | Late L/R corr 0.00, C80 +0.3 dB. **Confirmed.** |
| MARCo IRs are real tree IRs | marco_tree/main_000deg_3m.wav | Late corr 0.49, C80 +11.5 dB, 13 positions present. **Confirmed.** |
| VSCO Snare2 multi-velocity and RR exists | P/sources/git/sgossner_VSCO-2-CE/Percussion | HitSN/HitNS v1..v9 x rr1/rr2 _Sum present. **Confirmed.** |
| Engine state | S/work/v6_render.log | Clarinet 455 notes, 3 layers, pitch 50-90. Celesta is SSO (2 layers). Strings are VSCO susVib 2 layers. Flute, piano, guitar and harp are tonejs. |

## 2. Per-instrument decisions

| Instrument | Final source / blend | Path | Licence | Why | Fallback |
|---|---|---|---|---|---|
| Violins (incl. divisi up to 2) | VSCO-2-CE Violin Section susVib (2 layers), equal-power layer xfade, per-sample loudness levelling. Spiccato for notes < 0.22 s; attack trim 0.35 for sustained notes < 0.6 s. Legato xfade on the top voice only. | P/sources/npm/ghraw/VSCO-2-CE_git/Strings/Violin Section/{susVib,Spic} | CC0 | User said strings are good. Nothing better exists on git (SSO legato is fake, neural is 16 kHz). Technique gains are measured. | v6 bank, unchanged |
| Violas | VSCO Viola Section susvib + spic, same techniques. All-pass decorrelate to ICC about 0.5 (side gain 0.85-1.0). | VSCO-2-CE_git/Strings/Viola Section; P/sources/technique/vsco_spic | CC0 | Same reasons as violins | v6 |
| Cellos | VSCO Cello Section susvib + spic. Keep v6 +3.5 dB automation at 130-152 s and the softer low attack. | same | CC0 | User: cello slightly soft; short cello notes are 21.5 dB low (measured) | v6 |
| Violins/Violas/Cellos Pizz | VSCO pizz/pizzT (2 layers x RR). Layer xfade, true RR alternation, micro-variation. | VSCO-2-CE_git/Strings/*/pizz* | CC0 | Already lossless, only 22 notes in total | v6 |
| Strings Pad (3 held notes) | VSCO susVib sections at a soft layer, CC-swelled, no ducking | as v6 | CC0 | Sustained 3-note pad; v6 is fine | v6 |
| Harp | **VCSL Concert Harp, stereo**: mf1 for vel <= 80, f1 above, equal-power xfade 72-88. Tune +9 c. Keep v6 70 Hz HPF, -3.5 dB @180 Hz, extra hall. Micro-variation RR only (1 RR in the source). | P/sources/git/sgossner_VCSL/Chordophones/Composite Chordophones/Concert Harp | CC0 | Same recording the user liked (xcorr 0.999), plus stereo and a real loud layer. The f layer should help the 03:20 complaint. | tonejs harp (v6) |
| Flute | **Keep tonejs flute** (the user likes its vibrato). Add per-sample levelling (small, SD 0.5 to 0.2 dB), legato xfade past the attack, soxr resampling. | S/samples/dl/tonejs-instrument-flute-wav | MIT | Do not regress a liked sound. SSO Flute 2 is a different player with wider vibrato. | Only if the user picks it in AB_flute.ogg: SSO Flute 2 sus_vb mf/ff with sfz tune= values |
| Clarinet | VSCO susLong 3 layers (v6, octave fix kept). Per-sample loudness levelling, layer xfade, legato xfade past the attack, breath trim 0.35, mf layer for notes >= E5, no saturation, +3 dB @2.2 kHz. Balance target is the flute's +4.5 dB. | VSCO-2-CE_git/Woodwinds/Clarinet/susLong | CC0 | Addresses all clarinet feedback. Biggest loudness-SD gain measured (3.9 to 0.8 dB). | v6 clarinet |
| Celesta | SSO Celeste (2 layers), layer xfade, levelling, RR micro-variation. Target -4 dB, no ducking. | P/sources/npm/ghraw/sso_git/.../Samples/Celeste | CC Sampling+ 1.0 | User only asked for audibility after draft 4; no better celesta found | tonejs xylophone (user's own suggestion in draft 1) |
| Glockenspiel (2 notes) | VCSL Glockenspiel loud/soft layers (avoid the truncated medium layer) | P/sources/git/sgossner_VCSL/Idiophones/Struck Idiophones/Glockenspiel | CC0 | Stereo, more layers; trivial risk | VSCO glock (v6) |
| Piano | **Keep tonejs piano** (user: "piano is nice"). Add true RR micro-variation (no neighbour borrowing) and chord jitter SD <= 6 ms. | S/samples/dl/tonejs-instrument-piano-wav | MIT | Do not regress | v6 |
| Guitar (nylon) | Keep tonejs guitar-nylon as the default, at the v6 level (user asked for it softer). Micro RR only. | S/samples/dl/tonejs-instrument-guitar-nylon-wav | MIT | No reported complaint; FreePats is a different guitar with a noisy recording | FreePats Spanish Classical Guitar (CC0) if the user prefers AB_guitar.ogg B |
| Snare Drum (44 hits, vel 70-81) | **VSCO-2-CE Snare2 HitSN _Sum**, v5/v7 layers by velocity, alternating rr1/rr2 | P/sources/git/sgossner_VSCO-2-CE/Percussion | CC0 | Replaces 2 mono 0.4 s mp3 hits with a 24-bit stereo concert snare | Frankensnare 14x5 maple OH; else v6 |

Rejected: all neural (16 kHz output, noise, pitch errors that break faithfulness), STK, the SSO legato patches, Ixox flute (no sampled vibrato), Salamander piano (not the liked piano).

## 3. Room / IR setup

- **Primary: 3D-MARCo St Paul's Hall** (P/sources/acoustics/final/marco_tree, seats from seating.json). Per stem: `main(seat) + 0.6*amb(seat) + 0.3*dry` with the dry signal panned and delayed by `marco_direct_ms`. Wet/dry by family: strings and pizz at about 0.5 effective, winds 0.4, harp, celesta and glock 0.55 (the user asked for more reverb on the harp), piano 0.45, snare 0.5.
- Licence: **CC BY-NC 3.0**. This is fine for the user's personal render. Credit it in out/CREDITS.txt.
- Trim the master balance for the measured right-heavy lean of about 2.5 dB (target |L-R| <= 1 dB integrated).
- Licence-clean fallback: Detmold Konzerthaus tree/room S1-S8 (CC BY 4.0) + generic/usina_m5.wav as a shared bloom send at -13 dB.
- Retire P/work/hall_ir.wav.

## 4. Techniques, in priority order

1. Per-sample loudness levelling (`level='loudness'`): strings, clarinet, celesta, flute (light).
2. Equal-power velocity-layer crossfade (`layers='xfade'`): strings, pizz, clarinet, celesta, harp, snare.
3. Short-note handling: attack trim 0.35 for sustained notes < 0.6 s; VSCO spiccato for notes < 0.22 s (level -9 dB to start, then calibrate to match the trimmed susVib peak within 2 dB).
4. Legato crossfade past the attack (60 ms sin/cos) on Flute, Clarinet and the Violins top voice.
5. Round robin and micro-variation: true RR where it exists; neighbour borrowing only for celesta, harp and pizz.
6. Section width equalisation: Violins side gain 0.55, others 0.85-1.0, all-pass decorrelation on violas/cellos. No detuned doubling.
7. soxr resampling instead of np.interp.
8. Keep from v2-v6: balance targets, melody ducking up to 3 dB (not celesta), phrase arches, +5% tempo section, onset compensation.
9. Low priority: high shelf for velocities below the lowest layer only; natural release; expression contour (only if it does not raise the clarinet p90 step); chord jitter <= 6 ms (harp, piano).
10. Investigate 04:10 timing (9/8 bar + tempo change; check that onset compensation does not move notes across the tempo boundary).

## 5. Multi-agent build plan

| # | Owner | Input -> output (file contract) | Acceptance |
|---|---|---|---|
| A | **engine-strings** | Port lib.py switches 1-7 into S/render_v7.py (copy of render_v6.py); string, pizz and pad banks; spiccato routing -> S/work/v7_stems/{Violins,Violas,Cellos,*Pizz,Strings Pad}.wav | Float32 44.1k stereo, same length as the MIDI end + tail, sample 0 = MIDI 0. Chromatic loudness SD <= 1.0 dB. Short-note peak within 3 dB of the long notes. ICC: violins 0.4-0.55, violas/cellos <= 0.6. |
| B | **engine-winds-keys** | render_v7.py banks for Flute, Clarinet, Celesta, Harp (VCSL), Piano, Guitar, Glock, Snare (VSCO) -> the same stems dir | Clarinet: no >6 dB adjacent jump in 284-312 s, no saturation, attack to -12 dB < 40 ms. Harp: stereo, f layer used for vel > 80. Flute vibrato unchanged (tonejs). Snare: 44 hits, alternating RR. |
| C | **verifier** (blocking) | v7 stems + draft3_input.mid -> S/work/v7_verify.json | **Every note of every track pitch-checked:** median \|err\| <= 10 c, zero notes > 50 c. Note count per track equals the MIDI. Onsets within 30 ms. No clicks (> -40 dB step discontinuity). meta.json written. |
| D | **mixer** | S/mix_v7.py: v7 stems + seating.json + MARCo IRs -> S/work/v7_master.wav | -16 LUFS +-1; TP <= -1 dBTP; LRA >= 7 LU; \|L-R\| <= 1 dB. Clarinet active loudness within 1 dB of flute (target +4.5 dB offset kept). Melody stem 3-6 dB over accompaniment in melody passages. Celesta audible (masking check: celesta band SNR > 0 dB in its passages). |
| E | **A/B and export** | master -> S/out/Disney_Medley_original_draft7.ogg via `ffmpeg -c:a libvorbis -q:a 9`. Also S/out/draft7_AB/ (v6 vs v7 at 02:20, 03:20, 04:10, 05:10, plus the flute/guitar choice excerpts), all `-q:a 9`. S/out/CREDITS.txt (VSCO, VCSL CC0; SSO CC Sampling+; MARCo CC BY-NC; tonejs MIT). | ffprobe reports codec vorbis. Duration matches the master within 0.1 s. |
| Lead | integration | Runs C before D, D before E; sends the files to the user | All acceptance metrics met; the user's verdicts are recorded in USER_FEEDBACK.md |

A and B write disjoint stems. The previous stem directories are read-only (v4 and v6 stems were seen being rewritten during scouting), so v7 writes only to work/v7_stems. Disk: 17 GB free. 4 CPUs, so run A and B in parallel with 2 workers each.

## 6. Risks

- Swapping in VCSL/SSO/VSCO samples can bring the octave-mislabel bug back (VSCO violin, flute and SSO flute filenames are one octave low). Mitigation: verifier C is blocking, and every sample is pitch-measured with folder-offset inheritance as in v6.
- MARCo is non-commercial (CC BY-NC). The Detmold fallback is ready.
- The VCSL harp is at its natural level (-20 dBFS peak) rather than normalised, so recalibrate to the -8.5 dB harp target. Do not let it get louder (draft 1: "harp too loud").
- The spiccato level calibration is a guess and can make staccato sound too thin or too loud. Check it by ear in the A/B.
- The more realistic hall can push the melody back. Re-check melody prominence and keep the 0.3 dry spot.
- Layer xfade adds about 40% render time on the affected notes; acceptable.
- Flute and guitar alternatives are a user choice. Default to the liked sounds.
