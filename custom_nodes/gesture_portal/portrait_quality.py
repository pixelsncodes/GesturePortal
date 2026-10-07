"""Source-image retention for portrait translation; no recognition or identity claims."""
import cv2
import numpy as np


def retain_colors(original, styled, strength):
    if strength == 0:
        return styled
    source_lab = cv2.cvtColor(np.ascontiguousarray(original, dtype=np.float32), cv2.COLOR_RGB2LAB)
    result_lab = cv2.cvtColor(np.ascontiguousarray(styled, dtype=np.float32), cv2.COLOR_RGB2LAB)
    source_light = cv2.GaussianBlur(source_lab[:, :, 0], (0, 0), 6)
    result_light = cv2.GaussianBlur(result_lab[:, :, 0], (0, 0), 6)
    # Retain broad camera shading while keeping the model's finer paint/line detail.
    result_lab[:, :, 0] = (result_lab[:, :, 0] + strength * (source_light - result_light)).clip(0, 100)
    result_lab[:, :, 1:] = result_lab[:, :, 1:] * (1 - strength) + source_lab[:, :, 1:] * strength
    return cv2.cvtColor(result_lab, cv2.COLOR_LAB2RGB).clip(0, 1)


def retain_faces(original, styled, patches, mask, strength):
    if strength == 0 or not patches:
        return styled
    height, width = original.shape[:2]
    alpha = np.zeros((height, width), np.float32)
    for _, inverse in patches:
        alpha = np.maximum(alpha, cv2.warpAffine(mask, inverse, (width, height), borderValue=0))
    alpha = alpha.clip(0, 1)[:, :, None] * strength
    return styled * (1 - alpha) + original * alpha
