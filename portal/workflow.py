"""Full-scene, image-conditioned editing. The gesture never enters this graph."""

def edit_prompt(config):
    from .styles import upgrade_style
    prompt = upgrade_style(config)['edit_prompt']
    subject = config.get('subject', 'neutral')
    if subject == 'male':
        prompt += ' Use a masculine character presentation while preserving the current subject\'s age and camera appearance.'
    elif subject == 'female':
        prompt += ' Use a feminine character presentation while preserving the current subject\'s age and camera appearance.'
    elif subject != 'neutral':
        raise ValueError(f'Unknown subject preference: {subject}')
    return prompt


def make_workflow(config, frame_id):
    engine = config.get('engine', 'portrait')
    if engine == 'portrait':
        return {
            '4': {'class_type': 'GesturePortalInput', 'inputs': {'frame_id': frame_id}},
            '14': {'class_type': 'GesturePortraitModelLoader', 'inputs': {'model_name': config['portrait_model']}},
            '15': {'class_type': 'GesturePortraitStylize', 'inputs': {
                'images': ['4', 0], 'model': ['14', 0], 'strength': config.get('style_strength', 1.0),
                'face_detail': config.get('face_detail', True), 'face_likeness': config.get('face_likeness', 0.0),
                'color_preservation': config.get('color_preservation', 0.0), 'shadow_lift': config.get('shadow_lift', 0.0)}},
            '8': {'class_type': 'GesturePortalOutput', 'inputs': {'images': ['15', 0], 'frame_id': frame_id}},
        }

    if engine not in ('flux', 'qwen'):
        raise ValueError(f'Unknown conversion engine: {engine}')
    width, height = config['inference_width'], config['inference_height']
    if width % 32 or height % 32:
        raise ValueError('Image editors need canvas dimensions divisible by 32.')
    graph = {
        '4': {'class_type': 'GesturePortalInput', 'inputs': {'frame_id': frame_id}},
        '20': {'class_type': 'UNETLoader', 'inputs': {'unet_name': config['diffusion_model'], 'weight_dtype': 'default'}},
        '21': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': config['text_encoder'], 'type': 'flux2' if engine == 'flux' else 'qwen_image', 'device': 'default'}},
        '22': {'class_type': 'VAELoader', 'inputs': {'vae_name': config['vae']}},
        '28': {'class_type': 'RandomNoise', 'inputs': {'noise_seed': config.get('seed', 42)}},
        '29': {'class_type': 'KSamplerSelect', 'inputs': {'sampler_name': 'euler'}},
        '31': {'class_type': 'SamplerCustomAdvanced', 'inputs': {'noise': ['28', 0], 'guider': ['27', 0], 'sampler': ['29', 0], 'sigmas': ['30', 0], 'latent_image': ['26', 0]}},
        '32': {'class_type': 'VAEDecode', 'inputs': {'samples': ['31', 0], 'vae': ['22', 0]}},
        '33': {'class_type': 'GestureEditBlend', 'inputs': {'images': ['32', 0], 'source': ['4', 0], 'strength': config.get('style_strength', 1.0)}},
        '8': {'class_type': 'GesturePortalOutput', 'inputs': {'images': ['33', 0], 'frame_id': frame_id}},
    }
    if engine == 'flux':
        graph.update({
            '23': {'class_type': 'CLIPTextEncode', 'inputs': {'clip': ['21', 0], 'text': edit_prompt(config)}},
            '24': {'class_type': 'VAEEncode', 'inputs': {'pixels': ['4', 0], 'vae': ['22', 0]}},
            '25': {'class_type': 'ReferenceLatent', 'inputs': {'conditioning': ['23', 0], 'latent': ['24', 0]}},
            '26': {'class_type': 'EmptyFlux2LatentImage', 'inputs': {'width': width, 'height': height, 'batch_size': 1}},
            '27': {'class_type': 'BasicGuider', 'inputs': {'model': ['20', 0], 'conditioning': ['25', 0]}},
            '30': {'class_type': 'Flux2Scheduler', 'inputs': {'steps': 4, 'width': width, 'height': height}},
        })
    else:
        graph.update({
            '23': {'class_type': 'TextEncodeQwenImage21', 'inputs': {'clip': ['21', 0], 'prompt': edit_prompt(config), 'negative_prompt': '', 'vae': ['22', 0], 'resolution': 0, 'images.image_1': ['4', 0]}},
            '26': {'class_type': 'QwenImage21Cache', 'inputs': {'model': ['20', 0], 'device': 'auto', 'dtype': 'int8'}},
            '27': {'class_type': 'BasicGuider', 'inputs': {'model': ['26', 0], 'conditioning': ['23', 0]}},
            '30': {'class_type': 'GestureQwenTurboSigmas', 'inputs': {'latent': ['23', 2]}},
        })
        graph['31']['inputs']['latent_image'] = ['23', 2]
    return graph
