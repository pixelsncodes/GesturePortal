import threading
import time
import uuid
from urllib.parse import urlparse

import cv2
import numpy as np
import requests

from .workflow import make_workflow
from .compositor import prepare_full_frame, restore_full_frame


class ComfyClient:
    def __init__(self, config):
        self.config = config
        self.url = config["comfy_url"].rstrip("/")
        parsed = urlparse(self.url)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("comfy_url must be an HTTP loopback address; remote inference is disabled.")
        self.session = requests.Session()
        self.session.trust_env = False
        self.client_id = uuid.uuid4().hex
        self.prompt_id = None

    def request(self, method, path, **kwargs):
        response = self.session.request(method, self.url + path, timeout=10, **kwargs)
        if not response.ok:
            raise RuntimeError(f"ComfyUI {path}: {response.status_code} {response.text[:600]}")
        return response

    def check(self, config=None):
        health = self.request("GET", "/gesture_portal/health").json()
        selected = self.config if config is None else config
        if health.get('version', 0) < 5:
            raise ValueError('Close the old ComfyUI backend, then launch again to load the new image editors.')
        if selected.get('engine') == 'portrait' and not health.get('portrait_quality'):
            raise ValueError('Close the old ComfyUI backend, then launch again to load the portrait quality controls.')
        info = self.request("GET", "/object_info").json()
        graph = make_workflow(selected, "0" * 32)
        for node in graph.values():
            name = node["class_type"]
            if name not in info:
                raise ValueError(f"ComfyUI is missing {name}. Start it with Start-Comfy.ps1.")
            required = info[name]["input"]["required"]
            for field, value in node["inputs"].items():
                schema = required.get(field)
                if schema and isinstance(schema[0], list) and value not in schema[0]:
                    raise ValueError(f"{name}.{field}: {value!r} is unavailable in this ComfyUI installation.")

    def generate(self, frame, stopping, config=None):
        frame_id = uuid.uuid4().hex
        ok, encoded = cv2.imencode(".png", frame)
        if not ok:
            raise RuntimeError("Could not encode camera frame.")
        self.request("POST", f"/gesture_portal/frame/{frame_id}", data=encoded.tobytes(),
                     headers={"Content-Type": "image/png"})
        payload = {"prompt": make_workflow(self.config if config is None else config, frame_id), "client_id": self.client_id}
        self.prompt_id = self.request("POST", "/prompt", json=payload).json()["prompt_id"]
        deadline = time.monotonic() + 180
        # Finish and clean up an already-running job even if the viewer is closing.
        while True:
            history = self.request("GET", f"/history/{self.prompt_id}").json().get(self.prompt_id)
            if history:
                try:
                    status = history.get("status", {})
                    if status.get("status_str") == "error":
                        raise RuntimeError(f"ComfyUI execution failed: {status.get('messages', [])}")
                    data = self.request("GET", f"/gesture_portal/result/{frame_id}").content
                    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                    if image is None:
                        raise RuntimeError("ComfyUI returned an invalid image.")
                    return None if stopping.is_set() else image
                finally:
                    self.request("POST", "/history", json={"delete": [self.prompt_id]})
                    self.prompt_id = None
            if time.monotonic() > deadline:
                raise TimeoutError("ComfyUI exceeded 180 seconds. Streaming stopped to avoid building a queue.")
            time.sleep(0.025)


class InferenceWorker:
    """One running inference and one replaceable full frame; never a FIFO backlog."""
    def __init__(self, config):
        self.config = config
        self.client = ComfyClient(config)
        self.client.check()
        self.condition = threading.Condition()
        self.stopping = threading.Event()
        self.pending = None
        self.result = None
        self.error = None
        self.ai_fps = 0.0
        self.latency = 0.0
        self.completed = 0
        self.revision = 0
        self.thread = threading.Thread(target=self.run, daemon=True, name="comfy-inference")
        self.thread.start()

    def submit(self, frame, quad, epoch, captured):
        with self.condition:
            self.pending = (frame.copy(), None if quad is None else quad.copy(), epoch, captured,
                            dict(self.config), self.revision)
            self.condition.notify()

    def clear(self):
        with self.condition:
            self.pending = None
            self.result = None

    def select(self, config, validate=True):
        if config['comfy_url'].rstrip('/') != self.client.url:
            raise ValueError('Live model switching must use the same local backend.')
        # Validation uses its own session, independent of the in-flight job.
        if validate:
            validator = ComfyClient(config)
            try:
                validator.check()
            finally:
                validator.session.close()
        else:
            # Only scalar controls/prompts of an already-validated graph use this path.
            make_workflow(config, '0' * 32)
        with self.condition:
            self.config = dict(config)
            self.revision += 1
            self.pending = self.result = None
            self.ai_fps = self.latency = 0.0
            self.error = None

    def snapshot(self):
        with self.condition:
            return self.result, self.error, self.ai_fps, self.latency

    def run(self):
        previous = None
        previous_revision = None
        while not self.stopping.is_set():
            with self.condition:
                self.condition.wait_for(lambda: self.pending is not None or self.stopping.is_set())
                if self.stopping.is_set():
                    break
                item, self.pending = self.pending, None
            frame, quad, epoch, captured, config, revision = item
            started = time.monotonic()
            if started - captured > config["result_max_age"]:
                continue
            try:
                canvas, layout = prepare_full_frame(frame, config["inference_width"], config["inference_height"])
                styled = self.client.generate(canvas, self.stopping, config)
                if styled is None:
                    break
                styled = restore_full_frame(styled, layout)
                finished = time.monotonic()
                with self.condition:
                    if revision == self.revision:
                        self.result = (styled, frame, quad, epoch, captured)
                        self.latency = finished - captured
                        self.ai_fps = 0 if previous is None or previous_revision != revision else 1 / (finished - previous)
                        previous, previous_revision = finished, revision
                    self.completed += 1
                    self.condition.notify_all()
            except Exception as error:
                with self.condition:
                    if revision == self.revision:
                        self.error = str(error)
                        break
            self.stopping.wait(max(0, 1 / config["max_ai_fps"] - (time.monotonic() - started)))

    def close(self):
        self.stopping.set()
        with self.condition:
            self.condition.notify_all()
        self.thread.join(timeout=1)
