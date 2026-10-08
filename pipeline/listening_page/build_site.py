"""Build the GitHub Pages site: one listening page per piece (every folder with config/listening_page.json) plus an
index. Audio streams from raw.githubusercontent.com, so the site itself stays small.

usage: build_site.py REPO_ROOT OUT_DIR [owner/repo]
"""
import html, json, os, re, subprocess, sys
from urllib.parse import quote

root, out = sys.argv[1:3]
repo = sys.argv[3] if len(sys.argv) > 3 else os.environ['GITHUB_REPOSITORY']
here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(out, exist_ok=True)
pieces = []
for folder in sorted(os.listdir(root)):
    cf = os.path.join(root, folder, 'config', 'listening_page.json')
    if not os.path.isfile(cf):
        continue
    cfg = json.load(open(cf))
    slug = re.sub(r'[^a-z0-9]+', '-', folder.lower()).strip('-')
    os.makedirs(os.path.join(out, slug), exist_ok=True)
    base = f'https://raw.githubusercontent.com/{repo}/main/{quote(folder)}/drafts/'
    subprocess.run([sys.executable, os.path.join(here, 'build.py'), os.path.join(root, folder),
                    os.path.join(out, slug, 'index.html'), base], check=True)
    pieces.append((cfg['title'], slug, cfg['drafts'][0]['label'] if cfg['drafts'] else ''))
rows = '\n'.join(f'<li><a href="{s}/">{html.escape(t)}</a> <span>latest: {html.escape(l)}</span></li>' for t, s, l in pieces)
open(os.path.join(out, 'index.html'), 'w').write(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Orchestral Drafts</title>
<style>:root{{--bg:#faf8f3;--ink:#1d1b16;--sub:#6b665b;--accent:#8a3b12}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16140f;--ink:#ece7dc;--sub:#a59f92;--accent:#e08a5a}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.5 Georgia,serif;padding:32px 16px}}
main{{max-width:640px;margin:0 auto}} h1{{font-size:28px;margin:0 0 4px}} p{{color:var(--sub);margin:0 0 24px}}
ul{{list-style:none;padding:0}} li{{padding:12px 0;border-bottom:1px solid color-mix(in srgb,var(--ink) 15%,transparent)}}
a{{color:var(--accent);font-size:20px;text-decoration:none}} span{{color:var(--sub);font-size:14px;margin-left:8px}}</style>
</head><body><main><h1>Orchestral drafts</h1><p>Pick a piece to listen and leave comments. Comments stay on your device;
use "Copy my comments" on the piece's page to send them.</p><ul>
{rows}
</ul></main></body></html>""")
print(f'{out}: {len(pieces)} pieces')
