#!/bin/bash
# Render one piece: MIDI -> stems -> hall mix -> master -> m4a + mp3.
#
# usage: pipeline/run.sh "PIECE FOLDER" DRAFT_NAME
#   PIECE FOLDER  e.g. "Disney Medley". Needs config/piece.json; its "midi" entry names the MIDI file, relative to
#                 the folder. If config/make_input.sh exists it turns that MIDI into the render input; otherwise
#                 pipeline/prepare.py does it.
#   DRAFT_NAME    e.g. draft10 -> writes "PIECE FOLDER/drafts/draft10.mp3" (192k) and .m4a (AAC 256k)
# env: PY (python with requirements.txt), WORK (scratch dir, needs ~3 GB), MASTER_AIR (master high shelf)
set -e
PIPE=$(cd "$(dirname "$0")" && pwd)
PIECE=$(cd "$1" && pwd); NAME=$2
PY=${PY:-python3}; export PY
WORK=${WORK:-/tmp/midi-orchestra-work}/$(basename "$PIECE")/$NAME
mkdir -p "$WORK" "$PIECE/drafts"
export PIECE_JSON="$PIECE/config/piece.json"
MIDI="$PIECE/$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1]))['midi'])" "$PIECE_JSON")"

if [ -x "$PIECE/config/make_input.sh" ]; then
  "$PIECE/config/make_input.sh" "$MIDI" "$WORK/input.mid" "$WORK"
else
  "$PY" -I "$PIPE/prepare.py" "$MIDI" "$WORK/input.mid" "$PIECE_JSON"
fi
PIECE="$PIECE_JSON" "$PY" -I "$PIPE/render.py" "$WORK/input.mid" none "$WORK/stems" 2>&1 | grep -v -i warn
[ -f "$WORK/stems/Clarinet.wav" ] && ffmpeg -y -loglevel error -i "$WORK/stems/Clarinet.wav" \
  -af "equalizer=f=2200:t=q:w=1.0:g=3" -c:a pcm_f32le "$WORK/_c.wav" && mv "$WORK/_c.wav" "$WORK/stems/Clarinet.wav"
PIECE="$PIECE_JSON" "$PY" -I "$PIPE/mix.py" "$WORK/stems" "$WORK/dry.wav" "$WORK/input.mid"

# master: no bus compressor; gentle air shelf, static gain to -16 LUFS, safety limiter
MASTER_AIR=${MASTER_AIR-,treble=g=3:f=7000:t=s:w=0.6}
ffmpeg -y -loglevel error -i "$WORK/dry.wav" -af "highpass=f=28,equalizer=f=220:t=q:w=1:g=-1.0${MASTER_AIR}" -c:a pcm_f32le "$WORK/pre.wav"
I=$(ffmpeg -hide_banner -i "$WORK/pre.wav" -af ebur128=framelog=quiet -f null - 2>&1 | grep -E "^ +I:" | awk '{print $2}')
G=$(python3 -c "print(-16-($I))")
ffmpeg -y -loglevel error -i "$WORK/pre.wav" -af "volume=${G}dB,alimiter=limit=0.84:attack=5:release=80:level=false" -c:a pcm_f32le "$WORK/master.wav"
ffmpeg -y -loglevel error -i "$WORK/master.wav" -c:a aac -b:a 256k -movflags +faststart "$PIECE/drafts/$NAME.m4a"
ffmpeg -y -loglevel error -i "$WORK/master.wav" -c:a libmp3lame -b:a 192k "$PIECE/drafts/$NAME.mp3"
rm -f "$WORK/dry.wav" "$WORK/pre.wav"
echo "done: $PIECE/drafts/$NAME.mp3 (master and stems in $WORK)"
