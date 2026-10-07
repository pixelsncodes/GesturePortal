"""Explicit downloads of the Portrait face mask and MIT-licensed YuNet."""
import json
import re
from pathlib import Path

import requests
from download_models import download

ROOT = Path(__file__).resolve().parent


def main():
    session = requests.Session()
    session.trust_env = False
    manifest_path = ROOT / 'models' / 'sources.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    repo = 'iic/cv_unet_person-image-cartoon_compound-models'
    response = session.get(f'https://modelscope.cn/api/v1/models/{repo}/repo/files',
                           params={'Revision': 'master', 'Recursive': 'true'}, timeout=30)
    response.raise_for_status()
    files = response.json()['Data']['Files']
    for name in ['alpha.jpg']:
        previous = manifest.get('portrait_alpha.jpg')
        metadata = next(file for file in files if file['Path'] == name)
        revision = previous['revision'] if previous else metadata['Revision']
        checksum = previous['sha256'] if previous else metadata['Sha256']
        url = f'https://modelscope.cn/models/{repo}/resolve/{revision}/{name}'
        download(session, url, ROOT / 'models/face_detection/portrait_alpha.jpg', checksum)
        manifest['portrait_alpha.jpg'] = {'repo': repo, 'revision': revision, 'sha256': checksum,
                                     'url': url, 'license': 'Apache-2.0 (model card)'}
    for name in ['face_detection_yunet_2023mar.onnx', 'face_detection_yunet_2026may.onnx']:
        previous = manifest.get(name)
        if previous:
            url, revision, checksum = previous['url'], previous['revision'], previous['sha256']
        else:
            response = session.get('https://api.github.com/repos/opencv/opencv_zoo/commits/main', timeout=30)
            response.raise_for_status()
            revision = response.json()['sha']
            remote = f'models/face_detection_yunet/{name}'
            pointer = session.get(f'https://raw.githubusercontent.com/opencv/opencv_zoo/{revision}/{remote}', timeout=30)
            pointer.raise_for_status()
            match = re.search(r'oid sha256:([0-9a-f]{64})', pointer.text)
            if match is None:
                raise ValueError('Expected an official Git LFS pointer with its model checksum.')
            checksum = match.group(1)
            url = f'https://media.githubusercontent.com/media/opencv/opencv_zoo/{revision}/{remote}'
        download(session, url, ROOT / 'models/face_detection' / name, checksum)
        manifest[name] = {'repo': 'opencv/opencv_zoo', 'revision': revision, 'sha256': checksum,
                          'url': url, 'license': 'MIT'}
    licenses = [
        ('menyifang/DCT-Net', 'main', 'LICENSE', ROOT / 'custom_nodes/gesture_portal/dctnet_LICENSE'),
        ('opencv/opencv_zoo', revision, 'models/face_detection_yunet/LICENSE', ROOT / 'models/face_detection/LICENSE'),
    ]
    for repo, revision, name, path in licenses:
        download(session, f'https://raw.githubusercontent.com/{repo}/{revision}/{name}', path)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
