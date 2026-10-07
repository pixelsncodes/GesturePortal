"""Save only when the user explicitly presses C in the viewer."""
import json
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


def save_pair(result, config, folder):
    styled, source, quad, epoch, captured = result
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    for suffix, image in [('source', source), ('styled', styled), ('comparison', np.hstack([source, styled]))]:
        if not cv2.imwrite(str(folder / f'{name}-{suffix}.png'), image):
            raise OSError('Could not save the comparison snapshot.')
    metadata = {'preset': config.get('name', config.get('engine', 'diffusion')), 'config': config,
                'captured_monotonic': captured, 'gesture_epoch': epoch,
                'gesture_quad': None if quad is None else quad.tolist()}
    (folder / f'{name}.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return folder / f'{name}-comparison.png'
