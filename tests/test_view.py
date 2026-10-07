import time
import unittest

import numpy as np
from portal.view import render_feed


class RevealTests(unittest.TestCase):
    def test_new_gesture_reveals_cached_image_generated_without_any_gesture(self):
        now = time.monotonic()
        camera = np.full((80, 120, 3), 40, np.uint8)
        anime = np.full_like(camera, 220)
        quad = np.array([[20, 20], [100, 20], [100, 60], [20, 60]], np.float32)
        cache = (anime, camera, None, 0, now)
        result, mask, active = render_feed(camera, quad, cache, now, {'result_max_age': 3, 'feather_pixels': 0}, epoch=5)
        self.assertTrue(active)
        self.assertTrue(np.array_equal(mask, quad))
        self.assertTrue(np.all(result[40, 60] == 220))
        self.assertTrue(np.all(result[0, 0] == 40))

    def test_stale_or_previous_capture_epoch_does_not_appear_in_aligned_mode(self):
        now = time.monotonic()
        camera = np.full((80, 120, 3), 40, np.uint8)
        quad = np.array([[20, 20], [100, 20], [100, 60], [20, 60]], np.float32)
        config = {'result_max_age': 3, 'feather_pixels': 0}
        cache = (np.full_like(camera, 220), camera, quad, 1, now)
        result, _, active = render_feed(camera, quad, cache, now, config, synchronize=True, epoch=2)
        self.assertFalse(active)
        self.assertTrue(np.array_equal(result, camera))
        result, _, active = render_feed(camera, quad, cache, now+4, config)
        self.assertFalse(active)
        self.assertTrue(np.array_equal(result, camera))


if __name__ == '__main__': unittest.main()
