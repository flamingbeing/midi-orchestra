#!/bin/bash
# Disney Medley: original MIDI -> render input (called by pipeline/run.sh as: make_input.sh ORIGINAL.mid OUT.mid TMPDIR)
set -e
D=$(cd "$(dirname "$0")" && pwd)
"$PY" -I "$D/prepare.py" "$1" "$3/prepared.mid"            # Sibelius tracks -> named sounds (note-identical)
"$PY" -I "$D/tempo_plus5.py" "$3/prepared.mid" "$3/plus5.mid"   # listener request (draft 3)
"$PY" -I "$D/tempo_fixes.py" "$3/plus5.mid" "$2"                # draft 8 tempo-map fixes + fermata
