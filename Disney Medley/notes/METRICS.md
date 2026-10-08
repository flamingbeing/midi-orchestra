# Verification metrics (verify/verify.py)

Tool: `scratchpad/verify/verify.py`. It blocks: exit 0 = PASS, 1 = FAIL. A check fails on an absolute FAIL or on any REGRESSION against `--prev-metrics`.

```
venv/bin/python -I verify/verify.py --stems work/vX_stems --master work/vX_master.wav --midi work/draft3_input.mid \
   --encoded out/<file>.m4a --mix-log work/vX_mix.log --prev-metrics pipeline/notes/metrics_v7b.json \
   --out pipeline/notes/metrics_vX.json
```
Runtime is about 4.5 min on 4 CPUs. The full JSON for v7b is in `pipeline/notes/metrics_v7b.json`. Use it as `--prev-metrics` for v8.

## Baseline: v7b (draft 7b), full piece, 448.8 s. Status: PASS, 111 checks

**(0) Note loudness (HARD GATE: resid SD / p90 adjacent jump, dB, tolerance +0.3).** These numbers are identical to `v7b/noteloud.py`.
Flute 2.57/3.32 · Clarinet 2.00/3.00 · Celesta 3.56/4.01 · Harp 3.22/3.91 · Guitar 2.08/2.77 · Piano 2.34/3.17 · Snare 1.09/2.49 ·
Violins 4.25/8.15 · Violas 3.71/7.10 · Cellos 1.48/2.33

**(1) Pitch.** pyin runs on each note's own window, searching ±19 semitones. Every flag is also checked against the spectrum.
- **Octave errors: 0 on every stem.** "Suspect detector errors" are flags where the spectrum confirms the written fundamental: Flute 11, Clarinet 21, Celesta 134, Harp 252, Guitar 27, Piano 67, Violins 19, Violas 10, Cellos 2. Almost all of them are chords, ringing notes or ostinatos, where pyin locks onto another partial or note.
- **Tuning.** Median |cents| measured from the strongest spectral peak within ±100 c of the written pitch (spectral_median_abs_cents), which is robust in polyphony:
  Flute 2.0, Clarinet 3.1, Glock 0.2, Celesta 4.6, Harp 9.0, Guitar 3.8, Piano 2.2, Pad 3.0, Violins 3.8, Violas 7.2, Cellos 4.1, Pizz 6-8.
  The pyin median on isolated notes is 0-20 c.
  The pyin all-note medians for Celesta (110 c) and Harp (70 c) are polyphony artefacts of the detector, not mistuning.
- **Rule** (`pitch_check` docstring):
  - A flag (|dev| > 6 st) where pyin's pitch equals another sounding note is `other_note`. It is not counted.
  - A flag counts as a suspect detector error, not an octave error, only if all of these hold:
    - the note is low (< 48), short (< 0.2 s) or acoustically overlapped (including free ringing: harp 3 s, piano, guitar and celesta 2 s);
    - the onset-differential spectral check confirms the written fundamental (f present, or 2f and 3f present; no unexplained f/2 or 3f/2);
    - the pitch is not "systematic".
  - A pitch is systematic if ≥ 50% of its isolated occurrences are flagged, or if ≥ 2 of its flags fail the spectral check. All flags of a systematic pitch count as errors.
  - This differs from the literal "single" rule. Repeated ostinato notes under chords fail pyin the same way every time, so `single` is reported (`suspect_runs`) but does not gate. The systematic rule catches the sample-level bug that "single" was meant to catch.
- **Positive controls** (`verify/selftest_pitch.py`, `verify/selftest.py`):
  - Re-injecting the draft-5 clarinet bug (every G5/A5 an octave high): 15 of 17 notes reported, pitches 79 and 81 marked systematic, so the check FAILs.
  - Harp and piano passages shifted an octave down inside chords: 13 of 31 and 11 of 31 notes reported. Per-note recall is lower in chords, but the gate still trips.
  - 10 Clarinet notes shifted up: 10 of 10 flagged, all failing the spectral check.

**(2) Onsets.** Median flux-peak offset after the MIDI note-on, in ms (MAD):
Piano 14.3 (1.9) · Celesta 12.6 (1.8) · Snare 10.6 · Guitar 16.8 · Harp 19.0 (4.1) · Clarinet 12.7 (4.0) · Flute 18.9 (3.9) · Violins 18.0 (9.1) · Violas 15.6 (12.5) · Cellos 25.9 (7.1).
- The detector itself lags by about 12-14 ms; the piano, whose attack is instantaneous, reads +14.3. Relative to the piano, cellos land about 12 ms late and violins and flute about 4 ms late, even with the 25 ms and 12 ms onset compensation.
- Violas are loosest: p90 +58 ms, and 36 of 306 salient groups are more than 60 ms off.
- Control: shifting the piano by +40 ms moved the reading from 14.3 to 54.3 ms.
- Peaks at the edge of the search window are excluded as legato or no match.

**(3) Clicks.** The detector is an LPC-residual crest test confirmed by a broadband HF burst.
- **Master: 0 not at an onset** (5 at onsets).
- Stems with clicks away from onsets: Flute 9 (≈20 dB; worst at 6:52.76 and 2:58.93, at note ends), Clarinet 3 (0:25.97, 0:30.97, 0:35.97: periodic, worth listening to), Harp 6 (≥ 20 dB; 0:55.06, 6:59.16, 4:18.37, 6:14.67).
- Clicks at onsets (plucked or struck attacks) are expected and do not gate.
- Control: injected spikes, steps and dropouts at −34 dB re peak were detected 10 of 12 times on Flute and 5 of 12 on loud Violins. The misses were below the local RMS, or dropouts in silence.

**(4) Master.** −16.0 LUFS integrated, LRA 8.5 LU, true peak −1.9 dBTP (−2.0 after AAC), L/R balance −0.37 dB, L/R correlation 0.38, 0 clipped samples, 0 NaN.

**(5, 6) Masking.** This is the 1-4 kHz band SNR of each instrument against the sum of all other stems while its MIDI notes sound. It uses the mix-log gains and the v7b ducking model on dry stems, so it approximates the in-hall mix.

| Stem | Median SNR | p10 | Frames < 0 dB | Worst 5 s windows |
|---|---|---|---|---|
| Flute | +0.61 dB | −10.1 | 47% | 5:30 (−14.6), 5:35 |
| Clarinet | +0.35 dB | −10.6 | 48% | 0:30 (−13.0) |
| Celesta | −7.6 dB | −20.3 | 80% | 3:55 (−40.5) |
| Cellos 2:08-2:34 (100-1000 Hz) | −6.2 dB | −11.3 | 81% | |

- Flute and clarinet are matched, consistent with the user's "clarinet as loud as flute".
- The user has not reported celesta or cello problems since drafts 5 and 6, so these values are the accepted floor. Any drop beyond 1 dB (median) or 1.5 dB (p10) is a REGRESSION.

**(7) Arc.** Section LUFS, with sections taken from the MIDI tempo map:
0:00 −18.8 · 0:13 −18.4 · 0:46 −16.2 · 2:55 −19.3 · 3:22 −15.2 · 5:52 −15.4 · 6:52 −17.4.
Correlation with the MIDI velocity arc is 0.27 by section and 0.41 over 10 s windows. Both are informational.

**(8) Regression tolerances** (relative to prev):
- noteloud: +0.3 dB (hard gate)
- pitch median cents (pyin and spectral): +5 c
- onset |median|: +10 ms; MAD: +8 ms
- clicks not at onset: +max(2, 20%)
- masking median: −1 dB; p10: −1.5 dB
- LRA: −1.5 LU
- section-arc shape: ≤ 2 dB deviation
- arc correlation: −0.1

Absolute checks:
- octave errors = 0
- −16 ± 1 LUFS
- true peak ≤ −1 dBTP on the master and ≤ −0.5 dBTP after AAC
- LRA ≥ 7 LU
- |L/R| ≤ 1.5 dB
- no clipping or NaN

Regression logic test: a self-diff of v7b gives 0 non-PASS checks. Perturbing the metrics (Violas SD +0.4, Clarinet SNR −1.5, Piano onset MAD +10, Flute clicks +5, 3 octave errors) produced exactly the 5 expected flags.

## v8 (draft 8), full piece, 448.5 s. Status: PASS, 124 checks, 0 REGRESSION (vs v7b)

File: `pipeline/notes/metrics_v8.json`, run with `--midi work/draft8_input.mid`, which is the tempo-mapped MIDI the v8 stems were rendered from. Use it as `--prev-metrics` for v9.

- **Note loudness gate (resid SD / p90 jump, dB):** Flute 1.52/3.06 · Clarinet 1.51/3.08 · Celesta 3.13/3.85 · Harp 3.22/3.90 · Guitar 2.08/2.77 · Piano 2.34/3.17 · Snare 1.09/2.49 · Violins 2.50/5.07 · Violas 1.86/2.76 · Cellos 1.02/1.92. Every value equals or improves on v7b. Violins, Violas and Flute improved by 1.0-1.9 dB.
- **Pitch:** 0 octave errors on every stem. Spectral median |cents|: Flute 2.0, Clarinet 3.1, Celesta 4.6, Harp 9.0, Guitar 3.8, Piano 2.2, Violins 4.4, Violas 4.6, Cellos 3.5.
- **Onsets (median / MAD, ms):** Flute 13/10.1 · Clarinet 13/4.0 · Celesta 13/1.8 · Harp 19/4.3 · Piano 14/1.9 · Violins 16/7.9 · Violas 15/7.2 · Cellos 31/6.8.
- **Clicks not at onset:** Harp 6 (all ≥ 20 dB, most likely free-ringing re-plucks), Flute 4 (2 at ≥ 20 dB, at 6:51.8 and 7:12.7; worth a listen), Clarinet 3 (all < 20 dB), every other stem 0. The master has 2, both at onsets. None of these gates, because v8 is within tolerance of v7b.
- **Master:** −16.0 LUFS, LRA 10.5 LU (v7b: 8.5), true peak −1.5 dBTP (also −1.5 after AAC), L/R −0.45 dB, correlation 0.40, 0 clipped samples.
- **Masking, 1-4 kHz SNR (median / p10):** Flute +0.42/−8.4 · Clarinet +1.12/−9.4 · Celesta −8.28/−21.5 · Cellos 2:20 (100-1000 Hz) −6.23/−12.1. Worst Flute windows are at 3:35, 5:30 and 4:45; worst Celesta is 3:55 (−39 dB).
- **Arc (section LUFS):** 0:00 −20.0 · 0:13 −17.4 · 0:46 −15.4 · 2:55 −19.7 · 3:22 −17.1 · 4:20 −16.1 · 5:51 −14.4 · 6:52 −17.9. Correlation with the MIDI velocity arc is 0.53 by section (v7b: 0.27) and 0.49 over 10 s windows.
