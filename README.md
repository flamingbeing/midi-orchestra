# midi-orchestra

This repo turns MIDI scores into realistic orchestral recordings and keeps one folder per piece.

| Folder | Contents |
| --- | --- |
| [`inbox/`](inbox) | Upload a MIDI file here on GitHub. Draft 1 is then rendered automatically, along with its listening page. |
| [`pipeline/`](pipeline) | The rendering pipeline: code, free sample libraries, hall impulse responses, the listening-page builder and an instrument demo. |
| [`Disney Medley/`](Disney%20Medley) | The original MIDI, the PDF and Sibelius score, every draft as an MP3, and the listener feedback. |

**Listening site:** `https://flamingbeing.github.io/midi-orchestra/` has one page per piece. Play any draft, mark passages, comment, and download the MP3. It updates whenever a draft is added.

**Improving a piece:** open a Claude Code session on this repo and paste the listener's comments. [`CLAUDE.md`](CLAUDE.md) tells the session how drafts are improved and checked.
