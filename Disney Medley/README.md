# Disney Medley

An orchestral rendering of a Sibelius arrangement that runs through ten songs: Belle, I'll Make a Man Out of You, Just Around the Riverbend, I Won't Say, One Jump Ahead, Beauty and the Beast, Go the Distance, Reflection, Out There and A Whole New World.

## Score (`score/`)

| File | What it is |
| --- | --- |
| `disney_medley_original.mid` | The original MIDI exported from Sibelius. Every draft is rendered from this file. |
| `disney_medley_original.pdf` | The printed score. |
| `disney_medley_original.sib` | The Sibelius source file. |

## Drafts (`drafts/`)

All drafts are 192 kbps MP3. Every draft plays the original MIDI's notes, pitches and tempo map. The only things that change are articulation lengths and timing humanisation of 30 ms or less.

| File | Notes |
| --- | --- |
| `draft9.mp3` | Latest version. Adds breathing for flute and clarinet, true slurs, re-tongued repeated notes and balance automation. |
| `draft8.mp3` | Shorter string attacks, tempo-map fixes and no master compressor. |
| `draft7b.mp3` | Goes back to the draft 6 engine and adds balance calibration after the hall reverb. |
| `draft7.mp3` | The balance was much worse in this draft, which led to the draft 7b rule. |
| `draft6.mp3` | Fixes the clarinet squeak (wrong-octave samples). Louder cello around 2:20 and a softer, less thumpy harp. |
| `draft5.mp3` | Faster clarinet attack with no distortion, more even note loudness and an audible celesta. |
| `draft4.mp3` | New lossless sample sets: VSCO strings and clarinet, Sonatina celesta. |
| `draft3b.mp3` | Draft 3 with the clarinet boosted. |
| `draft3.mp3` | Louder clarinet, louder harp glissando at the end, softer guitar, and about 5% faster from Beauty and the Beast to Reflection. |
| `draft2.mp3` | First balance pass: melody ducking, legato joins and phrase shaping. |
| `draft1.mp3` | First rapid draft. |
| `original.mp3` | The plain MIDI rendered without any of the realism processing. |

Song start times differ slightly between drafts. Drafts 1 and 2 and `original.mp3` keep the score's own tempo. Drafts 3 and later play about 5% faster from Beauty and the Beast to Reflection.

## Notes (`notes/`)

- `USER_FEEDBACK.md` lists all listener feedback so far. It is the source of truth.
- `changes_v9.md` describes what changed in draft 9.
- `METRICS.md` holds the objective checks run on each draft.
- `FINAL_PLAN.md` covers the sample sources and techniques.

The code that produced these drafts is in [`../pipeline`](../pipeline).
