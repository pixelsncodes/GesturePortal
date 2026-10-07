"""Keep full-scene coordinates intact; the hand window only controls visibility."""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class FrameLayout:
    source_width: int
    source_height: int
    left: int
    top: int
    width: int
    height: int
    canvas_width: int
    canvas_height: int


def prepare_full_frame(frame, width, height):
    source_h, source_w = frame.shape[:2]
    scale = min(width / source_w, height / source_h)
    fitted_w = min(width, max(1, round(source_w * scale)))
    fitted_h = min(height, max(1, round(source_h * scale)))
    left, top = (width - fitted_w) // 2, (height - fitted_h) // 2
    canvas = np.zeros((height, width, 3), np.uint8)
    canvas[top:top + fitted_h, left:left + fitted_w] = cv2.resize(frame, (fitted_w, fitted_h), interpolation=cv2.INTER_AREA)
    layout = FrameLayout(source_w, source_h, left, top, fitted_w, fitted_h, width, height)
    return canvas, layout


def restore_full_frame(styled, layout):
    if styled.shape[:2] != (layout.canvas_height, layout.canvas_width):
        raise ValueError('Styled frame dimensions do not match the submitted full-frame canvas.')
    content = styled[layout.top:layout.top + layout.height, layout.left:layout.left + layout.width]
    return cv2.resize(content, (layout.source_width, layout.source_height), interpolation=cv2.INTER_LINEAR)


def composite_full_frame(real, anime, quad, feather=4):
    if real.shape != anime.shape:
        raise ValueError('Real and anime feeds must have matching dimensions.')
    mask = np.zeros(real.shape[:2], np.uint8)
    cv2.fillConvexPoly(mask, np.rint(quad).astype(np.int32), 255)
    alpha = np.minimum(cv2.distanceTransform(mask, cv2.DIST_L2, 3) / feather, 1) if feather > 0 else mask / 255.0
    alpha = alpha[:, :, None]
    return np.rint(real * (1 - alpha) + anime * alpha).clip(0, 255).astype(np.uint8)
