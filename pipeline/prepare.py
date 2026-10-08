"""Stage 1 (faithful), any MIDI: regroup the notes into one named track per sound the renderer knows.

No notes are added, removed or moved. Tempo, time signature and key signature events are copied untouched into the
conductor track. Each note goes to a sound chosen from its General MIDI program (and, for pizzicato/tremolo strings,
its pitch). Programs without a dedicated sound are mapped to the closest one and listed as warnings.

usage: prepare.py IN.mid OUT.mid [PIECE.json]

PIECE.json may carry "track_map": {"<source track name>": "<sound>"} to override the automatic choice
(for example {"Violin II": "Violins"}). Every sound listed in ORDER renders without further configuration.
"""
import json, os, sys
import mido
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instruments as INS

src, dst = sys.argv[1:3]
piece = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
TRACK_MAP = piece.get('track_map', {})
mf = mido.MidiFile(src)

# every sound the renderer has: the core set (render.py TRACKS), the catalogue (instruments.py) and Timpani.
# Channel-10 drum notes all go to one track; render.py plays each GM drum note on its own instrument (instruments.DRUMS).
CORE = ['Flute', 'Clarinet', 'Glockenspiel', 'Celesta', 'Harp', 'Guitar', 'Piano', 'Strings Pad', 'Violins',
        'Violins Pizz', 'Violas', 'Violas Pizz', 'Cellos', 'Cellos Pizz']
ORDER = CORE + list(INS.CATALOG) + ['Timpani', 'Snare Drum']
warn = {}
SECTIONS = ('Violins', 'Violas', 'Cellos', 'Contrabass')


def by_pitch(pitch):
    """Pizzicato / tremolo string programs carry no section, so pick it from the register."""
    return 'Violins' if pitch >= 67 else 'Violas' if pitch >= 55 else 'Cellos' if pitch >= 36 else 'Contrabass'


def string_art(section, art):
    if art == 'pizz':
        return 'Contrabass Pizz' if section == 'Contrabass' else section + ' Pizz'
    return section + ' Trem'


# track-name keywords, most specific first
NAME_HINTS = [('english horn', 'Cor Anglais'), ('cor anglais', 'Cor Anglais'), ('alto flute', 'Alto Flute'),
              ('piccolo', 'Piccolo'), ('bass clarinet', 'Bass Clarinet'), ('contrabassoon', 'Contrabassoon'),
              ('contra bassoon', 'Contrabassoon'), ('bassoon', 'Bassoon'), ('sax', 'Saxophone'), ('recorder', 'Recorder'),
              ('bass trombone', 'Bass Trombone'), ('trombone', 'Trombone'), ('tuba', 'Tuba'), ('horn', 'Horns'),
              ('trumpet', 'Trumpet'), ('cornet', 'Trumpet'), ('flugel', 'Trumpet'), ('flute', 'Flute'), ('oboe', 'Oboe'),
              ('clarinet', 'Clarinet'), ('solo violin', 'Solo Violin'), ('violin solo', 'Solo Violin'),
              ('solo viola', 'Solo Viola'), ('viola solo', 'Solo Viola'), ('solo cello', 'Solo Cello'),
              ('cello solo', 'Solo Cello'), ('contrabass', 'Contrabass'), ('double bass', 'Contrabass'),
              ('string bass', 'Contrabass'), ('basses', 'Contrabass'), ('violoncello', 'Cellos'), ('cello', 'Cellos'),
              ('viola', 'Violas'), ('violin', 'Violins'), ('choir', 'Choir'), ('chorus', 'Choir'), ('voice', 'Choir'),
              ('vocal', 'Choir'), ('soprano', 'Choir'), ('aahs', 'Choir'), ('oohs', 'Choir'),
              ('harpsichord', 'Harpsichord'), ('organ', 'Organ'), ('celest', 'Celesta'), ('glock', 'Glockenspiel'),
              ('xylo', 'Xylophone'), ('marimba', 'Marimba'), ('vibraphone', 'Vibraphone'), ('vibes', 'Vibraphone'),
              ('tubular', 'Tubular Bells'), ('chimes', 'Tubular Bells'), ('harp', 'Harp'), ('timpani', 'Timpani'),
              ('snare', 'Snare Drum')]
# General MIDI program -> sound; the second set is "closest available" and is reported as a warning
GM = {**{p: 'Piano' for p in range(0, 6)}, 6: 'Harpsichord', 8: 'Celesta', 9: 'Glockenspiel', 11: 'Vibraphone',
      12: 'Marimba', 13: 'Xylophone', 14: 'Tubular Bells', **{p: 'Organ' for p in range(16, 21)}, 24: 'Guitar',
      25: 'Guitar', 32: 'Contrabass Pizz', 40: 'Violins', 41: 'Violas', 42: 'Cellos', 43: 'Contrabass', 46: 'Harp',
      47: 'Timpani', 48: 'Strings Pad', 49: 'Strings Pad', 50: 'Strings Pad', 51: 'Strings Pad', 52: 'Choir',
      53: 'Choir', 56: 'Trumpet', 57: 'Trombone', 58: 'Tuba', 60: 'Horns', **{p: 'Saxophone' for p in range(64, 68)},
      68: 'Oboe', 69: 'Cor Anglais', 70: 'Bassoon', 71: 'Clarinet', 72: 'Piccolo', 73: 'Flute', 74: 'Recorder'}
NEAR = {7: 'Harpsichord', 10: 'Celesta', 15: 'Harp', 21: 'Organ', 22: 'Organ', 23: 'Organ',
        **{p: 'Guitar' for p in range(26, 32)}, **{p: 'Contrabass Pizz' for p in range(33, 40)}, 54: 'Choir',
        55: 'Strings Pad', 59: 'Trumpet', 61: 'Horns', 62: 'Horns', 63: 'Horns', **{p: 'Flute' for p in range(75, 80)},
        **{p: 'Strings Pad' for p in range(80, 104)}, 104: 'Guitar', 105: 'Guitar', 106: 'Guitar', 107: 'Harp',
        108: 'Marimba', 109: 'Oboe', 110: 'Solo Violin', 111: 'Oboe', 112: 'Glockenspiel', 113: 'Xylophone',
        114: 'Marimba', 115: 'Xylophone', **{p: 'Timpani' for p in range(116, 119)},
        **{p: 'Strings Pad' for p in range(119, 128)}}


def sound(track, ch, prog, pitch):
    if track in TRACK_MAP:
        return TRACK_MAP[track]
    if ch == 9:
        return 'Snare Drum'                      # the drum track: render.py maps each GM drum note to its instrument
    # notation programs export string sections as "String Ensemble" and similar, so an orchestral instrument name
    # in the track name wins - except for programs that define a distinct sound (keyboards, mallets, guitar, harp)
    if track in ORDER and track != 'Snare Drum':
        return track                             # already named after one of our sounds
    low = track.lower()
    hint = next((s for key, s in NAME_HINTS if key in low), None)
    sec = {'Solo Violin': 'Violins', 'Solo Viola': 'Violas', 'Solo Cello': 'Cellos'}.get(hint, hint)
    if sec in SECTIONS and ('pizz' in low or 'trem' in low):     # "Violins (pizz.)", "Cello trem"
        return string_art(sec, 'pizz' if 'pizz' in low else 'trem')
    if prog is None:                             # notes before any program change: trust the name, else GM piano
        if hint:
            return hint
        prog = 0
    if prog in (44, 45):                         # tremolo / pizzicato strings: section from the name, else the register
        return string_art(sec if sec in SECTIONS else by_pitch(pitch), 'trem' if prog == 44 else 'pizz')
    if hint and (prog == 0 or not (prog <= 15 or prog in (24, 25, 46, 47))):   # many exporters leave program 0
        return hint
    if prog in GM:
        return GM[prog]
    warn[(track, prog)] = NEAR[prog]
    return NEAR[prog]


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
