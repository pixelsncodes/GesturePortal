import json
import importlib.util
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import cv2
import numpy as np

from portal.client import ComfyClient, InferenceWorker
from portal.geometry import FrameTracker, canvas_corners, composite_portal, crop_portal
from portal.workflow import make_workflow
from portal.compositor import prepare_full_frame, restore_full_frame, composite_full_frame

ROOT = Path(__file__).resolve().parents[1]


class GeometryTests(unittest.TestCase):
    def test_full_feed_mask_uses_scene_coordinates_without_stretching(self):
        real = np.zeros((80, 120, 3), np.uint8)
        anime = np.zeros_like(real)
        anime[:, :, 0] = np.arange(120, dtype=np.uint8)[None, :]
        anime[:, :, 1] = np.arange(80, dtype=np.uint8)[:, None]
        quad = np.array([[15, 10], [90, 25], [105, 60], [20, 70]], np.float32)
        output = composite_full_frame(real, anime, quad, feather=0)
        mask = np.zeros(real.shape[:2], np.uint8)
        cv2.fillConvexPoly(mask, quad.astype(np.int32), 255)
        self.assertTrue(np.array_equal(output[mask > 0], anime[mask > 0]))
        self.assertTrue(np.array_equal(output[mask == 0], real[mask == 0]))
        moved = quad - [5, 2]
        other = composite_full_frame(real, anime, moved.astype(np.float32), feather=0)
        # Moving the mask reveals different pixels of one fixed scene.
        self.assertTrue(np.array_equal(output[35, 50], other[35, 50]))

    def test_letterboxing_restores_camera_aspect_and_alignment(self):
        frame = np.full((50, 100, 3), (30, 80, 150), np.uint8)
        canvas, layout = prepare_full_frame(frame, 200, 200)
        self.assertEqual((layout.left, layout.top, layout.width, layout.height), (0, 50, 200, 100))
        self.assertFalse(np.any(canvas[:50]))
        restored = restore_full_frame(canvas, layout)
        self.assertTrue(np.array_equal(restored, frame))

    def test_full_feed_mask_feathers_only_inward(self):
        real = np.full((80, 120, 3), 75, np.uint8)
        anime = np.full_like(real, 200)
        quad = np.array([[15, 10], [90, 25], [105, 60], [20, 70]], np.float32)
        output = composite_full_frame(real, anime, quad, feather=4)
        mask = np.zeros(real.shape[:2], np.uint8)
        cv2.fillConvexPoly(mask, quad.astype(np.int32), 255)
        self.assertTrue(np.array_equal(output[mask == 0], real[mask == 0]))

    def test_outside_polygon_is_unchanged(self):
        frame = np.full((120, 180, 3), 50, np.uint8)
        styled = np.full((64, 64, 3), 220, np.uint8)
        quad = np.array([[20, 30], [145, 18], [160, 90], [40, 105]], np.float32)
        result = composite_portal(frame, styled, quad)
        mask = np.zeros(frame.shape[:2], np.uint8)
        cv2.fillConvexPoly(mask, quad.astype(np.int32), 255)
        self.assertTrue(np.array_equal(result[mask == 0], frame[mask == 0]))
        self.assertGreater(int(result[60, 80, 0]), 200)

    def test_perspective_round_trip(self):
        image = np.zeros((96, 128, 3), np.uint8)
        image[:48, :64] = (20, 60, 200)
        image[48:, 64:] = (200, 60, 20)
        crop = crop_portal(image, canvas_corners(128, 96), 128, 96)
        self.assertTrue(np.array_equal(image, crop))

    def test_debounce_grace_and_reopen_invalidate_old_results(self):
        tracker = FrameTracker(hold=0.1, grace=0.15)
        quad = canvas_corners(100, 100)
        self.assertIsNone(tracker.update(quad, now=0))
        self.assertIsNotNone(tracker.update(quad, now=0.11))
        first_epoch = tracker.epoch
        self.assertIsNotNone(tracker.update(None, now=0.2))
        self.assertIsNone(tracker.update(None, now=0.3))
        self.assertIsNone(tracker.update(quad, now=0.4))
        self.assertIsNotNone(tracker.update(quad, now=0.51))
        self.assertGreater(tracker.epoch, first_epoch)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config.flux.json').read_text(encoding='utf-8'))

    def test_portrait_fallback_retains_full_frame_and_face_detail(self):
        config = json.loads((ROOT / 'config.portrait-v2.json').read_text())
        graph = make_workflow(config, 'a' * 32)
        self.assertEqual(graph['15']['inputs']['images'], ['4', 0])
        self.assertTrue(graph['15']['inputs']['face_detail'])
        self.assertEqual(graph['8']['inputs']['images'], ['15', 0])

    def test_remote_inference_is_rejected(self):
        self.config['comfy_url'] = 'https://example.com'
        with self.assertRaises(ValueError):
            ComfyClient(self.config)

    def test_flux_conditions_on_camera_latents_instead_of_only_text(self):
        graph = make_workflow(self.config, 'a' * 32)
        self.assertEqual(graph['24']['inputs']['pixels'], ['4', 0])
        self.assertEqual(graph['25']['inputs']['latent'], ['24', 0])
        self.assertEqual(graph['27']['inputs']['conditioning'], ['25', 0])
        self.assertEqual(graph['30']['inputs']['steps'], 4)
        self.assertEqual(graph['33']['inputs']['source'], ['4', 0])

    def test_qwen_uses_reference_vision_and_matching_reference_latent_size(self):
        config = json.loads((ROOT / 'config.qwen.json').read_text())
        graph = make_workflow(config, 'a' * 32)
        self.assertEqual(graph['23']['inputs']['images.image_1'], ['4', 0])
        self.assertEqual(graph['23']['inputs']['vae'], ['22', 0])
        self.assertEqual(graph['23']['inputs']['resolution'], 0)
        self.assertEqual(graph['31']['inputs']['latent_image'], ['23', 2])
        self.assertEqual(graph['30']['inputs']['latent'], ['23', 2])
        self.assertEqual(graph['27']['class_type'], 'BasicGuider')

    def test_worker_replaces_pending_frames_instead_of_queuing(self):
        entered, release, second = threading.Event(), threading.Event(), threading.Event()
        received = []

        class FakeClient:
            def __init__(self, config):
                pass

            def check(self):
                pass

            def generate(self, crop, stopping, config=None):
                received.append(int(crop[crop.shape[0] // 2, crop.shape[1] // 2, 0]))
                if len(received) == 1:
                    entered.set()
                    release.wait(2)
                else:
                    second.set()
                return crop

        with patch('portal.client.ComfyClient', FakeClient):
            worker = InferenceWorker(self.config)
            try:
                quad = canvas_corners(16, 16)
                worker.submit(np.full((16, 16, 3), 1, np.uint8), quad, 1, time.monotonic())
                self.assertTrue(entered.wait(1))
                for value in (2, 3, 4):
                    worker.submit(np.full((16, 16, 3), value, np.uint8), None, 1, time.monotonic())
                release.set()
                self.assertTrue(second.wait(1))
                self.assertEqual(received, [1, 4])
            finally:
                release.set()
                worker.close()

    def test_model_switch_discards_in_flight_old_model_result(self):
        entered, release, next_entered, next_release = [threading.Event() for _ in range(4)]
        seen = []
        initial = dict(self.config, checkpoint='old.safetensors', inference_width=64, inference_height=64)
        selected = dict(initial, checkpoint='new.safetensors')

        class FakeClient:
            def __init__(self, config):
                self.url = config['comfy_url'].rstrip('/')
                self.session = SimpleNamespace(close=lambda: None)

            def check(self):
                pass

            def generate(self, frame, stopping, config=None):
                seen.append(config['checkpoint'])
                if len(seen) == 1:
                    entered.set()
                    release.wait(2)
                else:
                    next_entered.set()
                    next_release.wait(2)
                return frame

        with patch('portal.client.ComfyClient', FakeClient):
            worker = InferenceWorker(initial)
            try:
                worker.submit(np.full((16, 16, 3), 1, np.uint8), None, 1, time.monotonic())
                self.assertTrue(entered.wait(1))
                worker.select(selected)
                worker.submit(np.full((16, 16, 3), 2, np.uint8), None, 1, time.monotonic())
                release.set()
                self.assertTrue(next_entered.wait(1))
                self.assertIsNone(worker.snapshot()[0])
                next_release.set()
                with worker.condition:
                    self.assertTrue(worker.condition.wait_for(lambda: worker.completed >= 2, timeout=1))
                result = worker.snapshot()[0]
                self.assertEqual(seen, ['old.safetensors', 'new.safetensors'])
                self.assertIsNotNone(result)
                self.assertTrue(np.all(result[1] == 2))
            finally:
                release.set()
                next_release.set()
                worker.close()


class FaceDetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('face_detail', ROOT / 'custom_nodes/gesture_portal/face_detail.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_face_alignment_preserves_rotation_scale_and_inverse_coordinates(self):
        original = self.module.reference_points(288)
        angle, scale = np.deg2rad(23), 0.65
        matrix = np.array([[scale * np.cos(angle), -scale * np.sin(angle), 85],
                           [scale * np.sin(angle), scale * np.cos(angle), 60]], np.float32)
        transformed = cv2.transform(original[None], matrix)[0]
        recovered = self.module.similarity_transform(transformed, original)
        restored = cv2.transform(transformed[None], recovered)[0]
        np.testing.assert_allclose(restored, original, atol=0.0001)

    def test_face_merge_preserves_pixels_outside_its_mask(self):
        styled = np.full((100, 120, 3), 0.2, np.float32)
        patch = np.full((32, 32, 3), 0.8, np.float32)
        mask = np.ones((32, 32), np.float32)
        inverse = np.array([[1, 0, 45], [0, 1, 25]], np.float32)
        result = self.module.merge_detail(styled, patch, inverse, mask)
        self.assertTrue(np.array_equal(result[:20], styled[:20]))
        self.assertTrue(np.array_equal(result[:, :40], styled[:, :40]))
        np.testing.assert_allclose(result[40, 60], 0.8)


if __name__ == '__main__':
    unittest.main()
