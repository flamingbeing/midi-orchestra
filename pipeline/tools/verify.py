#!/usr/bin/env python3
"""Blocking verification of one rendered version of the medley (stems + master) against the MIDI.

usage:
  verify.py --stems DIR --master WAV --midi MID [--encoded M4A] [--prev-metrics JSON] [--mix-log LOG] --out JSON

Exit code 0 = PASS, 1 = FAIL (any absolute failure or any REGRESSION vs --prev-metrics), 2 = usage error.

Checks
 (0) note loudness consistency (the user's hard gate) - identical algorithm to v7b/noteloud.py: per-note RMS over
     [start, start+clip(dur,0.08,0.3)] vs the quadratic velocity law; resid SD and p90 adjacent-note jump (dB).
 (1) per-note pitch of every pitched stem vs MIDI: pyin on the note's own window (range +-19 st around the written
     pitch so octave errors are visible); |dev| > 6 st is an octave error unless it is a SINGLE flag on a low / short /
     overlapped note AND a spectral check confirms the written fundamental (then it is a suspect detector error).
 (2) onset alignment per stem vs MIDI note-ons (spectral-flux peak near each note-on group; reported vs the note-on and
     vs the engine's intended early start (onset compensation table COMP)).
 (3) clicks / discontinuities in every stem and the master (2nd-difference spikes), classified at-onset vs elsewhere;
     clipping / NaN on the master.
 (4) master integrated loudness, LRA, true peak (ffmpeg ebur128), L/R balance; the same for --encoded if given.
 (5) melody prominence: 1-4 kHz band SNR of Flute and Clarinet vs everything else while they play (MIDI notes on),
     using the stems at mix gains (parsed from the mix log / STEMS/mix_gains.json) with the v7b ducking model.
 (6) celesta audibility the same way; (6b) cello audibility 2:08-2:34 (100-1000 Hz band; user feedback at 2:20).
 (7) per-section loudness arc of the master (sections from the MIDI tempo map) + 10 s arc, and its correlation with the
     MIDI velocity arc.
 (8) diff vs --prev-metrics with REGRESSION flags (tolerances in TOL below).
"""
import argparse, json, os, re, subprocess, sys, time
from multiprocessing import Pool
import numpy as np
import soundfile as sf
import pretty_midi as pm
from scipy.signal import butter, sosfilt
from scipy.ndimage import median_filter, uniform_filter1d

SR = 44100
PSR = 22050                                     # analysis rate for pyin / onsets
UNPITCHED = {'Snare Drum'}
# engine's intended early start (render_v7b.py COMP): perceived onset should land on the note-on
COMP = {'Violins': 0.025, 'Violas': 0.025, 'Cellos': 0.025, 'Strings Pad': 0.03, 'Flute': 0.012, 'Clarinet': 0.012}
# v7b mix model (mix_v7b.py) used to put the stems at their mix levels for the masking checks
ACCOMP = {'Harp', 'Guitar', 'Piano', 'Strings Pad', 'Violas', 'Glockenspiel'}
AUTOMATION = {'Cellos': [(130.0, 152.0, 3.5)]}
TARGET = {'Flute': 1, 'Clarinet': 4.5, 'Violins': -2, 'Cellos': -3.5, 'Violas': -5, 'Piano': -4, 'Harp': -8.5,
          'Guitar': -11, 'Celesta': -4, 'Glockenspiel': -9, 'Strings Pad': -9, 'Snare Drum': -10,
          'Violins Pizz': -6, 'Violas Pizz': -6, 'Cellos Pizz': -6}

# regression tolerances: (metric path, direction, tolerance). direction: 'lower' = lower is better, 'higher', 'abs0'
TOL_NOTELOUD = 0.3
HOLD_RESTS = False


DSF = [None]     # draft 9+: duck depth scale (10 ms grid) written by the mix
def load_models(stems_dir):
    """draft 8+: the renderer writes render_model.json (onset compensation) and the mix writes mix_model.json
    (ducked stems, automation, targets) next to the stems, so the masking model follows the actual mix."""
    global COMP, ACCOMP, AUTOMATION, TARGET, HOLD_RESTS
    p = os.path.join(stems_dir, 'render_model.json')
    if os.path.exists(p):
        COMP = json.load(open(p))['COMP']
    p = os.path.join(stems_dir, 'mix_model.json')
    if os.path.exists(p):
        m = json.load(open(p))
        ACCOMP = set(m['ACCOMP']); AUTOMATION = {k: [tuple(x) for x in v] for k, v in m['AUTOMATION'].items()}
        TARGET = m['TARGET']; HOLD_RESTS = bool(m.get('hold_rests'))
        DSF[0] = os.path.join(stems_dir, m['duck_scale_file']) if m.get('duck_scale_file') else None
    return {'COMP': COMP, 'ACCOMP': sorted(ACCOMP), 'AUTOMATION': AUTOMATION, 'HOLD_RESTS': HOLD_RESTS}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def load_mono(path, sr=SR):
    x, s = sf.read(path, dtype='float32', always_2d=True)
    assert s == SR, (path, s)
    x = x.mean(1)
    if sr != SR:
        import soxr
        x = soxr.resample(x, SR, sr).astype(np.float32)
    return x


def midi_hz(p):
    return 440.0 * 2 ** ((p - 69) / 12)


# ---------------------------------------------------------------- (0) note loudness (== v7b/noteloud.py)
def noteloud(x, notes):
    ns = sorted(notes, key=lambda n: n.start)
    lv = []
    for n in ns:
        a = int(max(0, n.start) * SR); b = int((n.start + min(0.3, max(0.08, n.end - n.start))) * SR)
        lv.append(20 * np.log10(np.sqrt(np.mean(x[a:b].astype(np.float64) ** 2)) + 1e-9))
    lv = np.array(lv); vel = np.array([n.velocity for n in ns], float)
    exp = 40 * np.log10(vel / 127)
    res = lv - exp; res -= np.median(res)
    jumps = [abs(lv[i + 1] - lv[i] - (exp[i + 1] - exp[i])) for i in range(len(ns) - 1) if ns[i + 1].start - ns[i].end < 0.15]
    worst = np.argsort(-np.abs(res))[:5]
    return {'n': len(ns), 'level_med_db': round(float(np.median(lv)), 2), 'resid_sd_db': round(float(np.std(res)), 2),
            'p90_adj_jump_db': round(float(np.percentile(jumps, 90)) if jumps else 0.0, 2),
            'worst_notes': [{'t': round(ns[i].start, 2), 'pitch': ns[i].pitch, 'vel': ns[i].velocity,
                             'resid_db': round(float(res[i]), 1)} for i in worst]}


# ---------------------------------------------------------------- (1) pitch
_CACHE = {}


def _stem22(path):
    if path not in _CACHE:
        _CACHE.clear()
        _CACHE[path] = load_mono(path, PSR)
    return _CACHE[path]


def _spec(seg, n):
    w = np.hanning(len(seg))
    return np.abs(np.fft.rfft(seg * w, n)) / (w.sum() + 1e-12)


def spectral_cents(seg, f, pre=None):
    """cents of the strongest spectral peak within +-100 c of the written fundamental (onset-differential spectrum if
    the note adds new energy), parabolic interpolation; None if no peak there within 30 dB of the band maximum."""
    n = max(1 << 16, 1 << int(np.ceil(np.log2(len(seg)))))
    sp = _spec(seg, n)
    if pre is not None and len(pre) >= 1024:
        sd = np.maximum(sp - _spec(pre, n), 0)
        if sd.max() > 0.25 * sp.max():
            sp = sd
    fr = np.fft.rfftfreq(n, 1 / PSR)
    m = np.flatnonzero((fr > f * 2 ** (-1 / 12)) & (fr < f * 2 ** (1 / 12)))
    if len(m) < 3 or f > 9000:
        return None
    k = m[np.argmax(sp[m])]
    if sp[k] < sp[(fr > 25) & (fr < 9000)].max() * 10 ** (-30 / 20) or k in (m[0], m[-1]):
        return None
    a, b, c = np.log(sp[k - 1:k + 2] + 1e-20)
    off = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
    return float(1200 * np.log2((fr[k] + off * (fr[1] - fr[0])) / f))


def spectral_check(seg, f, others, pre=None):
    """True if the written fundamental f is confirmed in the note's window.
    present: the written harmonic series is there - peak at f > -30 dB, or 2f AND 3f > -36 dB (re the strongest
             partial 25 Hz-9 kHz), in the plain OR the onset-differential spectrum.
    sub:     an unexplained subharmonic f/2 or 3f/2 within 12 dB of the strongest of f/2f/3f (the signature of a sample an
             octave too low), required in the plain AND (if usable) the onset-differential spectrum max(|S|-|S_pre|, 0),
             so partials of notes that were already ringing do not count.  'Explained' = a harmonic (1..11) of another
             note sounding in the window.
    Returns (present and not sub, {partial: dB} of the spectrum used for the decision)."""
    n = max(1 << 15, 1 << int(np.ceil(np.log2(len(seg)))))
    fr = np.fft.rfftfreq(n, 1 / PSR)
    band = (fr > 25) & (fr < 9000)
    plain = _spec(seg, n)
    specs = [plain]
    if pre is not None and len(pre) >= 1024:
        sd = np.maximum(plain - _spec(pre, n), 0)
        if sd[band].max() > 0.25 * plain[band].max():          # the note adds clearly new energy -> use the differential too
            specs.append(sd)

    def explained(fx):
        for of in others:
            for h in range(1, 12):
                if abs(1200 * np.log2(fx / (of * h))) < 60:
                    return True
        return False

    def judge(sp):
        ref = sp[band].max()
        if ref <= 0:
            return False, True, {}

        def pk(fx):
            m = (fr > fx * 2 ** (-0.6 / 12)) & (fr < fx * 2 ** (0.6 / 12))
            return max(-120.0, 20 * np.log10(sp[m].max() / ref + 1e-12)) if m.any() and fx < 9000 else -120.0
        d = {'f': pk(f), '2f': pk(2 * f), '3f': pk(3 * f), '4f': pk(4 * f), 'f/2': pk(f / 2), '3f/2': pk(1.5 * f)}
        present = d['f'] > -30 or (d['2f'] > -36 and d['3f'] > -36)   # odd partial 3f required: an octave-high sample has only 2f, 4f, ..
        top = max(d['f'], d['2f'], d['3f'])
        sub = any(fx > 25 and d[k] > top - 12 and not explained(fx) for k, fx in (('f/2', f / 2), ('3f/2', 1.5 * f)))
        return present, sub, {k: round(float(v), 1) for k, v in d.items()}

    J = [judge(s) for s in specs]
    present = any(j[0] for j in J)
    sub = all(j[1] for j in J)
    return bool(present and not sub), J[-1][2]


def pitch_task(args):
    import librosa
    path, items = args
    x = _stem22(path)
    out = []
    for it in items:
        p, s, e, others = it['pitch'], it['start'], it['end'], it['others']
        f = midi_hz(p)
        dur = e - s
        a = s + min(0.04, 0.25 * dur)
        b = s + float(np.clip(dur, 0.12, 0.6))
        fl = 4096 if p < 45 else 2048
        i0 = int(a * PSR) - fl // 2; i1 = int(b * PSR) + fl // 2
        if i0 < 0:
            i0 = 0
        seg = x[i0:i1].astype(np.float64)
        p1 = int((s - it.get('comp', 0.0) - 0.005) * PSR); p0 = max(0, p1 - min(len(seg), int(0.25 * PSR)))
        pre = x[p0:max(p0, p1)].astype(np.float64)
        rec = {'i': it['i']}
        if len(seg) >= fl + 4:
            sc = spectral_cents(seg, f, pre)
            if sc is not None:
                rec['spec_cents'] = round(sc, 1)
        if len(seg) < fl + 4 or np.sqrt(np.mean(seg ** 2)) < 1e-6:
            rec['status'] = 'silent'; out.append(rec); continue
        fmin = max(f * 2 ** (-19 / 12), 25.0); fmax = min(f * 2 ** (19 / 12), PSR / 2 - 200)
        try:
            f0, vf, vp = librosa.pyin(seg, fmin=fmin, fmax=fmax, sr=PSR, frame_length=fl, hop_length=256, center=False)
        except Exception as ex:                                  # pragma: no cover
            rec['status'] = 'error:' + str(ex)[:60]; out.append(rec); continue
        ok = vf & np.isfinite(f0)
        if not ok.any():
            ok = np.isfinite(f0) & (vp >= np.nanmax(vp) * 0.8) if np.isfinite(vp).any() and np.nanmax(vp) > 0.05 else np.zeros_like(vf)
        if not ok.any():
            rec['status'] = 'unvoiced'; out.append(rec); continue
        cents = float(np.median(1200 * np.log2(f0[ok] / f)))
        rec['cents'] = round(cents, 1)
        rec['status'] = 'ok'
        if abs(cents) > 600:
            got = p + cents / 100
            if any(abs(got - op) < 0.7 for op in it['others_pitch']):
                rec['status'] = 'other_note'                    # pyin locked onto another note sounding in the window
            else:
                rec['status'] = 'flag'
            conf, d = spectral_check(seg, f, others, pre)
            rec['spectral_confirms_written'] = conf; rec['spec_db'] = d
        out.append(rec)
    return out


SHORT = 0.2
# how long a note keeps ringing after its MIDI note-off in the stem (plucked / struck instruments decay freely)
RING = {'Harp': 3.0, 'Piano': 2.0, 'Guitar': 2.0, 'Celesta': 2.0, 'Glockenspiel': 3.0}


def _win_overlap(n, o, ring=0.1):
    """does note o sound inside n's pyin analysis window (incl. frame padding, legato extension and release)?"""
    dur = n.end - n.start
    pad = (4096 if n.pitch < 45 else 2048) / 2 / PSR
    a = n.start + min(0.04, 0.25 * dur) - pad
    b = n.start + float(np.clip(dur, 0.12, 0.6)) + pad
    return o.start < b and o.end + ring > a


def pitch_check(stems, midi, pool):
    """Octave-error rule (per stem):
       pyin |dev| > 6 st on a note is a FLAG, unless pyin's pitch equals another note sounding in the window
       ('other_note': chords / ringing notes - not evidence about this note).
       A flag is a SUSPECT detector error (not counted) only if the note is low (<48) / short (<0.2 s) / overlapped AND
       the spectral check confirms the written fundamental AND its pitch is not 'systematic'; every other flag is an
       OCTAVE ERROR.  'single' (no flag on the same written pitch in the neighbouring onset groups) is reported per
       suspect; runs of suspects (repeated ostinato notes under chords, where pyin fails the same way every time) are
       counted separately as suspect_runs.  A written pitch is 'systematic' (the draft-5 clarinet-bug pattern: one
       wrong sample = every occurrence wrong) if >= 50% of its >= 2 isolated occurrences are flagged, or >= 2 of its
       flags fail the spectral check; all flags of a systematic pitch count as errors."""
    tasks, meta = [], {}
    for inst in midi.instruments:
        if inst.name in UNPITCHED or inst.name not in stems:
            continue
        ns = sorted(inst.notes, key=lambda n: (n.start, n.pitch))
        meta[inst.name] = ns
        ring = RING.get(inst.name, 0.1)
        items = []
        for i, n in enumerate(ns):
            oth = [o for o in ns if o is not n and _win_overlap(n, o, ring)]
            items.append({'i': i, 'pitch': n.pitch, 'start': n.start, 'end': n.end, 'comp': COMP.get(inst.name, 0.0),
                          'others': [midi_hz(o.pitch) for o in oth], 'others_pitch': [o.pitch for o in oth]})
        for k in range(0, len(items), 60):
            tasks.append((stems[inst.name], items[k:k + 60]))
    res = {}
    for t, r in zip(tasks, pool.imap(pitch_task, tasks)):
        res.setdefault(t[0], []).extend(r)
    out = {}
    for name, ns in meta.items():
        ring = RING.get(name, 0.1)
        recs = sorted(res.get(stems[name], []), key=lambda r: r['i'])
        # onset-group index of every note, to define "neighbouring" notes in time (chords share a group)
        gidx, g, last = [], -1, -9.0
        for n in ns:
            if n.start - last > 0.03:
                g += 1
            last = n.start; gidx.append(g)
        flag_at = {}
        for r in recs:
            if r['status'] == 'flag':
                flag_at.setdefault(ns[r['i']].pitch, set()).add(gidx[r['i']])
        # isolated-by-MIDI (note-offs + 0.1 s) for the cents statistics; acoustically overlapped (incl. free ringing of
        # plucked / struck notes, RING) for the 'overlapped' octave-error exemption
        ovl = {r['i']: any(o is not ns[r['i']] and _win_overlap(ns[r['i']], o) for o in ns) for r in recs}
        ovl_ring = {r['i']: any(o is not ns[r['i']] and _win_overlap(ns[r['i']], o, ring) for o in ns) for r in recs}
        iso_cnt, iso_flag = {}, {}
        for r in recs:
            if not ovl[r['i']] and r['status'] in ('ok', 'flag'):
                pp = ns[r['i']].pitch
                iso_cnt[pp] = iso_cnt.get(pp, 0) + 1
                iso_flag[pp] = iso_flag.get(pp, 0) + (r['status'] == 'flag')
        unconf = {}
        for r in recs:
            if r['status'] == 'flag' and not r['spectral_confirms_written']:
                unconf[ns[r['i']].pitch] = unconf.get(ns[r['i']].pitch, 0) + 1
        systematic = sorted(set(pp for pp in iso_cnt if iso_flag[pp] >= 2 and iso_flag[pp] >= 0.5 * iso_cnt[pp]) |
                            set(pp for pp, c in unconf.items() if c >= 2))
        errors, suspects, cents_all, cents_iso = [], [], [], []
        for r in recs:
            n = ns[r['i']]
            dur = n.end - n.start
            oth = ovl[r['i']]
            special = n.pitch < 48 or dur < SHORT or ovl_ring[r['i']]
            if r['status'] == 'ok':
                cents_all.append(abs(r['cents']))
                if not oth:
                    cents_iso.append(abs(r['cents']))
            elif r['status'] == 'flag':
                gi = gidx[r['i']]
                single = not ({gi - 1, gi + 1} & flag_at.get(n.pitch, set()))
                e = {'t': round(n.start, 3), 'mmss': f"{int(n.start // 60)}:{n.start % 60:05.2f}", 'pitch': n.pitch,
                     'dev_st': round(r['cents'] / 100, 1), 'dur': round(dur, 3), 'overlapped': ovl_ring[r['i']], 'single': single,
                     'spectral_confirms_written': r['spectral_confirms_written'], 'spec_db': r['spec_db']}
                if special and r['spectral_confirms_written'] and n.pitch not in systematic:
                    suspects.append(e)
                else:
                    errors.append(e)
        st = {}
        for r in recs:
            st[r['status']] = st.get(r['status'], 0) + 1
        sc = np.array([abs(r['spec_cents']) for r in recs if 'spec_cents' in r])
        ca, ci = np.array(cents_all), np.array(cents_iso)
        out[name] = {'n': len(ns), 'status_counts': st, 'octave_errors': len(errors), 'suspect_detector_errors': len(suspects),
                     'suspect_runs': sum(not e['single'] for e in suspects),
                     'systematic_pitches': systematic,
                     'median_abs_cents': round(float(np.median(ca)), 1) if len(ca) else None,
                     'median_abs_cents_isolated': round(float(np.median(ci)), 1) if len(ci) else None,
                     'p90_abs_cents_isolated': round(float(np.percentile(ci, 90)), 1) if len(ci) else None,
                     'n_isolated': int(len(ci)),
                     'spectral_median_abs_cents': round(float(np.median(sc)), 1) if len(sc) else None,
                     'spectral_p90_abs_cents': round(float(np.percentile(sc, 90)), 1) if len(sc) else None,
                     'spectral_n': int(len(sc)), 'n_isolated_over_50c': int((ci > 50).sum()) if len(ci) else 0,
                     'errors': errors[:60], 'suspects': suspects[:60]}
    return out


# ---------------------------------------------------------------- (2) onsets
def onset_task(args):
    import librosa
    name, path, starts = args
    x = _stem22(path)
    hop = 128
    env = librosa.onset.onset_strength(y=x, sr=PSR, hop_length=hop, n_fft=1024, lag=1, max_size=3, center=True)
    t = np.arange(len(env)) * hop / PSR
    comp = COMP.get(name, 0.0)
    offs, weak, worst = [], 0, []
    for s in starts:
        a, b = np.searchsorted(t, [s - comp - 0.06, s + 0.15])
        if b - a < 3:
            continue
        loc0, loc1 = np.searchsorted(t, [s - 0.6, s + 0.6])
        base = np.median(env[loc0:loc1]) + 1e-9
        k = a + int(np.argmax(env[a:b]))
        if env[k] < 2.0 * base or k >= b - 2 or k <= a + 1:     # weak, or max at the window edge = no onset match
            weak += 1
            continue
        o = t[k] - s
        offs.append(o)
        worst.append((abs(o), s, o))
    offs = np.array(offs)
    worst.sort(reverse=True)
    r = {'groups': len(starts), 'salient': len(offs), 'weak_or_legato': weak}
    if len(offs):
        r.update({'median_ms': round(1000 * float(np.median(offs)), 1),
                  'median_ms_vs_render_start': round(1000 * float(np.median(offs) + comp), 1),
                  'p10_ms': round(1000 * float(np.percentile(offs, 10)), 1),
                  'p90_ms': round(1000 * float(np.percentile(offs, 90)), 1),
                  'mad_ms': round(1000 * float(np.median(np.abs(offs - np.median(offs)))), 1),
                  'n_over_60ms': int((np.abs(offs) > 0.06).sum()),
                  'worst': [{'t': round(s, 2), 'mmss': f"{int(s // 60)}:{s % 60:05.2f}", 'off_ms': round(1000 * o, 1)}
                            for _, s, o in worst[:5]]})
    return name, r


def onset_groups(notes):
    st = sorted(n.start for n in notes)
    g = []
    for s in st:
        if not g or s - g[-1] > 0.03:
            g.append(s)
    return g


# ---------------------------------------------------------------- (3) clicks
CLICK_HF_DB = 8.0


def clicks(x, sr=SR, rel_floor_db=-60.0, order=24, blk=4096):
    """Discontinuities (spikes, steps, dropouts): whiten the signal with a block-wise LPC predictor (order 24, 93 ms
    blocks) so that ordinary bright sustained audio has a flat residual; a click is a 10 ms residual frame whose crest
    (max/rms within the frame) > 6 and whose max is > 8x the median residual-frame rms of the surrounding 210 ms."""
    import librosa
    from scipy.signal import lfilter
    x = x.astype(np.float64)
    e = np.zeros_like(x)
    pk = np.abs(x).max() + 1e-12
    for i in range(0, len(x) - blk, blk):
        b = x[i:i + blk]
        if np.abs(b).max() < pk * 1e-4:
            continue
        h = x[max(0, i - order):i + blk]
        try:
            a = librosa.lpc(b + 1e-9 * np.random.default_rng(0).standard_normal(blk), order=order)
        except Exception:
            continue
        r = lfilter(a, [1.0], h)
        e[i:i + blk] = r[len(h) - blk:]
    fr = 441
    n = len(e) // fr
    d = np.abs(e[:n * fr].reshape(n, fr))
    mx = d.max(1); rms = np.sqrt((d ** 2).mean(1)) + 1e-15
    nb = median_filter(rms, size=21, mode='nearest')
    floor = pk * 10 ** (rel_floor_db / 20)            # residual jump must be > -60 dB re stem peak (audible size)
    hit = (mx / rms > 6) & (mx > 8 * nb) & (mx > floor)
    # confirmation: a real discontinuity is a broadband burst - peak 0.5 ms >6 kHz energy within +-1 ms must stand
    # the >6 kHz energy of the surrounding +-25 ms by CLICK_HF_DB (rejects LPC crest false positives on near-sinusoidal tones)
    hp = butter(4, 6000, 'high', fs=sr, output='sos')
    times = []
    for i in np.flatnonzero(hit):
        c = i * fr + int(np.argmax(d[i]))
        a0, a1 = max(0, c - 2205 - 512), min(len(x), c + 2205 + 512)
        h = uniform_filter1d(sosfilt(hp, x[a0:a1]) ** 2, 22)          # 0.5 ms HF energy
        cc = c - a0
        burst = h[max(0, cc - 44):cc + 44].max()
        ctx = np.concatenate([h[512:max(512, cc - 220)], h[cc + 220:len(h) - 512]])
        if len(ctx) < 100 or 10 * np.log10((burst + 1e-20) / (np.median(ctx) + 1e-20)) < CLICK_HF_DB:
            continue
        t = c / sr
        sev = 20 * np.log10(mx[i] / nb[i])
        if not times or t - times[-1][0] > 0.05:
            times.append((round(t, 3), round(float(sev), 1)))
    return times


def classify_clicks(times, onsets, ends):
    on = np.sort(np.array(onsets)) if len(onsets) else np.array([-9.0])
    en = np.sort(np.array(ends)) if len(ends) else np.array([-9.0])
    cls = {'at_onset': 0, 'at_note_end': 0, 'elsewhere': 0, 'elsewhere_sev_ge_20db': 0}
    where = []
    for t, sev in times:
        i = np.searchsorted(on, t)
        don = min(abs(t - on[max(i - 1, 0)]), abs(t - on[min(i, len(on) - 1)]))
        j = np.searchsorted(en, t)
        den = min(abs(t - en[max(j - 1, 0)]), abs(t - en[min(j, len(en) - 1)]))
        if don < 0.05:
            cls['at_onset'] += 1
        elif den < 0.05:
            cls['at_note_end'] += 1; where.append((t, sev, 'end'))
        else:
            cls['elsewhere'] += 1; where.append((t, sev, 'mid'))
            cls['elsewhere_sev_ge_20db'] += int(sev >= 20)
    where.sort(key=lambda w: -w[1])
    cls['worst_not_at_onset'] = [{'t': t, 'mmss': f"{int(t // 60)}:{t % 60:06.3f}", 'sev_db': sv, 'where': k} for t, sv, k in where[:15]]
    return cls


# ---------------------------------------------------------------- (4) master
def ebur(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true:framelog=quiet',
                        '-f', 'null', '-'], capture_output=True, text=True)
    txt = r.stderr[r.stderr.rfind('Summary:'):]
    g = lambda pat: float(re.search(pat, txt).group(1))
    return {'lufs_i': g(r'I:\s+(-?[\d.]+) LUFS'), 'lra_lu': g(r'LRA:\s+(-?[\d.]+) LU'), 'true_peak_dbtp': g(r'Peak:\s+(-?[\d.inf]+) dBFS')}


# ---------------------------------------------------------------- (5,6) masking
def mix_gains(stems_dir, mix_log, names):
    p = os.path.join(stems_dir, 'mix_gains.json')
    if os.path.exists(p):
        return json.load(open(p)), 'mix_gains.json'
    if mix_log and os.path.exists(mix_log):
        g = {}
        for line in open(mix_log):
            m = re.match(r'^(.+?)\s+(-?[\d.]+) LUFS in hall ->\s+([+-][\d.]+) dB', line)
            if m:
                g[m.group(1).strip()] = float(m.group(3))
        if set(names) <= set(g):
            return g, 'mix log ' + mix_log
    return {n: 0.0 for n in names}, 'NONE (stems at render level; masking numbers unreliable)'


def band_frames(x, lo, hi, fr=2048, hop=1024):
    sos = butter(4, [lo, hi], 'band', fs=SR, output='sos')
    y = sosfilt(sos, x).astype(np.float32) ** 2
    e = uniform_filter1d(y, fr)[fr // 2::hop]
    return e


def masking(stems_dir, mix_log, midi):
    names = sorted(f[:-4] for f in os.listdir(stems_dir) if f.endswith('.wav'))
    gains, src = mix_gains(stems_dir, mix_log, names)
    xs = {n: load_mono(os.path.join(stems_dir, n + '.wav')) for n in names}
    L = max(len(v) for v in xs.values())
    xs = {n: np.pad(v, (0, L - len(v))) for n, v in xs.items()}
    t = np.arange(L) / SR
    for n_, pts in AUTOMATION.items():
        if n_ in xs:
            gdb = np.zeros(L, np.float32)
            for a0, a1, gg in pts:
                gdb += gg * np.clip(np.minimum((t - a0) / 1.5, (a1 - t) / 1.5), 0, 1).astype(np.float32)
            xs[n_] = xs[n_] * 10 ** (gdb / 20)
    del t
    # v7b ducking model (from the dry melody stems)
    def envf(x):
        return np.sqrt(np.maximum(uniform_filter1d(x.astype(np.float64) ** 2, 2205), 0))
    w = np.zeros(L); wc = np.zeros(L)
    for n in ('Flute', 'Clarinet'):
        if n in xs:
            e = envf(xs[n]); w = np.maximum(w, e / (e.max() + 1e-12))
            if n == 'Clarinet':
                wc = e / (e.max() + 1e-12)
    def activity(x):
        b = x > 0.03
        if HOLD_RESTS:                       # draft-8 mix: duck held through melody rests < 1.5 s
            from scipy.ndimage import binary_closing
            h = 441
            bb = b[: len(b) // h * h].reshape(-1, h).any(1)
            bb = binary_closing(np.pad(bb, 150), structure=np.ones(150))[150:-150]
            b = np.pad(np.repeat(bb, h), (0, L - len(bb) * h), mode='edge')
        return uniform_filter1d(b.astype(np.float64), int(0.6 * SR))
    act = activity(w); actc = activity(wc)
    ds = np.ones(L)
    if DSF[0] and os.path.exists(DSF[0]):
        d_ = np.repeat(np.load(DSF[0]).astype(np.float64), 441); ds = np.pad(d_, (0, max(0, L - len(d_))), mode='edge')[:L]
    duck = np.minimum(10 ** (-3.0 * ds * np.clip(act * 1.5, 0, 1) / 20), 10 ** (-5.0 * ds * np.clip(actc * 1.5, 0, 1) / 20)).astype(np.float32)
    del w, wc, act, actc, ds
    for n in names:
        xs[n] = xs[n] * np.float32(10 ** (gains.get(n, 0.0) / 20))
        if n in ACCOMP:
            xs[n] = xs[n] * duck
    total = np.zeros(L, np.float32)
    for n in names:
        total += xs[n]
    hop = 1024
    out = {'gain_source': src, 'gains_db': gains}

    def snr(name, lo, hi, t0=None, t1=None):
        if name not in xs:
            return None
        inst = [i for i in midi.instruments if i.name == name][0]
        m = band_frames(xs[name], lo, hi); r = band_frames(total - xs[name], lo, hi)
        k = min(len(m), len(r)); m, r = m[:k], r[:k]
        tf = (np.arange(k) * hop + 1024) / SR
        on = np.zeros(k, bool)
        for nt in inst.notes:
            a, b = np.searchsorted(tf, [nt.start, max(nt.end, nt.start + 0.05)])
            on[a:b] = True
        if t0 is not None:
            on &= (tf >= t0) & (tf < t1)
        s = 10 * np.log10((m[on] + 1e-14) / (r[on] + 1e-14))
        # worst 5-s windows (median SNR) while playing
        win = []
        for w0 in np.arange(0, tf[-1], 5.0):
            sel = on & (tf >= w0) & (tf < w0 + 5)
            if sel.sum() >= 40:
                win.append((float(np.median(10 * np.log10((m[sel] + 1e-14) / (r[sel] + 1e-14)))), w0))
        win.sort()
        return {'band_hz': [lo, hi], 'frames': int(on.sum()), 'median_snr_db': round(float(np.median(s)), 2),
                'p10_snr_db': round(float(np.percentile(s, 10)), 2), 'pct_frames_below_0db': round(100 * float((s < 0).mean()), 1),
                'pct_frames_below_-6db': round(100 * float((s < -6).mean()), 1),
                'worst_5s': [{'t': w0, 'mmss': f"{int(w0 // 60)}:{int(w0 % 60):02d}", 'median_snr_db': round(v, 1)} for v, w0 in win[:5]]}

    out['Flute'] = snr('Flute', 1000, 4000)
    out['Clarinet'] = snr('Clarinet', 1000, 4000)
    out['Celesta'] = snr('Celesta', 1000, 4000)
    out['Cellos_2m20'] = snr('Cellos', 100, 1000, 128.0, 154.0)
    return out


# ---------------------------------------------------------------- (7) arc
def sections_from_tempo(midi, end):
    tt, bpm = midi.get_tempo_changes()
    bounds = [0.0]
    for i in range(1, len(tt)):
        nxt = tt[i + 1] if i + 1 < len(tt) else end
        prev_stable = bpm[i - 1]
        if abs(np.log(bpm[i] / prev_stable)) > 0.08 and nxt - tt[i] >= 8 and tt[i] - bounds[-1] >= 8:
            bounds.append(float(tt[i]))
    bounds.append(end)
    return bounds


def arc(master, midi):
    import pyloudnorm as pyln
    x, sr = sf.read(master, dtype='float64', always_2d=True)
    meter = pyln.Meter(sr)
    end = midi.get_end_time()
    b = sections_from_tempo(midi, end)
    notes = [n for i in midi.instruments for n in i.notes]
    secs = []
    for a, c in zip(b[:-1], b[1:]):
        seg = x[int(a * sr):int(c * sr)]
        vel = [n.velocity for n in notes if a <= n.start < c]
        secs.append({'start': round(a, 2), 'end': round(c, 2), 'mmss': f"{int(a // 60)}:{int(a % 60):02d}",
                     'lufs': round(float(meter.integrated_loudness(seg)), 2),
                     'rms_db': round(float(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)), 2),
                     'midi_vel_db': round(float(np.mean(40 * np.log10(np.array(vel) / 127))), 2) if vel else None,
                     'notes_per_s': round(len(vel) / (c - a), 2)})
    a10 = []
    for w0 in np.arange(0, end, 10.0):
        seg = x[int(w0 * sr):int((w0 + 10) * sr)]
        vel = [n.velocity for n in notes if w0 <= n.start < w0 + 10]
        a10.append({'t': float(w0), 'rms_db': round(float(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)), 2),
                    'midi_vel_db': round(float(np.mean(40 * np.log10(np.array(vel) / 127))), 2) if vel else None})
    ok = [(s['lufs'], s['midi_vel_db']) for s in secs if s['midi_vel_db'] is not None and np.isfinite(s['lufs'])]
    r = float(np.corrcoef(*zip(*ok))[0, 1]) if len(ok) > 2 else None
    ok10 = [(s['rms_db'], s['midi_vel_db']) for s in a10 if s['midi_vel_db'] is not None and s['rms_db'] > -90]
    r10 = float(np.corrcoef(*zip(*ok10))[0, 1]) if len(ok10) > 2 else None
    return {'sections': secs, 'arc_10s': a10, 'corr_sections_lufs_vs_midi_vel': round(r, 3) if r is not None else None,
            'corr_10s_rms_vs_midi_vel': round(r10, 3) if r10 is not None else None}


# ---------------------------------------------------------------- (8) checks / diff
def build_checks(M, P):
    checks = []

    def add(name, value, ok, detail='', prev=None, kind='ABS'):
        checks.append({'check': name, 'value': value, 'prev': prev, 'status': 'PASS' if ok else ('REGRESSION' if kind == 'REG' else 'FAIL'),
                       'detail': detail})

    # absolute checks
    for n, r in M['pitch'].items():
        add(f'pitch.{n}.octave_errors', r['octave_errors'], r['octave_errors'] == 0,
            '; '.join(f"{e['mmss']} p{e['pitch']} {e['dev_st']:+}st" for e in r['errors'][:6]))
    m = M['master']
    add('master.lufs_i', m['lufs_i'], abs(m['lufs_i'] + 16) <= 1.0, 'target -16 +-1')
    add('master.true_peak_dbtp', m['true_peak_dbtp'], m['true_peak_dbtp'] <= -1.0, '<= -1 dBTP')
    add('master.lra_lu', m['lra_lu'], m['lra_lu'] >= 7.0, '>= 7 LU')
    add('master.lr_balance_db', m['lr_balance_db'], abs(m['lr_balance_db']) <= 1.5, '|L-R| <= 1.5 dB')
    add('master.clipped_samples', m['clipped_samples'], m['clipped_samples'] == 0)
    add('master.nonfinite', m['nonfinite'], m['nonfinite'] == 0)
    if 'encoded' in M:
        add('encoded.true_peak_dbtp', M['encoded']['true_peak_dbtp'], M['encoded']['true_peak_dbtp'] <= -0.5, '<= -0.5 dBTP after AAC')
    if not P:
        return checks
    # regressions vs previous version
    for n, r in M['noteloud'].items():
        p = P.get('noteloud', {}).get(n)
        if not p:
            continue
        for k in ('resid_sd_db', 'p90_adj_jump_db'):
            add(f'noteloud.{n}.{k}', r[k], r[k] <= p[k] + TOL_NOTELOUD, f'HARD GATE: <= prev + {TOL_NOTELOUD}', p[k], 'REG')
    for n, r in M['pitch'].items():
        p = P.get('pitch', {}).get(n)
        if p and r['median_abs_cents'] is not None and p.get('median_abs_cents') is not None:
            add(f'pitch.{n}.median_abs_cents', r['median_abs_cents'], r['median_abs_cents'] <= p['median_abs_cents'] + 5, '<= prev + 5 c',
                p['median_abs_cents'], 'REG')
        if p and r.get('spectral_median_abs_cents') is not None and p.get('spectral_median_abs_cents') is not None:
            add(f'pitch.{n}.spectral_median_abs_cents', r['spectral_median_abs_cents'],
                r['spectral_median_abs_cents'] <= p['spectral_median_abs_cents'] + 5, '<= prev + 5 c', p['spectral_median_abs_cents'], 'REG')
    for n, r in M['onsets'].items():
        p = P.get('onsets', {}).get(n)
        if p and 'median_ms' in r and 'median_ms' in p:
            add(f'onsets.{n}.abs_median_ms', abs(r['median_ms']), abs(r['median_ms']) <= abs(p['median_ms']) + 10, '<= prev + 10 ms',
                abs(p['median_ms']), 'REG')
            add(f'onsets.{n}.mad_ms', r['mad_ms'], r['mad_ms'] <= p['mad_ms'] + 8, '<= prev + 8 ms', p['mad_ms'], 'REG')
    for n, r in M['clicks']['stems'].items():
        p = P.get('clicks', {}).get('stems', {}).get(n)
        if p:
            v, pv = r['at_note_end'] + r['elsewhere'], p['at_note_end'] + p['elsewhere']
            add(f'clicks.{n}.not_at_onset', v, v <= pv + max(2, int(0.2 * pv)), '<= prev + max(2, 20%)', pv, 'REG')
    pc = P.get('clicks', {}).get('master')
    if pc:
        v, pv = M['clicks']['master']['at_note_end'] + M['clicks']['master']['elsewhere'], pc['at_note_end'] + pc['elsewhere']
        add('clicks.master.not_at_onset', v, v <= pv + max(2, int(0.2 * pv)), '<= prev + max(2, 20%)', pv, 'REG')
    for k in ('Flute', 'Clarinet', 'Celesta', 'Cellos_2m20'):
        r, p = M['masking'].get(k), P.get('masking', {}).get(k)
        if r and p:
            add(f'masking.{k}.median_snr_db', r['median_snr_db'], r['median_snr_db'] >= p['median_snr_db'] - 1.0, '>= prev - 1 dB',
                p['median_snr_db'], 'REG')
            add(f'masking.{k}.p10_snr_db', r['p10_snr_db'], r['p10_snr_db'] >= p['p10_snr_db'] - 1.5, '>= prev - 1.5 dB',
                p['p10_snr_db'], 'REG')
    pm_ = P.get('master', {})
    if pm_:
        add('master.lra_lu(reg)', m['lra_lu'], m['lra_lu'] >= pm_['lra_lu'] - 1.5, '>= prev - 1.5 LU', pm_['lra_lu'], 'REG')
    ps = P.get('arc', {}).get('sections', [])
    cs = M['arc']['sections']
    if ps and len(ps) == len(cs):
        d = np.array([c['lufs'] - p['lufs'] for c, p in zip(cs, ps)])
        dev = d - np.median(d)
        worst = int(np.argmax(np.abs(dev)))
        add('arc.section_shape_dev_db', round(float(np.abs(dev).max()), 2), float(np.abs(dev).max()) <= 2.0,
            f"max deviation of section loudness change from the median change (<= 2 dB), worst at {cs[worst]['mmss']}", None, 'REG')
    pr = P.get('arc', {}).get('corr_sections_lufs_vs_midi_vel')
    if pr is not None and M['arc']['corr_sections_lufs_vs_midi_vel'] is not None:
        add('arc.corr_vs_midi', M['arc']['corr_sections_lufs_vs_midi_vel'], M['arc']['corr_sections_lufs_vs_midi_vel'] >= pr - 0.1,
            '>= prev - 0.1', pr, 'REG')
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stems', required=True); ap.add_argument('--master', required=True); ap.add_argument('--midi', required=True)
    ap.add_argument('--encoded'); ap.add_argument('--prev-metrics'); ap.add_argument('--mix-log'); ap.add_argument('--out', required=True)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--skip', default='', help='comma list of sections to skip: pitch,onsets,clicks,masking,arc (debug only)')
    A = ap.parse_args()
    skip = set(filter(None, A.skip.split(',')))
    T0 = time.time()
    midi = pm.PrettyMIDI(A.midi)
    stems = {f[:-4]: os.path.join(A.stems, f) for f in sorted(os.listdir(A.stems)) if f.endswith('.wav')}
    M = {'args': vars(A), 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    M['models'] = load_models(A.stems)
    missing = [i.name for i in midi.instruments if i.name not in stems]
    M['missing_stems'] = missing

    # (0) note loudness
    log('noteloud...')
    M['noteloud'] = {}
    for inst in midi.instruments:
        if inst.name in stems and len(inst.notes) >= 20:
            M['noteloud'][inst.name] = noteloud(load_mono(stems[inst.name]), inst.notes)

    with Pool(A.jobs) as pool:
        if 'pitch' not in skip:
            log('pitch...'); M['pitch'] = pitch_check(stems, midi, pool)
        else:
            M['pitch'] = {}
        if 'onsets' not in skip:
            log('onsets...')
            tasks = [(i.name, stems[i.name], onset_groups(i.notes)) for i in midi.instruments if i.name in stems]
            M['onsets'] = dict(pool.map(onset_task, tasks))
        else:
            M['onsets'] = {}

    # (3) clicks
    M['clicks'] = {'stems': {}}
    if 'clicks' not in skip:
        log('clicks...')
        all_on, all_end = [], []
        for inst in midi.instruments:
            if inst.name not in stems:
                continue
            comp = COMP.get(inst.name, 0.0)
            on = [n.start - comp for n in inst.notes]; en = [n.end for n in inst.notes]
            all_on += on; all_end += en
            t = clicks(load_mono(stems[inst.name]))
            M['clicks']['stems'][inst.name] = {'total': len(t), **classify_clicks(t, on, en)}
    # (4) master
    log('master...')
    x, sr = sf.read(A.master, dtype='float32', always_2d=True)
    assert sr == SR
    m = ebur(A.master)
    rl, rr = [float(np.sqrt(np.mean(x[:, c].astype(np.float64) ** 2))) for c in range(2)]
    m['lr_balance_db'] = round(20 * np.log10(rl / rr), 2)
    m['lr_correlation'] = round(float(np.corrcoef(x[::4, 0], x[::4, 1])[0, 1]), 3)
    m['sample_peak_dbfs'] = round(float(20 * np.log10(np.abs(x).max() + 1e-12)), 2)
    m['clipped_samples'] = int((np.abs(x) >= 0.999).sum())
    m['nonfinite'] = int((~np.isfinite(x)).sum())
    m['duration_s'] = round(len(x) / SR, 2)
    M['master'] = m
    if 'clicks' not in skip:
        t = sorted(clicks(x[:, 0]) + clicks(x[:, 1]))
        t = [a for i, a in enumerate(t) if i == 0 or a[0] - t[i - 1][0] > 0.05]
        M['clicks']['master'] = {'total': len(t), **classify_clicks(t, all_on, all_end)}
    del x
    if A.encoded:
        M['encoded'] = ebur(A.encoded)
    if 'masking' not in skip:
        log('masking...'); M['masking'] = masking(A.stems, A.mix_log, midi)
    else:
        M['masking'] = {}
    if 'arc' not in skip:
        log('arc...'); M['arc'] = arc(A.master, midi)
    else:
        M['arc'] = {'sections': [], 'corr_sections_lufs_vs_midi_vel': None}

    P = json.load(open(A.prev_metrics)) if A.prev_metrics else None
    M['checks'] = build_checks(M, P)
    bad = [c for c in M['checks'] if c['status'] != 'PASS']
    M['status'] = 'PASS' if not bad else 'FAIL'
    M['runtime_s'] = round(time.time() - T0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(A.out)), exist_ok=True)
    json.dump(M, open(A.out, 'w'), indent=1, default=float)

    # human summary
    print(f"== verify: {M['status']}  ({len(bad)} failing checks, {M['runtime_s']} s)")
    print('noteloud (resid SD / p90 jump dB):', ', '.join(f"{n} {r['resid_sd_db']}/{r['p90_adj_jump_db']}" for n, r in M['noteloud'].items()))
    print('pitch (octave err / suspect / median|c| pyin-isolated / median|c| spectral):', ', '.join(
        f"{n} {r['octave_errors']}/{r['suspect_detector_errors']}/{r['median_abs_cents_isolated']}/{r.get('spectral_median_abs_cents')}"
        for n, r in M['pitch'].items()))
    print('onsets median ms (MAD):', ', '.join(f"{n} {r.get('median_ms')}({r.get('mad_ms')})" for n, r in M['onsets'].items()))
    if M['clicks'].get('master'):
        print('clicks not-at-onset: master', M['clicks']['master']['at_note_end'] + M['clicks']['master']['elsewhere'], '| stems',
              ', '.join(f"{n} {r['at_note_end'] + r['elsewhere']}" for n, r in M['clicks']['stems'].items() if r['at_note_end'] + r['elsewhere']))
    print('master:', {k: m[k] for k in ('lufs_i', 'lra_lu', 'true_peak_dbtp', 'lr_balance_db', 'sample_peak_dbfs')},
          ('encoded: ' + str(M['encoded'])) if 'encoded' in M else '')
    for k in ('Flute', 'Clarinet', 'Celesta', 'Cellos_2m20'):
        r = M['masking'].get(k)
        if r:
            print(f"masking {k}: median SNR {r['median_snr_db']} dB, p10 {r['p10_snr_db']}, <0 dB {r['pct_frames_below_0db']}%")
    if M['arc']['sections']:
        print('arc LUFS:', ' '.join(f"{s['mmss']}:{s['lufs']}" for s in M['arc']['sections']), '| corr vs MIDI vel', M['arc']['corr_sections_lufs_vs_midi_vel'])
    for c in bad:
        print(f"  {c['status']:10s} {c['check']} = {c['value']} (prev {c['prev']}) {c['detail']}")
    sys.exit(0 if not bad else 1)


if __name__ == '__main__':
    main()
