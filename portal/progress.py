"""Measured graph-completion progress from ComfyUI execution events."""


def component_label(class_type, config):
    engine = config.get('engine', 'flux')
    model = {'flux': 'FLUX', 'qwen': 'Qwen', 'portrait': 'Portrait'}[engine]
    labels = {
        'GesturePortalInput': ('Reading camera reference', 'Full scene from local memory'),
        'UNETLoader': (f'Loading {model} image transformer', config.get('diffusion_model', 'Image model weights')),
        'CLIPLoader': ('Loading text encoder', config.get('text_encoder', 'Local text encoder weights')),
        'VAELoader': ('Loading image encoder / decoder', config.get('vae', 'Local VAE weights')),
        'CLIPTextEncode': ('Encoding the selected style', 'Turning the editing instruction into model conditioning'),
        'TextEncodeQwenImage21': ('Encoding style and camera reference', 'Qwen vision-language conditioning'),
        'VAEEncode': ('Encoding camera into image latents', 'Keeping the complete scene as the visual reference'),
        'ReferenceLatent': ('Attaching the camera reference', 'Connecting reference latents to the style instruction'),
        'EmptyFlux2LatentImage': ('Preparing the output canvas', 'Matching the requested image dimensions'),
        'BasicGuider': ('Preparing reference guidance', 'Combining the model and image conditioning'),
        'RandomNoise': ('Preparing the fixed seed', 'Keeping the same seed across camera frames'),
        'KSamplerSelect': ('Preparing the sampler', 'Local Euler image sampling'),
        'Flux2Scheduler': ('Preparing the 4-step schedule', 'FLUX distilled sampling schedule'),
        'GestureQwenTurboSigmas': ('Preparing the 6-step schedule', 'Qwen Turbo sampling schedule'),
        'QwenImage21Cache': ('Preparing Qwen reference cache', 'Local quantized reference editing'),
        'SamplerCustomAdvanced': ('Preparing GPU inference', f'{model} weights and sampling on the local GPU'),
        'VAEDecode': ('Decoding the styled image', 'Converting image latents back into pixels'),
        'GestureEditBlend': ('Applying style strength', 'Blending the styled scene with the camera image'),
        'GesturePortalOutput': ('Publishing the styled frame', 'Returning pixels through local memory'),
        'GesturePortraitModelLoader': ('Loading Portrait and face assets', 'Image translator, face detector and refinement mask'),
        'GesturePortraitStylize': ('Painting scene and refining face', 'Full-scene translation and camera-likeness retention'),
    }
    return labels.get(class_type, ('Preparing workflow component', class_type))


class WorkflowProgress:
    """Weighted completed nodes plus actual sampler steps; never elapsed-time interpolation."""
    def __init__(self, graph, config, prompt_id):
        self.graph, self.config, self.prompt_id = graph, config, prompt_id
        self.fractions = {key: 0.0 for key in graph}
        self.weights = {key: (6 if node['class_type'] == 'SamplerCustomAdvanced' else 1) for key, node in graph.items()}
        self.current = None

    def consume(self, message):
        kind, data = message.get('type'), message.get('data', {})
        if not isinstance(data, dict) or data.get('prompt_id') != self.prompt_id:
            return None
        if kind == 'execution_cached':
            for key in data.get('nodes', []):
                if str(key) in self.fractions:
                    self.fractions[str(key)] = 1
        elif kind == 'executing':
            key = data.get('node')
            if self.current is not None:
                self.fractions[self.current] = 1
            self.current = str(key) if str(key) in self.graph else None
        elif kind == 'progress_state':
            for key, state in data.get('nodes', {}).items():
                key = str(key)
                if key not in self.graph:
                    continue
                fraction = 1 if state.get('state') == 'finished' else self.fraction(state)
                self.fractions[key] = max(self.fractions[key], fraction)
                if state.get('state') == 'running':
                    self.current = key
        elif kind == 'progress':
            key = str(data.get('node', self.current))
            if key in self.graph:
                self.current = key
                self.fractions[key] = max(self.fractions[key], self.fraction(data))
        else:
            return None
        fraction = sum(self.weights[key]*value for key, value in self.fractions.items()) / sum(self.weights.values())
        if kind == 'execution_cached':
            stage = 'Reusing resident model components'
            detail = f"{len(data.get('nodes', []))} workflow components already cached by the local backend"
        elif self.current is None:
            stage, detail = 'Completing the image workflow', 'Waiting for the styled frame'
        else:
            stage, detail = component_label(self.graph[self.current]['class_type'], self.config)
            if self.graph[self.current]['class_type'] == 'SamplerCustomAdvanced' and kind == 'progress':
                stage = 'Generating the styled frame'
                detail = f"Sampling step {data.get('value', 0)} of {data.get('max', 0)} · local GPU"
            elif self.graph[self.current]['class_type'] == 'SamplerCustomAdvanced' and kind == 'progress_state':
                state = data.get('nodes', {}).get(self.current, {})
                if state.get('value', 0) > 0 and state.get('state') == 'running':
                    stage = 'Generating the styled frame'
                    detail = f"Sampling step {state['value']} of {state.get('max', 0)} · local GPU"
        return {'fraction': fraction, 'stage': stage, 'detail': detail}

    @staticmethod
    def fraction(state):
        maximum = float(state.get('max', 0))
        return max(0, min(1, float(state.get('value', 0)) / maximum)) if maximum > 0 else 0
