"""Memory-only transport for a local ComfyUI gesture portal client."""
import io
import re
import threading
import time
from collections import OrderedDict

import numpy as np
import torch
from aiohttp import web
from PIL import Image
from server import PromptServer
import folder_paths

from pathlib import Path

_portrait_folder = Path(__file__).resolve().parents[2] / 'models' / 'animegan'
_portrait_paths, _portrait_extensions = folder_paths.folder_names_and_paths.get('gesture_animegan', ([], set()))
folder_paths.folder_names_and_paths['gesture_animegan'] = (_portrait_paths, _portrait_extensions | {'.pt'})
folder_paths.add_model_folder_path('gesture_animegan', str(_portrait_folder))

_frames, _results = OrderedDict(), OrderedDict()
_lock = threading.Lock()
_id_pattern = re.compile(r"[a-f0-9]{32}")


def put(store, key, value):
    with _lock:
        now = time.monotonic()
        for old_key, (stamp, _) in list(store.items()):
            if now - stamp > 120:
                del store[old_key]
        store[key] = (now, value)
        while len(store) > 4:
            store.popitem(last=False)


def take(store, key):
    with _lock:
        item = store.pop(key, None)
        return None if item is None else item[1]


def local_request(request):
    if request.remote not in ("127.0.0.1", "::1"):
        raise web.HTTPForbidden(text="Gesture Portal only accepts loopback clients.")
    origin = request.headers.get("Origin")
    if origin and origin != f"{request.scheme}://{request.host}":
        raise web.HTTPForbidden(text="Cross-origin access is disabled.")
    if not _id_pattern.fullmatch(request.match_info["frame_id"]):
        raise web.HTTPBadRequest(text="Invalid frame ID.")


@PromptServer.instance.routes.get("/gesture_portal/health")
async def health(request):
    return web.json_response({'version': 5, 'transport': 'local-memory', 'portrait_quality': True,
                             'engines': ['portrait', 'flux', 'qwen']})


@PromptServer.instance.routes.post("/gesture_portal/frame/{frame_id}")
async def upload(request):
    local_request(request)
    if request.content_length and request.content_length > 4_000_000:
        raise web.HTTPRequestEntityTooLarge(max_size=4_000_000, actual_size=request.content_length)
    data = bytearray()
    async for chunk in request.content.iter_chunked(65536):
        data.extend(chunk)
        if len(data) > 4_000_000:
            raise web.HTTPRequestEntityTooLarge(max_size=4_000_000, actual_size=len(data))
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.width > 1024 or source.height > 1024:
                raise ValueError("Maximum input size is 1024 x 1024.")
            array = np.asarray(source.convert("RGB"), dtype=np.float32).copy() / 255.0
    except (OSError, ValueError) as error:
        raise web.HTTPBadRequest(text=str(error)) from error
    put(_frames, request.match_info["frame_id"], torch.from_numpy(array)[None, ...])
    return web.json_response({"ok": True})


@PromptServer.instance.routes.get("/gesture_portal/result/{frame_id}")
async def result(request):
    local_request(request)
    data = take(_results, request.match_info["frame_id"])
    if data is None:
        raise web.HTTPNotFound(text="Result not ready or expired.")
    return web.Response(body=data, content_type="image/png", headers={"Cache-Control": "no-store"})


class GesturePortalInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"frame_id": ("STRING", {"default": "uploaded-frame-id"})}}

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "load"
    CATEGORY = "Gesture Portal"

    def load(self, frame_id):
        image = take(_frames, frame_id)
        if image is None:
            raise ValueError("Start run_portal.py to supply live frames. This node needs an uploaded frame ID.")
        return (image,)


class GesturePortalOutput:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"images": ("IMAGE",), "frame_id": ("STRING", {"default": "uploaded-frame-id"})}}

    RETURN_TYPES = ()
    FUNCTION = "publish"
    OUTPUT_NODE = True
    CATEGORY = "Gesture Portal"

    def publish(self, images, frame_id):
        array = (images[0].detach().cpu().numpy().clip(0, 1) * 255).astype(np.uint8)
        stream = io.BytesIO()
        Image.fromarray(array).save(stream, format='PNG', compress_level=1)
        put(_results, frame_id, stream.getvalue())
        return {"ui": {"frame_id": [frame_id]}, "result": ()}


class GesturePortraitModelLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'model_name': (folder_paths.get_filename_list('gesture_animegan'),)}}

    RETURN_TYPES = ('GESTURE_PORTRAIT_MODEL',)
    FUNCTION = 'load'
    CATEGORY = 'Gesture Portal'

    def load(self, model_name):
        from .animegan2.model import Generator
        from comfy import model_management

        path = folder_paths.get_full_path_or_raise('gesture_animegan', model_name)
        # Never download or execute torch.hub code during inference.
        weights = torch.load(path, map_location='cpu', weights_only=True)
        model = Generator()
        model.load_state_dict(weights, strict=True)
        model.eval().requires_grad_(False)
        device = model_management.get_torch_device()
        model.to(device)
        from .face_detail import make_detector
        import cv2
        mask_path = Path(__file__).resolve().parents[2] / 'models/face_detection/portrait_alpha.jpg'
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            raise FileNotFoundError('Run Setup.ps1 -PortraitOnly for the local face-detail assets.')
        mask = cv2.resize(mask, (512, 512), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        return ({'network': model, 'device': device, 'detector': make_detector(), 'mask': mask},)


class GesturePortraitStylize:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'images': ('IMAGE',), 'model': ('GESTURE_PORTRAIT_MODEL',),
                             'strength': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 1.0, 'step': 0.05}),
                             'face_detail': ('BOOLEAN', {'default': True})},
                'optional': {'face_likeness': ('FLOAT', {'default': 0.0, 'min': 0.0, 'max': 1.0, 'step': 0.05}),
                             'color_preservation': ('FLOAT', {'default': 0.0, 'min': 0.0, 'max': 1.0, 'step': 0.05}),
                             'shadow_lift': ('FLOAT', {'default': 0.0, 'min': 0.0, 'max': 0.35, 'step': 0.05})}}

    RETURN_TYPES = ('IMAGE',)
    FUNCTION = 'stylize'
    CATEGORY = 'Gesture Portal'

    @torch.inference_mode()
    def stylize(self, images, model, strength, face_detail, face_likeness=0.0, color_preservation=0.0, shadow_lift=0.0):
        from .face_detail import refine_faces, face_patches
        from .portrait_quality import retain_colors, retain_faces

        if strength == 0:
            return (images,)
        device, network = model['device'], model['network']
        def predict(source):
            if shadow_lift:
                source = source.clamp(0, 1).pow(1 - shadow_lift)
            return (network(source * 2 - 1, align_corners=True) * 0.5 + 0.5).clamp(0, 1)
        # Direct RGB translation, with unchanged dimensions and no square face crop.
        source = images.to(device=device, dtype=torch.float32).permute(0, 3, 1, 2)
        output = predict(source).permute(0, 2, 3, 1).cpu().numpy()
        originals = images.cpu().numpy()
        for index, rgb in enumerate(originals):
            patches = face_patches(rgb, model['detector'], 512) if face_detail or face_likeness else []
            if face_detail:
                output[index] = refine_faces(rgb, output[index], predict, model['detector'], model['mask'], device, 512, patches)
            output[index] = rgb * (1 - strength) + output[index] * strength
            output[index] = retain_colors(rgb, output[index], color_preservation)
            output[index] = retain_faces(rgb, output[index], patches, model['mask'], face_likeness)
        return (torch.from_numpy(output.clip(0, 1)),)


from .editing import GestureEditBlend, GestureQwenTurboSigmas

NODE_CLASS_MAPPINGS = {
    'GesturePortalInput': GesturePortalInput, 'GesturePortalOutput': GesturePortalOutput,
    'GesturePortraitModelLoader': GesturePortraitModelLoader, 'GesturePortraitStylize': GesturePortraitStylize,
    'GestureEditBlend': GestureEditBlend, 'GestureQwenTurboSigmas': GestureQwenTurboSigmas,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'GesturePortalInput': 'Gesture Portal · Full camera frame',
    'GesturePortalOutput': 'Gesture Portal · Return full styled frame',
    'GesturePortraitModelLoader': 'Gesture Portal · Portrait v2 model',
    'GesturePortraitStylize': 'Gesture Portal · Portrait v2',
    'GestureEditBlend': 'Gesture Portal · Source blend',
    'GestureQwenTurboSigmas': 'Gesture Portal · Qwen 2.1 Turbo six-step schedule',
}
