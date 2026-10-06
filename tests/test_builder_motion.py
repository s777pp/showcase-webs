import math
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import processor
from smweb import loop_jobs
from smweb.routers.builder import _validated_project
from smweb.routers import seamless_loop as loop_api
from fastapi import FastAPI
from fastapi.testclient import TestClient


class BuilderMotionTests(unittest.TestCase):
    def test_shared_browser_calculations(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is not installed')
        subprocess.run([node, str(Path(__file__).with_name('builder-motion.test.js'))], check=True, capture_output=True)

    def test_motion_fields_roundtrip_and_are_bounded(self):
        project = _validated_project({'mode':'split', 'motion':{'intensity':999, 'loop':'blend', 'duration':8, 'fade':.5, 'seams':True}, 'layers':[
            {'type':'effect','effect':'lightning','depth':'mixed','depthAmount':60,'sceneLight':True,'lightColor':'#aabbcc','lightRadius':90,'lightStrength':40,'intensityLinked':False,'protectedArea':{'x':.8,'y':.2,'w':.5,'h':.3}},
            {'type':'character','src':'/api/builder/assets/example','localMotion':{'direction':90,'strength':8,'strokes':[{'radius':.05,'points':[[.3,.4],[.4,.5]],'erase':False}],'pins':[{'x':.5,'y':.5,'radius':.05}]}}
        ]})
        self.assertEqual(project['motion']['intensity'],100)
        self.assertEqual(project['motion']['loop'],'blend')
        effect, character = project['layers']
        self.assertEqual(effect['depth'],'mixed')
        self.assertFalse(effect['intensityLinked'])
        self.assertEqual(effect['lightColor'],'#aabbcc')
        self.assertAlmostEqual(effect['protectedArea']['w'],.2)
        self.assertEqual(character['localMotion']['strokes'][0]['points'],[[.3,.4],[.4,.5]])

    def test_invalid_and_nonfinite_motion_is_sanitized(self):
        project = _validated_project({'motion':{'intensity':math.nan,'loop':'script','fade':math.inf},'layers':[
            {'type':'effect','scale':math.inf,'opacity':math.nan,'depth':'script','lightColor':'javascript:bad','sceneLight':'false'},
            {'type':'text','localMotion':{'strokes':[]}}
        ]})
        self.assertEqual(project['motion'],{'intensity':50,'loop':'none','duration':8,'fade':.5,'seams':False})
        self.assertEqual(project['layers'][0]['scale'],1)
        self.assertEqual(project['layers'][0]['depth'],'flat')
        self.assertFalse(project['layers'][0]['sceneLight'])
        self.assertNotIn('localMotion',project['layers'][1])

    def test_brush_complexity_is_bounded(self):
        for region in ({'strokes':[{}]*81},{'strokes':[{'points':[[0,0]]*401}]},{'pins':[{}]*33},{'strokes':[{'points':[[0,0,0]]}]}):
            with self.assertRaises(ValueError):
                _validated_project({'layers':[{'type':'character','localMotion':region}]})

    def test_sequence_join_has_no_duplicate_turnaround_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);frames=[]
            for i in range(12):
                frame=root/f'raw_{i}.png';Image.new('RGB',(8,8),(i*20,0,0)).save(frame);frames.append(frame)
            count,_seam=loop_jobs._build_sequence(frames,root/'back','pingpong',2)
            values=[Image.open(p).getpixel((0,0))[0] for p in sorted((root/'back').glob('*.png'))]
            self.assertEqual(count,22)
            self.assertEqual(values,[i*20 for i in range(12)]+[i*20 for i in range(10,0,-1)])
            _count,seam=loop_jobs._build_sequence(frames,root/'fade','blend',3,want=8,preroll=3)
            values=[Image.open(p).getpixel((0,0))[0] for p in sorted((root/'fade').glob('*.png'))]
            # A ramp never repeats, so the end fades into the frames just before
            # the loop start and the jump back is no bigger than one normal step.
            self.assertEqual(seam,'crossfade')
            self.assertLessEqual(abs(values[0]-values[-1]),25)

    def test_true_loop_finds_the_natural_period_without_blending(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);frames=[]
            shades=[round(120+80*math.sin(2*math.pi*k/10)) for k in range(10)]
            for i in range(30):  # a smooth scene that repeats every 10 frames
                frame=root/f'raw_{i}.png';Image.new('RGB',(32,32),(shades[i%10],0,0)).save(frame);frames.append(frame)
            count,seam=loop_jobs._build_sequence(frames,root/'loop','blend',3,want=9,preroll=2)
            values=[Image.open(p).getpixel((0,0))[0] for p in sorted((root/'loop').glob('*.png'))]
            self.assertEqual(seam,'exact')
            self.assertEqual(count,10)
            self.assertEqual(sorted(values),sorted(shades))


class LoopEncoderSmokeTests(unittest.TestCase):
    def test_real_gif_and_mp4_export_for_both_loop_methods(self):
        if not processor.find_ffmpeg() or not processor.find_ffprobe():
            self.skipTest('FFmpeg/FFprobe are not installed')
        with tempfile.TemporaryDirectory() as folder:
            for mode in ('blend','pingpong'):
                for output_format in ('gif','mp4'):
                    for source_format in ('gif','mp4'):
                        with self.subTest(mode=mode, output=output_format, source=source_format):
                            self._render_case(Path(folder),mode,output_format,source_format)

    def _render_case(self, folder, mode, output_format, source_format):
        root=folder/f'{mode}-{output_format}-{source_format}';root.mkdir()
        source=root/'source.gif'
        frames=[Image.new('RGB',(64,48),(i*10,80,180)) for i in range(24)]
        frames[0].save(source,save_all=True,append_images=frames[1:],duration=80,loop=0)
        if source_format=='mp4':
            video=root/'source.mp4'
            loop_jobs._run_cmd([processor.find_ffmpeg(),'-y','-i',str(source),'-an','-c:v','libx264','-pix_fmt','yuv420p',str(video)])
            source=video
        updates=[]
        with patch.object(loop_jobs.rs,'job_update',side_effect=lambda jid,**kw:updates.append(kw)),patch.object(loop_jobs.object_store,'configured',return_value=False):
            loop_jobs.run('test',{'job_dir':str(root),'source_path':str(source),'fps':12,'duration':1.5,'transition':.25,'mode':mode,'output_format':output_format})
        self.assertEqual(updates[-1]['status'],'done',updates[-1])
        result=Path(updates[-1]['result_path']);self.assertGreater(result.stat().st_size,100)
        self.assertLessEqual(updates[-1]['output_duration'],8)
        if output_format=='gif':
            with Image.open(result) as image:self.assertGreater(image.n_frames,1)
            self.assertLessEqual(result.stat().st_size,5*1024*1024)


class LoopModeApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.app=FastAPI();self.app.include_router(loop_api.router)
        self.client=TestClient(self.app)
        self.patches=[patch.object(loop_api,'DATA',self.temp.name),patch.object(loop_api,'_auth_user',return_value={'id':1}),
                      patch.object(loop_api.auth_db,'effective_pro',return_value=True),
                      patch.object(loop_api.rs,'job_count_user',return_value=0),patch.object(loop_api.rs,'rate_limit',return_value=(True,0)),
                      patch.object(loop_api,'_worker_mode',return_value='external'),patch.object(loop_api.rs,'redis_ok',return_value=True),
                      patch.object(loop_api.rs,'worker_alive',return_value=True),patch.object(loop_api.rs,'job_create')]
        self.mocks=[p.start() for p in self.patches]

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.client.close();self.temp.cleanup()

    def test_both_modes_are_preserved_in_worker_payload(self):
        for mode in ('blend','pingpong'):
            response=self.client.post('/api/loop/start',files={'file':('source.gif',b'GIF89a'+b'x'*30,'image/gif')},data={'mode':mode,'transition':'.75','duration':'8'})
            self.assertEqual(response.status_code,202)
            payload=self.mocks[-1].call_args.args[1]
            self.assertEqual(payload['mode'],mode)
            self.assertEqual(payload['transition'],.75)

    def test_invalid_modes_and_nonfinite_numbers_are_rejected(self):
        for options in ({'mode':'script'},{'mode':'blend','transition':'nan'},{'mode':'blend','start':'inf'}):
            response=self.client.post('/api/loop/start',files={'file':('source.gif',b'GIF89a'+b'x'*30,'image/gif')},data=options)
            self.assertEqual(response.status_code,400)
        self.mocks[-1].assert_not_called()

    def test_free_account_without_a_weekly_use_left_is_refused(self):
        # Since 2026-10-06 a Free account gets one loop a week (smweb/free_limits.py); a spent one is still a wall.
        self.mocks[2].return_value=False
        with patch.object(loop_api.free_limits,'left',return_value=0):
            response=self.client.post('/api/loop/start',files={'file':('source.gif',b'GIF89a'+b'x'*30,'image/gif')},data={'mode':'blend'})
        self.assertEqual(response.status_code,429)
        self.assertEqual(response.json()['code'],'weekly_limit')
        self.mocks[-1].assert_not_called()

    def test_free_account_spends_its_weekly_use_on_a_loop(self):
        self.mocks[2].return_value=False
        with patch.object(loop_api.free_limits,'left',return_value=1),patch.object(loop_api.free_limits,'consume',return_value=True) as consume:
            response=self.client.post('/api/loop/start',files={'file':('source.gif',b'GIF89a'+b'x'*30,'image/gif')},data={'mode':'blend'})
        self.assertEqual(response.status_code,202)
        consume.assert_called_once()
        self.assertEqual(self.mocks[-1].call_args.args[1]['free_try']['feature'],'loop')


if __name__=='__main__':unittest.main()


def test_asset_upload_accepts_a_steam_patched_gif(tmp_path, monkeypatch):
    # A GIF this site prepared for Steam ends with 0x21 (HEX 21); Pillow raised IndexError (prod 500, 2026-10-02)
    import io
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from PIL import Image
    from smweb import object_store
    from smweb.routers import builder

    frames = [Image.new("RGB", (8, 8), c) for c in ((255, 0, 0), (0, 0, 255))]
    buf = io.BytesIO()
    frames[0].save(buf, "GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    patched = buf.getvalue()[:-1] + b"!"
    monkeypatch.setattr(builder, "_user", lambda request: ({"id": 7}, None))
    monkeypatch.setattr(object_store, "configured", lambda: False)
    monkeypatch.setattr(builder, "_local_asset_path", lambda rel: tmp_path / rel)
    app = FastAPI()
    app.include_router(builder.router)
    res = TestClient(app).post("/api/builder/assets", files={"file": ("steam.gif", patched, "image/gif")})
    assert res.status_code == 200 and res.json()["animated"] is True
    broken = TestClient(app).post("/api/builder/assets", files={"file": ("bad.gif", b"GIF89a" + b"\0" * 20, "image/gif")})
    assert broken.status_code == 400
