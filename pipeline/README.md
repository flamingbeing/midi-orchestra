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
| `extra_tracks` | Optional, rarely needed: `{"track name": [bank, pan, gain_dB, voices]}` for a custom track. Every sound listed below already renders without it. |
| `fermata_end_ticks` | The MIDI ticks where fermata bars end. Release tails are lifted there. |
| `mix.target` | Loudness of each instrument relative to the melody, in dB after the hall. |
| `mix.automation` | `{"Instrument": [[start_s, end_s, dB], ...]}`. Passage-level balance fixes from listener feedback. |
| `mix.accomp` | The instruments that duck under the flute or clarinet melody. |

Without a `mix` block, a piece gets the default loudness targets and no time-based automation. Add automation only in response to listener feedback.

## Sounds

`prepare.py` picks a sound for each MIDI track from its name (e.g. "Horn in F 1", "Violoncello", "English Horn") or its General MIDI program. The sounds are defined in `instruments.py` (catalogue) and `render.py` (the original core set).

| Family | Sounds |
| --- | --- |
| Woodwinds | Piccolo, Flute, Alto Flute, Oboe, Cor Anglais, Clarinet, Bass Clarinet, Bassoon, Contrabassoon, Saxophone, Recorder |
| Brass | Horns, Trumpet, Trombone, Bass Trombone, Tuba |
| Strings | Violins, Violas, Cellos, Contrabass (each also as Pizz and Trem), Solo Violin, Solo Viola, Solo Cello, Strings Pad |
| Voices | Choir (male and female) |
| Keyboards and plucked | Piano, Harpsichord, Organ, Celesta, Harp, Guitar |
| Pitched percussion | Timpani, Glockenspiel, Xylophone, Marimba, Vibraphone, Tubular Bells |
| Drum kit and orchestral percussion (channel 10) | Each General MIDI drum note plays its own instrument: bass drum, snare, toms, hi-hat, crash/suspended cymbals, gong, tambourine, triangle, woodblock, claves, cowbell, bongos, congas, agogo, cabasa, shaker, guiro, vibraslap, sleigh bells, claps (`instruments.DRUMS`). Unlisted drum notes play on the snare. |

To hear every sound, play [`demo/drafts/instrument_demo.mp3`](demo/drafts/instrument_demo.mp3); [`demo/timeline.txt`](demo/timeline.txt) lists when each instrument starts. Rebuild it with `pipeline/run.sh pipeline/demo instrument_demo`.

Every new sound was checked with a test score covering its full range: the pitch of each rendered note matched the MIDI. A few notes were flagged by the automatic octave check (timpani, tubular bells, vibraphone, organ, plus single notes on oboe, solo violin and violin tremolo), but all of them were confirmed correct on the spectrum. Pitch detectors misread drum and bell tones.

Limits:
- The core sounds (strings, flute, clarinet, harp, piano, celesta) have the most performance modelling: breath planning, slurs and phrase shaping tuned on the Disney Medley. The catalogue winds and brass get breath planning, slurs and phrasing too, but nobody has listened to them yet. Expect the first draft of a new piece to need listening feedback.
- Saxophone uses tenor sax samples for all saxophones. Tremolo strings use section tremolo samples. Choir sings "aah" only.
- Programs with no orchestral equivalent (synths, sound effects, electric instruments) fall back to the nearest sound, and `prepare.py` prints a warning for each.
- To add an instrument, fetch its free samples, add an entry to `instruments.py`, and run `tools/import_samples.py` to copy the files into `assets/` as FLAC.

Sample libraries and their licences are listed in [`assets/SOURCES.md`](assets/SOURCES.md).

## Lessons that are now rules

- **Check the pitch of every rendered note against the MIDI.** In draft 5 a mislabelled sample folder made clarinet notes play an octave high, and the listener heard it as squeaks.
- **Re-measure on the full piece.** Techniques that sounded better on short excerpts made the full piece worse in draft 7. The hard gate is per-note loudness consistency (`tools/noteloud.py`), which must not get worse.
- **Calibrate balance after the hall reverb, not before.**
- **The listener's feedback is the ground truth.** Keep it in `<Piece>/notes/USER_FEEDBACK.md`, and never let something they liked get worse.
