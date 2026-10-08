# Draft 10: changes from draft 9

Draft 10 responds to the second listener's comments on draft 9 (`USER_FEEDBACK.md`, "panda"). Times below are draft 9 times; draft 10 keeps the same timeline.

| Comment on draft 9 | What changed | Where |
| --- | --- | --- |
| Harp glissandos a bit too soft | Every harp glissando (8 in the piece) is played 1.3× harder, about +4.5 dB, with a brighter tone. | Engine (`render.py`, `V10_GLISS`, on by default) |
| Guitar should sound more like an acoustic guitar | The guitar now uses a steel-string acoustic sample set instead of nylon. Each note is levelled on its pluck, which makes it far more even than before. | `piece.json` `banks` + new samples |
| 1:37.8–1:42.8 strings overwhelm the harp | In that passage the harp is raised 3 dB and the violins and violas lowered 2 dB. | `piece.json` `mix.automation` |
| 2:17.5–2:22.5 guitar strumming should be staccato | The strums are played at half length: 2:17–2:23 strums now stop after about 180 ms instead of 310 ms. | `piece.json` `articulation` |
| 3:05.4–3:10.4 harp should roll the right-hand chords | The three right-hand chords are rolled upward, 30 ms per note. | `piece.json` `roll` |
| 5:29.4–5:34.4 piano too soft; the semiquavers should be heard | The piano is raised 10 dB there. It sat about 21 dB under the fortissimo clarinet melody. | `piece.json` `mix.automation` |
| 6:32.5–6:37.5 harp glissando missing | The glissando was in the score but buried. It gets the general glissando boost plus another 7 dB in the mix. | engine + `piece.json` |
| Liked: flute at 2:28; flute trill at 3:38 | Unchanged: the flute renders identically to draft 9. | — |

## Checks

- **Faithfulness:** all 3,993 notes are present and no note has the wrong octave. The notes, pitches and tempo map are as in draft 9. The rolled harp chords are the one exception, requested by the listener: up to 90 ms of onset spread inside each rolled chord.
- **Draft 9 unaffected:** with the glissando boost switched off and draft 9's settings, the new engine rebuilds draft 9 sample for sample.
- **Melody clarity:** the flute and clarinet are as clear as in draft 9 (median in-hall 1–4 kHz SNR 0.08 / 1.31 dB, against 0.11 / 1.32).
- **Note-to-note evenness:** unchanged for every instrument except two.
  - The guitar is much more even (p90 jump 0.80 dB, against 2.77).
  - The harp's figure rises (3.22 → 3.89) only because the glissando notes are now deliberately louder than their written velocity. Without the glissandi and the rolled chords it is identical (2.92 / 3.83).

## What you should hear differently

- Harp glissandi are clearer throughout. The one at 6:32 is now plainly audible.
- The guitar sounds like a steel-string acoustic, and the strums at 2:17 are short and crisp.
- The harp arpeggios at 1:38 sit above the strings.
- The harp's right-hand chords at 3:05 are rolled like a real harpist's.
- The piano's semiquaver run at 5:30 comes through the orchestra.
