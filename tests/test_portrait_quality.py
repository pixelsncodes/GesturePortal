import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np

from portal.workflow import make_workflow

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('portrait_quality', ROOT / 'custom_nodes/gesture_portal/portrait_quality.py')
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


class PortraitQualityTests(unittest.TestCase):
    def test_full_color_retention_matches_uniform_camera_color_and_lighting(self):
        original = np.full((32, 32, 3), [.15, .35, .45], np.float32)
        styled = np.full_like(original, [.6, .7, .8])
        np.testing.assert_allclose(quality.retain_colors(original, styled, 1), original, atol=.004)

    def test_zero_retention_preserves_original_model_result(self):
        original = np.full((32, 32, 3), .2, np.float32)
        styled = np.full_like(original, .8)
        self.assertIs(quality.retain_colors(original, styled, 0), styled)
        self.assertIs(quality.retain_faces(original, styled, [], np.ones((8, 8), np.float32), 1), styled)

    def test_face_retention_only_changes_the_aligned_face_mask(self):
        original = np.full((64, 64, 3), .37, np.float32)
        styled = np.full_like(original, .8)
        patches = [(None, np.array([[1, 0, 16], [0, 1, 16]], np.float32))]
        mask = np.ones((32, 32), np.float32)
        result = quality.retain_faces(original, styled, patches, mask, 1)
        self.assertTrue(np.array_equal(result[16:48, 16:48], original[16:48, 16:48]))
        self.assertTrue(np.array_equal(result[:16], styled[:16]))
        self.assertTrue(np.array_equal(result[:, :16], styled[:, :16]))

    def test_tuned_default_passes_quality_settings_to_portrait_node(self):
        config = json.loads((ROOT / 'docs/legacy/config.portrait-v2.json').read_text())
        self.assertEqual(config['portrait_model'], 'face_paint_512_v2.pt')
        inputs = make_workflow(config, 'a' * 32)['15']['inputs']
        self.assertEqual(inputs['strength'], .85)
        self.assertEqual(inputs['face_likeness'], .35)
        self.assertEqual(inputs['color_preservation'], .75)
        self.assertEqual(inputs['shadow_lift'], .15)


if __name__ == '__main__':
    unittest.main()
