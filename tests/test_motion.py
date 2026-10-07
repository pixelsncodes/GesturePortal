import unittest
from unittest.mock import patch
import numpy as np
from portal.view import FeedRenderer, alignment_mode, ALIGNMENT_MODES, render_feed

class ExactAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.frame=np.full((80,120,3),45,np.uint8)
        self.quad=np.float32([[20,20],[90,20],[90,65],[20,65]])
        self.result=(np.full_like(self.frame,220),np.full_like(self.frame,30),self.quad.copy(),4,10.)
        self.config={'result_max_age':3,'feather_pixels':4}
        self.renderer=FeedRenderer()
    def render(self, **kw):
        args=dict(view='portal',mode='exact',epoch=4);args.update(kw)
        return self.renderer.render(self.frame,self.quad,self.result,10.,self.config,**args)
    def test_reuse_matches_uncached_pixels_and_drawing_does_not_mutate_cache(self):
        with patch('portal.view.composite_full_frame', wraps=__import__('portal.compositor',fromlist=['composite_full_frame']).composite_full_frame) as compose:
            expected=render_feed(self.frame,self.quad,self.result,10.,self.config,synchronize=True,epoch=4)[0]
            compose.reset_mock()
            first=self.render()[0];first[:]=0
            second=self.render()[0]
            self.assertTrue(np.array_equal(second,expected))
            self.assertEqual(compose.call_count,1)
            self.result=(np.full_like(self.frame,120),*self.result[1:])
            self.assertFalse(np.array_equal(self.render()[0],second))
            self.assertEqual(compose.call_count,2)
            self.config['feather_pixels']=0
            self.render();self.assertEqual(compose.call_count,3)
    def test_cache_cannot_survive_expiry_ended_gesture_or_epoch_change(self):
        self.render()
        for quad,time,epoch in [(None,10.,4),(self.quad,14.,4),(self.quad,10.,5)]:
            output,_,active=self.renderer.render(self.frame,quad,self.result,time,self.config,mode='exact',epoch=epoch)
            self.assertFalse(active);self.assertTrue(np.array_equal(output,self.frame))
        resized=np.zeros((40,60,3),np.uint8)
        self.assertTrue(np.array_equal(self.renderer.render(resized,self.quad,self.result,10.,self.config,mode='exact',epoch=4)[0],resized))
    def test_view_and_mode_switches_keep_correct_source(self):
        self.render()
        self.assertTrue(np.array_equal(self.render(view='anime')[0],self.result[0]))
        self.assertTrue(np.array_equal(self.render(view='split')[0][:,:60],self.result[1][:,:60]))
        self.assertTrue(np.array_equal(self.render(mode='off')[0][0,0],self.frame[0,0]))
    def test_only_off_and_exact_are_selectable_with_legacy_migration(self):
        self.assertEqual(ALIGNMENT_MODES,('off','exact'))
        self.assertEqual(alignment_mode({'alignment_mode':'smooth'}),'exact')
        self.assertEqual(alignment_mode({'synchronize_feed':True}),'exact')
        self.assertEqual(alignment_mode({}),'off')
        with self.assertRaises(ValueError): alignment_mode({'alignment_mode':'invalid'})

if __name__=='__main__': unittest.main()
