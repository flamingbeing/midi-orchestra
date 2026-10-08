# MIDI → orchestral recording pipeline

This pipeline turns a MIDI file (for example a Sibelius or MuseScore export) into a recording that sounds as close to a real orchestra as possible. It changes none of the notes, pitches or tempo map. The only changes are articulation lengths and humanisation of 30 ms or less.

It produced the [Disney Medley](../Disney%20Medley) drafts. Running it on that piece reproduces draft 9 sample for sample.

## Quick start: a new piece

```bash
pip install -r pipeline/requirements.txt          # Python 3.11, plus ffmpeg on PATH
mkdir -p "My Piece/score" "My Piece/config" "My Piece/notes"
cp ~/my_piece.mid "My Piece/score/"
echo '{"title": "My Piece", "midi": "score/my_piece.mid"}' > "My Piece/config/piece.json"
python3 pipeline/prepare.py "My Piece/score/my_piece.mid" /tmp/check.mid "My Piece/config/piece.json"   # check the instrument mapping
pipeline/run.sh "My Piece" draft1                 # about 5 minutes on 4 CPUs -> My Piece/drafts/draft1.mp3
```

In a Claude Code session you can simply say: *"render `My Piece/score/x.mid` with the pipeline in this repo"*.

## Stages

| Step | File | What it does |
| --- | --- | --- |
| 1. Prepare | `prepare.py` | Regroups the MIDI into one track per sound, chosen by track name (Violin, Flute, …) and General MIDI program. It keeps every note and the conductor track. It prints a warning for each instrument that has no dedicated sound. A piece can supply its own `config/make_input.sh` instead (Disney Medley does). |
| 2. Render | `render.py` | Renders each track from multi-layer samples. This step includes pitch-verified sample mapping, legato and slur crossfades, breath planning for winds, re-tongued repeated notes, onset compensation, release tails and fermata lifts. |
| 3. Mix | `mix.py` | Places each instrument at its own measured seat in a real hall (3D-MARCo impulse responses). It calibrates each instrument's loudness *after* the hall to the `TARGET` table and ducks the accompaniment under the melody. |
| 4. Master | `run.sh` | Applies a high-pass filter, a small air shelf and a static gain to −16 LUFS, plus a safety limiter (no bus compressor). It then exports a 192k MP3 and a 256k AAC m4a. |
| Check | `tools/verify.py`, `tools/noteloud.py` | Measures the pitch of every rendered note against the MIDI, plus onsets, clicks, loudness, melody masking and the section arc. It flags regressions against the previous draft's metrics. |
| Improve | `workflow/refine_round.js` | A Claude Code workflow for one refinement round: five critics, then a fixer that renders the next draft, then an independent verifier. Run it with args `{piece, cur, next}`. |
| Share | `listening_page/` | Builds the listening-notes web page (play the drafts, comment on passages, download). It runs `build.py "Piece" out.html` from `config/listening_page.json`. |

## Per-piece settings: `<Piece>/config/piece.json`

| Key | Meaning |
| --- | --- |
| `midi` | The MIDI file, as a path relative to the piece folder. |
| `track_map` | `{"source track name": "sound"}`. This overrides `prepare.py`'s choice of sound. |
| `extra_tracks` | Turns on the sounds outside the core set (`Contrabass`, `Oboe`, `Horns`, `Trumpet`, `Trombone`, `Timpani`). `prepare.py` prints the exact line to paste in. |
| `fermata_end_ticks` | The MIDI ticks where fermata bars end. Release tails are lifted there. |
| `mix.target` | Loudness of each instrument relative to the melody, in dB after the hall. |
| `mix.automation` | `{"Instrument": [[start_s, end_s, dB], ...]}`. Passage-level balance fixes from listener feedback. |
| `mix.accomp` | The instruments that duck under the flute or clarinet melody. |

Without a `mix` block, a piece gets the default loudness targets and no time-based automation. Add automation only in response to listener feedback.

## Sounds and current limits

The best-sampled sounds are the string sections (arco and pizzicato), flute, clarinet, harp, piano, celesta, glockenspiel, nylon guitar and strings pad. Oboe, horns, trumpet, trombone, timpani and contrabass work too, but come from smaller sample sets, so expect less realism there until better free samples are added.

Other current limits:
- Every General MIDI drum note plays as a snare.
- Bassoon, tuba and choir have no dedicated sound and fall back to the nearest one, with a warning.

Sample libraries and their licences are listed in [`assets/SOURCES.md`](assets/SOURCES.md).

## Lessons that are now rules

- **Check the pitch of every rendered note against the MIDI.** In draft 5 a mislabelled sample folder made clarinet notes play an octave high, and the listener heard it as squeaks.
- **Re-measure on the full piece.** Techniques that sounded better on short excerpts made the full piece worse in draft 7. The hard gate is per-note loudness consistency (`tools/noteloud.py`), which must not get worse.
- **Calibrate balance after the hall reverb, not before.**
- **The listener's feedback is the ground truth.** Keep it in `<Piece>/notes/USER_FEEDBACK.md`, and never let something they liked get worse.
