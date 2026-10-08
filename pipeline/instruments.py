"""Instrument catalogue: every sound the pipeline can render beyond the core Disney Medley set.

render.py loads a sound from here the first time a MIDI track with that name appears; mix.py reads pan, seat depth,
family and loudness target from here. prepare.py maps General MIDI programs / track names onto these names.

Pitched sounds ("parts") are folders under assets/samples with a filename regex whose groups are
  note (A-G, optional #), oct (octave digit) or key (keyboard index, with key_base), and layer (dynamic layer name).
Every sample's real pitch is measured on load (render.folder_bank), so octave-mislabelled filenames are corrected;
measure=False trusts the names instead. (Organ check: the VSCO "Open" manual rank sounds at 16' pitch - key 1 = C1 -
and the pedal at 32'; the harmonic series of the samples confirms what the pitch measurement reports.)
When several parts are given, a later part only adds samples more than 1.5 semitones away from those already loaded
(e.g. organ pedal pipes below the manual, female choir above the male choir).

DRUMS maps General MIDI percussion notes (channel 10) to one-shot sample sets. Notes not listed (and the snare notes
37/38/40) play on the snare, as before.
"""
N = r'(?P<note>[A-G]#?)(?P<oct>-?\d)'
VSCO = 'VSCO-2-CE_git'
SSO = 'sso_git/Sonatina Symphonic Orchestra/Samples'
VCSL = 'VCSL'
DYN = {'ppp': 0.2, 'pp': 0.3, 'p': 0.45, 'mp': 0.55, 'mf': 0.7, 'f': 0.85, 'ff': 1.0, 'fff': 1.0,
       'soft': 0.45, 'med': 0.7, 'loud': 1.0}


def P(folder, regex, **kw):
    return dict(folder=folder, regex=regex, **kw)


# family: winds / brass / strings / perc / piano / choir (mix ambience + stage depth); target: loudness after the hall
# relative to the melody (dB, see mix.py TARGET); comp: onset compensation (s, slow speakers start early);
# melodic: legato joins + phrase arch; cap: breath capacity in seconds (wind/brass players breathe); damped: the note
# stops at note-off (harpsichord, pizzicato) instead of ringing on.
CATALOG = {
    # woodwinds
    'Piccolo':        dict(parts=[P(f'{SSO}/Piccolo', r'^piccolo-' + N + r'(?P<layer>)\.')], sustain=True, release=0.25, attack=0.02,
                           pan=-0.15, family='winds', target=-1, melodic=True, cap=6.0, comp=0.012),
    'Alto Flute':     dict(parts=[P(f'{SSO}/Alto Flute', r'^alto_flute-' + N + r'(?P<layer>)\.')], sustain=True, release=0.25, attack=0.02,
                           pan=-0.12, family='winds', target=-1, melodic=True, cap=6.0, comp=0.012),
    'Oboe':           dict(parts=[P(f'{VSCO}/Woodwinds/Oboe/Vib', r'Oboe_Vib_' + N + r'_(?P<layer>v\d)')], sustain=True, release=0.25,
                           attack=0.02, pan=0.05, family='winds', target=0, melodic=True, cap=12.0, comp=0.012),
    'Cor Anglais':    dict(parts=[P(f'{SSO}/Cor Anglais', r'^cor_anglais-' + N + r'(?P<layer>)\.')], sustain=True, release=0.25,
                           attack=0.02, pan=0.1, family='winds', target=-1, melodic=True, cap=10.0, comp=0.012),
    'Bass Clarinet':  dict(parts=[P(f'{SSO}/Bass Clarinet', r'^bass_clarinet-' + N + r'(?P<layer>)\.')], sustain=True, release=0.25,
                           attack=0.02, pan=0.15, family='winds', target=-3, melodic=True, cap=9.0, comp=0.012),
    'Bassoon':        dict(parts=[P(f'{VSCO}/Woodwinds/Bassoon/sus', r'PSBassoon_' + N + r'_(?P<layer>v\d)'),
                                  P(f'{VSCO}/Woodwinds/Bassoon/vib', r'PSBassoon_' + N + r'_(?P<layer>v\d)')], sustain=True,
                           release=0.25, attack=0.02, pan=0.2, family='winds', target=-3, melodic=True, cap=9.0, comp=0.012),
    'Contrabassoon':  dict(parts=[P(f'{SSO}/Contrabassoon', r'^contrabassoon-' + N + r'(?P<layer>)\.')], sustain=True, release=0.3,
                           attack=0.03, pan=0.25, family='winds', target=-5, melodic=True, cap=7.0, comp=0.015),
    'Saxophone':      dict(parts=[P(f'{VCSL}/Aerophones/Reed Aerophones/Tenor Saxophone/Non-Vibrato',
                                    r'BrettTenor_NV_Main_' + N + r'_(?P<layer>vl\d)_rr\d')], sustain=True, release=0.25, attack=0.015,
                           pan=0.0, family='winds', target=0, melodic=True, cap=10.0, comp=0.010),
    'Recorder':       dict(parts=[P(f'{VCSL}/Aerophones/Edge-blown Aerophones/Baroque Alto Recorder/SusVib',
                                    r'AltRecorder_SusVib_' + N + r'_(?P<layer>)rr\d')], sustain=True, release=0.2, attack=0.015,
                           pan=-0.1, family='winds', target=-1, melodic=True, cap=8.0, comp=0.010),
    # brass
    'Horns':          dict(parts=[P(f'{VSCO}/Brass/F Horn/sus', r'MOHorn_sus_' + N + r'_(?P<layer>v\d)')], sustain=True, release=0.35,
                           attack=0.03, pan=-0.35, family='brass', target=-2, melodic=True, cap=10.0, comp=0.020),
    'Trumpet':        dict(parts=[P(f'{VSCO}/Brass/Trumpet/susvib', r'SHTrumpet_susvib_' + N + r'_(?P<layer>v\d)')], sustain=True,
                           release=0.3, attack=0.015, pan=0.3, family='brass', target=-1, melodic=True, cap=10.0, comp=0.010),
    'Trombone':       dict(parts=[P(f'{VSCO}/Brass/Tenor Trombone/sus', r'tenortbn_sus_' + N + r'_(?P<layer>v\d)')], sustain=True,
                           release=0.35, attack=0.025, pan=0.45, family='brass', target=-3, melodic=True, cap=9.0, comp=0.015),
    'Bass Trombone':  dict(parts=[P(f'{SSO}/Bass Trombone', r'^bass_trombone-' + N + r'(?P<layer>)\.')], sustain=True, release=0.35,
                           attack=0.03, pan=0.5, family='brass', target=-4, melodic=True, cap=8.0, comp=0.015),
    'Tuba':           dict(parts=[P(f'{VSCO}/Brass/Tuba/sus', r'Tuba3_sus_' + N + r'_(?P<layer>v\d)')], sustain=True, release=0.35,
                           attack=0.03, pan=0.55, family='brass', target=-4, melodic=True, cap=7.0, comp=0.020),
    # strings: soloists, basses, tremolo
    'Solo Violin':    dict(parts=[P(f'{VSCO}/Strings/Solo Violin/Arco Vib', r'LLVln_ArcoVib_' + N + r'_(?P<layer>p|f)\.')], sustain=True,
                           release=0.3, attack=0.03, pan=-0.25, family='strings', target=0, melodic=True, comp=0.015),
    'Solo Viola':     dict(parts=[P(f'{SSO}/Viola', r'^viola-sus-' + N + r'(?P<layer>)\.')], sustain=True, release=0.3, attack=0.03,
                           pan=0.1, family='strings', target=-1, melodic=True, comp=0.015),
    'Solo Cello':     dict(parts=[P(f'{SSO}/Cello', r'^cello-' + N + r'(?P<layer>)\.')], sustain=True, release=0.3, attack=0.03,
                           pan=0.25, family='strings', target=-1, melodic=True, comp=0.015),
    'Contrabass':     dict(parts=[P(f'{SSO}/Basses', r'^basses-sus-' + N + r'(?P<layer>)\.')], sustain=True, release=0.4, attack=0.04,
                           pan=0.6, family='strings', target=-5, comp=0.025),
    'Contrabass Pizz': dict(parts=[P(f'{VSCO}/Strings/Solo Contrabass/Pizz', r'BKCtbss_Pizz_' + N + r'_(?P<layer>v\d)_rr\d')],
                            sustain=False, damped=True, release=0.25, attack=0.002, pan=0.6, family='strings', target=-6),
    'Violins Trem':   dict(parts=[P(f'{VSCO}/Strings/Violin Section/Trem', r'VlnEns_Trem_' + N + r'_(?P<layer>v\d)')], sustain=True,
                           release=0.3, attack=0.02, pan=-0.45, family='strings', target=-3, seat='Violins', comp=0.010),
    'Violas Trem':    dict(parts=[P(f'{VSCO}/Strings/Viola Section/trem', r'Violas_trem_' + N + r'_(?P<layer>v\d)')], sustain=True,
                           release=0.3, attack=0.02, pan=0.2, family='strings', target=-5, seat='Violas', comp=0.010),
    'Cellos Trem':    dict(parts=[P(f'{VSCO}/Strings/Cello Section/trem', r'^trem_' + N + r'_(?P<layer>v\d)')], sustain=True,
                           release=0.3, attack=0.02, pan=0.45, family='strings', target=-4, seat='Cellos', comp=0.010),
    'Contrabass Trem': dict(parts=[P(f'{SSO}/Basses', r'^basses-trm-' + N + r'(?P<layer>)\.')], sustain=True, release=0.35,
                            attack=0.03, pan=0.6, family='strings', target=-6, comp=0.015),
    # voices
    'Choir':          dict(parts=[P(f'{SSO}/Chorus', r'^chorus-male-' + N + r'(?P<layer>)\.'),
                                  P(f'{SSO}/Chorus', r'^chorus-female-' + N + r'(?P<layer>)\.')], sustain=True, release=0.5,
                           attack=0.06, pan=0.0, family='choir', target=-3, comp=0.030),
    # keyboards and mallets
    'Harpsichord':    dict(parts=[P(f'{SSO}/Harpsichord/Sustains/Low', r'HarpsiRH_Low_Far_' + N + r'_(?P<layer>)rr\d'),
                                  P(f'{SSO}/Harpsichord/Sustains/High', r'HarpsiRH_High_Far_' + N + r'_(?P<layer>)rr\d')],
                           sustain=False, damped=True, release=0.25, attack=0.002, pan=-0.2, family='piano', target=-4),
    'Organ':          dict(parts=[P(f'{VSCO}/Keys/Organ/Loud', r'Rode_Man3Open_(?P<key>\d+)(?P<layer>)\.', key_base=36),
                                  P(f'{VSCO}/Keys/Organ/Loud', r'Rode_Pedal_(?P<key>\d+)(?P<layer>)\.', key_base=24)],
                           sustain=True, release=0.6, attack=0.04, pan=0.0, family='piano', target=-4),
    'Marimba':        dict(parts=[P(f'{VCSL}/Idiophones/Struck Idiophones/Marimba',
                                    r'Marimba_hit_Outrigger_' + N + r'_(?P<layer>soft|med|loud)_\d+')], sustain=False, release=0.4,
                           attack=0.001, pan=0.25, family='perc', target=-5),
    'Xylophone':      dict(parts=[P(f'{VCSL}/Idiophones/Struck Idiophones/Xylophone/Medium Mallets',
                                    r'Xylo_Medium_' + N + r'_(?P<layer>pp|ff)_\d+')], sustain=False, release=0.4, attack=0.001,
                           pan=0.3, family='perc', target=-6),
    'Vibraphone':     dict(parts=[P(f'{VCSL}/Idiophones/Struck Idiophones/Vibraphone/Soft Mallets',
                                    r'Vibes_soft_' + N + r'_(?P<layer>v\d)_rr\d')], sustain=False, release=0.6, attack=0.002,
                           pan=0.2, family='perc', target=-5),
    'Tubular Bells':  dict(parts=[P(f'{VCSL}/Idiophones/Struck Idiophones/Tubular Bells 1',
                                    r'chimes_' + N + r'_(?P<layer>pp|p|f|ff|fff)_rr\d')], sustain=False, release=1.0, attack=0.001,
                           pan=0.35, family='perc', target=-6),
}

_I = f'{VCSL}/Idiophones/Struck Idiophones'
_M = f'{VCSL}/Membranophones/Struck Membranophones'
# GM drum note -> (folder, filename regex with optional (?P<layer>...)). Snare notes 37/38/40 stay on the snare bank.
DRUMS = {
    35: (f'{_M}/Bass Drum 2', r'bassdrum_hit_(?P<layer>pp|mp|mf|f|ff)\d*\.'),
    36: (f'{_M}/Bass Drum 2', r'bassdrum_hit_(?P<layer>pp|mp|mf|f|ff)\d*\.'),
    39: (f'{_I}/Claps', r'^Clap_rr\d'),
    41: (f'{_M}/Tom 2/Stick', r'TomL_HitS_(?P<layer>v\d)_rr\d'),
    43: (f'{_M}/Tom 2/Stick', r'TomL_HitS_(?P<layer>v\d)_rr\d'),
    45: (f'{_M}/Tom 1/Stick', r'TomH_HitS_(?P<layer>v\d)_rr\d'),
    47: (f'{_M}/Tom 1/Stick', r'TomH_HitS_(?P<layer>v\d)_rr\d'),
    48: (f'{_M}/Tom 1/Stick', r'TomH_HitS_(?P<layer>v\d)_rr\d'),
    50: (f'{_M}/Tom 1/Stick', r'TomH_HitS_(?P<layer>v\d)_rr\d'),
    42: (f'{_I}/Hi-Hat Cymbal', r'HiHat_HitC_(?P<layer>v\d)_rr\d'),
    44: (f'{_I}/Hi-Hat Cymbal', r'HiHat_Close_rr\d'),
    46: (f'{_I}/Hi-Hat Cymbal', r'HiHat_HitO_rr\d'),
    49: (f'{_I}/Clash Cymbals 1', r'cymbal_crash\d_(?P<layer>pp|mp|mf|f)\d\.'),
    57: (f'{_I}/Clash Cymbals 1', r'cymbal_crash\d_(?P<layer>pp|mp|mf|f)\d\.'),
    51: (f'{_I}/Suspended Cymbal 1', r'susCymb\d_hit_(?:stick_)?(?P<layer>pp|mp|f|fff)\d\.'),
    59: (f'{_I}/Suspended Cymbal 1', r'susCymb\d_hit_(?:stick_)?(?P<layer>pp|mp|f|fff)\d\.'),
    53: (f'{_I}/Suspended Cymbal 1', r'susCymb\d_hit_bell_(?P<layer>pp|mf|fff)\d\.'),
    55: (f'{_I}/Suspended Cymbal 1', r'susCymb\d_hit_(?P<layer>pp|mp|f|fff)\d\.'),
    52: (f'{_I}/Gong 1', r'^gong_(?P<layer>p|mf|f|fff)\.'),
    54: (f'{_I}/Tambourine 1', r'Tam\w*_Hit_(?P<layer>v\d)_rr\d'),
    56: (f'{_I}/Cowbells', r'Cowbell\d_Hit_(?P<layer>v\d)_rr\d'),
    58: (f'{_I}/Vibraslap/Legacy', r'vibraslap_rr\d'),
    60: (f'{_M}/Bongos', r'BongoH_Hit\d_(?P<layer>v\d)_rr\d'),
    61: (f'{_M}/Bongos', r'BongoL_Hit\d_(?P<layer>v\d)_rr\d'),
    62: (f'{_M}/Conga', r'^Conga_HitFM_(?P<layer>v\d)_rr\d'),
    63: (f'{_M}/Conga', r'^Conga_HitN_(?P<layer>v\d)_rr\d'),
    64: (f'{_M}/Conga', r'^Tumba_HitN_(?P<layer>v\d)_rr\d'),
    67: (f'{_I}/Agogo Bells', r'Agogo_High_(?P<layer>v\d)_rr\d'),
    68: (f'{_I}/Agogo Bells', r'Agogo_Low_(?P<layer>v\d)_rr\d'),
    69: (f'{_I}/Cabasa', r'Cabasa\d_Hit_rr\d'),
    70: (f'{_I}/Shaker, Small', r'Shaker_Slap_rr\d'),
    82: (f'{_I}/Shaker, Small', r'Shaker_Slap_rr\d'),
    73: (f'{_I}/Guiro', r'Guiro_Fast_rr\d'),
    74: (f'{_I}/Guiro', r'Guiro_Slow_rr\d'),
    75: (f'{_I}/Claves', r'Claves\d_Hit_(?P<layer>v\d)_rr\d'),
    76: (f'{_I}/Woodblock', r'wood_click_(?P<layer>pp|mp|f|ff)'),
    77: (f'{_I}/Woodblock', r'wood_click_(?P<layer>pp|mp|f|ff)'),
    80: (f'{_I}/Triangles', r'Triangle\d_HitM_(?P<layer>v\d)_rr\d'),
    81: (f'{_I}/Triangles', r'Triangle\d_Hit_(?P<layer>v\d)_rr\d'),
    83: (f'{_I}/Sleigh Bells', r'Sleighbells_Hit_rr\d'),
}
PERC = dict(pan=0.1, family='perc', target=-10)       # the "Percussion" stem (all mapped drum notes)
