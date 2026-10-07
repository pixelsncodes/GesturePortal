import json
import argparse
from pathlib import Path

from portal.workflow import make_workflow

ROOT = Path(__file__).resolve().parent


def export(config_path=ROOT / 'config.json', output='gesture_portal'):
    config = json.loads(config_path.read_text(encoding='utf-8'))
    graph = make_workflow(config, 'live-frame-supplied-by-portal-client')
    schemas = {
        'GesturePortalInput': ([], ['IMAGE']), 'GesturePortalOutput': (['images'], []),
        'GesturePortraitModelLoader': ([], ['GESTURE_PORTRAIT_MODEL']),
        'GesturePortraitStylize': (['images', 'model'], ['IMAGE']),
        'UNETLoader': ([], ['MODEL']), 'CLIPLoader': ([], ['CLIP']), 'VAELoader': ([], ['VAE']),
        'CLIPTextEncode': (['clip'], ['CONDITIONING']), 'VAEEncode': (['pixels', 'vae'], ['LATENT']),
        'ReferenceLatent': (['conditioning', 'latent'], ['CONDITIONING']),
        'EmptyFlux2LatentImage': ([], ['LATENT']), 'BasicGuider': (['model', 'conditioning'], ['GUIDER']),
        'RandomNoise': ([], ['NOISE']), 'KSamplerSelect': ([], ['SAMPLER']), 'Flux2Scheduler': ([], ['SIGMAS']),
        'SamplerCustomAdvanced': (['noise', 'guider', 'sampler', 'sigmas', 'latent_image'], ['LATENT', 'LATENT']),
        'VAEDecode': (['samples', 'vae'], ['IMAGE']), 'GestureEditBlend': (['images', 'source'], ['IMAGE']),
        'TextEncodeQwenImage21': (['clip', 'images.image_1', 'vae'], ['CONDITIONING', 'CONDITIONING', 'LATENT']),
        'QwenImage21Cache': (['model'], ['MODEL']), 'GestureQwenTurboSigmas': (['latent'], ['SIGMAS']),
    }
    # Connected inputs first; optional/dynamic sockets preserve their native schema positions.
    layouts = {}
    for index, (key, entry) in enumerate(graph.items()):
        sockets, outputs = schemas[entry['class_type']]
        layouts[key] = ([40 + (index % 4) * 380, 40 + (index // 4) * 300], sockets, outputs)
    nodes, links = [], []
    node_by_id = {}
    for key, entry in graph.items():
        position, sockets, outputs = layouts[key]
        widgets = [value for name, value in entry['inputs'].items() if name not in sockets]
        if entry['class_type'] == 'RandomNoise':
            widgets.append('fixed')
        node = {'id': int(key), 'type': entry['class_type'], 'pos': position, 'size': [320, 210],
                'flags': {}, 'order': len(nodes), 'mode': 0, 'inputs': [],
                'outputs': [{'name': kind, 'type': kind, 'links': []} for kind in outputs],
                'properties': {'Node name for S&R': entry['class_type']}, 'widgets_values': widgets}
        node['widgets_values_named'] = {name: value for name, value in entry['inputs'].items() if name not in sockets}
        for socket in sockets:
            source, source_slot = entry['inputs'][socket]
            socket_type = layouts[source][2][source_slot]
            node['inputs'].append({'name': socket, 'type': socket_type, 'link': None})
        nodes.append(node)
        node_by_id[key] = node
    for key, entry in graph.items():
        for target_slot, socket in enumerate(layouts[key][1]):
            source, source_slot = entry['inputs'][socket]
            link_id = len(links) + 1
            kind = layouts[source][2][source_slot]
            links.append([link_id, int(source), source_slot, int(key), target_slot, kind])
            node_by_id[source]['outputs'][source_slot]['links'].append(link_id)
            node_by_id[key]['inputs'][target_slot]['link'] = link_id
    # Native Autogrow keeps a spare image socket after the connected reference.
    for key, entry in graph.items():
        if entry['class_type'] == 'TextEncodeQwenImage21':
            node_by_id[key]['inputs'].insert(2, {'name': 'images.image_2', 'type': 'IMAGE', 'shape': 7, 'link': None})
            for link in links:
                if link[3] == int(key) and link[4] >= 2:
                    link[4] += 1
    workflow = {'last_node_id': max(int(k) for k in graph), 'last_link_id': len(links), 'nodes': nodes,
                'links': links, 'groups': [], 'config': {}, 'extra': {'ds': {'scale': 0.65, 'offset': [30, 30]}}, 'version': 0.4}
    directory = ROOT / 'workflows'
    directory.mkdir(exist_ok=True)
    for filename, content in [(f'{output}_api.json', graph), (f'{output}.json', workflow)]:
        (directory / filename).write_text(json.dumps(content, indent=2), encoding='utf-8')
        print(f'Exported {filename}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=ROOT / 'config.json')
    parser.add_argument('--output', default='gesture_portal')
    args = parser.parse_args()
    export(args.config, args.output)
