# Sample and impulse-response sources

The pipeline loads only the files kept here. They come from the original free libraries; the audio is unchanged, although files added through `pipeline/tools/import_samples.py` are stored as lossless FLAC. Each library keeps its own licence, listed below. Some licences are non-commercial: they allow sharing these files and the renders made with them, but not selling them.

| Folder | Library | Licence | Used for |
| --- | --- | --- | --- |
| `samples/VSCO-2-CE_git/` | Versilian Studios Chamber Orchestra 2, Community Edition ([GitHub](https://github.com/sgossner/VSCO-2-CE)) | CC0 1.0. The organ was recorded by Simon Dalzell of Ivy Audio and is redistributed with Versilian Studios' permission (`Keys/Organ/Info.txt`). | String sections (sustain, pizzicato, tremolo), clarinet, oboe, bassoon, horn, trumpet, tenor trombone, tuba, solo violin, contrabass pizzicato and organ |
| `samples/sso_git/` | Sonatina Symphonic Orchestra (Mattias Westlund / P. Eastman) | Creative Commons Sampling Plus 1.0 | Celesta, piccolo, alto flute, cor anglais, bass clarinet, contrabassoon, bass trombone, solo viola, solo cello, contrabass section (sustain, tremolo), choir and harpsichord |
| `samples/VCSL/` | Versilian Community Sample Library ([GitHub](https://github.com/sgossner/VCSL)) | CC0 1.0 | Tenor saxophone, alto recorder, marimba, xylophone, vibraphone, tubular bells and the General MIDI drum-kit percussion (bass drum, toms, hi-hat, cymbals, gong, tambourine, triangle, woodblock, bongos, congas, claves and more) |
| `samples/tiny-orchestra/` | tiny-orchestra npm package, a compact VSCO-2 subset ([GitHub](https://github.com/MarianBecher/tiny-orchestra)) | CC0 1.0 | Glockenspiel, snare and timpani |
| `samples/tonejs-instrument-*-wav/` | tonejs-instruments WAV packages ([GitHub](https://github.com/Makefully-Studios/tonejs-instruments)) | MIT (as the npm packages declare it) | Flute, piano, nylon guitar and harp (the horn, trumpet, trombone and xylophone sets still load, but the catalogue's better samples replace them) |
| `hall/marco_tree/` | 3D-MARCo, St Paul's Hall, Huddersfield: per-seat impulse responses rebuilt as a Decca tree plus a Hamasaki ambience pair (see `hall/README.txt`) | CC BY-NC 3.0 | Concert-hall reverb (each instrument plays from its own measured seat) |

**Attribution for the hall:** "3D-MARCo, Hyunkook Lee & Dale Johnson, Applied Psychoacoustics Lab, University of Huddersfield (zenodo.org/records/3477602)".

`hall/seating.json` maps each instrument to a stage position.
