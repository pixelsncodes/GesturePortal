"""Select and reveal cached full-scene inference without gesture-gating generation."""
from .compositor import composite_full_frame


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
