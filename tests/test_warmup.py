import json
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from portal.client import InferenceWorker

ROOT = Path(__file__).resolve().parents[1]


class WarmupTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config.flux.json').read_text())
        self.config.update(inference_width=64, inference_height=64, result_max_age=.15)

    def test_no_gesture_warms_model_and_cold_stale_frame_is_not_ready(self):
        entered, release, second, finish = [threading.Event() for _ in range(4)]
        class Client:
            def __init__(self, config):
                self.session = SimpleNamespace(close=lambda: None)
            def check(self): pass
            def generate(self, frame, stopping, config=None):
                if not entered.is_set():
                    entered.set()
                    release.wait(2)
                else:
                    second.set()
                    finish.wait(2)
                return frame
        with patch('portal.client.ComfyClient', Client):
            worker = InferenceWorker(self.config)
            try:
                frame = np.zeros((16, 16, 3), np.uint8)
                worker.submit(frame, None, 0, time.monotonic())
                self.assertTrue(entered.wait(1))
                self.assertEqual(worker.readiness()['phase'], 'loading')
                time.sleep(.18)
                release.set()
                with worker.condition:
                    self.assertTrue(worker.condition.wait_for(lambda: worker.completed == 1, 1))
                self.assertEqual(worker.readiness()['phase'], 'refreshing')
                self.assertFalse(worker.readiness()['ready'])
                worker.submit(frame, None, 0, time.monotonic())
                self.assertTrue(second.wait(1))
                finish.set()
                with worker.condition:
                    self.assertTrue(worker.condition.wait_for(lambda: worker.completed == 2, 1), worker.error)
                self.assertTrue(worker.readiness()['ready'])
                self.assertIsNone(worker.snapshot()[0][2])
            finally:
                release.set()
                finish.set()
                worker.close()

    def test_validation_does_not_block_constructor_and_error_can_retry(self):
        entered, release = threading.Event(), threading.Event()
        checks = []
        class Client:
            def __init__(self, config):
                self.url = config['comfy_url']
                self.session = SimpleNamespace(close=lambda: None)
            def check(self):
                checks.append(1)
                entered.set()
                release.wait(2)
                if len(checks) == 1: raise ValueError('Model missing')
            def generate(self, frame, stopping, config=None): return frame
        with patch('portal.client.ComfyClient', Client):
            worker = InferenceWorker(self.config)
            try:
                frame = np.zeros((16, 16, 3), np.uint8)
                self.assertFalse(entered.is_set())
                worker.submit(frame, None, 0, time.monotonic())
                self.assertTrue(entered.wait(1))
                release.set()
                with worker.condition:
                    self.assertTrue(worker.condition.wait_for(lambda: worker.error is not None, 1))
                self.assertEqual(worker.readiness()['phase'], 'error')
                worker.submit(frame, None, 0, time.monotonic())
                self.assertIsNone(worker.pending)
                worker.retry()
                worker.submit(frame, None, 0, time.monotonic())
                with worker.condition:
                    self.assertTrue(worker.condition.wait_for(lambda: worker.completed == 1, 1))
                self.assertTrue(worker.readiness()['ready'])
            finally:
                release.set()
                worker.close()


if __name__ == '__main__': unittest.main()
