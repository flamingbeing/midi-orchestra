# midi-orchestra

This repo turns MIDI scores into realistic orchestral recordings and keeps one folder per piece.

| Folder | Contents |
| --- | --- |
| [`pipeline/`](pipeline) | The rendering pipeline: code, free sample libraries, hall impulse responses and the listening-notes page. |
| [`Disney Medley/`](Disney%20Medley) | The original MIDI, the PDF and Sibelius score, every draft as an MP3, and the listener feedback. |

To add a piece, create a folder named after it with `score/`, `config/piece.json` and `notes/`, then run `pipeline/run.sh "<Piece>" draft1`. See [`pipeline/README.md`](pipeline/README.md).
