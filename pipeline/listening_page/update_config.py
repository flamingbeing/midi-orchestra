"""Create or update "<Piece>/config/listening_page.json" from the MP3s in "<Piece>/drafts/".

usage: update_config.py "PIECE FOLDER" [owner/repo]

New drafts (<midi name>_<draft>.mp3) are added at the top, so the newest is the page's default; existing entries keep
their ids, labels and song markers (saved comments are tagged by id). Song markers for a new draft come from the
MIDI's marker / rehearsal-mark events, else one marker with the title.
"""
import json, os, re, subprocess, sys
from urllib.parse import quote
import mido

piece = os.path.abspath(sys.argv[1])
repo = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('GITHUB_REPOSITORY') or re.sub(
    r'(\.git)?$', '', re.sub(r'^.*github\.com[:/]', '', subprocess.run(
        ['git', '-C', piece, 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()), count=1)
folder = os.path.basename(piece)
pj = json.load(open(os.path.join(piece, 'config', 'piece.json')))
midi = os.path.join(piece, pj['midi'])
name = os.path.splitext(os.path.basename(midi))[0]
title = pj.get('title', folder)
cf = os.path.join(piece, 'config', 'listening_page.json')
cfg = json.load(open(cf)) if os.path.exists(cf) else {
    'title': title, 'short_title': title, 'storage_key': re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-'),
    'github_raw': f'https://github.com/{repo}/raw/main/{quote(folder)}/drafts/', 'drafts': []}


def markers():
    mf = mido.MidiFile(midi)
    out, t = [], 0.0
    for msg in mido.merge_tracks(mf.tracks):          # merged track: delta ticks, tempo applied below
        t += mido.tick2second(msg.time, mf.ticks_per_beat, tempo[0]) if msg.time else 0.0
        if msg.type == 'set_tempo':
            tempo[0] = msg.tempo
        elif msg.type == 'marker' and msg.text.strip():
            out.append([round(t, 1), msg.text.strip()])
    return out if out and out[0][0] < 1 else [[0.0, title]] + out


tempo = [500000]
songs = markers()
have = {d.get('file', d['id'] + '.mp3') for d in cfg['drafts']}
new = []
for f in os.listdir(os.path.join(piece, 'drafts')):
    m = re.fullmatch(re.escape(name) + r'_(.+)\.mp3', f)
    if m and f not in have:
        did = m.group(1)
        label = re.sub(r'^draft(\w+)$', r'Draft \1', did).replace('_', ' ')
        new.append({'id': did, 'label': label, 'file': f, 'songs': songs})
key = lambda d: [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', d['id'])]
cfg['drafts'] = sorted(new, key=key, reverse=True) + cfg['drafts']
json.dump(cfg, open(cf, 'w'), indent=1)
print(f'{cf}: {len(cfg["drafts"])} drafts ({len(new)} new)')
