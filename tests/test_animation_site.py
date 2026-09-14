import io
import json
import unittest
from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from smweb.routers import animation as api
from smweb import animation_jobs as runner
from smweb.animation_experiment import keys, PROTOCOL_VERSION

def png():
    output=io.BytesIO();Image.new('RGB',(128,128),'red').save(output,format='PNG');return output.getvalue()
def options():
    return {'selection':{'targets':['hair'],'strokes':[{'target':'hair','radius':.1,'points':[[.5,.5]]}]}}

class SiteTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI();app.include_router(api.router);self.client=TestClient(app)
        self.user={'id':123,'email':'OWNER@example.com'}
        self.patches=[patch.dict('os.environ',{'ANIMATION_ENABLED':'1','ANIMATION_ALLOWED_EMAILS':'owner@example.com'}),patch.object(api,'_auth_user',return_value=self.user)]
        for p in self.patches:p.start();self.addCleanup(p.stop)

    def start(self,**kwargs):
        return self.client.post('/api/animation/start',files={'file':('image.png',kwargs.pop('raw',png()),'image/png')},data={'options':json.dumps(kwargs.pop('options',options())),'confirm_cost':kwargs.pop('consent','yes'),'request_id':kwargs.pop('request_id','')})

    def services(self,admission=1):
        client=Mock();client.health.return_value={'protocol_version':PROTOCOL_VERSION}
        mocks=[patch.object(api.object_store,'configured',return_value=True),patch.object(api.rs,'redis_ok',return_value=True),patch.object(api.rs,'worker_alive',return_value=True),patch.object(api,'AnimationClient',return_value=client),patch.object(api,'reserve',return_value=admission),patch.object(api.object_store,'put_bytes'),patch.object(api.rs,'job_create'),patch.object(api.rs,'job_get',return_value=None)]
        for p in mocks:p.start();self.addCleanup(p.stop)
        return client

    def test_config_off_by_default_no_identity_disclosure(self):
        with patch.dict('os.environ',{'ANIMATION_ENABLED':'0'}):
            self.assertEqual(self.client.get('/api/animation/config').json(),{'enabled':False,'user_id':None,'job_id':None})

    def test_unauthenticated_and_unlisted_pro_cannot_run(self):
        for user in [None,{'id':456,'email':'stranger@example.com','is_pro':True}]:
            with patch.object(api,'_auth_user',return_value=user),patch.object(api,'AnimationClient') as client:
                self.assertEqual(self.start().status_code,403);client.assert_not_called()

    def test_consent_and_static_file_validation_before_network(self):
        with patch.object(api,'AnimationClient') as client:
            self.assertEqual(self.start(consent='').status_code,400)
            self.assertEqual(self.start(raw=b'not an image').status_code,400)
            output=io.BytesIO();Image.new('RGB',(128,128)).save(output,format='GIF')
            self.assertEqual(self.start(raw=output.getvalue()).status_code,400)
            data=options();data['selection']['strokes'].append({**data['selection']['strokes'][0],'erase':True})
            self.assertEqual(self.start(options=data).status_code,400)
            client.assert_not_called()

    def test_prompt_has_no_gpu_submission(self):
        with patch.object(api,'AnimationClient') as client:
            response=self.client.post('/api/animation/prompt',json=options())
            self.assertEqual(response.status_code,200);self.assertIn('hair strands',response.json()['prompt']);client.assert_not_called()

    def test_same_request_replay_never_enqueues_or_pays_twice(self):
        remote=self.services();jid='a'*32
        self.assertEqual(self.start(request_id=jid).json()['job_id'],jid)
        saved=api.rs.job_create.call_args.args[1]
        api.rs.job_get.return_value=saved
        self.assertEqual(self.start(request_id=jid).json()['job_id'],jid)
        api.rs.job_create.assert_called_once();api.reserve.assert_called_once();remote.health.assert_called_once()
        changed=options();changed['intensity']='strong'
        self.assertEqual(self.start(request_id=jid,options=changed).status_code,409)
        api.rs.job_get.return_value={**saved,'user_key':'456'}
        self.assertEqual(self.start(request_id=jid).status_code,404)

    def test_last_task_discovery_is_owner_bound(self):
        r=Mock();r.get.return_value='a'*32
        with patch.object(api.rs,'get_redis',return_value=r),patch.object(api.rs,'job_get',return_value={'kind':'ai_animation','user_key':'123'}):
            self.assertEqual(self.client.get('/api/animation/config').json()['job_id'],'a'*32)
        with patch.object(api.rs,'get_redis',return_value=r),patch.object(api.rs,'job_get',return_value={'kind':'ai_animation','user_key':'456'}):
            self.assertIsNone(self.client.get('/api/animation/config').json()['job_id'])

    def test_start_only_enqueues_strict_private_job(self):
        remote=self.services()
        response=self.start();self.assertEqual(response.status_code,202)
        jid=response.json()['job_id'];args=api.rs.job_create.call_args
        self.assertEqual(args.args[1]['user_key'],'123')
        self.assertEqual(args.args[1]['kind'],'ai_animation')
        self.assertTrue(args.kwargs['fail_closed'])
        self.assertEqual(args.args[1]['source_key'],keys(jid)[0])
        self.assertNotIn('source_url',response.text)
        remote.submit.assert_not_called()

    def test_busy_daily_cap_and_protocol(self):
        remote=self.services(admission=0)
        self.assertEqual(self.start().json()['error'],'busy')
        with patch.object(api,'reserve',return_value=-1):self.assertEqual(self.start().json()['error'],'daily_limit')
        remote.health.return_value={'protocol_version':2}
        self.assertEqual(self.start().json()['error'],'update_modal')
        api.rs.job_create.assert_not_called()

    def test_ambiguous_queue_returns_only_own_resumable_id(self):
        self.services();api.rs.job_create.side_effect=RuntimeError('private secret URL')
        response=self.start();self.assertEqual(response.status_code,503)
        self.assertEqual(response.json()['error'],'outcome_unknown')
        self.assertEqual(len(response.json()['job_id']),32)
        self.assertNotIn('private secret',response.text)

    def test_status_and_download_are_owner_bound(self):
        jid='a'*32
        for job in [None,{'kind':'upscale','user_key':'123'}, {'kind':'ai_animation','user_key':'456'}]:
            with patch.object(api.rs,'job_get',return_value=job):
                self.assertEqual(self.client.get('/api/animation/status/'+jid).status_code,404)
                self.assertEqual(self.client.get('/api/animation/download/'+jid).status_code,404)
        job={'kind':'ai_animation','user_key':'123','status':'done','result_key':keys(jid)[1],'secret':'not returned'}
        body=io.BytesIO(b'mp4-fixture');storage=Mock();storage.get_object.return_value={'ContentLength':11,'Body':body}
        with patch.object(api.rs,'job_get',return_value=job),patch.object(api.object_store,'client',return_value=storage):
            self.assertNotIn('secret',self.client.get('/api/animation/status/'+jid).text)
            response=self.client.get('/api/animation/download/'+jid)
            self.assertEqual(response.content,b'mp4-fixture');self.assertTrue(body.closed)

    def test_cancel_does_not_spawn_gpu(self):
        jid='a'*32;r=Mock()
        with patch.object(api.rs,'job_get',return_value={'kind':'ai_animation','user_key':'123','status':'queued'}),patch.object(api.rs,'get_redis',return_value=r),patch.object(api,'AnimationClient') as remote:
            self.assertEqual(self.client.post('/api/animation/cancel/'+jid).json()['status'],'cancel_pending')
            self.assertEqual(r.set.call_args.args[0],'sm:animation:cancel:'+jid);remote.assert_not_called()

    def test_range_preview_and_malformed_ranges(self):
        jid='a'*32;job={'kind':'ai_animation','user_key':'123','status':'done'}
        storage=Mock();storage.get_object.return_value={'ContentLength':4,'ContentRange':'bytes 2-5/10','Body':io.BytesIO(b'part')}
        with patch.object(api.rs,'job_get',return_value=job),patch.object(api.object_store,'client',return_value=storage):
            response=self.client.get('/api/animation/download/'+jid,headers={'Range':'bytes=2-5'})
            self.assertEqual(response.status_code,206);self.assertEqual(response.content,b'part')
            self.assertEqual(storage.get_object.call_args.kwargs['Range'],'bytes=2-5')
            self.assertEqual(response.headers['content-range'],'bytes 2-5/10')
            for value in ['bytes=5-2','bytes=-0','bytes=0-5,6-9','bytes=999999999-']:
                self.assertEqual(self.client.get('/api/animation/download/'+jid,headers={'Range':value}).status_code,416)

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.jid='a'*32;self.job={'source_key':keys(self.jid)[0],'result_key':keys(self.jid)[1],**api.Options.model_validate(options()).model_dump()}
        self.redis=Mock();self.redis.set.return_value=True
        self.remote=Mock();self.remote.health.return_value={'protocol_version':PROTOCOL_VERSION}
        self.remote.result.return_value=(True,{'status':'done','bytes':100,'width':128,'height':128,'motion':{'status':'motion_detected'}})
        storage=Mock();storage.head_object.return_value={'ContentLength':100}
        patches=[patch.object(runner.rs,'get_redis',return_value=self.redis),patch.object(runner.rs,'redis_ok',return_value=True),patch.object(runner.rs,'job_update'),patch.object(runner,'cancelled',return_value=False),patch.object(runner,'AnimationClient',return_value=self.remote),patch.object(runner.object_store,'client',return_value=storage),patch.object(runner.object_store,'presigned_get_url',return_value='private fixture get'),patch.object(runner.object_store,'presigned_put_url',return_value='private fixture put'),patch.object(runner.object_store,'delete'),patch.object(runner,'release')]
        for p in patches:p.start();self.addCleanup(p.stop)

    def test_done_matches_actual_modal_contract(self):
        runner.run(self.jid,self.job)
        self.remote.submit.assert_called_once()
        self.assertEqual(runner.rs.job_update.call_args.kwargs['status'],'done')
        runner.release.assert_called_once_with(self.jid)

    def test_worker_replay_polls_without_resubmission(self):
        self.redis.set.return_value=False
        runner.run(self.jid,self.job)
        self.remote.submit.assert_not_called();self.remote.result.assert_called_once_with(self.jid)

    def test_uncertain_submission_never_retries_and_retains_guard(self):
        self.remote.submit.side_effect=RuntimeError('secret signed URL')
        self.remote.result.side_effect=RuntimeError('secret signed URL')
        runner.run(self.jid,self.job)
        self.remote.submit.assert_called_once()
        runner.release.assert_not_called();runner.object_store.delete.assert_not_called()
        self.assertEqual(runner.rs.job_update.call_args.kwargs['error'],'outcome_unknown')

    def test_cancel_before_submission_is_free(self):
        with patch.object(runner,'cancelled',return_value=True):runner.run(self.jid,self.job)
        self.remote.submit.assert_not_called()
        self.assertEqual(runner.rs.job_update.call_args.kwargs['status'],'cancelled')

    def test_changed_protocol_blocks_gpu(self):
        self.remote.health.return_value={'protocol_version':2}
        runner.run(self.jid,self.job)
        self.remote.submit.assert_not_called();runner.release.assert_called_once()

    def test_cleanup_error_never_escapes_into_worker_traceback(self):
        runner.object_store.delete.side_effect=RuntimeError('secret signed URL')
        runner.run(self.jid,self.job)
        self.assertEqual(runner.rs.job_update.call_args.kwargs['status'],'done')
        runner.release.assert_called_once()

    def test_transient_poll_failure_recovers_without_paid_retry(self):
        from smweb.modal_animation_client import AnimationServiceError
        completed=self.remote.result.return_value
        self.remote.result.side_effect=[AnimationServiceError('unavailable'),completed]
        with patch.object(runner.time,'sleep'):
            runner.run(self.jid,self.job)
        self.remote.submit.assert_called_once();self.assertEqual(self.remote.result.call_count,2)
        self.assertEqual(runner.rs.job_update.call_args.kwargs['status'],'done')

if __name__=='__main__':unittest.main()
