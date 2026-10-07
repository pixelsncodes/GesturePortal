import argparse
import json
import statistics
import threading
import time
from pathlib import Path

import cv2
import numpy as np

from portal.client import ComfyClient
from portal.geometry import crop_portal, composite_portal
from portal.compositor import prepare_full_frame, restore_full_frame, composite_full_frame

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description='Measure full-feed local ComfyUI latency, including transport and VAE')
    parser.add_argument('--video', type=Path, default=ROOT / 'ref' / 'camera-anime-ref.mp4')
    parser.add_argument('--samples', type=int, default=12)
    parser.add_argument('--config', type=Path, default=ROOT / 'config.json')
    parser.add_argument('--output', type=str, default='benchmark')
    parser.add_argument('--legacy-crop', action='store_true', help='Compare the previous crop-based approach')
    parser.add_argument('--source-rect', type=int, nargs=4, metavar=('X', 'Y', 'W', 'H'))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    client = ComfyClient(config)
    client.check()
    cap = cv2.VideoCapture(str(args.video))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError('Could not read benchmark input.')
    if args.source_rect:
        x, y, rw, rh = args.source_rect
        if x < 0 or y < 0 or rw <= 0 or rh <= 0 or x + rw > frame.shape[1] or y + rh > frame.shape[0]:
            raise ValueError('Source rectangle is outside the video frame.')
        frame = frame[y:y + rh, x:x + rw]
    h, w = frame.shape[:2]
    quad = np.array([[w*.30, h*.25], [w*.70, h*.25], [w*.70, h*.65], [w*.30, h*.65]], np.float32)
    if args.legacy_crop:
        canvas = crop_portal(frame, quad, config['inference_width'], config['inference_height'])
        layout = None
    else:
        canvas, layout = prepare_full_frame(frame, config['inference_width'], config['inference_height'])
    durations = []
    stopping = threading.Event()
    directory = ROOT / 'artifacts'
    directory.mkdir(exist_ok=True)
    for index in range(args.samples):
        started = time.monotonic()
        styled = client.generate(canvas, stopping)
        elapsed = time.monotonic() - started
        durations.append(elapsed)
        print(f'{index+1}/{args.samples}: {elapsed:.3f}s ({1/elapsed:.2f} fps)', flush=True)
        if index == 0:
            cv2.imwrite(str(directory / f'{args.output}-input.png'), canvas)
            cv2.imwrite(str(directory / f'{args.output}-styled.png'), styled)
            if layout is None:
                display = composite_portal(frame, styled, quad, config['feather_pixels'])
            else:
                full = restore_full_frame(styled, layout)
                cv2.imwrite(str(directory / f'{args.output}-full.png'), full)
                display = composite_full_frame(frame, full, quad, config['feather_pixels'])
            cv2.imwrite(str(directory / f'{args.output}-composite.png'), display)
    warm = durations[1:] if len(durations) > 1 else durations
    result = {'engine': config.get('engine', 'portrait'),
              'model': config.get('portrait_model', config.get('diffusion_model')),
              'resolution': [config['inference_width'], config['inference_height']],
              'steps': config.get('steps'), 'cfg': config.get('cfg'), 'denoise': config.get('denoise'),
              'vae': config.get('vae', 'none'),
              'style_strength': config.get('style_strength'),
              'guidance_mode': config.get('guidance_mode'), 'subject': config.get('subject', 'neutral'),
              'controlnet': config.get('depth_controlnet') if config.get('guidance_mode') == 'depth' else config.get('controlnet', ''),
              'controlnet_strength': config.get('controlnet_strength', 0),
              'first_seconds': durations[0], 'warm_median_seconds': statistics.median(warm),
              'warm_throughput_fps': len(warm)/sum(warm), 'all_seconds': durations,
              'scope': 'Sequential local HTTP full-frame-to-anime round trips; excludes webcam capture and hand tracking.'
                       if layout is not None else 'Previous crop-based comparison.'}
    (directory / f'{args.output}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
