"""Turn a MIDI file into a new piece folder: "<Title>/score/<name>.mid", config/piece.json, notes/USER_FEEDBACK.md.

usage: new_piece.py PATH/TO/My Song.mid [REPO_ROOT]     -> prints the new folder name ("My Song")

The folder is named after the file (underscores become spaces); the MIDI is stored as a lower-case, underscore name
(my_song.mid), which is also the prefix of every draft (my_song_draft1.mp3). An existing folder of the same name gets
a numeric suffix rather than being overwritten.
"""
import json, os, re, shutil, sys

src = sys.argv[1]
root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
stem = os.path.splitext(os.path.basename(src))[0]
title = re.sub(r'\s+', ' ', stem.replace('_', ' ')).strip() or 'Untitled'
name = re.sub(r'[^a-z0-9]+', '_', stem.lower()).strip('_') or 'piece'
folder, k = title, 2
while os.path.exists(os.path.join(root, folder)):
    folder, k = f'{title} {k}', k + 1
d = os.path.join(root, folder)
for sub in ('score', 'config', 'notes', 'drafts'):
    os.makedirs(os.path.join(d, sub), exist_ok=True)
shutil.copyfile(src, os.path.join(d, 'score', name + '.mid'))
json.dump({'title': folder, 'midi': f'score/{name}.mid', 'mix': {'automation': {}}},
          open(os.path.join(d, 'config', 'piece.json'), 'w'), indent=1)
open(os.path.join(d, 'notes', 'USER_FEEDBACK.md'), 'w').write(
    f'# {folder}: listening feedback\n\nThe listener can hear; we cannot. Record every comment here, newest last, with the '
    'draft it refers to. Nothing they liked may get worse in a later draft.\n')
print(folder)
