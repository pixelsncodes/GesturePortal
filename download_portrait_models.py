"""Explicit setup-only downloads from the portrait model author's repository."""
import hashlib
import json
from pathlib import Path

import requests

from download_models import download

ROOT = Path(__file__).resolve().parent
REPO = 'bryandlee/animegan2-pytorch'


def main():
    session = requests.Session()
    session.trust_env = False
    response = session.get(f'https://api.github.com/repos/{REPO}/commits/main', timeout=30)
    response.raise_for_status()
    revision = response.json()['sha']
    manifest_path = ROOT / 'models' / 'sources.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    entries = [
        ('model.py', ROOT / 'custom_nodes' / 'gesture_portal' / 'animegan2' / 'model.py'),
        ('LICENSE', ROOT / 'custom_nodes' / 'gesture_portal' / 'animegan2' / 'LICENSE'),
        ('weights/face_paint_512_v2.pt', ROOT / 'models' / 'animegan' / 'face_paint_512_v2.pt'),
    ]
    for remote, local in entries:
        previous = manifest.get(local.name, {})
        pinned_revision = previous.get('revision', revision)
        url = f'https://raw.githubusercontent.com/{REPO}/{pinned_revision}/{remote}'
        download(session, url, local, previous.get('sha256'))
        with local.open('rb') as stream:
            checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        manifest[local.name] = {'repo': REPO, 'revision': pinned_revision, 'sha256': checksum,
                                'url': url, 'license': 'MIT (author repository)'}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
