# Working in midi-orchestra

This repo turns MIDI scores into realistic orchestral recordings. There is one folder per piece (for example `Disney Medley/`), plus the shared engine in `pipeline/`. Read `pipeline/README.md` first.

## The contract with the listener

- **Faithfulness:** the notes, pitches and tempo map of the MIDI are fixed. Only articulation lengths and humanisation of 30 ms or less may change. A tempo edit is allowed only if the listener asks for it; it goes in `<Piece>/config/`, never in the engine.
- **The listener can hear; we cannot.** `<Piece>/notes/USER_FEEDBACK.md` is the ground truth. Add every new comment there, along with the draft it refers to. Nothing the listener liked may get worse.
- **Measure, don't guess.** Run `pipeline/tools/verify.py` on every new draft and compare it with the previous draft's metrics. Hard gates:
  - every rendered note's pitch matches the MIDI;
  - per-note loudness consistency (`tools/noteloud.py`) is no worse;
  - balance is calibrated after the hall reverb;
  - nothing is adopted on excerpt evidence alone.

## Improving a piece (the usual session)

1. The listener's comments arrive as text: copied from the listening page, or pasted by the user. Add them to `<Piece>/notes/USER_FEEDBACK.md`.
2. Decide where each fix belongs.
   - **Only this piece** (a passage too loud, a part to bring out, a tempo the listener wants): put it in `<Piece>/config/piece.json` (`mix.target`, `mix.automation`, `fermata_end_ticks`, `track_map`) or in `<Piece>/config/`.
   - **How an instrument or technique sounds everywhere** (a sample problem, attacks, breathing, the hall): change `pipeline/*.py`. That improves every piece's future drafts.
3. Render the next draft: `PY=python3 pipeline/run.sh "<Piece>" draftN`. This writes `<Piece>/drafts/<midi name>_draftN.mp3` (MP3 VBR V2).
4. Verify the draft. Then write `<Piece>/notes/changes_draftN.md`, ending with a short "what you should hear differently" list.
5. Commit and push. GitHub Actions rebuilds the listening site (`.github/workflows/pages.yml`), and the new draft becomes its default.

## Engine changes must not break other pieces

- Put a new behaviour behind an environment switch at first. Make it the default only once it has been verified on the full piece.
- After any change to `pipeline/`, rebuild Disney Medley draft 9 (`pipeline/run.sh "Disney Medley" draft9_rebuild`) and compare its master WAV with the published draft 9 master.
  - If the change was not meant to affect the medley, the two must be identical.
  - If it was, say so in the commit message and render a new medley draft for the listener instead of silently changing old drafts.
  - Delete the rebuild's MP3 afterwards.
- Also render `pipeline/demo` (`pipeline/run.sh pipeline/demo draftN`) after changing instruments or the mix.
- Never re-encode or overwrite a draft the listener has already heard; drafts are a history.

## New pieces

- A MIDI file committed to `inbox/` is rendered as draft 1 by `.github/workflows/render.yml`. You can also run `pipeline/tools/ingest_inbox.sh` locally.
- `notes/draft1_render.md` records which sound each track was given. Check its warnings, and add a `track_map` to `piece.json` if a part landed on the wrong sound.

## Housekeeping

- WAV files and stems stay out of git (`.gitignore`). Commit MP3 drafts only.
- Sample libraries live in `pipeline/assets/` with their licences (`assets/SOURCES.md`). To add an instrument:
  1. add an entry to `pipeline/instruments.py`;
  2. run `pipeline/tools/import_samples.py` (it stores the samples as FLAC);
  3. pitch-check the new sound across its full range.
