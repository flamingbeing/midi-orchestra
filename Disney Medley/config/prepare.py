"""Stage 1 (faithful): split the original Sibelius MIDI into one named track per sound.

No notes are added, removed or moved. Tempo map, time and key signatures are copied untouched.

usage: prepare.py original.mid OUT.mid
"""
import sys
import mido

src, dst = sys.argv[1:3]
mf = mido.MidiFile(src)

# (source track name, channel, program) -> output track name
def target(track, ch, prog):
    if track.startswith('Flute'): return 'Flute'
    if track.startswith('Clarinet'): return 'Clarinet'
    if track.startswith('Snare'): return 'Snare Drum'
    if track == 'Harp': return 'Harp' if prog == 46 else 'Glockenspiel'
    if track == 'Guitar': return 'Guitar'
    if track == 'Keyboard':
        return {48: 'Strings Pad', 8: 'Celesta', 0: 'Piano', 1: 'Piano'}[prog]
    base = {'Violin': 'Violins', 'Viola': 'Violas', 'Violoncello': 'Cellos'}[track]
    return base + (' Pizz' if prog == 45 else '')

ORDER = ['Flute', 'Clarinet', 'Glockenspiel', 'Celesta', 'Harp', 'Guitar', 'Piano', 'Snare Drum', 'Strings Pad',
         'Violins', 'Violins Pizz', 'Violas', 'Violas Pizz', 'Cellos', 'Cellos Pizz']
CHANNEL = {n: i if i < 9 else i + 1 for i, n in enumerate(ORDER)}
CHANNEL['Snare Drum'] = 9

events = {n: [] for n in ORDER}           # absolute tick, message
for tr in mf.tracks[1:]:
    name = next((m.name for m in tr if m.type == 'track_name'), '')
    tick, prog = 0, {}
    for m in tr:
        tick += m.time
        if m.type == 'program_change':
            prog[m.channel] = m.program
        elif m.type in ('note_on', 'note_off'):
            out = target(name, m.channel, prog.get(m.channel, 0))
            events[out].append((tick, m.copy(channel=CHANNEL[out], time=0)))

out = mido.MidiFile(type=1, ticks_per_beat=mf.ticks_per_beat)
out.tracks.append(mido.MidiTrack(m.copy() for m in mf.tracks[0]))   # conductor: tempo, meters, key
counts = {}
for n in ORDER:
    evs = sorted(events[n], key=lambda e: (e[0], 0 if (e[1].type == 'note_off' or e[1].velocity == 0) else 1))
    if not evs:
        continue
    tr = mido.MidiTrack()
    tr.append(mido.MetaMessage('track_name', name=n, time=0))
    if n != 'Snare Drum':
        tr.append(mido.Message('program_change', channel=CHANNEL[n], program=0, time=0))
    now = 0
    for t, m in evs:
        tr.append(m.copy(time=t - now)); now = t
    out.tracks.append(tr)
    counts[n] = sum(1 for _, m in evs if m.type == 'note_on' and m.velocity > 0)
out.save(dst)
src_notes = sum(1 for tr in mf.tracks for m in tr if m.type == 'note_on' and m.velocity > 0)
print(counts, '| total', sum(counts.values()), 'of', src_notes)
assert sum(counts.values()) == src_notes
