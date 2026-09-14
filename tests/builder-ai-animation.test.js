const assert=require('node:assert/strict');
const ai=require('../static/js/builder-ai-animation.js');
for(const [w,h] of [[128,128],[768,1152],[1280,704],[600,1800],[1800,600]]){
  const size=ai.canvasSize(w,h);assert.equal(size.w%32,0);assert.equal(size.h%32,0);assert.ok(Math.max(size.w,size.h)<=1280);assert.ok(size.w*size.h<=1280*704);
}
assert.deepEqual(ai.point({clientX:20,clientY:50},{left:0,top:0,width:100,height:100}),[.2,.5]);
assert.deepEqual(ai.point({clientX:-10,clientY:999},{left:0,top:0,width:100,height:100}),[0,1]);
assert.ok(ai.eligible({type:'character',src:'source',mediaType:'image/png',rotation:90}));
assert.ok(!ai.eligible({type:'character',src:'source',mediaType:'video/mp4'}));
assert.ok(!ai.eligible({type:'character',src:'source',mediaType:'image/gif'}));
assert.ok(!ai.eligible({type:'character',src:'source',locked:true}));
console.log('Builder AI coordinate/eligibility tests passed.');
const jid='a'.repeat(32),older='b'.repeat(32),original={id:'layer',src:'fixture'};
assert.equal(ai.recovery({job_id:jid},null).job,jid);
assert.equal(ai.recovery({job_id:jid},{dismissed:jid}).job,'');
assert.deepEqual(ai.recovery({job_id:jid},{job:jid,original,started:42}).original,original);
assert.equal(ai.recovery({job_id:jid},{job:older,original}).job,older);
assert.equal(ai.recovery({job_id:jid},{dismissed:older}).original,null);
assert.equal(ai.recovery({job_id:'invalid'},null).job,'');
console.log('Builder AI task recovery tests passed.');
