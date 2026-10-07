"""Face detail uses the same source image; it is independent of hand gestures."""
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def make_detector():
    version = '2026may' if int(cv2.__version__.split('.')[0]) >= 5 else '2023mar'
    model_path = ROOT / 'models' / 'face_detection' / f'face_detection_yunet_{version}.onnx'
    if not model_path.exists():
        raise FileNotFoundError('Run Setup.ps1 -DctOnly to download the local face detector.')
    return cv2.FaceDetectorYN.create(str(model_path), '', (640, 640), 0.75, 0.3, 5000)


def reference_points(size):
    # Released DCT-Net alignment: square 112 reference, +1 pixel, ratio 0.75.
    points = np.array([[39.29459953, 52.69630051], [74.53179932, 52.50139999],
                       [57.02519989, 72.73660278], [42.54930115, 93.3655014],
                       [71.72990036, 93.20410156]], np.float32)
    return ((points - 56) * 0.75 + 56) * (size / 112)


def similarity_transform(source, target):
    source, target = np.asarray(source), np.asarray(target)
    if source.shape != (5, 2) or target.shape != (5, 2) or not np.isfinite(source).all():
        raise ValueError('Expected five finite face landmarks.')
    rows = []
    for x, y in source:
        rows.extend([[x, -y, 1, 0], [y, x, 0, 1]])
    parameters, _, rank, _ = np.linalg.lstsq(np.asarray(rows), target.reshape(-1), rcond=None)
    if rank != 4:
        raise ValueError('Degenerate face landmarks.')
    scale_x, scale_y, tx, ty = parameters
    return np.array([[scale_x, -scale_y, tx], [scale_y, scale_x, ty]], np.float32)


def face_patches(rgb, detector, size):
    height, width = rgb.shape[:2]
    scale = min(1.0, 640 / max(height, width))
    preview = cv2.resize((rgb.clip(0, 1) * 255).astype(np.uint8),
                         (max(1, round(width * scale)), max(1, round(height * scale))))
    detector.setInputSize((preview.shape[1], preview.shape[0]))
    _, faces = detector.detect(cv2.cvtColor(preview, cv2.COLOR_RGB2BGR))
    if faces is None:
        return []
    patches = []
    for face in sorted(faces, key=lambda row: row[2] * row[3], reverse=True)[:2]:
        if min(face[2], face[3]) / scale < 32:
            continue
        landmarks = face[4:14].reshape(5, 2) / scale
        try:
            matrix = similarity_transform(landmarks, reference_points(size))
        except ValueError:
            continue
        patch = cv2.warpAffine(rgb, matrix, (size, size), borderValue=(1, 1, 1))
        patches.append((patch, cv2.invertAffineTransform(matrix)))
    return patches


def merge_detail(styled, patch, inverse, mask):
    height, width = styled.shape[:2]
    translated = cv2.warpAffine(patch, inverse, (width, height), borderValue=(0, 0, 0))
    alpha = cv2.warpAffine(mask, inverse, (width, height), borderValue=0).clip(0, 1)[:, :, None]
    return styled * (1 - alpha) + translated * alpha


def refine_faces(rgb, styled, predict, detector, mask, device, size, patches=None):
    import torch

    for patch, inverse in face_patches(rgb, detector, size) if patches is None else patches:
        tensor = torch.from_numpy(np.ascontiguousarray(patch)).permute(2, 0, 1)[None].to(device)
        result = predict(tensor)[0].permute(1, 2, 0).cpu().numpy()
        styled = merge_detail(styled, result, inverse, mask)
    return styled
