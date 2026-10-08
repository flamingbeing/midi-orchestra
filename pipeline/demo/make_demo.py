"""Instrument audition: every catalogue sound plays the same short phrase in its natural range, one after another,
then the drum kit. usage: make_demo.py OUT.mid   (prints the start time of each instrument)"""
import sys, pretty_midi as pm
# (sound, GM program, phrase root)
ORDER = [('Piccolo', 72, 86), ('Flute', 73, 74), ('Alto Flute', 73, 62), ('Oboe', 68, 69), ('Cor Anglais', 69, 62),
         ('Clarinet', 71, 62), ('Bass Clarinet', 71, 46), ('Bassoon', 70, 46), ('Contrabassoon', 70, 34),
         ('Saxophone', 66, 58), ('Recorder', 74, 77), ('Horns', 60, 57), ('Trumpet', 56, 67), ('Trombone', 57, 53),
         ('Bass Trombone', 57, 41), ('Tuba', 58, 34), ('Solo Violin', 40, 74), ('Solo Viola', 41, 62),
         ('Solo Cello', 42, 50), ('Violins', 48, 74), ('Violas', 48, 62), ('Cellos', 48, 50), ('Contrabass', 43, 38),
         ('Violins Pizz', 45, 74), ('Contrabass Pizz', 45, 38), ('Violins Trem', 44, 74), ('Choir', 52, 60),
         ('Harpsichord', 6, 67), ('Organ', 19, 60), ('Piano', 0, 67), ('Harp', 46, 67), ('Celesta', 8, 79),
         ('Glockenspiel', 9, 84), ('Xylophone', 13, 79), ('Marimba', 12, 67), ('Vibraphone', 11, 67),
         ('Tubular Bells', 14, 67), ('Timpani', 47, 45)]
PHRASE = [(0, 0, .5), (2, .5, .5), (4, 1, .5), (5, 1.5, .5), (7, 2, 1), (4, 3, .5), (0, 3.5, 1.5)]   # (interval, beat, beats)
m = pm.PrettyMIDI(initial_tempo=100); b = 60 / 100; t = 0.5
for name, prog, root in ORDER:
    i = pm.Instrument(prog, name=name)
    for iv, st, du in PHRASE:
        p = root + iv if name != 'Timpani' else root + (0 if iv < 4 else 7)
        i.notes.append(pm.Note(84, p, t + st * b, t + (st + du) * b - 0.02))
    m.instruments.append(i); print(f'{t:6.1f}s {name}'); t += 6 * b
d = pm.Instrument(0, is_drum=True, name='Drums')
for k in range(16):                                   # a simple bar pattern: kick, snare, hi-hat, crash at the start
    s = t + k * b / 2
    d.notes.append(pm.Note(70, 42, s, s + .1))
    if k % 4 == 0: d.notes.append(pm.Note(100, 36, s, s + .1))
    if k % 4 == 2: d.notes.append(pm.Note(95, 38, s, s + .1))
d.notes.append(pm.Note(110, 49, t, t + .1)); t += 8 * b
for k, p in enumerate([41, 45, 48, 52, 53, 54, 56, 60, 61, 62, 63, 64, 69, 70, 73, 75, 76, 81, 83, 49]):   # tour of the rest
    s = t + k * 0.6; d.notes.append(pm.Note(100, p, s, s + .1))
m.instruments.append(d); print(f'{t - 8 * b:6.1f}s drum kit, then percussion tour')
m.write(sys.argv[1])
