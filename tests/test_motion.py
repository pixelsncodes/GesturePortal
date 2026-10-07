import time
import unittest

import cv2
import numpy as np

from portal.motion import MotionAligner
from portal.view import FeedRenderer, alignment_mode


class MotionAlignmentTests(unittest.TestCase):
    def test_known_translation_moves_styled_features_toward_the_current_camera(self):
        rng = np.random.default_rng(12)
        gray = cv2.GaussianBlur(rng.integers(0, 256, (128, 192), dtype=np.uint8), (3, 3), 0)
        source = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        transform = np.float32([[1, 0, 6], [0, 1, 4]])
        current = cv2.warpAffine(source, transform, (192, 128))
        styled = np.zeros_like(source)
        styled[45:85, 70:110, 2] = 255
        aligned, confidence = MotionAligner().warp(source, styled, current)
        expected = cv2.warpAffine(styled, transform, (192, 128))
        roi = np.s_[25:105, 40:140]
        self.assertLess(np.mean(np.abs(aligned[roi].astype(float)-expected[roi])), 8)
        self.assertGreater(float(confidence[50:80, 80:110].mean()), .9)

    def test_smooth_mode_keeps_current_camera_outside_the_portal_and_current_mask(self):
        now = time.monotonic()
        source = np.full((80, 120, 3), 40, np.uint8)
        current = np.full_like(source, 45)
        quad = np.float32([[30, 20], [100, 20], [100, 65], [30, 65]])
        old_quad = quad-10
        result = (np.full_like(source, 220), source, old_quad, 0, now)
        output, mask, active = FeedRenderer().render(current, quad, result, now,
                           {'result_max_age': 3, 'feather_pixels': 0}, mode='smooth', epoch=4)
        self.assertTrue(active)
        self.assertTrue(np.array_equal(mask, quad))
        self.assertTrue(np.all(output[0, 0] == 45))
        self.assertGreater(int(output[40, 60, 0]), 200)

    def test_unmatchable_new_content_falls_back_to_current_pixels(self):
        now = time.monotonic()
        current = np.full((80, 120, 3), 255, np.uint8)
        source = np.zeros_like(current)
        result = (np.full_like(current, 100), source, None, 0, now)
        output, _, _ = FeedRenderer().render(current, None, result, now,
                   {'result_max_age': 3, 'feather_pixels': 0}, view='anime', mode='smooth')
        self.assertTrue(np.array_equal(output, current))

    def test_old_result_and_shape_changes_do_not_reuse_motion_from_another_image(self):
        now = time.monotonic()
        renderer = FeedRenderer()
        for shape in ((80, 120, 3), (64, 96, 3)):
            camera = np.full(shape, 40, np.uint8)
            result = (np.full(shape, 200, np.uint8), camera, None, 0, now)
            output, _, _ = renderer.render(camera, None, result, now,
                 {'result_max_age': 3, 'feather_pixels': 0}, view='anime', mode='smooth')
            self.assertEqual(output.shape, shape)
            output, _, active = renderer.render(camera, None, result, now+4,
                 {'result_max_age': 3, 'feather_pixels': 0}, view='anime', mode='smooth')
            self.assertFalse(active)
            self.assertTrue(np.array_equal(output, camera))
            self.assertIsNone(renderer.motion.reference)

    def test_legacy_alignment_configuration_keeps_exact_behavior(self):
        self.assertEqual(alignment_mode({'synchronize_feed': True}), 'exact')
        self.assertEqual(alignment_mode({'synchronize_feed': False}), 'off')
        self.assertEqual(alignment_mode({'alignment_mode': 'smooth'}), 'smooth')
        with self.assertRaises(ValueError): alignment_mode({'alignment_mode': 'invalid'})


if __name__ == '__main__': unittest.main()
