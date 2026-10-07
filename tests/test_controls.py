import json, unittest
from pathlib import Path
from portal.controls import apply_settings, default_settings, normalized_settings, MODEL_LABELS
from portal.workflow import make_workflow
ROOT = Path(__file__).resolve().parents[1]

class LiveControlTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT/'config.flux.json').read_text())
        self.settings = default_settings(self.config)

    def test_subject_selection_does_not_accumulate_gender_instructions(self):
        selected = apply_settings(self.config, dict(self.settings, subject='male'))
        self.assertIn('masculine character presentation', make_workflow(selected,'a'*32)['23']['inputs']['text'])
        selected = apply_settings(selected, dict(self.settings, subject='female'))
        prompt = make_workflow(selected,'a'*32)['23']['inputs']['text']
        self.assertIn('feminine character presentation', prompt)
        self.assertNotIn('masculine character presentation', prompt)
        selected = apply_settings(selected, dict(self.settings, subject='neutral'))
        self.assertEqual(make_workflow(selected,'a'*32)['23']['inputs']['text'],self.config['edit_prompt'])

    def test_inactive_editor_prompt_leaves_portrait_graph_unchanged(self):
        config = json.loads((ROOT/'config.portrait-v2.json').read_text())
        settings = default_settings(config)
        settings.update(subject='male',edit_prompt='A new style')
        self.assertEqual(make_workflow(config,'a'*32),make_workflow(apply_settings(config,settings),'a'*32))

    def test_invalid_values_cannot_enter_model_graph(self):
        for field,value in [('subject','auto'),('style_strength',float('nan')),('edit_prompt',''),('edit_prompt','a'*4001)]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                normalized_settings(dict(self.settings,**{field:value}))

    def test_editor_rejects_dimension_rounding_that_would_shift_camera(self):
        with self.assertRaises(ValueError):
            make_workflow(dict(self.config,inference_height=360),'a'*32)

    def test_only_remaining_models_are_selectable(self):
        self.assertEqual(len(MODEL_LABELS),3)
        self.assertTrue(all('DCT' not in label and 'Portrait v1' not in label for label in MODEL_LABELS))

if __name__ == '__main__': unittest.main()
