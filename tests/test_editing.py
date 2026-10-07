import importlib.util, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HAS_TORCH=importlib.util.find_spec('torch') is not None

@unittest.skipUnless(HAS_TORCH,'Run with the ComfyUI Python runtime for tensor-node checks')
class EditingNodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        cls.torch=torch
        spec=importlib.util.spec_from_file_location('editing',ROOT/'custom_nodes/gesture_portal/editing.py')
        cls.editing=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.editing)

    def test_qwen_schedule_has_six_steps_and_required_zero_endpoint(self):
        t=self.torch
        latent={'samples':t.zeros(1,64,32,32)}
        sigmas=self.editing.GestureQwenTurboSigmas().schedule(latent)[0]
        self.assertEqual(len(sigmas),7)
        self.assertEqual(sigmas[0].item(),1)
        self.assertEqual(sigmas[-1].item(),0)
        self.assertTrue(t.all(sigmas[:-1]>sigmas[1:]).item())
        # The published terminal raw node is .25; shifting .5 would make this >.6.
        self.assertTrue(.35<sigmas[-2].item()<.38)

    def test_rgba_output_is_rgb_and_source_blending_does_not_shift_pixels(self):
        t=self.torch
        source=t.zeros(1,32,64,3);source[:,8:16,24:32,:]=.4
        output=t.ones(1,32,64,4)
        result=self.editing.GestureEditBlend().blend(output,source,0)[0]
        self.assertTrue(t.equal(source,result))
        result=self.editing.GestureEditBlend().blend(output,source,1)[0]
        self.assertEqual(result.shape,source.shape)
        self.assertTrue(t.all(result==1).item())
        with self.assertRaises(ValueError):
            self.editing.GestureEditBlend().blend(t.ones(1,32,32,4),source,1)

if __name__=='__main__':unittest.main()
