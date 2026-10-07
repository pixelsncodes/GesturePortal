"""Setup-only, checksum-verified downloads for native ComfyUI image editors."""
import argparse
import json
from pathlib import Path
import requests
from download_models import download

ROOT = Path(__file__).resolve().parent
MODELS = {
    'flux': [
        ('Comfy-Org/flux2-klein-4B', 'split_files/diffusion_models/flux-2-klein-4b.safetensors'),
        ('Comfy-Org/flux2-klein-4B', 'split_files/text_encoders/qwen_3_4b_fp4_flux2.safetensors'),
        ('Comfy-Org/flux2-klein-4B', 'split_files/vae/flux2-vae.safetensors'),
    ],
    'qwen': [
        ('Viggle/Qwen-Image-2.1-viggle-turbo', 'Qwen-Image-2.1-viggle-turbo-v0.3-6step-int8_convrot.safetensors'),
        ('Comfy-Org/Qwen-Image-2.1', 'text_encoders/qwen3vl_8b_int8_convrot.safetensors'),
        ('Comfy-Org/Qwen-Image-2.1', 'vae/qwen_image_2.1_vae_bf16.safetensors'),
    ],
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model', choices=MODELS)
    parser.add_argument('--research-use', action='store_true', help='Accept Qwen research/evaluation-only licensing')
    args = parser.parse_args()
    if args.model == 'qwen' and not args.research_use:
        parser.error('Qwen 2.1 requires --research-use; read its research license first.')
    session = requests.Session()
    session.trust_env = False
    manifest_path = ROOT / 'models/sources.json'
    for repo, remote in MODELS[args.model]:
        response = session.get(f'https://huggingface.co/api/models/{repo}?blobs=true', timeout=30)
        response.raise_for_status()
        metadata = response.json()
        license_name = metadata.get('cardData', {}).get('license')
        if license_name == 'other':
            license_name = metadata.get('cardData', {}).get('license_name')
        if license_name not in ('apache-2.0', 'qwen-research') or (license_name == 'qwen-research' and not args.research_use):
            raise RuntimeError(f'License changed for {repo}; inspect it before downloading.')
        entry = next(e for e in metadata['siblings'] if e['rfilename'] == remote)
        checksum = entry['lfs']['sha256']
        filename = Path(remote).name
        folder = ('diffusion_models' if args.model == 'qwen' and remote.startswith('Qwen-Image-')
                  else Path(remote).parent.name)
        url = f"https://huggingface.co/{repo}/resolve/{metadata['sha']}/{remote}"
        download(session, url, ROOT / 'models' / folder / filename, checksum)
        # Read again after each completed file so separate setup runs preserve one another's entries.
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest[filename] = dict(repo=repo, revision=metadata['sha'], sha256=checksum,
                                  url=url, license=license_name)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
