# Disney Medley — final: draft 10

An orchestral rendering of a Sibelius arrangement that runs through ten songs: Belle, I'll Make a Man Out of You, Just Around the Riverbend, I Won't Say, One Jump Ahead, Beauty and the Beast, Go the Distance, Reflection, Out There and A Whole New World.

## Score (`score/`)

| File | What it is |
| --- | --- |
| `disney_medley_original.mid` | The original MIDI exported from Sibelius. Every draft is rendered from this file. |
| `disney_medley_original.pdf` | The printed score. |
| `disney_medley_original.sib` | The Sibelius source file. |

## Drafts (`drafts/`)

Drafts 1–9 are 192 kbps MP3 and draft 10 onwards VBR V2 MP3, all named after the MIDI file: `disney_medley_original_draft<N>.mp3`. Every draft plays the original MIDI's notes, pitches and tempo map. The only things that change are articulation lengths and timing humanisation of 30 ms or less.

| File | Notes |
| --- | --- |
| `disney_medley_original_draft10.mp3` | **Final version** (approved by the listener). Made from the second listener's comments: steel-string acoustic guitar, louder harp glissandi, harp over strings at 1:38, staccato strums at 2:17, rolled harp chords at 3:05, piano semiquavers at 5:30 brought out. See `notes/changes_draft10.md`. |
| `disney_medley_original_draft9.mp3` | Breathing for flute and clarinet, true slurs, re-tongued repeated notes and balance automation. |
| `disney_medley_original_draft8.mp3` | Shorter string attacks, tempo-map fixes and no master compressor. |
| `disney_medley_original_draft7b.mp3` | Goes back to the draft 6 engine and adds balance calibration after the hall reverb. |
| `disney_medley_original_draft7.mp3` | The balance was much worse in this draft, which led to the draft 7b rule. |
| `disney_medley_original_draft6.mp3` | Fixes the clarinet squeak (wrong-octave samples). Louder cello around 2:20 and a softer, less thumpy harp. |
| `disney_medley_original_draft5.mp3` | Faster clarinet attack with no distortion, more even note loudness and an audible celesta. |
| `disney_medley_original_draft4.mp3` | New lossless sample sets: VSCO strings and clarinet, Sonatina celesta. |
| `disney_medley_original_draft3b.mp3` | Draft 3 with the clarinet boosted. |
| `disney_medley_original_draft3.mp3` | Louder clarinet, louder harp glissando at the end, softer guitar, and about 5% faster from Beauty and the Beast to Reflection. |
| `disney_medley_original_draft2.mp3` | First balance pass: melody ducking, legato joins and phrase shaping. |
| `disney_medley_original_draft1.mp3` | First rapid draft. |
| `disney_medley_original_plain.mp3` | The plain MIDI rendered without any of the realism processing. |

Song start times differ slightly between drafts. Drafts 1 and 2 and the plain render keep the score's own tempo. Drafts 3 and later play about 5% faster from Beauty and the Beast to Reflection.

## Notes (`notes/`)

- `USER_FEEDBACK.md` lists all listener feedback so far. It is the source of truth.
- `changes_v9.md` describes what changed in draft 9.
- `METRICS.md` holds the objective checks run on each draft.
- `FINAL_PLAN.md` covers the sample sources and techniques.

## Config (`config/`)

| File | What it does |
| --- | --- |
| `piece.json` | Fermata positions and the mix balance (loudness targets plus passage automation tuned from listener feedback). |
| `make_input.sh` | Builds the render input from the original MIDI: `prepare.py` assigns the Sibelius tracks to sounds, then `tempo_plus5.py` and `tempo_fixes.py` apply the tempo edits. |
| `listening_page.json` | Draft list and song start times for the listening-notes page. |

**Final: draft 10** (commit `0e4cfe9`). To rebuild it, run `pipeline/run.sh "Disney Medley" draft10_rebuild` from the repo root at that commit; `config/piece.json` holds every setting it used. The engine's regression check still rebuilds draft 9 (see `CLAUDE.md`). The code is in [`../pipeline`](../pipeline).
