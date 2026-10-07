import time

import cv2
import numpy as np


def is_frame_hand(points):
    """An extended index and thumb, with at least two other fingers curled."""
    wrist = points[0]
    palm = max(np.linalg.norm(points[5] - points[17]), 1e-5)
    index = np.linalg.norm(points[8] - wrist) > np.linalg.norm(points[6] - wrist) * 1.02
    thumb = np.linalg.norm(points[4] - points[5]) > palm * 0.60
    a, b = points[8] - points[5], points[4] - points[2]
    cosine = np.dot(a, b) / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-5)
    spread = cosine < np.cos(np.deg2rad(25))
    curled = sum(np.linalg.norm(points[tip] - wrist) < np.linalg.norm(points[pip] - wrist) * 1.18
                 for tip, pip in [(12, 10), (16, 14), (20, 18)])
    return bool(index and thumb and spread and curled >= 2)


def hand_quad(hands, width, height):
    valid = [np.array([(p.x * width, p.y * height) for p in hand], np.float32)
             for hand in hands]
    valid = [p for p in valid if is_frame_hand(p)]
    if len(valid) != 2:
        return None
    left, right = sorted(valid, key=lambda p: p[0, 0])
    # Finger identities keep correspondence stable while the window tilts.
    quad = np.array([left[8], right[8], right[4], left[4]], np.float32)
    if quad[:2, 1].mean() > quad[2:, 1].mean():
        quad = quad[[3, 2, 1, 0]]
    quad[:, 0] = np.clip(quad[:, 0], 0, width - 1)
    quad[:, 1] = np.clip(quad[:, 1], 0, height - 1)
    if not cv2.isContourConvex(quad) or abs(cv2.contourArea(quad)) < width * height * 0.0008:
        return None
    if min(np.linalg.norm(quad - np.roll(quad, 1, axis=0), axis=1)) < 8:
        return None
    return quad


class FrameTracker:
    def __init__(self, smoothing=0.55, hold=0.12, grace=0.15):
        self.smoothing, self.hold, self.grace = smoothing, hold, grace
        self.quad = None
        self.candidate_since = None
        self.last_seen = -float('inf')
        self.epoch = 0

    def update(self, candidate, now=None):
        now = time.monotonic() if now is None else now
        if candidate is None:
            self.candidate_since = None
            if now - self.last_seen > self.grace and self.quad is not None:
                self.quad = None
                self.epoch += 1
            return self.quad
        self.last_seen = now
        if self.quad is None:
            if self.candidate_since is None:
                self.candidate_since = now
            if now - self.candidate_since >= self.hold:
                self.quad = candidate.copy()
                self.epoch += 1
        else:
            smoothed = self.quad * (1 - self.smoothing) + candidate * self.smoothing
            self.quad = smoothed if cv2.isContourConvex(smoothed) else candidate.copy()
        return self.quad


def canvas_corners(width, height):
    return np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], np.float32)


def crop_portal(frame, quad, width, height):
    transform = cv2.getPerspectiveTransform(quad.astype(np.float32), canvas_corners(width, height))
    return cv2.warpPerspective(frame, transform, (width, height))


def composite_portal(frame, styled, quad, feather=4):
    height, width = frame.shape[:2]
    sh, sw = styled.shape[:2]
    transform = cv2.getPerspectiveTransform(canvas_corners(sw, sh), quad.astype(np.float32))
    warped = cv2.warpPerspective(styled, transform, (width, height))
    mask = np.zeros((height, width), np.uint8)
    cv2.fillConvexPoly(mask, np.rint(quad).astype(np.int32), 255)
    # Feather inward, keeping every pixel outside the selected polygon untouched.
    if feather > 0:
        alpha = np.minimum(cv2.distanceTransform(mask, cv2.DIST_L2, 3) / feather, 1)
    else:
        alpha = mask.astype(np.float32) / 255
    alpha = alpha[:, :, None]
    return np.rint(frame * (1 - alpha) + warped * alpha).clip(0, 255).astype(np.uint8)
