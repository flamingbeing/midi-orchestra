"""Copy the sample files named by pipeline/instruments.py from local clones of the source libraries into
pipeline/assets/samples, converting WAV to lossless FLAC (half the size, bit-identical audio).

usage: import_samples.py VSCO_CLONE SSO_CLONE VCSL_CLONE
  clones of github.com/sgossner/VSCO-2-CE, github.com/peastman/sso, github.com/sgossner/VCSL
  (sparse checkouts are fine as long as the catalogue's folders are checked out)
"""
import os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import instruments as I

vsco, sso, vcsl = sys.argv[1:4]
ROOTS = {'VSCO-2-CE_git': vsco, 'sso_git': sso, 'VCSL': vcsl}
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'samples')


def src_dir(folder):
    lib, rest = folder.split('/', 1)
    return os.path.join(ROOTS[lib], rest), os.path.join(OUT, lib, rest)


jobs = []
specs = [(p['folder'], p['regex']) for e in I.CATALOG.values() for p in e['parts']] + list(I.DRUMS.values())
for folder, regex in specs:
    s, d = src_dir(folder)
    hits = [f for f in sorted(os.listdir(s)) if re.search(regex, f, re.I)]
    if not hits:
        sys.exit(f'no files match {regex!r} in {s}')
    for f in hits:
        jobs.append((os.path.join(s, f), os.path.join(d, os.path.splitext(f)[0] + '.flac')))
jobs = sorted(set(jobs))


def conv(j):
    a, b = j
    if os.path.exists(b):
        return 0
    os.makedirs(os.path.dirname(b), exist_ok=True)
    if a.lower().endswith('.flac'):
        subprocess.run(['cp', a, b], check=True)
    else:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a, '-map_metadata', '-1', '-c:a', 'flac',
                        '-compression_level', '8', b], check=True)
    return 1


with ThreadPoolExecutor(4) as ex:
    n = sum(ex.map(conv, jobs))
print(f'{len(jobs)} files ({n} new) in {OUT}')
