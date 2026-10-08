#!/bin/bash
# For every MIDI file in inbox/: create its piece folder, render draft 1, set up its listening page, and remove it
# from the inbox. Prints one line per new piece folder. Used by .github/workflows/render.yml; runs locally too.
# env: PY (python with pipeline/requirements.txt), WORK (scratch dir)
set -eo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
PY=${PY:-python3}; export PY
shopt -s nullglob nocaseglob
for f in "$ROOT"/inbox/*.mid "$ROOT"/inbox/*.midi; do
  folder=$("$PY" -I "$ROOT/pipeline/tools/new_piece.py" "$f" "$ROOT")
  log=$(mktemp)
  "$ROOT/pipeline/run.sh" "$ROOT/$folder" draft1 2>&1 | tee "$log" >&2
  {
    echo "# Draft 1 render notes"
    echo
    echo "Source: \`$(basename "$f")\`. Which sound each MIDI track was given (from its name or General MIDI program):"
    echo
    grep -E "^notes per sound|^WARNING" "$log" | sed 's/^/- /'
  } > "$ROOT/$folder/notes/draft1_render.md"
  rm -f "$log"
  "$PY" -I "$ROOT/pipeline/listening_page/update_config.py" "$ROOT/$folder" >&2
  rm "$f"
  echo "$folder"
done
