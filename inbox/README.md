# Inbox

Drop a MIDI file (`.mid` or `.midi`) here, using **Add file → Upload files** on GitHub, and commit it to `main`.
GitHub Actions then:

1. creates a folder named after the file (e.g. `My Song.mid` → `My Song/`) with the score, settings and notes;
2. renders draft 1 (`My Song/drafts/my_song_draft1.mp3`, about 5–15 minutes);
3. adds the piece to the listening site (`https://<owner>.github.io/<repo>/`).

Export MIDI from your notation program (Sibelius, MuseScore, Dorico…). Name the tracks after the instruments
("Flute", "Horn in F", "Violin I", …): that is how each part gets its sound. Scanned sheet music (PDF) is not
supported, because automatic note recognition is not reliable enough to keep the music faithful.
