"""Build the listening-notes page for one piece.

usage: build.py "PIECE FOLDER" OUT.html

Reads PIECE FOLDER/config/listening_page.json:
  {"title": "Disney Medley", "short_title": "Medley", "storage_key": "medley",
   "github_raw": "https://github.com/<owner>/<repo>/raw/main/<folder, URL-encoded>/drafts/",
   "drafts": [{"id": "draft9", "label": "Draft 9", "songs": [[0.0, "Belle"], ...]}, ...]}   (newest first = default)
and fills duration and waveform peaks from PIECE FOLDER/drafts/<id>.mp3. The page plays audio/<id>.mp3, so publish
those MP3s next to the page (Artifact files {"audio/<id>.mp3": ...}). Download buttons link to github_raw + <id>.mp3.
storage_key keeps a listener's saved comments across rebuilds: never change it for a published page.
"""
import json, os, subprocess, sys
import numpy as np

piece, out = sys.argv[1:3]
cfg = json.load(open(os.path.join(piece, 'config', 'listening_page.json')))
drafts = []
for d in cfg['drafts']:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(piece, 'drafts', d['id'] + '.mp3'), '-ac', '2',
                          '-ar', '44100', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    m = np.abs(np.frombuffer(raw, np.float32).reshape(-1, 2)).max(1)
    n = len(m) // 1200
    pk = [float(np.sqrt(np.mean(m[i * n:(i + 1) * n] ** 2))) for i in range(1200)]
    mx = max(pk)
    drafts.append(dict(id=d['id'], label=d['label'], src=f"audio/{d['id']}.mp3", dur=round(len(m) / 44100, 2),
                       peaks=[round(100 * p / mx) for p in pk], songs=d['songs']))
t = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.html')).read()
for k, v in {'__TITLE_SHORT__': cfg.get('short_title', cfg['title']), '__TITLE__': cfg['title'],
             '__GH__': cfg['github_raw'], '__KEY__': cfg['storage_key'],
             '__DRAFTS__': json.dumps(drafts, separators=(',', ':'))}.items():
    t = t.replace(k, v)
open(out, 'w').write(t)
print(f'{out}: {len(drafts)} drafts')
