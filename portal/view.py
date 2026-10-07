"""Select and reveal cached full-scene inference without gesture-gating generation."""
from .compositor import composite_full_frame

ALIGNMENT_MODES = ('off', 'exact')


def alignment_mode(config):
    mode = config.get('alignment_mode', 'exact' if config.get('synchronize_feed', False) else 'off')
    if mode == 'smooth':
        mode = 'exact'  # Retired approximation: preserve the user's alignment intent.
    if mode not in ALIGNMENT_MODES:
        raise ValueError('Alignment must be off or exact.')
    return mode


class FeedRenderer:
    """Reuse immutable matched captures; callers may safely draw on returned copies."""
    def __init__(self):
        self.cached_result = None
        self.cached_key = None
        self.cached_output = None

    def render(self, frame, quad, result, captured, config, view='portal', mode='off', epoch=0):
        if mode not in ALIGNMENT_MODES:
            raise ValueError('Alignment must be off or exact.')
        eligible = (mode == 'exact' and result is not None
                    and captured-result[-1] <= config['result_max_age']
                    and result[1].shape == frame.shape
                    and (view in ('anime', 'split') or
                         (quad is not None and result[2] is not None and result[3] == epoch)))
        if not eligible:
            self.cached_result = self.cached_key = self.cached_output = None
            return render_feed(frame, quad, result, captured, config, view, mode == 'exact', epoch)
        key = (view, config['feather_pixels'], epoch, frame.shape)
        if result is not self.cached_result or key != self.cached_key:
            self.cached_output = render_feed(frame, quad, result, captured, config, view, True, epoch)
            self.cached_result, self.cached_key = result, key
        output, reveal, active = self.cached_output
        return output.copy(), reveal, active


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
