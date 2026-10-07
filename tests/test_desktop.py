import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from portal.desktop import DesktopWindow
from portal import theme

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform == 'win32', 'Desktop Tk regression')
class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config.flux.json').read_text())
        self.window = DesktopWindow(self.config, ROOT)
        self.window.root.update()

    def tearDown(self):
        self.window.close()

    def test_loader_animates_without_waiting_for_inference_then_hides_when_ready(self):
        window = self.window
        ok, encoded = cv2.imencode('.jpg', np.zeros((360, 640, 3), np.uint8))
        self.assertTrue(ok)
        window.show_frame(encoded.tobytes(), {'phase': 'loading', 'elapsed': 4, 'ready': False})
        self.assertTrue(window.viewer.find_withtag('loader'))
        rotation = window.rotation
        window.animate()
        self.assertNotEqual(rotation, window.rotation)
        window.show_frame(encoded.tobytes(), {'phase': 'ready', 'ready': True, 'fresh': True, 'active': True})
        self.assertGreater(window.photo.width(), 640)
        self.assertFalse(window.viewer.find_withtag('loader'))
        self.assertIn('Portal active', window.state_text.get())
        self.assertEqual(str(window.save_button.cget('state')), 'normal')

    def test_widget_settings_and_error_recovery_controls(self):
        window = self.window
        window.toggle_widget()
        window.root.update()
        self.assertTrue(window.compact)
        self.assertFalse(window.sidebar.winfo_ismapped())
        window.toggle()
        window.root.update()
        self.assertFalse(window.compact)
        self.assertTrue(window.sidebar.winfo_ismapped())
        window.update_status({'phase': 'error', 'error': 'Model file missing'})
        window.root.update()
        self.assertEqual(window.message.get(), 'Model file missing')
        self.assertTrue(window.retry_button.winfo_ismapped())
        window.retry_button.invoke()
        self.assertEqual(window.actions[-1], ord('r'))
        window.update_status({'phase': 'ready', 'fresh': True})
        self.assertFalse(window.retry_button.winfo_manager())

    def test_alignment_labels_distinguish_live_motion_from_exact_capture(self):
        for mode in ('off', 'smooth', 'exact'):
            self.window.update_status({'phase': 'ready', 'alignment': mode, 'preview_fps': 29.4, 'ai_fps': .8})
            self.assertEqual(self.window.align_button.cget('text'), f'Align: {mode}')
            self.assertIn('29 camera fps', self.window.metrics.get())
            self.assertIn('0.8 AI updates/s', self.window.metrics.get())

    def test_style_dropdown_updates_instruction_and_customization_is_reachable(self):
        window = self.window
        window.style_var.set('Black ink doodle')
        window.style_box.event_generate('<<ComboboxSelected>>')
        window.root.update()
        self.assertEqual(window.values['style_preset'], 'doodle')
        self.assertIn('black ink', window.values['edit_prompt'])
        self.assertEqual(window.prompt_text.get('1.0', 'end').strip(), window.values['edit_prompt'])
        window.style_var.set('Custom instruction')
        window.style_box.event_generate('<<ComboboxSelected>>')
        window.root.update()
        self.assertTrue(window.instruction_open)
        window.prompt_text.delete('1.0', 'end')
        window.prompt_text.insert('1.0', 'Render as charcoal, preserve pose.')
        window.prompt_button.invoke()
        self.assertEqual(window.values['style_preset'], 'custom')

    def test_saved_style_reopens_and_legacy_custom_instructions_survive_upgrade(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            folder = Path(directory)
            shutil.copyfile(ROOT / 'config.flux.json', folder / 'config.flux.json')
            window = DesktopWindow(self.config, folder)
            try:
                window.change('style_preset', 'blueprint')
                window.save()
                expected_prompt = window.values['edit_prompt']
            finally:
                window.close()
            window = DesktopWindow(self.config, folder)
            try:
                self.assertEqual(window.style_var.get(), 'Cyanotype blueprint')
                self.assertEqual(window.values['edit_prompt'], expected_prompt)
            finally:
                window.close()
            (folder / 'controls.json').write_text(json.dumps({'edit_prompt': 'Draw with charcoal.'}))
            window = DesktopWindow(self.config, folder)
            try:
                self.assertEqual(window.style_var.get(), 'Custom instruction')
                self.assertEqual(window.values['edit_prompt'], 'Draw with charcoal.')
                self.assertTrue(window.instruction_open)
            finally:
                window.close()

    def test_instruction_typing_preserves_shortcuts_and_model_specific_controls(self):
        window = self.window
        window.keypress(SimpleNamespace(widget=window.prompt_text, keysym='a', char='a'))
        self.assertEqual(window.actions, [])
        window.keypress(SimpleNamespace(widget=window.viewer, keysym='a', char='a'))
        self.assertEqual(window.actions, [ord('a')])
        self.assertTrue(window.editor_group.winfo_ismapped())
        self.assertFalse(window.portrait_group.winfo_ismapped())
        portrait = json.loads((ROOT / 'config.portrait-v2.json').read_text())
        window.sync_model(portrait)
        window.root.update()
        self.assertFalse(window.editor_group.winfo_ismapped())
        self.assertTrue(window.portrait_group.winfo_ismapped())
        window.widgets['shadow_lift'].set(.25)
        self.assertEqual(window.values['shadow_lift'], .25)


class ThemeTests(unittest.TestCase):
    def test_normal_text_and_primary_button_have_readable_contrast(self):
        def luminance(color):
            rgb = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
            rgb = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
            return sum(a*b for a, b in zip(rgb, (.2126, .7152, .0722)))
        for fg, bg in [(theme.TEXT, theme.SURFACE), (theme.MUTED, theme.SURFACE),
                       (theme.ON_ACCENT, theme.ACCENT), (theme.TEXT, theme.FIELD)]:
            a, b = sorted((luminance(fg), luminance(bg)))
            self.assertGreaterEqual((b+.05)/(a+.05), 4.5)


if __name__ == '__main__': unittest.main()
