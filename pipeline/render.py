"""Draft 9 renderer (draft-8 engine + performer realism, see pipeline/notes/changes_v9.md).
Every draft-9 change has an env switch V9_* (default = adopted setting).
Render an orchestrated MIDI with real orchestral samples (VSCO-2 CE + tonejs-instruments WAV).

usage: render_samples.py orch.mid audio_ref_mono.wav out_dry.wav
"""
import json, os, re, subprocess, sys
import numpy as np
import pretty_midi as pm
import soundfile as sf
from scipy.signal import lfilter

midi_path, ref_path, out_path = sys.argv[1:4]
SR = 44100
OFFSET = 0.139
ASSETS = os.environ.get('ASSETS', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets'))
DL = os.path.join(ASSETS, 'samples')
VSCO = os.path.join(DL, 'tiny-orchestra', 'package', 'samples')
MAN = json.load(open(os.path.join(VSCO, 'manifest.json')))['instruments']
NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def rms_level(x):
    seg = x[int(0.05 * SR): int(1.0 * SR)]
    if len(seg) < 1000:
        seg = x
    return float(np.sqrt(np.mean(np.asarray(seg, dtype=np.float64) ** 2)) + 1e-9)


class Bank:
    """Samples of one instrument: list of dicts with audio + metadata, normalised to a common level."""

    def __init__(self, name, samples, sustain, release, gain, attack):
        self.name, self.samples, self.sustain, self.release, self.gain, self.attack = name, samples, sustain, release, gain, attack

    def pick(self, midi, vel):
        layers = sorted({s['vel'] for s in self.samples})
        layer = next((l for l in layers if l >= vel - 1e-9), layers[-1])
        cands = [s for s in self.samples if s['vel'] == layer]
        best = min(abs(s['midi'] - midi) for s in cands)
        near = [s for s in cands if abs(s['midi'] - midi) < best + 0.6]
        rr = self.__dict__.setdefault('rrs', {})
        rr[CUR[0]] = rr.get(CUR[0], 0) + 1
        return sorted(near, key=lambda s: s.get('rr') or '')[rr[CUR[0]] % len(near)]


def vsco_bank(name, attack=0.004):
    m = MAN[name]
    out = []
    for s in m['samples']:
        x = decode(os.path.join(VSCO, s['file']))
        extra = len(x) / SR - s['duration']
        shift = extra if 0.005 < extra < 0.1 else 0.0          # decoder delay
        start = int((s.get('offset', 0) + shift) * SR)
        out.append(dict(midi=s.get('midi', 60), vel=s.get('vel', 1), tune=s.get('tune', 0), audio=x[start:],
                        loop=(s['loopStart'] - s.get('offset', 0), s['loopEnd'] - s.get('offset', 0)) if 'loopStart' in s else None,
                        variant=s.get('variant')))
    ref = np.median([rms_level(s['audio']) for s in out if s['vel'] == max(t['vel'] for t in out)])
    for s in out:
        s['audio'] = s['audio'] / ref * 0.1      # louder layers at a common level; quiet layers stay quieter
    return Bank(name, out, m.get('sustain', False), m.get('release', 0.3), m.get('gain', 1), attack)


def lead_trim(x, db=-10.0, pre=0.040):
    e = np.abs(x).max(1)
    k = int(0.01 * SR)
    env = np.convolve(e, np.ones(k) / k, mode='same')
    plateau = np.percentile(env[int(0.3 * SR): int(1.2 * SR)], 80) if len(env) > 1.2 * SR else env.max()
    i10 = int(np.argmax(env > plateau * 10 ** (db / 20)))
    return x[max(0, i10 - int(pre * SR)):]


def tonejs_bank(name, sustain=True, release=0.3, gain=1.0, attack=0.004, trim=False):
    d = os.path.join(DL, f'tonejs-instrument-{name}-wav', 'package')
    out = []
    for f in sorted(os.listdir(d)):
        mm = re.fullmatch(r'([A-G])(s?)(-?\d)\.wav', f)
        if not mm:
            continue
        midi = 12 * (int(mm.group(3)) + 1) + NOTE[mm.group(1)] + (1 if mm.group(2) else 0)
        x = decode(os.path.join(d, f))
        # trim leading silence
        on = np.argmax(np.abs(x).max(1) > np.abs(x).max() * 0.02)
        x = x[max(0, on - int(0.003 * SR)):]
        if trim and os.environ.get('V8_FLUTETRIM', '1') == '1':
            x = lead_trim(x)
        out.append(dict(midi=midi, vel=1, tune=0, audio=x / (rms_level(x) + 1e-9) * 0.1, loop=None, variant=None))
    return Bank(name, out, sustain, release, gain, attack)


import librosa
NN = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}
def folder_bank(name, folder, regex, layer_vel, sustain, release, gain, attack, octave_offset=0, measure=True, trim_attack=0.0,
                key_base=36):
    out = []
    for f in sorted(os.listdir(folder)):
        mm = re.search(regex, f, re.I)
        if not mm:
            continue
        gd = mm.groupdict(); layer = gd['layer']
        if gd.get('key') is not None:                 # keyboard index (1 = key_base), e.g. organ pipes numbered by key
            nominal = key_base + int(gd['key']) - 1
        else:
            note = gd['note']
            L = NN[note[0].lower()] + note.count('#') - (1 if len(note) > 1 and note[1] == 'b' and note[0].lower() != 'b' else 0)
            nominal = 12 * (int(gd['oct']) + 1 + octave_offset) + L
        x = decode(os.path.join(folder, f))
        on = np.argmax(np.abs(x).max(1) > np.abs(x).max() * 0.02)
        x = x[max(0, on - int(0.003 * SR)):]
        exact = float(nominal)
        if measure:
            seg = x[int(0.25 * SR): int(1.5 * SR)].mean(1)
            try:
                f0, vf, _ = librosa.pyin(seg, fmin=librosa.midi_to_hz(nominal - 14), fmax=librosa.midi_to_hz(nominal + 14), sr=SR,
                                         frame_length=4096)
                f0 = f0[vf & np.isfinite(f0)]
                if len(f0) > 5:
                    m = float(librosa.hz_to_midi(np.median(f0)))
                    k = round((m - nominal) / 12) * 12            # fix octave-naming conventions
                    if abs(m - (nominal + k)) < 0.7:
                        exact = m
            except Exception:
                pass
        out.append(dict(midi=exact, vel=layer.lower(), tune=0, audio=x, loop=None, variant=None, rr=f, nominal=nominal,
                        measured=exact != float(nominal)))
    # samples whose pitch could not be measured inherit the folder's octave-naming offset (VSCO names are an octave low)
    offs = [round((s['midi'] - s['nominal']) / 12) * 12 for s in out if s['measured']]
    if offs:
        k = int(np.median(offs))
        for s in out:
            if not s['measured']:
                s['midi'] = float(s['nominal'] + k)
            elif abs(s['midi'] - (s['nominal'] + k)) > 1.0:
                print(f'   fixed {name} {s["rr"]}: measured {s["midi"]:.2f} -> expected {s["nominal"] + k}')
                s['midi'] = float(s['nominal'] + k)
    names = sorted({s['vel'] for s in out}, key=lambda l: layer_vel.get(l, 0) if l in layer_vel else int(re.sub(r'\D', '', l) or 0))
    vals = {l: layer_vel[l] for l in names} if all(l in layer_vel for l in names) else \
        {l: round(0.4 + 0.6 * i / max(1, len(names) - 1), 2) if len(names) > 1 else 1.0 for i, l in enumerate(names)}
    for s in out:
        s['vel'] = vals[s['vel']]
    for s in out:
        if trim_attack:
            # skip the slow breath/bow lead-in: start where the envelope reaches trim_attack of its plateau
            e = np.abs(s['audio']).max(1)
            k = int(0.01 * SR)
            env = np.convolve(e, np.ones(k) / k, mode='same')
            plateau = np.percentile(env[int(0.3 * SR): int(1.2 * SR)], 80) if len(env) > 1.2 * SR else env.max()
            i0 = int(np.argmax(env > plateau * trim_attack))
            s['audio'] = s['audio'][max(0, i0 - int(0.012 * SR)):]
        # every sample levelled on its own (round-robins and neighbours match); quieter layers keep their relative level
        s['audio'] = s['audio'] / rms_level(s['audio']) * 0.1 * s['vel']
    print(f'  {name}: {len(out)} samples, layers {sorted({s["vel"] for s in out})}, pitch {min(s["midi"] for s in out):.1f}-{max(s["midi"] for s in out):.1f}', flush=True)
    return Bank(name, out, sustain, release, gain, attack)

G = os.path.join(ASSETS, 'samples')
V = os.path.join(G, 'VSCO-2-CE_git')
print('loading samples...', flush=True)
BANKS = {
    'violins': vsco_bank('violins', 0.03), 'violas': vsco_bank('violas', 0.03), 'cellos': vsco_bank('celli', 0.03),
    'contrabass': vsco_bank('basses', 0.03), 'violinsPizz': vsco_bank('violinsPizz'), 'celliPizz': vsco_bank('celliPizz'),
    'harp': tonejs_bank('harp', sustain=False, release=0.8), 'glockenspiel': vsco_bank('glockenspiel'),
    'flute': tonejs_bank('flute', release=0.25, gain=0.85, attack=0.02, trim=True), 'oboe': vsco_bank('oboe', 0.015),
    'clarinet': tonejs_bank('clarinet', release=0.25, gain=0.85, attack=0.02),
    'horns': tonejs_bank('french-horn', release=0.35, gain=0.8, attack=0.03),
    'trumpet': tonejs_bank('trumpet', release=0.3, gain=0.75, attack=0.01),
    'trombone': tonejs_bank('trombone', release=0.35, gain=0.8, attack=0.02),
    'timpani': vsco_bank('timpani'), 'timpaniRoll': vsco_bank('timpaniRoll', 0.05), 'cymbal': vsco_bank('cymbal'),
    'piano': tonejs_bank('piano', sustain=False, release=0.4, gain=0.9, attack=0.002),
    'guitar': tonejs_bank('guitar-nylon', sustain=False, release=0.3, gain=0.9, attack=0.002),
    'snare': vsco_bank('snare'),
    'xylophone': tonejs_bank('xylophone', sustain=False, release=0.5, gain=0.8, attack=0.001),
}
STRTRIM = float(os.environ.get('V8_STRTRIM', '0.5'))
STR = r'_(?P<note>[A-G]#?)(?P<oct>-?\d)_(?P<layer>v\d)'
BANKS['violins'] = folder_bank('violins', os.path.join(V, 'Strings/Violin Section/susVib'), STR, {'v1': 0.55, 'v2': 1.0}, True, 0.5, 1.0, 0.035, trim_attack=STRTRIM)
BANKS['violas'] = folder_bank('violas', os.path.join(V, 'Strings/Viola Section/susvib'), STR, {'v1': 0.55, 'v2': 1.0}, True, 0.5, 1.0, 0.035, trim_attack=STRTRIM)
# VSCO cello susvib files are v1/v3: the fallback maps them to 0.4/1.0, so cellos always play the v3 layer. Deliberate:
# the v1 cello samples swell for 133-478 ms and failed the note-loudness gate (critic test, draft 8).
BANKS['cellos'] = folder_bank('cellos', os.path.join(V, 'Strings/Cello Section/susvib'), STR, {'v1': 0.55, 'v2': 1.0}, True, 0.5, 1.0, 0.035, trim_attack=STRTRIM)
BANKS['violinsPizz'] = folder_bank('violinsPizz', os.path.join(V, 'Strings/Violin Section/Pizz'), STR, {'v1': 0.6, 'v2': 1.0}, False, 0.15, 1.0, 0.002)
BANKS['violasPizz'] = folder_bank('violasPizz', os.path.join(V, 'Strings/Viola Section/pizz'), STR, {'v1': 0.6, 'v2': 1.0}, False, 0.15, 1.0, 0.002)
BANKS['celliPizz'] = folder_bank('celliPizz', os.path.join(V, 'Strings/Cello Section/pizzT'), STR, {'v1': 0.6, 'v2': 1.0}, False, 0.15, 1.0, 0.002)
for b in ('violinsPizz', 'violasPizz', 'celliPizz'):
    BANKS[b].name = b if b != 'violasPizz' else 'violinsPizz'
BANKS['clarinet'] = folder_bank('clarinet', os.path.join(V, 'Woodwinds/Clarinet/susLong'), STR, {'v1': 0.45, 'v2': 0.75, 'v3': 1.0}, True, 0.25, 0.9, 0.012, trim_attack=0.35)
CEL = os.path.join(G, 'sso_git/Sonatina Symphonic Orchestra/Samples/Celeste')
BANKS['celesta'] = folder_bank('celesta', CEL, r'celeste-(?P<note>[a-g]#?)(?P<oct>\d)-(?P<layer>hard|soft)', {'soft': 0.6, 'hard': 1.0}, False, 0.5, 1.0, 0.002)
BANKS['piano'].name = 'piano_damped'; BANKS['guitar'].name = 'guitar_damped'
# catalogue instruments (pipeline/instruments.py): loaded the first time a track needs them
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instruments as INS
CAT = INS.CATALOG


def catalog_bank(name):
    e = CAT[name]
    samples = []
    for p in e['parts']:
        b = folder_bank(name, os.path.join(G, p['folder']), p['regex'], INS.DYN, e['sustain'], e['release'], 1.0, e['attack'],
                        trim_attack=e.get('trim', 0.0), key_base=p.get('key_base', 36), measure=p.get('measure', True))
        prev = list(samples)        # a later part only fills pitches the earlier parts don't cover
        samples += [s for s in b.samples if not prev or min(abs(s['midi'] - q['midi']) for q in prev) > 1.5]
    bank = Bank('cat:' + name, samples, e['sustain'], e['release'], 1.0, e['attack'])
    bank.damped = e.get('damped', False)
    return bank


_DRUMB = {}
def drum_bank(note):
    """one-shot samples for a GM drum note: list of dicts (audio at natural relative level, layer value)"""
    if note not in _DRUMB:
        folder, regex = INS.DRUMS[note]
        d = os.path.join(G, folder)
        out = []
        for f in sorted(os.listdir(d)):
            mm = re.search(regex, f, re.I)
            if not mm:
                continue
            x = decode(os.path.join(d, f))
            on = np.argmax(np.abs(x).max(1) > np.abs(x).max() * 0.02)
            out.append(dict(audio=x[max(0, on - int(0.002 * SR)):], layer=(mm.groupdict().get('layer') or '').lower()))
        names = sorted({s['layer'] for s in out}, key=lambda l: INS.DYN.get(l, int(re.sub(r'\D', '', l) or 0)))
        vals = {l: (INS.DYN[l] if all(n in INS.DYN for n in names) else round(0.4 + 0.6 * i / max(1, len(names) - 1), 2))
                if len(names) > 1 else 1.0 for i, l in enumerate(names)}
        top = max(vals.values())
        ref = np.median([np.sqrt(np.mean(s['audio'][: int(0.5 * SR)] ** 2)) + 1e-9 for s in out if vals[s['layer']] == top])
        for s in out:
            s['vel'] = vals[s['layer']]; s['audio'] = s['audio'] / ref * 0.1
        _DRUMB[note] = out
        print(f'  drum {note}: {len(out)} samples, layers {sorted(set(vals.values()))}', flush=True)
    return _DRUMB[note]


_DRR = {}
def drum_hit(n):
    smp = drum_bank(n.pitch)
    v = n.velocity / 127
    lays = sorted({s['vel'] for s in smp})
    lay = next((l for l in lays if l >= v - 1e-9), lays[-1])
    c = [s for s in smp if s['vel'] == lay]
    _DRR[n.pitch] = _DRR.get(n.pitch, -1) + 1
    y = c[_DRR[n.pitch] % len(c)]['audio'][: int(8 * SR)].copy()
    kf = min(len(y) // 4, int(0.3 * SR))
    if kf > 1:
        y[-kf:] *= (np.cos(np.linspace(0, np.pi / 2, kf)) ** 2)[:, None]
    y *= float(np.clip(v / lay, 0.3, 1.5)) ** 1.5
    i0 = int(n.start * SR)
    b = stem('Percussion'); y = y[: len(b) - i0]; b[i0:i0 + len(y)] += y


# MIDI track name -> (bank, pan -1..1, mix gain dB, section voices)
TRACKS_OLD = {
    'Violins': ('violins', -0.45, 0, 1), 'Violas': ('violas', 0.2, -2, 1), 'Cellos': ('cellos', 0.45, -1, 1),
    'Contrabass': ('contrabass', 0.6, -1, 2), 'Pizz Strings': ('pizz', 0.0, -2, 1), 'Harp': ('harp', -0.6, -3, 1),
    'Celesta': ('glockenspiel', 0.3, -9, 1), 'Glockenspiel': ('glockenspiel', 0.3, -6, 1),
    'Flute': ('flute', -0.1, -3, 1), 'Oboe': ('oboe', 0.1, -3, 1), 'Clarinet': ('clarinet', -0.2, -3, 1),
    'Horns': ('horns', -0.25, -3, 2), 'Trumpet': ('trumpet', 0.25, -4, 1), 'Trombone': ('trombone', 0.4, -4, 2),
    'Timpani': ('timpani', 0.0, -2, 1),
}

TRACKS = {
    'Violins': ('violins', -0.45, 0, 1), 'Violas': ('violas', 0.2, -1, 1), 'Cellos': ('cellos', 0.45, 0, 1),
    'Violins Pizz': ('pizz', -0.45, -2, 1), 'Violas Pizz': ('pizz', 0.2, -2, 1), 'Cellos Pizz': ('pizz', 0.45, -2, 1),
    'Strings Pad': ('pad', 0.0, -4, 1), 'Harp': ('harp', -0.6, -2, 1), 'Glockenspiel': ('glockenspiel', 0.3, -6, 1),
    'Celesta': ('celesta', 0.25, 0, 1), 'Flute': ('flute', -0.1, -2, 1), 'Clarinet': ('clarinet', 0.1, -2, 1),
    'Piano': ('piano', 0.35, -3, 1), 'Guitar': ('guitar', -0.3, -3, 1),
}
# piece config (env PIECE=path/to/piece.json): extra MIDI track names -> (bank, pan, gain dB, voices), fermatas
PIECE = json.load(open(os.environ['PIECE'])) if os.environ.get('PIECE') else {}
for k, v in PIECE.get('extra_tracks', {}).items():
    TRACKS[k] = tuple(v) if isinstance(v, list) else TRACKS_OLD[v]
src = pm.PrettyMIDI(midi_path)
end_t = src.get_end_time() + 6
NLEN = int(end_t * SR)
stems = {}
mix = None
def stem(name):
    if name not in stems:
        stems[name] = np.zeros((NLEN, 2), dtype=np.float32)
    return stems[name]
CUR = ['x']


def looped(s, need):
    """Audio long enough for `need` samples, using the loop (or an automatic crossfade loop)."""
    a = s['audio']
    if len(a) >= need:
        return a[:need]
    if s['loop']:
        ls, le = int(s['loop'][0] * SR), int(s['loop'][1] * SR)
    else:
        ls, le = int(len(a) * 0.45), int(len(a) * 0.9)
    le = min(le, len(a)); body = a[ls:le]
    xf = min(int(0.08 * SR), len(body) // 4)
    fade = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
    seg = body.copy()
    out = [a[:le]]
    total = le
    while total < need:
        prev = out[-1]
        blended = prev[-xf:] * np.sqrt(1 - fade) + seg[:xf] * np.sqrt(fade)
        out[-1] = prev[:-xf]
        out.append(np.concatenate([blended, seg[xf:]]))
        total += len(seg) - xf
    return np.concatenate(out)[:need]


def attack_end(s_):
    """index where the sample's 10 ms envelope first reaches 0.7 x plateau (start point for a slurred note)"""
    if 'att_end' not in s_:
        e = np.abs(s_['audio']).max(1); k = int(0.01 * SR)
        env_ = np.convolve(e, np.ones(k) / k, mode='same')
        pl = np.percentile(env_[int(0.3 * SR): int(1.2 * SR)], 80) if len(env_) > 1.2 * SR else env_.max()
        s_['att_end'] = int(np.argmax(env_ > pl * 0.7))
    return s_['att_end']


def render(bank, midi, vel, start, dur, pan, gain_db, detune=0.0, delay=0.0, layer_vel=None, taper=0.0, taper_db=-8.0,
           slur_in=False, slur_out=False, keep_rel=False, xf_in=None, xf_out=None):
    v = vel / 127.0
    lv = v if layer_vel is None else layer_vel / 127.0
    if bank.name == 'clarinet' and midi >= 76:
        lv = min(lv, 0.75)                     # loud altissimo layer squeaks: use the mf layer up there
    s = bank.pick(midi, lv)
    if bank.name == 'harp' and os.environ.get('V8_HARPRR', '0') == '1':
        # OFF by default: tested on the full piece, harp p90 adjacent jump 3.91 -> 4.1 dB (worse); kept as an option
        # one recording per root: vary each pluck slightly (deterministic) so quick repeats aren't machine-gun identical
        _r = np.random.default_rng(int(start * 1000) * 131 + int(midi))
        detune += _r.uniform(-3, 3); delay += _r.uniform(0, 0.003)
    rate = 2 ** ((midi - s['midi'] + (detune - s['tune']) / 100) / 12)
    rel = bank.release
    if bank.sustain:
        out_len = dur + rel * 1.3
    else:
        out_len = min(len(s['audio']) / SR / rate, (dur + rel * 1.3) if (bank.name in ('violinsPizz', 'celliPizz', 'piano_damped', 'guitar_damped') or getattr(bank, 'damped', False)) else 12)
    n = int(out_len * SR)
    need_src = int(n * rate) + 2
    off = attack_end(s) if (slur_in and bank.sustain) else 0
    a = looped(s, need_src + off)[off:] if bank.sustain else s['audio'][:need_src]
    pos = np.arange(n) * rate
    pos = pos[pos < len(a) - 1]
    if len(pos) < 10:
        return
    y = np.stack([np.interp(pos, np.arange(len(a)), a[:, c]) for c in range(2)], 1).astype(np.float32)
    n = len(y)
    env = np.ones(n, dtype=np.float32)
    att = bank.attack
    if bank.name == 'harp':
        att = 0.004 + 0.010 * float(np.clip((60 - midi) / 24, 0, 1))      # softer pluck on low strings (less thump)
    if slur_in and bank.sustain:
        # slurred: no new attack; equal-power crossfade from the previous note (which fades out with slur_out)
        at = min(n, int((xf_in or XF) * SR)); env[:at] = np.sin(0.5 * np.pi * np.linspace(0, 1, at))
    else:
        at = min(n, int(att * SR)); env[:at] = np.linspace(0, 1, at)
    if bank.sustain or (bank.name in ('violinsPizz', 'celliPizz', 'piano_damped', 'guitar_damped') or getattr(bank, 'damped', False)):
        r0 = int(dur * SR)
        if r0 < n:
            tt = np.arange(n - r0) / SR
            if slur_out and bank.sustain:
                r1 = max(0, r0 - int((xf_out or XF) * SR))
                env[r1:r0] *= np.cos(0.5 * np.pi * np.linspace(0, 1, r0 - r1)); env[r0:] = 0
            elif taper:
                # breath / re-tongue / phrase end: the player tapers the note (diminuendo + air release)
                tp = int(min(taper, 0.35 * dur) * SR); r1 = max(0, r0 - tp); tg = 10 ** (taper_db / 20)
                env[r1:r0] *= np.linspace(1, tg, r0 - r1)
                env[r0:] *= tg * np.exp(-tt / (rel / (5 if keep_rel else 8)))
            else:
                env[r0:] *= np.exp(-tt / (rel / 5))
    if not bank.sustain and TAILFADE:
        # ringing samples are cut at out_len (12 s cap): fade the end so the cut never clicks (harp/celesta/glock)
        kf = min(n // 4, int(0.3 * SR))
        if kf > 1:
            env[n - kf:] *= np.cos(np.linspace(0, np.pi / 2, kf)) ** 2
    y *= env[:, None]
    # velocity: level (quadratic, sample layer compensated) and brightness
    if 'nominal' in s and os.environ.get('V8_LAYERFIX', '1') == '1':
        g = (v * v) / s['vel'] * bank.gain * 10 ** (gain_db / 20)      # folder_bank: levelled to 0.1*layer -> 0.1*v^2
    else:
        g = (v * v) / (s['vel'] ** 2) * bank.gain * 10 ** (gain_db / 20)
    cutoff = 1800 + 16000 * v ** 1.5
    alpha = np.exp(-2 * np.pi * cutoff / SR)
    y = lfilter([1 - alpha], [1, -alpha], y, axis=0).astype(np.float32)
    if dur > 0.8 and (bank.sustain):
        # messa di voce: gentle swell and taper on long notes
        tt = np.arange(len(y)) / SR
        sw = 1.0 + 0.18 * np.sin(np.pi * np.clip(tt / dur, 0, 1)) - 0.08 * np.clip(tt / dur, 0, 1)
        y = y * sw.astype(np.float32)[:, None]
    i0 = int((start + delay) * SR)
    buf = stem(CUR[0])
    if i0 < 0 or i0 >= len(buf):
        return
    y = y[: len(buf) - i0]
    buf[i0:i0 + len(y)] += y * g


E9 = lambda k, d='1': os.environ.get(k, d) == '1'
LOWSLUR = set(filter(None, os.environ.get('V9_LOWSLUR', 'Cellos').split(',')))   # Violas failed the gate (p90 2.76 -> 3.50)
CELLOX = float(os.environ.get('V9_CELLOCOMP', '0.012'))       # cellos speak ~20 ms behind harp/piano they double
XF = 0.06                         # slur crossfade (s), equal power
TAILFADE = E9('V9_TAILFADE')
BEATS = src.get_beats(); DOWNS = src.get_downbeats()
BREATHS = []
CAPTOL = 1.05        # a 4-bar phrase that overshoots the air capacity by < 5 % is still taken in one breath
CAP = {'Flute': float(os.environ.get('V9_CAPF', '7.0')), 'Clarinet': float(os.environ.get('V9_CAPC', '11.0'))}
CAP.update({k: e['cap'] for k, e in CAT.items() if 'cap' in e})        # catalogue winds and brass breathe too
WINDS = set(CAP)


def plan_breaths(notes, name, forced=None):
    """Professional-player breath plan for a wind line (critic_performer prototype, full-piece gated).
    Air capacity cap = base x (1 + 0.4 x (0.75 - mean vel)); breathe at the best phrase boundary with air in
    [0.75 cap, cap] (long previous note, next note on a downbeat / even bar), never within 2 s of the run end.
    Only the note before the breath is shortened (articulation length): onsets, pitches and tempo are untouched.
    forced: onset times where a doubling instrument breathes -> breathe there too (players agree on breaths)."""
    def blen(t):
        i = min(max(int(np.searchsorted(BEATS, t, 'right')) - 1, 0), len(BEATS) - 2); return BEATS[i + 1] - BEATS[i]
    ondown = lambda t: np.min(np.abs(DOWNS - t)) < 0.02
    onbeat = lambda t: np.min(np.abs(BEATS - t)) < 0.02
    def breathe(kk, r, last):
        a, b = notes[r[kk]], notes[r[kk + 1]]
        gap = float(np.clip(0.25 * blen(a.start), 0.10, 0.18)); gap = min(gap, 0.3 * (b.start - a.start))
        a.end = b.start - gap; a.breath = True
        BREATHS.append((name, round(b.start, 2), round(b.start - last, 1), round(gap * 1000)))
    runs = [[0]]
    for i in range(1, len(notes)):
        if notes[i].start - notes[i - 1].end > 0.25: runs.append([])
        runs[-1].append(i)
    for r in runs:
        last = notes[r[0]].start; run_end = notes[r[-1]].end
        if forced is not None:              # breath times decided in the pre-pass (shared by doubling players)
            for kk in range(len(r) - 1):
                if any(abs(notes[r[kk + 1]].start - t) < 0.005 for t in forced):
                    breathe(kk, r, last); last = notes[r[kk + 1]].start
            continue
        k = 0
        while k < len(r) - 1:
            vel = np.mean([notes[j].velocity for j in r]) / 127
            cap = CAP[name] * (1.0 + 0.4 * (0.75 - vel))
            best = None
            for kk in range(k, len(r) - 1):
                a, b = notes[r[kk]], notes[r[kk + 1]]
                air = b.start - last
                if air > CAPTOL * cap and best is not None: break
                if air > CAPTOL * cap: continue
                if air < 0.75 * cap or run_end - b.start < 2.0 or not onbeat(b.start): continue
                bl = blen(a.start); d = (min(a.end, b.start) - a.start) / bl
                if d < 0.9: continue
                bar = int(np.searchsorted(DOWNS, b.start + 0.02)) - int(np.searchsorted(DOWNS, notes[r[0]].start + 0.02))
                sc = d + 2.0 * ondown(b.start) + 0.5 * (ondown(b.start) and bar % 2 == 0) - 0.15 * max(0, air - 0.8 * cap)
                if best is None or sc > best[0] + 1e-6: best = (sc, kk)
                if air > cap: break
            if best is None:
                cand = [kk for kk in range(k, len(r) - 1) if notes[r[kk + 1]].start - last > cap and
                        notes[r[kk + 1]].start - notes[r[kk]].start >= 0.3 and run_end - notes[r[kk + 1]].start > 1.5]
                if not cand: break
                kk = cand[0]
            else:
                kk = best[1]
            breathe(kk, r, last)
            last = notes[r[kk + 1]].start; k = kk + 1


def runs_of(notes):
    rs = [[notes[0]]]
    for a, b in zip(notes, notes[1:]):
        if b.start - a.end > 0.25: rs.append([])
        rs[-1].append(b)
    return rs


# breath plan pre-pass on copies; where flute & clarinet double a passage (>= 80 % shared onsets within +-3 s),
# a breath planned for one player is used by both, and the other's own breaths within 4 s are dropped.
_WN = {i.name: sorted(i.notes, key=lambda n: n.start) for i in src.instruments if i.name in ('Flute', 'Clarinet')}
FIN = None
if E9('V9_BREATH') and E9('V9_BREATHSYNC') and len(_WN) == 2:
    import copy
    cp_ = {k: copy.deepcopy(v) for k, v in _WN.items()}
    for nn in cp_.values():                   # articulation as the main loop sees it (v8 slur extension)
        for a, b in zip(nn, nn[1:]):
            if b.start - a.end < 0.12 and b.start > a.start + 0.05: a.end = b.start + 0.05
    B0 = len(BREATHS)
    plan_breaths(cp_['Flute'], 'Flute'); plan_breaths(cp_['Clarinet'], 'Clarinet')
    planned = [(nm, t) for nm, t, _, _ in BREATHS[B0:]]; del BREATHS[B0:]
    FIN = {k: {t for nm, t in planned if nm == k} for k in cp_}
    ons = {k: np.array([n.start for n in v]) for k, v in cp_.items()}
    for nm, t in planned:
        if t not in FIN[nm]: continue
        ot = 'Clarinet' if nm == 'Flute' else 'Flute'
        w0 = ons[nm][(ons[nm] > t - 3) & (ons[nm] < t + 3)]; w1 = ons[ot][(ons[ot] > t - 3) & (ons[ot] < t + 3)]
        if len(w0) < 3 or len(w1) < 3: continue
        sh = min(np.mean([np.min(np.abs(w1 - x)) < 0.005 for x in w0]), np.mean([np.min(np.abs(w0 - x)) < 0.005 for x in w1]))
        j = np.argmin(np.abs(ons[ot] - t))
        if sh < 0.8 or abs(ons[ot][j] - t) > 0.005 or j == 0 or cp_[ot][j - 1].end < t - 0.02: continue
        rs_ot = [r_ for r_ in runs_of(cp_[ot]) if r_[0].start <= t <= r_[-1].end]
        if rs_ot and t - rs_ot[0][0].start < 4.0:
            # the partner joined < 4 s ago: move the shared breath to a later common boundary (<= 2.6 s later)
            # after a note of >= 0.9 beat, on a beat, so neither player breathes "too early"
            nn = cp_[nm]; best_ = None
            for i_ in range(1, len(nn)):
                x = nn[i_].start
                if not (t < x <= t + 2.6) or np.min(np.abs(ons[ot] - x)) > 0.005 or x - rs_ot[0][0].start < 4.0: continue
                if np.min(np.abs(BEATS - x)) > 0.02 or nn[i_ - 1].end < x - 0.02: continue
                bl_ = BEATS[min(max(int(np.searchsorted(BEATS, x)) - 1, 0), len(BEATS) - 2) + 1] - BEATS[min(max(int(np.searchsorted(BEATS, x)) - 1, 0), len(BEATS) - 2)]
                d_ = (x - nn[i_ - 1].start) / bl_
                if d_ < 0.9: continue
                sc_ = d_ + 2.0 * (np.min(np.abs(DOWNS - x)) < 0.02)
                if best_ is None or sc_ > best_[0]: best_ = (sc_, x)
            if best_ is None: continue
            print(f'  shared breath moved {t:.2f} -> {best_[1]:.2f}s', flush=True)
            FIN[nm].discard(t); t = round(best_[1], 2); FIN[nm].add(t)
        drop = {x for x in FIN[ot] if abs(x - t) < 4 and abs(x - t) > 0.005}
        FIN[ot] -= drop; FIN[ot].add(t)
        print(f'  shared breath at {t:.2f}s ({nm} -> {ot}, share {sh:.2f}, dropped {sorted(drop)})', flush=True)

FERM_END = set(PIECE.get('fermata_end_ticks', []))       # MIDI ticks where a fermata bar ends (piece config)
ONLY = set(filter(None, os.environ.get('V9_ONLY', '').split(',')))
count = 0
for inst in src.instruments:
    if ONLY and inst.name not in ONLY and not (inst.is_drum and 'Snare Drum' in ONLY): continue
    if inst.is_drum:
        for n in inst.notes:
            if n.pitch in INS.DRUMS:
                drum_hit(n); continue
            s = BANKS['snare'].samples[count % len(BANKS['snare'].samples)]
            y = s['audio'][: int(2 * SR)] * (n.velocity / 127) ** 2 * 0.5
            i0 = int(n.start * SR)
            b = stem('Snare Drum'); y = y[: len(b) - i0]; b[i0:i0 + len(y)] += y * 0.7; count += 1
        continue
    if False:
        for n in inst.notes:      # crash cymbals
            s = [c for c in BANKS['cymbal'].samples if c['variant'] == 'crash'][count % 2]
            y = s['audio'][: int(6 * SR)] * (n.velocity / 127) ** 2 * 0.12
            i0 = int(n.start * SR)
            mix[i0:i0 + len(y)] += np.stack([y * 0.75, y * 0.75], axis=1); count += 1
        continue
    if inst.name not in TRACKS and inst.name in CAT:
        if 'cat:' + inst.name not in BANKS:
            BANKS['cat:' + inst.name] = catalog_bank(inst.name)
        TRACKS[inst.name] = ('cat:' + inst.name, CAT[inst.name]['pan'], 0, 1)
    elif inst.name not in TRACKS and inst.name in TRACKS_OLD:
        TRACKS[inst.name] = TRACKS_OLD[inst.name]
    if inst.name not in TRACKS:
        print('skip', inst.name); continue
    bname, pan, gdb, voices = TRACKS[inst.name]
    CUR[0] = inst.name
    notes = sorted(inst.notes, key=lambda n: n.start)
    # phrasing for melodic lines: legato joins + phrase arch (velocity offsets)
    if inst.name in ('Flute', 'Clarinet', 'Violins') or CAT.get(inst.name, {}).get('melodic'):
        mono = inst.name != 'Violins'
        phr = [[]]
        for a, b in zip(notes, notes[1:] + [None]):
            phr[-1].append(a)
            if b is None or b.start - a.end > 0.35:
                phr.append([])
            elif b.start - a.end < 0.12 and b.start > a.start + 0.05 and (mono or b.start >= a.end - 0.01):
                a.end = b.start + 0.05          # slur into the next note
        for ph in phr:
            if len(ph) < 3:
                continue
            ps = np.array([n.pitch for n in ph], float)
            v0 = np.array([n.velocity for n in ph], float)        # written velocities (accents)
            k = len(ph)
            for i, n in enumerate(ph):
                arch = np.sin(np.pi * (i + 0.5) / k)               # rise and fall over the phrase
                hi = (n.pitch - ps.mean()) / (np.ptp(ps) + 1e-6)    # higher notes a little stronger
                n.velocity = int(np.clip(n.velocity * (0.9 + 0.14 * arch + 0.08 * hi), 1, 127))
            # smooth note-to-note loudness inside the phrase (keep the overall contour)
            v = np.array([n.velocity for n in ph], float)
            sm = np.convolve(np.pad(v, 1, mode='edge'), np.ones(3) / 3, mode='valid')
            if E9('V9_ACCENT'):
                # smooth only among neighbours with similar WRITTEN velocity: a jump of >= 12 is a composed accent
                for i in range(k):
                    js = [j for j in (i - 1, i, i + 1) if 0 <= j < k and abs(v0[j] - v0[i]) < 12]
                    sm[i] = np.mean(v[js])
            pl = float(np.median(v))
            for n, a in zip(ph, sm):
                n.velocity = int(np.clip(0.35 * n.velocity + 0.65 * a, 1, 127))
                n.layer_vel = pl
    if E9('V9_FERMATA') and (inst.name in ('Violins', 'Violas', 'Cellos', 'Flute', 'Clarinet', 'Strings Pad') or
                             CAT.get(inst.name, {}).get('sustain')):
        # fermata release: the orchestra lifts before the next section (note end only; onsets/tempo unchanged)
        for n in notes:
            te = src.time_to_tick(n.end)
            for t in FERM_END:
                tt_ = src.tick_to_time(t)
                if abs(n.end - tt_) < 0.06 or abs(te - t) <= 10:
                    n.end = tt_ - (0.15 if tt_ - n.start >= 0.6 else 0.10)
                    n.fermata = True; n.breath = inst.name in WINDS
                    print(f'  fermata lift {inst.name} at {tt_:.2f}s', flush=True)
                    break
    if inst.name in WINDS:
        if E9('V9_BREATH'):
            plan_breaths(notes, inst.name, None if FIN is None else FIN.get(inst.name))
        if E9('V9_RETONGUE'):
            # repeated same-pitch notes: re-tongued (short stop), not two overlapping copies of the sample
            for a, b in zip(notes, notes[1:]):
                if a.pitch == b.pitch and b.start - a.end < 0.12 and b.start > a.start + 0.2 and not getattr(a, 'breath', False):
                    a.end = b.start - 0.035; a.retongue = True
        if E9('V9_SLURXF'):
            # true slur: next note enters without its attack via an equal-power crossfade
            for a, b in zip(notes, notes[1:]):
                if b.start - a.end < 0 and a.pitch != b.pitch and not getattr(a, 'breath', False) and \
                        not getattr(a, 'retongue', False) and b.start - a.start > XF + 0.05:
                    # short notes in fast runs get a shorter crossfade so they still reach full level (no dip)
                    xf = float(np.clip(min(XF, 0.3 * (b.end - b.start), 0.3 * (b.start - a.start)), 0.02, XF)) if E9('V9_XFSCALE', '0') else XF
                    a.end = b.start + xf / 2; a.slur_out = True; b.slur_in = True; a.xf_out = xf; b.xf_in = xf
        if E9('V9_PHRASEEND'):
            # phrase-final notes (rest > 0.25 s follows, or last note): taper -6 dB, note value kept
            for a, b in zip(notes, notes[1:] + [None]):
                if (b is None or b.start - a.end > 0.25) and not getattr(a, 'breath', False):
                    a.phrase_end = True
    if inst.name in LOWSLUR:
        # back-to-back notes in the inner/low strings: join like the violins (+50 ms), no velocity change
        for a, b in zip(notes, notes[1:]):
            if 0 <= b.start - a.end < 0.01 and b.start - a.start > 0.15:
                a.end = b.start + 0.05
    if (inst.name in ('Piano', 'Harp', 'Guitar', 'Celesta') or (inst.name in CAT and not CAT[inst.name]['sustain'])) and E9('V9_DEDUP'):
        # one key / string cannot be struck twice at the same instant: merge same-pitch notes within 5 ms
        keep = []
        for n in notes:
            d = next((k for k in keep[-12:] if k.pitch == n.pitch and abs(k.start - n.start) < 0.005), None)
            if d is None:
                keep.append(n)
            else:
                d.velocity = max(d.velocity, n.velocity); d.end = max(d.end, n.end)
        if len(keep) != len(notes):
            print(f'  {inst.name}: merged {len(notes) - len(keep)} duplicate notes', flush=True)
        notes = keep
    if inst.name == 'Violas' and os.environ.get('V8_VLALAYER', '1') == '1':
        # one velocity layer per phrase (as Flute/Clarinet/Violins), so timbre doesn't flip note by note;
        # velocities themselves are left untouched (no arch / smoothing)
        ph = [[]]
        for a, b in zip(notes, notes[1:] + [None]):
            ph[-1].append(a)
            if b is None or b.start - a.end > 0.35:
                ph.append([])
        for p_ in ph:
            if p_:
                pl = float(np.median([n.velocity for n in p_]))
                for n in p_:
                    n.layer_vel = pl
    if inst.name == 'Timpani':
        # rolls arrive as rapid repeated hits: turn runs into one rolled note
        i = 0
        while i < len(notes):
            j = i
            while j + 1 < len(notes) and notes[j + 1].start - notes[j].start < 0.08 and notes[j + 1].pitch == notes[i].pitch:
                j += 1
            if j - i >= 4:
                st, en = notes[i].start, notes[j].end
                render(BANKS['timpaniRoll'], notes[i].pitch, 100, st, en - st, pan, gdb)
            else:
                render(BANKS['timpani'], notes[i].pitch, notes[i].velocity, notes[i].start, notes[i].end - notes[i].start, pan, gdb)
            count += 1; i = j + 1
        continue
    # final harp glissando: boost the last fast run
    if inst.name == 'Harp':
        endt = max(n.end for n in notes)
        tail = [n for n in notes if n.start > endt - 30]
        run = []
        for a, b in zip(tail, tail[1:]):
            if b.start - a.start < 0.09:
                run += [a, b]
        for n in set(run):
            n.velocity = int(min(127, n.velocity * 1.4))
    # slow-attack instruments speak late: start them a little early so the perceived onset sits on the beat
    SC = float(os.environ.get('V8_STRCOMP', '0.010')) if STRTRIM else 0.025
    COMP = {'violins': SC, 'violas': SC, 'cellos': SC + CELLOX, 'contrabass': 0.025, 'pad': SC if STRTRIM else 0.03,
            'flute': 0.012, 'clarinet': 0.012}.get(bname, CAT.get(inst.name, {}).get('comp', 0.0))
    for k, n in enumerate(notes):
        if bname == 'pizz':
            bank = {'Violins Pizz': BANKS['violinsPizz'], 'Violas Pizz': BANKS['violasPizz'], 'Cellos Pizz': BANKS['celliPizz']}[inst.name]
        elif bname == 'pad':
            bank = BANKS['violins'] if n.pitch >= 60 else BANKS['violas'] if n.pitch >= 48 else BANKS['cellos']
        else:
            bank = BANKS[bname]
        for vce in range(voices):
            det = 0 if voices == 1 else (-6 if vce == 0 else 7)
            dly = 0 if vce == 0 else 0.014
            pv = pan if voices == 1 else pan + (-0.12 if vce == 0 else 0.12)
            gv = gdb - (3 if voices > 1 else 0)
            cp = COMP
            if inst.name == 'Flute' and os.environ.get('V8_FLUTEGRID', '1') == '1' and src.time_to_tick(n.start) % 120 == 0:
                cp = 0.035      # on-grid flute notes speak ~25 ms late; notes the source already anticipates keep 0.012
            si, so = getattr(n, 'slur_in', False), getattr(n, 'slur_out', False)
            if si:
                cp = getattr(n, 'xf_in', XF) / 2                        # slurred note: crossfade centred on the written onset
            tp, tdb, kr = 0.0, -8.0, False
            if getattr(n, 'retongue', False):
                tp = 0.04
            elif getattr(n, 'breath', False):
                tp = 0.12
            elif getattr(n, 'phrase_end', False):
                tp, tdb, kr = 0.15, -6.0, True
            render(bank, n.pitch, n.velocity, max(0.0, n.start - cp), n.end - n.start + (cp if (si or so) else 0), pv, gv, det, dly,
                   getattr(n, 'layer_vel', None), taper=tp, taper_db=tdb, slur_in=si, slur_out=so, keep_rel=kr,
                   xf_in=getattr(n, 'xf_in', None), xf_out=getattr(n, 'xf_out', None))
        count += 1
    print(f'{inst.name:14s} {len(notes)} notes', flush=True)

pass  # dynamics come from the original velocities

os.makedirs(out_path, exist_ok=True)
for name, b in stems.items():
    sf.write(os.path.join(out_path, name + '.wav'), b, SR, subtype='FLOAT')
json.dump({k: v[1] for k, v in TRACKS.items()} | {'Snare Drum': 0.0, 'Percussion': INS.PERC['pan']}, open(os.path.join(out_path, 'pans.json'), 'w'))
# onset compensation actually used (per track; on-grid flute notes use 0.035) for verify.py
_SC = float(os.environ.get('V8_STRCOMP', '0.010')) if STRTRIM else 0.025
_CT = {'violins': _SC, 'violas': _SC, 'cellos': _SC + CELLOX, 'contrabass': 0.025, 'pad': _SC if STRTRIM else 0.03, 'flute': 0.012, 'clarinet': 0.012}
json.dump({'COMP': {k: _CT.get(v[0], 0.0) for k, v in TRACKS.items()}}, open(os.path.join(out_path, 'render_model.json'), 'w'))
mix = stems[next(iter(stems))][:, None]
print('breaths', len(BREATHS), BREATHS)
print('rendered', count, 'events; length %.1fs' % (len(mix) / SR))
