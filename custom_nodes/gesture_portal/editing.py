"""Image editor output alignment and Qwen Turbo's published six-step schedule."""
import math
import torch


class GestureEditBlend:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'images': ('IMAGE',), 'source': ('IMAGE',),
                             'strength': ('FLOAT', {'default': 1.0, 'min': 0, 'max': 1, 'step': .05})}}
    RETURN_TYPES = ('IMAGE',)
    FUNCTION = 'blend'
    CATEGORY = 'Gesture Portal'

    def blend(self, images, source, strength):
        if images.shape[:3] != source.shape[:3]:
            raise ValueError('Image editor changed the canvas dimensions; matching the camera would be unsafe.')
        rgb = images[..., :3].to(device=source.device, dtype=source.dtype)
        return ((source[..., :3] * (1 - strength) + rgb * strength).clamp(0, 1),)


class GestureQwenTurboSigmas:
    """Viggle v0.3 schedule, exponential resolution shift, no terminal shift.

    Formula from Viggle/Qwen-Image-2.1-viggle-turbo, revision
    009a44a895ef85f7e643c80fdca9543795248867, comfyui/viggle_turbo.py.
    Research license and NOTICE are distributed beside this module.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'latent': ('LATENT',)}}
    RETURN_TYPES = ('SIGMAS',)
    FUNCTION = 'schedule'
    CATEGORY = 'Gesture Portal'

    def schedule(self, latent):
        samples = latent['samples']
        tokens = samples.shape[-2] * samples.shape[-1]
        mu = .5 + .4 * (tokens - 256) / (8192 - 256)
        times = torch.tensor([1, .9375, .875, .75, .5, .25], dtype=torch.float64)
        shifted = math.exp(mu) / (math.exp(mu) + (1 / times - 1))
        return (torch.cat([shifted, shifted.new_zeros(1)]).float(),)
