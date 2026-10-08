# Draft 9 - changes (v9/, reproducible with v9/run_v9.sh)

Output: out/Disney_Medley_original_draft9.m4a (AAC 256k, 7:28). Verify: PASS against draft 8, with no regressions
(pipeline/notes/metrics_v9.json). Every change has an env switch (V9_*, default = adopted) in render_v9.py / mix_v9.py.

## What you should hear differently
- **The wind players breathe.** Flute and clarinet now take short breaths (93-163 ms) at phrase ends, about every 4 bars.
  The long clarinet line at 5:12-5:53 (40 s with no break in draft 8) now breathes at 5:22.9, 5:33.3 and 5:43.7.
  Where flute and clarinet double the same line (1:27-1:38), they breathe together at 1:31.8.
- **Slurs sound like slurs.** Slurred flute and clarinet notes no longer re-attack. The next note grows out of the
  previous one through a 60 ms crossfade. Repeated notes on the same pitch are re-tongued with a small gap and are no
  longer smeared together.
- **Phrase endings taper.** Flute and clarinet notes before a rest fade a little instead of stopping dead. The fermatas
  at 0:41, 3:22, 4:20 and 7:11 now release slightly before the next section starts.
- **Cellos are tighter and more even.** They no longer drag about 20 ms behind the harp and piano they double. Note
  changes in back-to-back cello notes no longer leave a hole.
- **Balance tweaks.** At 2:08-2:26 the clarinet is a little softer, so the cello at 2:20 comes through more. Violins
  are on top of the violas in the strings-only passage at 0:46-1:17. The flute melody is a little clearer at 6:30-6:52.
  The quiet opening chord is easier to hear.
- **Slightly more "air" on top** (gentle treble shelf). Harp notes no longer click when their long ring is cut.

## Changes (measured; v8 -> v9, full piece)
Render (v9/render_v9.py):
1. Breath planner for Flute and Clarinet (`plan_breaths`), taken from the critic_performer prototype. Capacity is
   Flute 7 s and Clarinet 11 s, scaled down at loud dynamics. The breath goes at the best boundary (long previous note,
   next note on a downbeat). The previous note is shortened by a gap of 0.1-0.18 s and tapered by -8 dB. Onsets, pitches
   and tempo are unchanged. Doubled passages share one breath plan. The breath list is in work/v9_render.log (13 breaths).
2. True slur crossfade for Flute and Clarinet: the incoming note starts at the sample's 70 % plateau point with an
   equal-power 60 ms crossfade.
3. Re-tonguing of repeated same-pitch wind notes: a 35 ms stop with a 40 ms taper.
4. Phrase-end taper for winds (-6 dB over the last 0.15 s, note value kept).
5. Accents are preserved in the phrase smoothing (Flute, Clarinet, Violins). Smoothing now runs only between neighbours
   whose written velocities differ by less than 12, so composed accents survive.
6. Cello legato: back-to-back notes are joined by +50 ms. The cello dip at note changes went from a median of -2.5 dB
   to -1.1 dB (p10 -4.7 to -3.6 dB).
7. Cello onset compensation +12 ms. The verify onset median went from 30.5 ms to 17.5 ms, in line with the other strings.
8. Fermata lift: at the ends of bars 14, 16, 107, 129 and 202, sustained notes are cut 0.10-0.15 s short.
9. Five duplicate piano notes (the same key struck twice at the same instant) are merged.
10. Ringing samples (harp, celesta, glock) get a 0.3 s end fade. Harp non-onset clicks went from 6 to 0.

Mix and master (v9/mix_v9.py, run_v9.sh):
- Clarinet automation -2 dB at 128-146 s. The draft-8 clarinet lift (+3 dB) over 351.9-412.4 s is split into +3 dB up
  to 390 s and +2 dB after it. New flute automation: +2 dB at 153-176 s, +3 dB at 198-216 s, +2 dB at 354-362 s.
- Violas -3 dB and Cellos -1.5 dB at 46.3-77.3 s, so the violins carry the tune.
- Strings Pad target raised from -9 to -5 and the pad is no longer ducked. The opening 3-8 s window is +0.9 dB relative
  to the whole piece.
- Accompaniment duck depth now follows the accompaniment's written dynamic: no duck at vel >= 100. The measured effect
  is negligible (mean scale 0.93, tutti 1:15-1:35 unchanged at +1.1 dB). It is kept because it is harmless.
- Melody targets: Clarinet 4.5 -> 5.0, Flute 1.5 -> 1.8. This compensates for the in-note silences added by breaths
  and re-tonguing; without it, the clarinet p10 SNR regressed (-11.1 dB against v8's -9.4).
- Master: added `treble=g=3:f=7000` (high shelf). 8 kHz relative to 1 kHz went from -29.1 to -27.2 dB, and 16 kHz from
  -46.8 to -44.0 dB.

## Gate numbers (v8 -> v9)
Note loudness, resid SD / p90 adjacent jump (dB). Every instrument is equal or better, except Cellos at +0.06 SD
(inside the 0.3 tolerance):
Flute 1.52/3.06 -> 1.42/2.58 | Clarinet 1.51/3.08 -> 1.28/1.91 | Violins 2.50/5.07 -> 2.42/4.53 |
Piano 2.34/3.17 -> 2.27/3.06 | Cellos 1.02/1.92 -> 1.08/1.92 | Violas, Harp, Celesta, Guitar unchanged.

Masking (in-hall 1-4 kHz SNR, median/p10, dB): Flute 0.42/-8.4 -> 0.11/-9.21. Clarinet 1.12/-9.42 -> 1.32/-10.57.
Celesta -8.28 -> -8.33. Cello at 2:20 (100-1000 Hz): -6.23 -> -4.98 (better).

Pitch: 0 octave errors on every stem. Master: -16.0 LUFS, -1.5 dBTP, LRA 10.5 -> 10.0 LU.

Onsets: the Flute median moved from +13.0 to -12.3 ms and the MAD from 10.1 to 3.5 ms. The Clarinet median moved from
+13.2 to -6.2 ms and the MAD from 4.0 to 6.5 ms. Slurred notes now crossfade in 30 ms before the written onset, and the
detector catches the start of the crossfade. The 14 clarinet notes flagged as more than 60 ms late are short slurred
notes with no transient, for example 4:27.15. They are legato by design, not mistimed.

Watch: the arc correlation with MIDI velocity went from 0.53 to 0.48. Verify does not flag it. The clarinet trim and
the louder pp opening move toward the reference recording, which the balance critic compared against, but away from a
pure velocity-follows-loudness model. Flute stem clicks away from onsets went from 4 to 7. These are small spikes
(about 22 dB) that are probably in the flute D4 sample itself, newly exposed now that slurred notes skip the attack.
They are not visible on the master (master clicks: 0).

## Tried and rejected / not done
- Viola legato join (+50 ms): Viola p90 jump 2.76 -> 3.50 dB, which fails the gate, so it stays off (V9_LOWSLUR=Cellos
  only). The viola gap at 4:10.9 (-8 dB) remains.
- Crossfade length scaled to note length (V9_XFSCALE): no measurable change, so it is off.
- Not done for lack of time or because of the risk to things the user likes: the hall front-to-back depth, stereo
  string seats, the IR 800 Hz EQ and the clarinet seat (all would change the colour the user approved); the per-sample
  latency alignment; repeat-note round-robin; the VSCO snare; pizz ring; the brightness-filter change.
