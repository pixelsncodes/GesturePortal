import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

import cv2
import numpy as np

from portal.controls import ControlPanel, ControlWindow

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform == 'win32', 'Windows desktop event-loop regression')
class ControlEventLoopTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=ROOT / 'artifacts')
        self.path = Path(self.directory.name)
        shutil.copyfile(ROOT / 'config.flux.json', self.path / 'config.flux.json')
        self.dct = json.loads((ROOT / 'config.portrait-v2.json').read_text())
        self.diffusion = json.loads((ROOT / 'config.flux.json').read_text())

    def tearDown(self):
        self.assertTrue(self.path.resolve().is_relative_to(ROOT.resolve()))
        self.directory.cleanup()

    def test_controls_process_handles_input_while_viewer_blocks_and_pumps_opencv(self):
        panel = ControlPanel(self.dct, self.path)
        window = 'Controls event-loop regression'
        try:
            panel.change('style_strength', .65)
            # No panel.poll(): a slow camera/HTTP call must not stop Tk's debounce/input loop.
            time.sleep(.8)
            self.assertTrue(panel.connection.poll())
            _, changed = panel.poll()
            self.assertTrue(changed)
            self.assertEqual(panel.values['style_strength'], .65)
            panel.sync_model(self.diffusion)
            panel.change('edit_prompt', 'Convert into anime; preserve the camera layout.')
            panel.change('subject', 'male')
            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
            cv2.imshow(window, np.zeros((40, 80, 3), np.uint8))
            deadline = time.monotonic() + .8
            while time.monotonic() < deadline:
                cv2.waitKey(10)
            self.assertTrue(panel.connection.poll())
            _, changed = panel.poll()
            self.assertTrue(changed)
            self.assertIn('preserve the camera layout', panel.values['edit_prompt'])
            self.assertEqual(panel.values['subject'], 'male')
        finally:
            cv2.destroyAllWindows()
            panel.close()
        self.assertFalse(panel.process.is_alive())

    def test_widgets_edit_prompt_and_model_selection_remain_connected(self):
        window = ControlWindow(self.dct, self.path)
        try:
            window.root.update()
            window.widgets['style_strength'].set(.6)
            self.assertEqual(window.values['style_strength'], .6)
            self.assertEqual(str(window.widgets['subject'].cget('state')), 'disabled')
            window.model_var.set(window.model_box.cget('values')[1])
            window.model_box.event_generate('<<ComboboxSelected>>')
            window.root.update()
            self.assertEqual(window.take_events()[0], 2)
            window.sync_model(self.diffusion)
            window.root.update()
            self.assertEqual(str(window.widgets['subject'].cget('state')), 'readonly')
            window.variables['subject'].set('Male')
            window.widgets['subject'].event_generate('<<ComboboxSelected>>')
            window.root.update()
            self.assertEqual(window.values['subject'], 'male')
            window.prompt_text.delete('1.0', 'end')
            window.prompt_text.insert('1.0', 'Draw anime and preserve camera framing.')
            window.prompt_button.invoke()
            self.assertEqual(window.values['edit_prompt'], 'Draw anime and preserve camera framing.')
            self.assertEqual(str(window.widgets['face_likeness'].cget('state')), 'disabled')
            window.sync_model(self.dct)
            self.assertEqual(str(window.widgets['face_likeness'].cget('state')), 'normal')
            window.widgets['face_likeness'].set(.5)
            self.assertEqual(window.values['face_likeness'], .5)
        finally:
            window.close()

if __name__ == '__main__': unittest.main()
