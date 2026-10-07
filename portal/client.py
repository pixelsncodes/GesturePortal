import threading
import json
import time
import uuid
from urllib.parse import urlparse

import cv2
import numpy as np
import requests
import websocket

from .workflow import make_workflow
from .compositor import prepare_full_frame, restore_full_frame
from .progress import WorkflowProgress


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
        self.progress_callback = None

    def report(self, **event):
        if self.progress_callback:
            self.progress_callback(event)

    def request(self, method, path, **kwargs):
        response = self.session.request(method, self.url + path, timeout=10, **kwargs)
        if not response.ok:
            raise RuntimeError(f"ComfyUI {path}: {response.status_code} {response.text[:600]}")
        return response

    def check(self, config=None):
        self.report(percent=0, stage='Connecting local AI backend', detail='Checking the local model server')
        health = self.request("GET", "/gesture_portal/health").json()
        selected = self.config if config is None else config
        if health.get('version', 0) < 5:
            raise ValueError('Close the old ComfyUI backend, then launch again to load the new image editors.')
        if selected.get('engine') == 'portrait' and not health.get('portrait_quality'):
            raise ValueError('Close the old ComfyUI backend, then launch again to load the portrait quality controls.')
        self.report(percent=2, stage='Checking model files and workflow', detail='Validating the model, text encoder, decoder and workflow nodes')
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
        self.report(percent=5, stage='Workflow validated', detail='Preparing the full camera reference')

    def generate(self, frame, stopping, config=None):
        selected = self.config if config is None else config
        self.report(fraction=0, stage='Uploading full camera reference', detail='Encoding the local camera frame as PNG')
        frame_id = uuid.uuid4().hex
        ok, encoded = cv2.imencode(".png", frame)
        if not ok:
            raise RuntimeError("Could not encode camera frame.")
        self.request("POST", f"/gesture_portal/frame/{frame_id}", data=encoded.tobytes(),
                     headers={"Content-Type": "image/png"})
        graph = make_workflow(selected, frame_id)
        payload = {"prompt": graph, "client_id": self.client_id}
        channel = None
        try:
            channel = websocket.create_connection(self.url.replace('http://', 'ws://', 1) + '/ws?clientId=' + self.client_id,
                                                   timeout=2, suppress_origin=True,
                                                   http_no_proxy=['127.0.0.1', 'localhost', '::1'])
            channel.settimeout(.01)
        except (OSError, websocket.WebSocketException):
            if channel:
                channel.close()
            channel = None
            self.report(fraction=0, stage='Running the image workflow', detail='Detailed progress unavailable; waiting for backend completion')
        try:
            self.prompt_id = self.request("POST", "/prompt", json=payload).json()["prompt_id"]
            return self.wait_result(frame_id, graph, selected, channel, stopping)
        finally:
            if channel:
                channel.close()

    def wait_result(self, frame_id, graph, selected, channel, stopping):
        progress = WorkflowProgress(graph, selected, self.prompt_id)
        deadline = time.monotonic() + 180
        last_poll = 0
        # Finish and clean up an already-running job even if the viewer is closing.
        while True:
            if channel:
                for _ in range(50):
                    try:
                        message = channel.recv()
                        if not message:
                            channel.close()
                            channel = None
                            break
                        if isinstance(message, str):
                            event = progress.consume(json.loads(message))
                            if event:
                                self.report(**event)
                    except websocket.WebSocketTimeoutException:
                        break
                    except (OSError, websocket.WebSocketException, ValueError):
                        channel.close()
                        channel = None
                        break
            if time.monotonic() - last_poll < .1:
                time.sleep(.01)
                continue
            last_poll = time.monotonic()
            history = self.request("GET", f"/history/{self.prompt_id}").json().get(self.prompt_id)
            if history:
                try:
                    status = history.get("status", {})
                    if status.get("status_str") == "error":
                        raise RuntimeError(f"ComfyUI execution failed: {status.get('messages', [])}")
                    self.report(fraction=1, stage='Receiving styled pixels', detail='Restoring the camera aspect ratio and reveal canvas')
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
        self.condition = threading.Condition()
        self.stopping = threading.Event()
        self.pending = None
        self.result = None
        self.error = None
        self.ai_fps = 0.0
        self.latency = 0.0
        self.completed = 0
        self.revision = 0
        self.checked_revision = None
        self.failed_revision = None
        self.executed_revision = None
        self.phase = 'checking'
        self.ready = False
        self.phase_started = time.monotonic()
        self.percent = 0
        self.stage = 'Opening camera and hand tracking'
        self.detail = 'Preparing the local camera input and MediaPipe tracker'
        self.thread = threading.Thread(target=self.run, daemon=True, name="comfy-inference")
        self.thread.start()

    def submit(self, frame, quad, epoch, captured):
        with self.condition:
            if self.failed_revision == self.revision:
                return
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
        # HTTP validation belongs to the inference thread, never the camera/UI loop.
        make_workflow(config, '0' * 32)
        with self.condition:
            checked = self.checked_revision == self.revision and not validate
            self.config = dict(config)
            self.revision += 1
            self.checked_revision = self.revision if checked else None
            self.pending = self.result = None
            self.ai_fps = self.latency = 0.0
            self.error = None
            self.failed_revision = None
            self.ready = False
            self.phase = 'loading' if checked else 'checking'
            self.phase_started = time.monotonic()
            self.percent = 0
            self.stage = 'Preparing selected style and workflow' if checked else 'Checking selected model and workflow'
            self.detail = 'The previous result has been cleared; camera and controls remain live'
            self.condition.notify_all()

    def snapshot(self):
        with self.condition:
            return self.result, self.error, self.ai_fps, self.latency

    def readiness(self):
        with self.condition:
            return {'phase': self.phase, 'ready': self.ready, 'error': self.error,
                    'revision': self.revision, 'elapsed': time.monotonic() - self.phase_started,
                    'percent': self.percent, 'stage': self.stage, 'detail': self.detail}

    def update_progress(self, revision, event):
        with self.condition:
            if revision != self.revision or self.ready or self.error:
                return
            value = event.get('percent')
            if value is None:
                fraction = event.get('fraction', 0)
                value = 90 + 9 * fraction if self.phase == 'refreshing' else 5 + 85 * fraction
            self.percent = max(self.percent, min(99, int(value)))
            self.stage = event.get('stage', self.stage)
            self.detail = event.get('detail', self.detail)

    def retry(self):
        self.select(dict(self.config))

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
                if self.checked_revision != revision:
                    validator = ComfyClient(config)
                    validator.progress_callback = lambda event: self.update_progress(revision, event)
                    try:
                        # The launcher opens the UI while its local backend boots.
                        # Transient loopback connection failures keep the loader visible.
                        deadline = time.monotonic() + 120
                        while not self.stopping.is_set():
                            try:
                                validator.check()
                                break
                            except (requests.ConnectionError, requests.Timeout):
                                with self.condition:
                                    if revision != self.revision:
                                        break
                                if time.monotonic() >= deadline:
                                    raise RuntimeError('The local AI backend did not start. Check .comfy-stderr.log, then Retry model.')
                                self.stopping.wait(.5)
                    finally:
                        if hasattr(validator, 'session'):
                            validator.session.close()
                    with self.condition:
                        if revision != self.revision:
                            continue
                        if self.stopping.is_set():
                            break
                        self.checked_revision = revision
                        self.phase = 'loading'
                canvas, layout = prepare_full_frame(frame, config["inference_width"], config["inference_height"])
                self.client.progress_callback = lambda event: self.update_progress(revision, event)
                styled = self.client.generate(canvas, self.stopping, config)
                if styled is None:
                    break
                styled = restore_full_frame(styled, layout)
                finished = time.monotonic()
                with self.condition:
                    if revision == self.revision:
                        self.result = (styled, frame, quad, epoch, captured)
                        # The cold-load image may already be stale. Keep the loader until
                        # a fresh follow-up image is available; a finished graph is not enough.
                        age_limit = config['result_max_age'] if self.executed_revision == revision else min(3, config['result_max_age'])
                        self.ready = finished - captured <= age_limit
                        self.executed_revision = revision
                        if not self.ready:
                            self.result = None
                        self.phase = 'ready' if self.ready else 'refreshing'
                        self.percent = 100 if self.ready else max(90, self.percent)
                        self.stage = 'Ready to reveal the styled feed' if self.ready else 'Preparing a fresh camera frame'
                        self.detail = 'Camera, gesture mask and styled feed are ready' if self.ready else 'The cold-load frame was old; updating the camera reference'
                        self.latency = finished - captured
                        self.ai_fps = 0 if previous is None or previous_revision != revision else 1 / max(1e-6, finished - previous)
                        previous, previous_revision = finished, revision
                    self.completed += 1
                    self.condition.notify_all()
            except Exception as error:
                with self.condition:
                    if revision == self.revision:
                        self.error = str(error)
                        self.phase = 'error'
                        self.stage = 'Workflow could not finish'
                        self.ready = False
                        self.failed_revision = revision
                        self.pending = self.result = None
                        self.condition.notify_all()
            self.stopping.wait(max(0, 1 / config["max_ai_fps"] - (time.monotonic() - started)))

    def close(self):
        self.stopping.set()
        with self.condition:
            self.condition.notify_all()
        self.thread.join(timeout=1)
