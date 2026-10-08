"""Per-note loudness consistency per stem: residual of note RMS vs velocity-expected level; adjacent-note jumps in phrases."""
import sys, numpy as np, soundfile as sf, pretty_midi as pm, os
D, MID = sys.argv[1:3]
m = pm.PrettyMIDI(MID)
for inst in m.instruments:
    p = os.path.join(D, inst.name + '.wav')
    if not os.path.exists(p) or len(inst.notes) < 20: continue
    x, sr = sf.read(p); x = x.mean(1) if x.ndim == 2 else x
    ns = sorted(inst.notes, key=lambda n: n.start)
    lv = []
    for n in ns:
        a = int(max(0, n.start) * sr); b = int((n.start + min(0.3, max(0.08, n.end - n.start))) * sr)
        lv.append(20 * np.log10(np.sqrt(np.mean(x[a:b] ** 2)) + 1e-9))
    lv = np.array(lv); vel = np.array([n.velocity for n in ns], float)
    exp = 40 * np.log10(vel / 127)                       # quadratic velocity law, dB
    res = lv - exp; res -= np.median(res)
    jumps = [abs(lv[i+1] - lv[i] - (exp[i+1] - exp[i])) for i in range(len(ns)-1) if ns[i+1].start - ns[i].end < 0.15]
    print(f'{inst.name:13s} n={len(ns):4d} level med {np.median(lv):6.1f} dB  resid SD {np.std(res):5.2f} dB  p90 adj-jump {np.percentile(jumps,90) if jumps else 0:5.2f} dB')
