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
                    os.path.join(out, slug, 'index.html'), base, repo], check=True)
    pieces.append((cfg['title'], slug, cfg['drafts'][0]['label'] if cfg['drafts'] else ''))
rows = '\n'.join(f'<li><a href="{s}/">{html.escape(t)}</a> <span>latest: {html.escape(l)}</span></li>' for t, s, l in pieces)
open(os.path.join(out, 'index.html'), 'w').write(r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Orchestral Drafts</title>
<style>:root{--bg:#faf8f3;--card:#fff;--ink:#1d1b16;--sub:#6b665b;--accent:#8a3b12;--rule:#e4ded2}
@media (prefers-color-scheme:dark){:root{--bg:#16140f;--card:#211e17;--ink:#ece7dc;--sub:#a59f92;--accent:#e08a5a;--rule:#3a352b}}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.5 Georgia,serif;padding:32px 16px}
main{max-width:640px;margin:0 auto} h1{font-size:28px;margin:0 0 4px} h2{font-size:20px;margin:0 0 8px}
p{color:var(--sub);margin:0 0 16px} ul{list-style:none;padding:0;margin:0 0 32px}
li{padding:12px 0;border-bottom:1px solid var(--rule)} a{color:var(--accent);font-size:20px;text-decoration:none}
li span{color:var(--sub);font-size:14px;margin-left:8px}
.card{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:16px;margin-bottom:16px}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center} input{font:inherit;font-size:15px;max-width:100%}
input[type=password]{flex:1;min-width:200px;padding:8px;border:1px solid var(--rule);border-radius:8px;background:var(--bg);color:var(--ink)}
button{font:600 15px system-ui,sans-serif;padding:9px 16px;border-radius:8px;border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer}
button.ghost{background:transparent;color:var(--accent)} button:disabled{opacity:.5}
#status{font:14px system-ui,sans-serif;color:var(--sub);margin:12px 0 0;white-space:pre-line}
details summary{cursor:pointer;color:var(--sub);font-size:15px}</style>
</head><body><main><h1>Orchestral drafts</h1><p>Pick a piece to listen and leave comments.</p><ul>
__ROWS__
</ul>
<section class="card" aria-labelledby="upT"><h2 id="upT">Add a new piece</h2>
<p>Upload a MIDI file exported from your notation program. Name its tracks after the instruments (Flute, Horn in F,
Violin I…). Draft 1 is rendered automatically and appears here in about 5–15 minutes.</p>
<div id="upBox" hidden><div class="row"><input type="file" id="midi" accept=".mid,.midi,audio/midi,audio/x-midi">
<button id="upBtn" disabled>Upload and render</button></div></div>
<p id="needKey">Uploading needs this device to be connected to GitHub (below).</p>
<p id="status" role="status"></p></section>
<section class="card"><details id="ghBox"><summary id="ghSum">Connect this device to GitHub</summary>
<p style="margin-top:10px">Paste the access key you were given, or open the connect link you were sent. It is kept only in this browser
and lets this device save comments and upload MIDI files.</p>
<div class="row"><input type="password" id="ghKey" placeholder="github_pat_…" autocomplete="off">
<button id="ghSave">Connect</button><button class="ghost" id="ghForget" hidden>Disconnect</button></div></details></section>
</main>
<script>
const REPO = "__REPO__";
(() => { const m = location.hash.match(/connect=([^&]+)/); if (!m) return;
  try { localStorage.setItem("gh-token", decodeURIComponent(m[1])); } catch (e) {}
  history.replaceState(null, "", location.pathname + location.search); })();
const $ = (i) => document.getElementById(i);
const tok = () => { try { return localStorage.getItem("gh-token") || ""; } catch (e) { return ""; } };
const say = (s) => { $("status").textContent = s; };
function ui() {
  const on = !!tok(); $("upBox").hidden = !on; $("needKey").hidden = on; $("ghForget").hidden = !on;
  $("ghSum").textContent = on ? "GitHub connection: connected" : "Connect this device to GitHub";
}
$("ghSave").onclick = () => { const k = $("ghKey").value.trim(); if (k) { try { localStorage.setItem("gh-token", k); } catch (e) {} $("ghKey").value = ""; ui(); } };
$("ghForget").onclick = () => { try { localStorage.removeItem("gh-token"); } catch (e) {} ui(); };
$("midi").onchange = () => { $("upBtn").disabled = !$("midi").files.length; };
const api = (path, opt = {}) => fetch("https://api.github.com/repos/" + REPO + path, { ...opt, cache: "no-store",
  headers: { Accept: "application/vnd.github+json", Authorization: "Bearer " + tok() } });
$("upBtn").onclick = async () => {
  const f = $("midi").files[0]; if (!f) return;
  const name = f.name.replace(/[^\w .()-]+/g, "_").replace(/\.(midi?|MIDI?)$/, "") + ".mid";
  if (!/\.midi?$/i.test(f.name)) { say("That isn't a MIDI file (.mid or .midi)."); return; }
  if (f.size > 5e6) { say("That file is over 5 MB, which is unusually large for a MIDI file."); return; }
  $("upBtn").disabled = true; say("Uploading " + name + "…");
  const u = new Uint8Array(await f.arrayBuffer()); let s = ""; for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode(...u.subarray(i, i + 8192));
  const t0 = Date.now();
  const r = await api("/contents/inbox/" + encodeURIComponent(name), { method: "PUT",
    body: JSON.stringify({ message: "Upload " + name + " for rendering", content: btoa(s), branch: "main" }) });
  if (!r.ok) { $("upBtn").disabled = false; say(r.status === 422 ? "A file called " + name + " is already waiting to be rendered." :
    r.status === 401 || r.status === 403 || r.status === 404 ? "GitHub refused the upload: the access key is missing, expired or lacks permission (" + r.status + ")." :
    "Upload failed (GitHub " + r.status + "). Try again in a minute."); return; }
  say("Uploaded. Rendering draft 1 (usually 5–15 minutes); you can leave this page and come back.");
  for (let k = 0; k < 120; k++) {                       // follow the render run for up to an hour
    await new Promise((res) => setTimeout(res, 30000));
    const q = await api("/actions/workflows/render.yml/runs?per_page=3");
    if (!q.ok) { say("Uploaded. Rendering draft 1: the piece appears on this page when it's ready (usually 5–15 minutes)."); return; }
    const run = (await q.json()).workflow_runs.find((x) => Date.parse(x.created_at) >= t0 - 60000);
    if (!run) continue;
    if (run.status !== "completed") { say("Rendering draft 1… (" + Math.round((Date.now() - t0) / 60000) + " min so far)"); continue; }
    if (run.conclusion === "success") { say("Draft 1 is ready. Updating this page…"); setTimeout(() => location.reload(), 120000); }
    else say("Rendering failed. The details are on GitHub: " + run.html_url);
    return;
  }
};
ui();
</script></body></html>""".replace('__ROWS__', rows).replace('__REPO__', repo))
print(f'{out}: {len(pieces)} pieces')
