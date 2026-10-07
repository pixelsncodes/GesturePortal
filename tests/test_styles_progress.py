import json
import unittest
from pathlib import Path

from portal.controls import apply_settings, default_settings, normalized_settings
from portal.progress import WorkflowProgress
from portal.styles import STYLES, infer_style
from portal.workflow import make_workflow

ROOT = Path(__file__).resolve().parents[1]


class StyleTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config.flux.json').read_text())

    def test_nine_distinct_presets_use_the_same_model_and_camera_reference(self):
        self.assertEqual(len(STYLES), 9)
        self.assertEqual(len({value[1] for value in STYLES.values()}), 9)
        for key, (_, prompt, _) in STYLES.items():
            settings = dict(default_settings(self.config), style_preset=key, edit_prompt=prompt)
            selected = apply_settings(self.config, settings)
            graph = make_workflow(selected, 'a'*32)
            self.assertEqual(graph['20']['inputs']['unet_name'], self.config['diffusion_model'])
            self.assertEqual(graph['24']['inputs']['pixels'], ['4', 0])
            self.assertEqual(graph['23']['inputs']['text'], prompt)
            self.assertEqual(infer_style(prompt), key)

    def test_invalid_style_is_rejected_and_old_custom_prompts_remain_valid(self):
        settings = default_settings(dict(self.config, edit_prompt='Preserve camera; paint in gouache.'))
        settings.pop('style_preset')
        self.assertEqual(normalized_settings(settings)['style_preset'], 'custom')
        with self.assertRaises(ValueError):
            normalized_settings(dict(settings, style_preset='missing'))


class ProgressTests(unittest.TestCase):
    def setUp(self):
        config = json.loads((ROOT / 'config.flux.json').read_text())
        self.progress = WorkflowProgress(make_workflow(config, 'a'*32), config, 'owned')

    def event(self, kind, **data):
        return self.progress.consume({'type': kind, 'data': dict(prompt_id='owned', **data)})

    def test_cached_nodes_and_sampling_steps_make_measured_monotonic_progress(self):
        first = self.event('execution_cached', nodes=['20', '21', '22'])
        loading = self.event('executing', node='31')
        sample = self.event('progress', node='31', value=2, max=4)
        self.assertGreaterEqual(loading['fraction'], first['fraction'])
        self.assertGreater(sample['fraction'], loading['fraction'])
        self.assertIn('step 2 of 4', sample['detail'])
        states = {key: {'state': 'finished', 'value': 1, 'max': 1} for key in self.progress.graph}
        done = self.event('progress_state', nodes=states)
        self.assertEqual(done['fraction'], 1)

    def test_foreign_jobs_are_ignored_and_unknown_messages_do_not_invent_progress(self):
        self.assertIsNone(self.progress.consume({'type': 'executing', 'data': {'prompt_id': 'foreign', 'node': '20'}}))
        self.assertIsNone(self.event('unknown'))
        self.assertEqual(sum(self.progress.fractions.values()), 0)


if __name__ == '__main__': unittest.main()
