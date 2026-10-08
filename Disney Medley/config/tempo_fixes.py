"""Draft-8 tempo map fixes (notes and ticks unchanged; only set_tempo events move).

usage: tempo_v8.py IN.mid OUT.mid

1. The +5% region (user: "Beauty and the Beast .. Reflection slightly draggy") ended at MIDI bar 145 (tick 534960),
   six bars before Reflection. Move the step back to 92 bpm onto the Reflection double bar (score m150, tick 556080).
2. Go The Distance's q=92 (x1.05 = 96.6) sat one eighth after the barline (tick 483600, a Sibelius export quirk);
   put it on the barline (tick 483120).
3. Fermata at score m129 (9/8 bar, last two eighths held, ticks 481680-483120): played as a strict 1.5x eighth. Hold it
   at 2x the written eighth (tempo 69.3 bpm over those two eighths) like a conducted fermata. FERMATA=0 disables.
"""
import os, sys
import mido

src, dst = sys.argv[1:3]
m = mido.MidiFile(src)
tr = m.tracks[0]
ev, t = [], 0
for e in tr:
    t += e.time
    ev.append([t, e])
out = []
for t, e in ev:
    if e.type == 'set_tempo' and 534960 <= t < 556080 and round(mido.tempo2bpm(e.tempo), 1) == 92.0:
        continue                                                   # (1) drop the mid-song step
    if e.type == 'set_tempo' and t == 483600 and round(mido.tempo2bpm(e.tempo), 1) == 96.6:
        t = 483120                                                 # (2) onto the barline
    out.append([t, e])
out.append([556080, mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(92.0), time=0)])     # (1)
if os.environ.get('FERMATA', '1') == '1':
    out.append([481680, mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(69.3), time=0)])  # (3)
out.sort(key=lambda p: (p[0], 0 if p[1].type == 'time_signature' else 1))
# the 96.6 event at 483120 must come after the fermata tempo (same track, later tick: fine)
new = mido.MidiTrack()
prev = 0
for t, e in out:
    new.append(e.copy(time=t - prev)); prev = t
m.tracks[0] = new
m.save(dst)
for t, e in out:
    if e.type == 'set_tempo' and 470000 <= t <= 560000:
        print(t, round(mido.tempo2bpm(e.tempo), 2))
