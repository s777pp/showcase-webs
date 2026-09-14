"""LOCAL-ONLY browser QA: real Builder/animation router, fake auth/R2/queue/Modal.

No production users, external requests, upload credentials or GPU calls.
Run: python tests/animation_preview_server.py --port 8769
"""
import argparse
import base64
import io
import json
import re
import sys
import tempfile
import subprocess
import shutil
import time
from pathlib import Path
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PIL import Image,ImageDraw
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse,Response
from fastapi.staticfiles import StaticFiles
from smweb.routers import animation
from smweb.animation_experiment import PROTOCOL_VERSION

image=Image.new('RGBA',(400,600),(0,0,0,0));draw=ImageDraw.Draw(image)
draw.ellipse((130,40,270,180),fill='#a6eaff');draw.rounded_rectangle((100,180,300,580),radius=35,fill='#204967')
for y in range(220,560,25):draw.line((110,y,290,y),fill='#52d5ff',width=5)
buffer=io.BytesIO();image.save(buffer,format='PNG');source=buffer.getvalue()
video=b''
folder=tempfile.TemporaryDirectory(prefix='builder-ai-browser-')
if shutil.which('ffmpeg'):
    output=Path(folder.name)/'preview.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=size=384x576:rate=24','-t','1','-c:v','libx264','-pix_fmt','yuv420p',str(output)],check=True)
    video=output.read_bytes()
jobs={};uploads={};report={};memory={};delay=0
animation.os.environ.update(ANIMATION_ENABLED='1',ANIMATION_ALLOWED_EMAILS='fixture@example.com')
animation._auth_user=lambda request:{'id':123,'email':'fixture@example.com'}
animation.rs.redis_ok=lambda:True;animation.rs.worker_alive=lambda:True
animation.rs.rate_limit=lambda *args,**kwargs:(True,19)
def job_get(jid):
    job=jobs.get(jid)
    if job and time.monotonic()-job.get('queued_at',0)>=delay:
        job.update(status='done',stage='done',pct=100)
    if job and memory.get(f'sm:animation:cancel:{jid}'):
        job.update(status='cancelled',stage='cancelled',pct=100)
    return job
animation.rs.job_get=job_get
redis=Mock();redis.get.side_effect=lambda key:memory.get(key);redis.set.side_effect=lambda key,value,**kwargs:memory.update({key:value}) or True
animation.rs.get_redis=lambda:redis
animation.object_store.configured=lambda:True
animation.object_store.put_bytes=lambda key,data,**kwargs:uploads.update({key:data})
animation.object_store.presigned_get_url=lambda key,**kwargs:'https://private-fixture.invalid/source'
animation.object_store.delete=lambda key,**kwargs:uploads.pop(key,None)
storage=Mock()
storage.get_object.side_effect=lambda **kwargs:{'ContentLength':len(video),'Body':io.BytesIO(video)}
animation.object_store.client=lambda:storage
animation.reserve=lambda jid,owner:1
animation.release=lambda jid:None
def mask_result(target):
    mask=Image.new('RGBA',(256,256),(255,255,255,0));paint=ImageDraw.Draw(mask)
    boxes={'hair':(70,18,186,118),'eyes':(105,58,151,82),'cloth':(58,92,198,242),'breathing':(76,102,180,180)}
    paint.ellipse(boxes[target],fill=(255,255,255,255));output=io.BytesIO();mask.save(output,format='PNG')
    return {'target':target,'found':True,'width':256,'height':256,'png':base64.b64encode(output.getvalue()).decode(),'confidence':.91}
class AnimationFixtureClient:
    def health(self):return {'protocol_version':PROTOCOL_VERSION}
    def segment(self,payload):return {'request_id':payload['request_id'],'protocol_version':PROTOCOL_VERSION,'model':'CIDAS/clipseg-rd64-refined','masks':[mask_result(target) for target in payload['targets']]}
animation.AnimationClient=AnimationFixtureClient
def enqueue(jid,data,**kwargs):
    report.update(options=data,fail_closed=kwargs.get('fail_closed'))
    jobs[jid]={**data,'status':'queued','pct':0,'stage':'queued','motion_low':False,'queued_at':time.monotonic()}
    memory[f"sm:animation:last:{data['user_key']}"]=jid
animation.rs.job_create=enqueue
app=FastAPI();app.include_router(animation.router);app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
@app.get('/fixture.png')
def fixture():return Response(source,media_type='image/png')
@app.get('/api/builder/assets/fixture.mp4')
def asset():return Response(video,media_type='video/mp4')
@app.get('/qa/report')
def qa_report():return report
@app.get('/{language}/app')
def page(language:str):
    if language not in {'ru','en','de','tr','fr','uk','es','pt'}:language='en'
    html=(ROOT/'static/app.html').read_text(encoding='utf-8').replace('<html lang="en">',f'<html lang="{language}">')
    # Prevent external analytics/font requests in the disposable QA page.
    html=re.sub(r'<script[^>]+src="https?://[^>]+></script>','',html)
    html=re.sub(r'<link[^>]+href="https?://[^>]+>','',html)
    project={'version':1,'mode':'featured','width':630,'height':1000,'background':'#061019','layers':[{'id':'fixture-character','type':'character','src':'/fixture.png','mediaType':'image/png','name':'QA character','x':.5,'y':.5,'scale':1,'rotation':90,'opacity':1,'visible':True,'animation':'none'}]}
    bootstrap='<script>window.ShowcaseBuilder.loadProject('+json.dumps(project)+',"QA fixture");</script>'
    return HTMLResponse(html.replace('</body>',bootstrap+'</body>'))
@app.api_route('/api/{path:path}',methods=['GET','POST'])
async def mock_api(path:str,request:Request):
    if path=='auth/me':return {'ok':True,'user':{'id':123,'email':'fixture@example.com','name':'QA owner'},'is_pro':True,'pro':True,'left':100,'limit':100}
    if path=='builder/assets' and request.method=='POST':
        form=await request.form();file=form['file'];data=await file.read();report.update(applied_bytes=len(data),applied_type=file.content_type)
        return {'ok':True,'url':'/api/builder/assets/fixture.mp4','media_type':'video/mp4'}
    if path=='maintenance':return {'enabled':False,'message':''}
    return {'ok':True,'items':[],'left':100,'limit':100,'pro':True}
if __name__=='__main__':
    import uvicorn
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8769);parser.add_argument('--delay',type=int,default=0);args=parser.parse_args();delay=args.delay
    uvicorn.run(app,host='127.0.0.1',port=args.port,log_level='warning')
