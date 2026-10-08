"""Stage 1 (faithful), any MIDI: regroup the notes into one named track per sound the renderer knows.

No notes are added, removed or moved. Tempo, time signature and key signature events are copied untouched into the
conductor track. Each note goes to a sound chosen from its General MIDI program (and, for pizzicato/tremolo strings,
its pitch). Programs without a dedicated sound are mapped to the closest one and listed as warnings.

usage: prepare.py IN.mid OUT.mid [PIECE.json]

PIECE.json may carry "track_map": {"<source track name>": "<sound>"} to override the program-based choice
(for example {"Violin II": "Violins"}). The sounds that need an "extra_tracks" entry in PIECE.json to render
(Contrabass, Oboe, Horns, Trumpet, Trombone, Timpani) are printed at the end so you can paste them in.
"""
import json, sys
import mido

src, dst = sys.argv[1:3]
piece = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
TRACK_MAP = piece.get('track_map', {})
mf = mido.MidiFile(src)

# sounds render.py has a bank for. The last six render through "extra_tracks" (render.py TRACKS_OLD).
ORDER = ['Flute', 'Oboe', 'Clarinet', 'Horns', 'Trumpet', 'Trombone', 'Timpani', 'Glockenspiel', 'Celesta', 'Harp',
         'Guitar', 'Piano', 'Snare Drum', 'Strings Pad', 'Violins', 'Violins Pizz', 'Violas', 'Violas Pizz', 'Cellos',
         'Cellos Pizz', 'Contrabass']
EXTRA = ['Contrabass', 'Oboe', 'Horns', 'Trumpet', 'Trombone', 'Timpani']
warn = {}


def by_pitch(pitch, kind):
    """Pizzicato / tremolo string programs carry no section, so pick it from the register."""
    base = 'Violins' if pitch >= 67 else 'Violas' if pitch >= 55 else 'Cellos' if pitch >= 36 else 'Contrabass'
    return base + (' Pizz' if kind == 'pizz' and base != 'Contrabass' else '')


NAME_HINTS = [('violin', 'Violins'), ('viola', 'Violas'), ('cello', 'Cellos'), ('violoncello', 'Cellos'),
              ('contrabass', 'Contrabass'), ('double bass', 'Contrabass'), ('flute', 'Flute'), ('piccolo', 'Flute'),
              ('oboe', 'Oboe'), ('clarinet', 'Clarinet'), ('horn', 'Horns'), ('trumpet', 'Trumpet'),
              ('trombone', 'Trombone'), ('harp', 'Harp'), ('celest', 'Celesta'), ('glock', 'Glockenspiel'),
              ('timpani', 'Timpani'), ('snare', 'Snare Drum')]


def sound(track, ch, prog, pitch):
    if track in TRACK_MAP:
        return TRACK_MAP[track]
    if ch == 9:
        return 'Snare Drum'                      # every GM drum note is played on the snare (see pipeline/README.md)
    # notation programs export string sections as "String Ensemble" and similar, so an orchestral instrument name
    # in the track name wins - except for programs that define a distinct sound (keyboards, mallets, guitar, pizz, harp)
    low = track.lower()
    hint = next((s for key, s in NAME_HINTS if key in low), None)
    if prog is None:                             # notes before any program change: trust the name, else GM piano
        if hint:
            return hint
        prog = 0
    if prog == 45 and hint in ('Violins', 'Violas', 'Cellos'):
        return hint + ' Pizz'
    if hint and not (prog <= 15 or prog in (24, 25, 45, 46, 47)):
        return hint
    exact = {8: 'Celesta', 9: 'Glockenspiel', 24: 'Guitar', 25: 'Guitar', 40: 'Violins', 41: 'Violas', 42: 'Cellos',
             43: 'Contrabass', 46: 'Harp', 47: 'Timpani', 56: 'Trumpet', 57: 'Trombone', 60: 'Horns', 68: 'Oboe',
             71: 'Clarinet', 73: 'Flute'}
    if prog in exact:
        return exact[prog]
    if prog <= 7:
        return 'Piano'
    if prog == 44:
        return by_pitch(pitch, 'arco')
    if prog == 45:
        return by_pitch(pitch, 'pizz')
    if 48 <= prog <= 51:
        return 'Strings Pad'
    near = {range(10, 16): 'Glockenspiel', range(16, 24): 'Strings Pad', range(26, 40): 'Guitar',
            range(52, 56): 'Strings Pad', range(58, 60): 'Trombone', range(61, 64): 'Horns', range(64, 68): 'Clarinet',
            range(69, 71): 'Clarinet', range(72, 73): 'Flute', range(74, 80): 'Flute', range(80, 128): 'Strings Pad'}
    out = next(v for r, v in near.items() if prog in r)
    warn[(track, prog)] = out
    return out


events = {n: [] for n in ORDER}
conductor = []
for tr in mf.tracks:
    name = next((m.name for m in tr if m.type == 'track_name'), '')
    tick, prog = 0, {}
    for m in tr:
        tick += m.time
        if m.type in ('set_tempo', 'time_signature', 'key_signature'):
            conductor.append((tick, m.copy(time=0)))
        elif m.type == 'program_change':
            prog[m.channel] = m.program
        elif m.type in ('note_on', 'note_off'):
            out = sound(name, m.channel, prog.get(m.channel), m.note)
            if out not in events:
                sys.exit(f'track_map sends {name!r} to unknown sound {out!r}; choose one of {ORDER}')
            events[out].append((tick, m))

CHANNEL = {n: i if i < 9 else i + 1 for i, n in enumerate(n for n in ORDER if n != 'Snare Drum')}
CHANNEL['Snare Drum'] = 9
out = mido.MidiFile(type=1, ticks_per_beat=mf.ticks_per_beat)
ct = mido.MidiTrack(); now = 0
for t, m in sorted(conductor, key=lambda e: e[0]):
    ct.append(m.copy(time=t - now)); now = t
out.tracks.append(ct)
counts = {}
for n in ORDER:
    evs = sorted(events[n], key=lambda e: (e[0], 0 if (e[1].type == 'note_off' or e[1].velocity == 0) else 1))
    if not evs:
        continue
    chan = min(CHANNEL[n], 15)
    tr = mido.MidiTrack()
    tr.append(mido.MetaMessage('track_name', name=n, time=0))
    if n != 'Snare Drum':
        tr.append(mido.Message('program_change', channel=chan, program=0, time=0))
    now = 0
    for t, m in evs:
        tr.append(m.copy(channel=chan, time=t - now)); now = t
    out.tracks.append(tr)
    counts[n] = sum(1 for _, m in evs if m.type == 'note_on' and m.velocity > 0)
out.save(dst)
src_notes = sum(1 for tr in mf.tracks for m in tr if m.type == 'note_on' and m.velocity > 0)
print('notes per sound:', counts, '| total', sum(counts.values()), 'of', src_notes)
assert sum(counts.values()) == src_notes
for (track, prog), s in warn.items():
    print(f'WARNING: {track or "(unnamed track)"} uses GM program {prog}, which has no dedicated sound -> {s}')
need = [n for n in EXTRA if n in counts]
if need:
    print('add to PIECE.json so these render:', json.dumps({'extra_tracks': {n: n for n in need}}))
