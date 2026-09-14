import unittest
import io
from PIL import Image
from pydantic import ValidationError
from smweb.animation_selection import MotionSelection, selection_mask, selection_prompts, isolate_video
from smweb.animation_experiment import prepare_image

def selection(**extra):
    return MotionSelection.model_validate({"targets":["hair"], "strokes":[{"target":"hair", "radius":.1, "points":[[.5,.5]]}], **extra})

class SelectionTests(unittest.TestCase):
    def test_canonical_wide_canvas_never_refits_or_moves_mask(self):
        output=io.BytesIO();Image.new('RGB',(1280,416),'red').save(output,format='PNG')
        image=prepare_image(output.getvalue(),canonical=True)
        self.assertEqual(image.size,(1280,416))
        with self.assertRaises(ValueError):
            prepare_image(output.getvalue())
        output=io.BytesIO();Image.new('RGB',(1290,704)).save(output,format='PNG')
        with self.assertRaises(ValueError):prepare_image(output.getvalue(),canonical=True)
    def test_outside_is_original_inside_is_generated(self):
        original=Image.new('RGB',(100,100),'red')
        frames=isolate_video([Image.new('RGB',(100,100),'blue')],original,selection(feather=0))
        self.assertEqual(frames[0].getpixel((0,0)),(255,0,0))
        self.assertEqual(frames[0].getpixel((50,50)),(0,0,255))
        self.assertEqual(original.getpixel((50,50)),(255,0,0))

    def test_brush_uses_short_side(self):
        for size in [(100,300),(300,100)]:
            mask=selection_mask(selection(feather=0),size)
            box=mask.getbbox()
            self.assertEqual(box[2]-box[0],21)
            self.assertEqual(box[3]-box[1],21)

    def test_empty_erased_mask_is_detectable(self):
        data=selection().model_dump()
        data['strokes'].append({**data['strokes'][0],'erase':True})
        mask=selection_mask(MotionSelection.model_validate(data),(100,100))
        self.assertIsNone(mask.getbbox())
        with self.assertRaises(ValueError):
            isolate_video([Image.new('RGB',(100,100))],Image.new('RGB',(100,100)),MotionSelection.model_validate(data))

    def test_no_mask_requires_explicit_whole_image_permission(self):
        with self.assertRaises(ValidationError):
            selection(strokes=[])
        data=selection(strokes=[],lock_outside=False)
        frames=[Image.new('RGB',(100,100),'blue')]
        self.assertIs(isolate_video(frames,Image.new('RGB',(100,100),'red'),data),frames)

    def test_invalid_coordinates_and_limits(self):
        for point in [[float('nan'),.5],[float('inf'),.5],[-.1,.5],[.5,1.1],[.2]]:
            with self.assertRaises(ValidationError):
                selection(strokes=[{'target':'hair','radius':.1,'points':[point]}])
        with self.assertRaises(ValidationError):
            selection(strokes=[{'target':'hair','radius':.16,'points':[[.5,.5]]}])
        with self.assertRaises(ValidationError):
            selection(targets=['hair','hair'])
        with self.assertRaises(ValidationError):
            selection(targets=['water'])

    def test_prompts_are_targeted_not_everything_at_once(self):
        positive,negative=selection_prompts(selection(),'normal')
        self.assertIn('free hair tips',positive)
        self.assertIn('central',positive)
        self.assertIn('locked animation cel',positive)
        self.assertIn("head, neck, torso, shoulders, arms, hands, waist, hips and legs",positive)
        self.assertNotIn('shirt shading',positive)
        self.assertIn('blinking',negative)
        self.assertIn('full-body animation',negative)
        self.assertIn('moving hair roots',negative)
        data=selection(targets=['breathing'],strokes=[{'target':'breathing','radius':.1,'points':[[.5,.6]]}])
        positive,negative=selection_prompts(data,'gentle')
        self.assertIn('shirt shading',positive)
        self.assertIn('Do not lift, lower, translate or reshape the chest',positive)
        self.assertIn('torso movement',negative)

    def test_custom_requires_description(self):
        with self.assertRaises(ValidationError):
            selection(targets=['custom'],strokes=[],lock_outside=False)
        positive,_=selection_prompts(selection(targets=['custom'],strokes=[],lock_outside=False,description='Rotate the wheel slowly.'),'normal')
        self.assertIn('Rotate the wheel slowly',positive)
        self.assertIn('cannot override the locked character rig',positive)

    def test_output_size_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            isolate_video([Image.new('RGB',(200,100))],Image.new('RGB',(100,100)),selection())

    def test_float_frames_supported(self):
        import numpy as np
        frames=isolate_video([np.ones((100,100,3),dtype=np.float32)],Image.new('RGB',(100,100),'black'),selection(feather=0))
        self.assertEqual(frames[0].getpixel((50,50)),(255,255,255))

if __name__=='__main__':unittest.main()
