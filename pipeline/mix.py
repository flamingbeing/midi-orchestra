"""Draft-9 mix (draft-8 mix + V9_* balance fixes, see changes_v9.md): balance + melody ducking + per-seat measured hall (3D-MARCo, St Paul's Hall Huddersfield),
loudness calibrated AFTER the hall to the TARGET table (draft 7b), with the draft-8 changes (see changes_v8.md).

usage: mix_v8.py STEMS_DIR OUT.wav [MIDI]      (MIDI only for the optional in-hall melody stats, env MIXSTATS=1)

Every draft-8 change has an env switch (default = adopted setting) so it can be A/B'd:
  V8_PREDUCK=1   duck the accompaniment's dry signal BEFORE the hall (tails decay naturally) + hold through short rests
  V8_NOVLADUCK=1 violas no longer ducked (string section breathes together)
  V8_AMB=1       more hall ambience (C80 nearer a real tree pickup) + 3.5 ms later arrival for harp/keyboards (stage depth)
  V8_LFMONO=1    narrow the out-of-phase cello bass below 150 Hz (mono-compatible low end)
  V8_HPF=1       high-pass Celesta (140 Hz) and Glockenspiel (400 Hz): remove mechanism rumble below the lowest note
  V8_RETARGET=1  re-balance after the render fixes (Celesta -2, Violins -3.5, Flute 1.5, cello 2:20 automation +5)
  V8_CLARAUTO=1  section-specific clarinet lift/trim (ballad and finale lift, 5:05-5:50 ff trim)
"""
import json, os, sys
import numpy as np, soundfile as sf
import pyloudnorm as pyln
from scipy.ndimage import uniform_filter1d, binary_closing
from scipy.signal import oaconvolve, sosfilt, sosfiltfilt, butter, lfilter

D, OUT = sys.argv[1:3]
MID = sys.argv[3] if len(sys.argv) > 3 else None
SR = 44100
A = os.path.join(os.environ.get('ASSETS', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')), 'hall')
SEATS = json.load(open(os.path.join(A, 'seating.json')))
pans = json.load(open(os.path.join(D, 'pans.json')))
on = lambda k, d='1': os.environ.get(k, d) == '1'

# perceived (K-weighted) loudness of each stem while it plays, relative to the melody instruments (user-tuned in drafts 2-6)
TARGET = {'Flute': 1, 'Clarinet': 4.5, 'Violins': -2, 'Cellos': -3.5, 'Violas': -5, 'Piano': -4, 'Harp': -8.5,
          'Guitar': -11, 'Celesta': -4, 'Glockenspiel': -9, 'Strings Pad': -9, 'Snare Drum': -10,
          'Violins Pizz': -6, 'Violas Pizz': -6, 'Cellos Pizz': -6}
# draft 8: the string/layer fixes cost the celesta ~1.4 dB of audibility -> Celesta -4 -> -2; violins back toward the
# draft-6 balance the user approved ("strings and flute good"; in-hall calibration had lifted them 3.7 dB) -> -2 -> -3.5;
# flute +0.5 to keep its in-hall 1-4 kHz SNR within 0.5 dB of draft 7b.
if on('V8_RETARGET'):
    TARGET.update({'Celesta': -2.0, 'Violins': -3.5, 'Flute': 1.5})
if os.environ.get('V9_MELTGT', '1') == '1':
    # draft 9: breaths, re-tonguing and phrase-end tapers put short silences inside the melody notes and the clarinet
    # is trimmed at 2:08-2:26; +0.5 / +0.3 dB keeps the melody's in-hall 1-4 kHz SNR (p10) within the v8 tolerance
    TARGET.update({'Clarinet': 5.0, 'Flute': 1.8})
for kv in filter(None, os.environ.get('V8_TARGET', '').split(',')):      # e.g. V8_TARGET=Violins:-3
    k_, v_ = kv.split(':'); TARGET[k_] = float(v_)
ACCOMP = {'Harp', 'Guitar', 'Piano', 'Strings Pad', 'Violas', 'Glockenspiel'}       # dip under flute/clarinet (not celesta)
if on('V8_NOVLADUCK'):
    ACCOMP.discard('Violas')
AUTOMATION = {'Cellos': [(130.0, 152.0, float(os.environ.get('V8_CELLO', '5.0' if on('V8_RETARGET') else '3.5')))]}   # cello masked by guitar around 2:20
if on('V8_CLARAUTO'):
    # draft-8 times (work/draft8_input.mid): ballad 0:17-0:46 lift, 5:05-5:50 ff (G5-A5, vel 100-119) trim, finale lift
    AUTOMATION['Clarinet'] = [(17.3, 46.3, float(os.environ.get('V8_CL1', '4.5'))),
                              (304.6, 349.6, float(os.environ.get('V8_CL2', '-3.0'))),
                              (351.9, 412.4, float(os.environ.get('V8_CL3', '3.0')))]
on9 = lambda k: os.environ.get(k, '1') == '1'
if on9('V9_CLARTRIM'):
    # the ff clarinet at 2:08-2:26 is 74-86 % of what masks the cello at 2:20 and makes that passage almost tutti-loud
    AUTOMATION['Clarinet'].append((128.0, 146.0, float(os.environ.get('V9_CLT', '-2.0'))))
if on9('V9_FLUTELIFT'):
    # flute-led passages sat 3-5 dB under the reference arc; at 6:30-6:52 the flute melody was buried by the clarinet lift
    AUTOMATION['Clarinet'] = [t for t in AUTOMATION['Clarinet'] if t[0] != 351.9] + [(351.9, 390.0, 3.0), (390.0, 412.4, float(os.environ.get('V9_CL3B', '2.0')))]
    AUTOMATION['Flute'] = [(153.0, 176.0, 2.0), (198.0, 216.0, 3.0), (354.0, 362.0, 2.0)]
if on9('V9_VIOLINTOP'):
    # strings-only passage 0:46-1:17: violins carry the tune -> inner voices back off
    AUTOMATION['Violas'] = [(46.3, 77.3, -3.0)]
    AUTOMATION['Cellos'] = AUTOMATION['Cellos'] + [(46.3, 77.3, -1.5)]
if on9('V9_PAD'):
    # opening pp strings pad was 8.7 dB under the reference arc: louder target, not ducked (it plays 0:03-0:26 only)
    TARGET['Strings Pad'] = -5.0; ACCOMP.discard('Strings Pad')
# piece config (env PIECE=path/to/piece.json). Its "mix" block sets the balance automation (times in seconds of the
# rendered piece; none if absent) and may replace the accompaniment set and update loudness targets. Without PIECE
# (legacy invocation) the draft-9 Disney Medley settings above apply.
PIECE = json.load(open(os.environ['PIECE'])) if os.environ.get('PIECE') else None
if PIECE is not None:
    _pm = PIECE.get('mix', {})
    AUTOMATION = {k: [tuple(p) for p in v] for k, v in _pm.get('automation', {}).items()}
    if 'accomp' in _pm: ACCOMP = set(_pm['accomp'])
    TARGET.update(_pm.get('target', {}))
SIDE = {'Violins': 0.55, 'Violins Pizz': 0.55}                                       # VSCO violins are recorded very wide
AMB = {'strings': 0.5, 'winds': 0.4, 'perc': 0.55, 'piano': 0.45}
BACK_DELAY = {}
if on('V8_AMB'):
    AMB = {'strings': 1.0, 'winds': 0.8, 'perc': 1.7, 'piano': 1.7}
    BACK_DELAY = {n: 0.0035 for n in ('Harp', 'Piano', 'Celesta', 'Glockenspiel', 'Guitar')}
for kv in filter(None, os.environ.get('V8_AMBSET', '').split(',')):      # e.g. V8_AMBSET=perc:1.2
    k_, v_ = kv.split(':'); AMB[k_] = float(v_)
FAMILY = {'Flute': 'winds', 'Clarinet': 'winds', 'Harp': 'perc', 'Celesta': 'perc', 'Glockenspiel': 'perc',
          'Piano': 'piano', 'Guitar': 'piano', 'Snare Drum': 'perc'}
DRY = 0.3


def peq(x, f0, gain_db, q=1.0):
    Ag = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q)
    b = np.array([1 + al * Ag, -2 * np.cos(w), 1 - al * Ag]); a = np.array([1 + al / Ag, -2 * np.cos(w), 1 - al / Ag])
    return lfilter(b / a[0], a / a[0], x, axis=0).astype(np.float32)


stems = {f[:-4]: sf.read(os.path.join(D, f), dtype='float32')[0] for f in os.listdir(D) if f.endswith('.wav')}
stems = {k: (v if v.ndim == 2 else np.stack([v, v], 1)) for k, v in stems.items()}
L = max(len(v) for v in stems.values())
stems = {k: np.pad(v, ((0, L - len(v)), (0, 0))) for k, v in stems.items()}

# tone shaping from user feedback
if 'Clarinet' in stems and os.environ.get('CLAR_EQ', '0') == '1':      # run_v8.sh applies the EQ to the stem already
    stems['Clarinet'] = peq(stems['Clarinet'], 2200, 3.0, 1.0)
if 'Harp' in stems:
    h = sosfilt(butter(2, 70, 'high', fs=SR, output='sos'), stems['Harp'], axis=0).astype(np.float32)
    stems['Harp'] = peq(h, 180, -3.5, 0.9)
if on('V8_HPF'):
    for n_, fc in (('Celesta', 140), ('Glockenspiel', 400)):
        if n_ in stems:
            stems[n_] = sosfilt(butter(4, fc, 'high', fs=SR, output='sos'), stems[n_], axis=0).astype(np.float32)
for n_, pts in AUTOMATION.items():
    if n_ in stems:
        t = np.arange(L) / SR
        gdb = np.zeros(L)
        for a0, a1, gg in pts:
            gdb += gg * np.clip(np.minimum((t - a0) / 1.5, (a1 - t) / 1.5), 0, 1)
        stems[n_] = stems[n_] * (10 ** (gdb / 20)).astype(np.float32)[:, None]


def env(x):
    return np.sqrt(np.maximum(uniform_filter1d(x.astype(np.float64) ** 2, 2205), 0))


meter = pyln.Meter(SR)

# melody ducking envelopes (from the dry melody stems)
w = np.zeros(L); wc = np.zeros(L)
for n in ('Flute', 'Clarinet'):
    if n in stems:
        e = env(stems[n].mean(1)); w = np.maximum(w, e / (e.max() + 1e-12))
        if n == 'Clarinet':
            wc = e / (e.max() + 1e-12)


def activity(x):
    b = x > 0.03
    if on('V8_PREDUCK'):
        # hold the duck through melody rests shorter than 1.5 s (no swell-and-dip of the accompaniment)
        h = 441                                                    # 10 ms grid
        bb = b[: len(b) // h * h].reshape(-1, h).any(1)
        bb = binary_closing(np.pad(bb, 150), structure=np.ones(150))[150:-150]
        b = np.repeat(bb, h)
        b = np.pad(b, (0, L - len(b)), mode='edge')
    return uniform_filter1d(b.astype(np.float64), int(0.6 * SR))


act = activity(w); actc = activity(wc)
DSCALE = np.ones(L)
if on9('V9_DUCKDYN') and MID:
    # a real orchestra doesn't thin out the accompaniment at a tutti ff: duck depth follows the accompaniment's own
    # written dynamic (full duck at vel <= 80, none at vel >= 100), max velocity of the ACCOMP parts smoothed over 1 s
    import pretty_midi as _pm
    _m = _pm.PrettyMIDI(MID); h = 441; av = np.zeros(L // h + 1)
    for _i in _m.instruments:
        if _i.name in ACCOMP:
            for _n in _i.notes:
                a_, b_ = int(_n.start * SR / h), int(max(_n.end, _n.start + 0.3) * SR / h) + 1
                av[a_:b_] = np.maximum(av[a_:b_], _n.velocity)
    av = uniform_filter1d(av, 100)
    DSCALE = np.repeat(np.clip((100 - av) / 20, 0, 1), h)[:L]
    print(f'duck depth scale: mean {DSCALE.mean():.2f}, no duck {100*np.mean(DSCALE < 0.05):.0f}% of the time')
duck = np.minimum(10 ** (-3.0 * DSCALE * np.clip(act * 1.5, 0, 1) / 20), 10 ** (-5.0 * DSCALE * np.clip(actc * 1.5, 0, 1) / 20)).astype(np.float32)
dd_db = 20 * np.log10(duck[::441])
print(f'duck: <=-2.5 dB {100*np.mean(dd_db <= -2.5):.0f}% of the time, transitions {int(np.sum(np.abs(np.diff((dd_db <= -2.5).astype(int)))))}')

_ir = {}
def ir(path):
    if path not in _ir:
        x, sr = sf.read(os.path.join(A, path), dtype='float32')
        assert sr == SR
        _ir[path] = x
    return _ir[path]
ref_main = ir('marco_tree/main_000deg_3m.wav')
cal = 1.0 / np.abs(ref_main[: int(0.02 * SR)]).max()

def hall(n, y):
    """stem as heard from the tree: per-seat measured hall + delayed close spot."""
    seat = SEATS.get(n) or SEATS.get(n.replace(' Pizz', '')) or SEATS['Strings Pad']
    mono = y.mean(1); fam = FAMILY.get(n, 'strings')
    main = ir(seat['marco_main']) * cal; amb = ir(seat['marco_amb']) * cal
    out = np.zeros((L + 4 * SR, 2), np.float32)
    for c in range(2):
        wet = oaconvolve(mono, main[:, c]) + (0.6 * AMB[fam] / 0.5) * oaconvolve(mono, amb[:, c])
        out[:len(wet), c] += wet[:len(out)].astype(np.float32)
    mid, side = (y[:, 0] + y[:, 1]) / 2, (y[:, 0] - y[:, 1]) / 2 * SIDE.get(n, 0.8)
    th = (pans.get(n, 0) + 1) * np.pi / 4
    d = int(seat.get('marco_direct_ms', 5) / 1000 * SR)
    out[d:d + L, 0] += DRY * (mid + side) * np.cos(th) * np.sqrt(2)
    out[d:d + L, 1] += DRY * (mid - side) * np.sin(th) * np.sqrt(2)
    bd = int(BACK_DELAY.get(n, 0) * SR)
    if bd:
        out = np.concatenate([np.zeros((bd, 2), np.float32), out[:-bd]])
    return out

STATS = on('MIXSTATS', '0') and MID
if STATS:
    import pretty_midi as pm
    midi = pm.PrettyMIDI(MID)
    BANDS = {'Flute': (1000, 4000), 'Clarinet': (1000, 4000), 'Celesta': (1000, 4000), 'Cellos': (100, 1000)}
    bandsig = {}; bandtot = {}; stemfr = {}
mix = np.zeros((L + 4 * SR, 2), np.float32)
for n, x in stems.items():
    proc = hall(n, x)
    # calibrate AFTER the hall: perceived loudness while playing, as heard in the room (measured without the duck)
    e = env(x.mean(1)); mask = np.zeros(len(proc), bool); mask[:L] = e > e.max() * 10 ** (-35 / 20)
    act_ = proc[mask] if mask.sum() > SR else proc
    lv = meter.integrated_loudness(act_.astype(np.float64))
    g = 10 ** ((TARGET.get(n, -8) - lv) / 20)
    print(f'{n:14s} {lv:6.1f} LUFS in hall -> {20*np.log10(g):+6.1f} dB', flush=True)
    if n in ACCOMP:
        if on('V8_PREDUCK'):
            proc = hall(n, x * duck[:, None])                      # duck the players, not the room
        else:
            dd = np.ones(len(proc), np.float32); dd[:L] = duck
            proc *= dd[:, None]
    mix += proc * g
    if STATS:
        for bnd in {(1000, 4000), (100, 1000)}:
            bs = sosfilt(butter(4, bnd, 'band', fs=SR, output='sos'), (proc * g).mean(1)).astype(np.float32)
            bandtot[bnd] = bandtot.get(bnd, 0) + bs
            if BANDS.get(n) == bnd:
                bandsig[n] = bs
            if bnd == (1000, 4000):
                stemfr[n] = uniform_filter1d(bs.astype(np.float64) ** 2, 2048)[1024::1024]
    del proc

if on('V8_LFMONO'):
    # cello section through one spaced-pair IR = fixed half-wavelength L/R delay at 90-140 Hz (anti-phase bass).
    # Narrow the side signal below 150 Hz (zero-phase) and give the lost energy back to the mid.
    sos = butter(2, 150, 'low', fs=SR, output='sos')
    M = (mix[:, 0] + mix[:, 1]) / 2; S_ = (mix[:, 0] - mix[:, 1]) / 2
    Ml = sosfiltfilt(sos, M); Sl = sosfiltfilt(sos, S_)
    bp = butter(4, [80, 160], 'band', fs=SR, output='sos')
    eM, eS = np.mean(sosfilt(bp, Ml) ** 2), np.mean(sosfilt(bp, Sl) ** 2)
    k = float(os.environ.get('V8_LFK', '0.6'))
    eS2 = (1 - k) ** 2 * eS
    gm = min(np.sqrt((eM + eS - eS2) / eM), 10 ** (float(os.environ.get('V8_LFMAXDB', '2.0')) / 20))
    M = M + (gm - 1) * Ml; S_ = S_ - k * Sl
    mix = np.stack([M + S_, M - S_], 1).astype(np.float32)
    del M, S_, Ml, Sl
    print(f'LF mono: side below 150 Hz x{1-k:.1f}, mid LF x{gm:.2f} ({20*np.log10(gm):+.1f} dB)')

# correct left/right balance to within 1 dB
rl, rr = np.sqrt(np.mean(mix[:, 0] ** 2)), np.sqrt(np.mean(mix[:, 1] ** 2))
bal = 20 * np.log10(rl / rr)
if abs(bal) > 1.0:
    k = 10 ** ((abs(bal) - 0.5) / 40)
    if bal > 0:
        mix[:, 0] /= k; mix[:, 1] *= k
    else:
        mix[:, 0] *= k; mix[:, 1] /= k
print(f'L/R balance {bal:+.1f} dB -> {20*np.log10(np.sqrt(np.mean(mix[:,0]**2))/np.sqrt(np.mean(mix[:,1]**2))):+.1f} dB')
pk = np.abs(mix).max() / 0.7
mix /= pk
sf.write(OUT, mix, SR, subtype='FLOAT')
# mix model for verify.py's masking checks (it rebuilds the mix from dry stems)
np.save(os.path.join(D, 'duck_scale.npy'), DSCALE[::441].astype(np.float32))
json.dump({'ACCOMP': sorted(ACCOMP), 'AUTOMATION': AUTOMATION, 'TARGET': TARGET, 'hold_rests': on('V8_PREDUCK'),
           'duck_scale_file': 'duck_scale.npy' if on9('V9_DUCKDYN') and MID else None},
          open(os.path.join(D, 'mix_model.json'), 'w'), indent=1)

if STATS:
    hop = 1024
    def frames(sig):
        return uniform_filter1d(sig.astype(np.float64) ** 2, 2048)[1024::hop]
    mono = mix.mean(1) * pk                     # undo the peak normalisation (stems were added at gain g)
    for n, (lo, hi) in BANDS.items():
        if n not in bandsig:
            continue
        tot = bandtot[(lo, hi)]
        m = frames(bandsig[n]); r = frames(tot - bandsig[n])
        tf = (np.arange(len(m)) * hop + 1024) / SR
        onm = np.zeros(len(m), bool)
        inst = [i for i in midi.instruments if i.name == n][0]
        for nt in inst.notes:
            a, b = np.searchsorted(tf, [nt.start, max(nt.end, nt.start + 0.05)]); onm[a:b] = True
        s = 10 * np.log10((m + 1e-14) / (r + 1e-14))
        spans = {'all': (0, 1e9)}
        if n == 'Clarinet':
            spans |= {'0:13-0:46': (13, 46.3), '5:05-5:50': (304.6, 349.6), '5:52-6:52': (351.9, 412.4)}
        if n == 'Cellos':
            spans = {'2:08-2:34': (128, 154)}
        if n == 'Flute':
            spans |= {'6:30-6:40': (390, 400)}
        if n == 'Flute':
            sh = {k: float(np.sum(v[:len(onm)][onm[:len(v)]])) for k, v in stemfr.items() if k != 'Flute'}
            tot_ = sum(sh.values())
            print('  flute maskers (1-4 kHz energy share while flute plays): ' +
                  ', '.join(f'{k} {100*v/tot_:.0f}%' for k, v in sorted(sh.items(), key=lambda kv: -kv[1])[:5]))
        print(f'in-hall SNR {n:9s} ' + '  '.join(f"{k}: {np.median(s[onm & (tf >= a) & (tf < b)]):+.1f}" for k, (a, b) in spans.items()
                                              if (onm & (tf >= a) & (tf < b)).sum() > 20))
    for lo_, hi_ in ((71, 90), (90, 112), (112, 141), (141, 178)):
        bp_ = butter(4, [lo_, hi_], 'band', fs=SR, output='sos')
        l_, r_ = sosfilt(bp_, mix[:, 0]), sosfilt(bp_, mix[:, 1])
        print(f'  L/R corr {lo_}-{hi_} Hz {np.sum(l_*r_)/np.sqrt(np.sum(l_**2)*np.sum(r_**2)):+.2f}', end='')
    print()
    # 5-s loudness contour of the (pre-master) mix relative to its integrated loudness, for the dynamic arc
    il = meter.integrated_loudness(mix.astype(np.float64))
    cont = np.array([meter.integrated_loudness(mix[int(t0 * SR): int((t0 + 5) * SR)].astype(np.float64)) - il
                     for t0 in np.arange(0, len(mix) / SR - 5, 5.0)])
    top = np.argsort(cont)[::-1][:4]
    print('arc: loudest 5-s windows ' + ', '.join(f'{int(i*5)//60}:{int(i*5)%60:02d} {cont[i]:+.1f}' for i in top) +
          f' | 1:15-1:35 mean {np.mean(cont[15:19]):+.1f}, 5:10-5:45 mean {np.mean(cont[62:69]):+.1f}')
