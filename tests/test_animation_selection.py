import unittest
import io
import base64
from PIL import Image, ImageDraw
from pydantic import ValidationError
from smweb.animation_selection import MotionSelection, selection_mask, selection_prompts, isolate_video
from smweb.animation_experiment import prepare_image

def selection(**extra):
    return MotionSelection.model_validate({"targets":["hair"], "strokes":[{"target":"hair", "radius":.1, "points":[[.5,.5]]}], **extra})

def automatic(target="hair"):
    image=Image.new('RGBA',(32,32),(255,255,255,0));ImageDraw.Draw(image).rectangle((4,8,15,23),fill=(255,255,255,255))
    output=io.BytesIO();image.save(output,format='PNG')
    return {'target':target,'width':32,'height':32,'png':base64.b64encode(output.getvalue()).decode(),'confidence':.87}

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

    def test_automatic_mask_can_replace_and_combine_with_brush(self):
        data=selection(strokes=[],auto_masks=[automatic()],feather=0)
        mask=selection_mask(data,(100,100),feather=False)
        self.assertIsNotNone(mask.getbbox())
        self.assertGreater(mask.getpixel((20,50)),0)
        self.assertEqual(mask.getpixel((90,90)),0)
        positive,_=selection_prompts(data,'normal')
        self.assertIn('left middle area',positive)

    def test_automatic_masks_are_bounded_and_target_matched(self):
        invalid=automatic();invalid['png']=base64.b64encode(b'not png').decode()
        for masks,targets in [([invalid],['hair']),([automatic('cloth')],['hair']),
                              ([automatic(),automatic()],['hair'])]:
            with self.assertRaises(ValidationError):
                selection(strokes=[],targets=targets,auto_masks=masks)

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
