"""Select and reveal cached full-scene inference without gesture-gating generation."""
import numpy as np
from .compositor import composite_full_frame
from .motion import MotionAligner

ALIGNMENT_MODES = ('off', 'smooth', 'exact')


def alignment_mode(config):
    mode = config.get('alignment_mode', 'exact' if config.get('synchronize_feed', False) else 'off')
    if mode not in ALIGNMENT_MODES:
        raise ValueError('Alignment must be off, smooth or exact.')
    return mode


class FeedRenderer:
    def __init__(self):
        self.motion = MotionAligner()

    def render(self, frame, quad, result, captured, config, view='portal', mode='off', epoch=0):
        if mode not in ALIGNMENT_MODES:
            raise ValueError('Alignment must be off, smooth or exact.')
        if mode != 'smooth':
            self.motion.reset()
            return render_feed(frame, quad, result, captured, config, view, mode == 'exact', epoch)
        if (result is None or captured-result[-1] > config['result_max_age']
                or result[1].shape != frame.shape or (view == 'portal' and quad is None)):
            self.motion.reset()
            return frame.copy(), quad, False
        region = None
        if view == 'portal':
            left, top = np.maximum(np.floor(quad.min(axis=0))-2, 0).astype(int)
            right, bottom = np.minimum(np.ceil(quad.max(axis=0))+3, [frame.shape[1], frame.shape[0]]).astype(int)
            if right <= left or bottom <= top:
                return frame.copy(), quad, False
            region = (left, top, right, bottom)
        warped, confidence = self.motion.warp(result[1], result[0], frame, region)
        if view == 'portal':
            return composite_full_frame(frame, warped, quad, config['feather_pixels'], confidence), quad, True
        opacity = confidence[:, :, None]
        styled = np.rint(frame*(1-opacity)+warped*opacity).clip(0, 255).astype(np.uint8)
        if view == 'anime':
            return styled, None, False
        output = frame.copy()
        middle = frame.shape[1]//2
        output[:, middle:] = styled[:, middle:]
        return output, None, False


def render_feed(frame, quad, result, captured, config, view='portal', synchronize=False, epoch=0):
    if result is None or captured - result[-1] > config['result_max_age']:
        return frame.copy(), quad, False
    styled, source, source_quad, result_epoch, _ = result
    if source.shape != frame.shape:
        return frame.copy(), quad, False
    base = source if synchronize else frame
    reveal = source_quad if synchronize else quad
    if view == 'anime':
        return styled.copy(), None, False
    if view == 'split':
        output = base.copy()
        middle = frame.shape[1] // 2
        output[:, middle:] = styled[:, middle:]
        return output, None, False
    if quad is not None and reveal is not None and (not synchronize or result_epoch == epoch):
        return composite_full_frame(base, styled, reveal, config['feather_pixels']), reveal, True
    return frame.copy(), quad, False
