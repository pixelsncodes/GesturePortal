"""CPU motion assistance for cached image output; no extra AI model."""
import cv2
import numpy as np


class MotionAligner:
    def __init__(self, width=256):
        self.width = width
        self.reference = None
        self.gray = None
        self.shape = None

    def reset(self):
        self.reference = self.gray = None

    def warp(self, source, styled, current, region=None):
        height, width = current.shape[:2]
        small_width = min(self.width, width)
        small_height = max(1, round(height*small_width/width))
        small_size = (small_width, small_height)
        if self.shape != current.shape:
            self.shape = current.shape
            self.y, self.x = np.indices((height, width), dtype=np.float32)
            self.sy, self.sx = np.indices((small_height, small_width), dtype=np.float32)
            self.reset()
        if self.reference is not source:
            self.reference = source
            self.gray = cv2.cvtColor(cv2.resize(source, small_size, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        now = cv2.cvtColor(cv2.resize(current, small_size, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        # Backward flow: each current-camera pixel samples the corresponding reference pixel.
        flow = cv2.calcOpticalFlowFarneback(now, self.gray, None, .5, 4, 25, 3, 5, 1.2, 0)
        mx, my = self.sx+flow[:, :, 0], self.sy+flow[:, :, 1]
        reference = cv2.remap(self.gray, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        error = cv2.GaussianBlur(cv2.absdiff(reference, now).astype(np.float32), (5, 5), 0)
        confidence = np.clip((44-error)/28, 0, 1)
        confidence *= ((mx >= 0) & (my >= 0) & (mx <= small_width-1) & (my <= small_height-1))
        # Reject extreme displacement rather than stretching an old face into new content.
        confidence *= np.linalg.norm(flow, axis=2) <= min(small_size)*.25
        full = cv2.resize(flow, (width, height), interpolation=cv2.INTER_LINEAR)
        left, top, right, bottom = region if region is not None else (0, 0, width, height)
        roi = np.s_[top:bottom, left:right]
        map_x = self.x[roi]+full[roi][:, :, 0]*(width/small_width)
        map_y = self.y[roi]+full[roi][:, :, 1]*(height/small_height)
        pixels = cv2.remap(styled, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        if region is None:
            warped = pixels
        else:
            warped = current.copy()
            warped[roi] = pixels
        confidence = cv2.resize(confidence, (width, height), interpolation=cv2.INTER_LINEAR)
        confidence[roi] *= ((map_x >= 0) & (map_y >= 0) & (map_x <= width-1) & (map_y <= height-1))
        return warped, confidence
