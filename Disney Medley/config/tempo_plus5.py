"""Disney Medley, draft 3 listener request: "Beauty and the Beast .. Reflection slightly draggy" -> +5 % tempo from the
Beauty and the Beast tempo change (202.15 s) to the downbeat of MIDI bar 145. Only set_tempo events change.

usage: tempo_plus5.py PREPARED.mid OUT.mid
"""
import sys
import mido, pretty_midi as pm

src, dst = sys.argv[1:3]
m = pm.PrettyMIDI(src); db = m.get_downbeats()
t0, t1 = 202.15, db[145 - 1]
k0, k1 = m.time_to_tick(t0), m.time_to_tick(t1)
mf = mido.MidiFile(src); cond = mf.tracks[0]
ev = []; tick = 0
for msg in cond:
    tick += msg.time; ev.append((tick, msg))


def tempo_at(k):
    t = 500000
    for tk, msg in ev:
        if tk <= k and msg.type == 'set_tempo': t = msg.tempo
    return t


end_tempo = tempo_at(k1)
new = []
for tk, msg in ev:
    if msg.type == 'set_tempo' and k0 <= tk < k1:
        msg = msg.copy(tempo=int(msg.tempo / 1.05))
    new.append((tk, msg))
new.append((k1, mido.MetaMessage('set_tempo', tempo=end_tempo)))   # restore at Reflection
new.sort(key=lambda e: (e[0], 0 if e[1].type == 'set_tempo' else 1))
tr = mido.MidiTrack(); now = 0
for tk, msg in new:
    if msg.type == 'end_of_track': continue
    tr.append(msg.copy(time=tk - now)); now = tk
tr.append(mido.MetaMessage('end_of_track', time=0))
mf.tracks[0] = tr; mf.save(dst)
