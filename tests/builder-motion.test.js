'use strict';
const assert = require('node:assert/strict');
const motion = require('../static/js/builder-motion.js');
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-8, `${a} != ${b}`);
const layer = {type:'effect',x:.2,y:.4,scale:1.2,rotation:30,opacity:.8,effectSpeed:100,effectDensity:100,lightStrength:40};
const normal = motion.effectiveLayer(layer,50);
assert.deepEqual({...normal,motionPower:undefined},{...layer,motionPower:undefined});
for (const intensity of [0,25,100]) {
  const result = motion.effectiveLayer(layer,intensity);
  for (const key of ['x','y','scale','rotation','opacity']) assert.equal(result[key],layer[key]);
}
assert.equal(layer.effectSpeed,100); // No mutations of saved baseline values.
assert.equal(motion.effectiveLayer({...layer,intensityLinked:false},100).effectSpeed,100);
assert.ok(motion.effectiveLayer(layer,100).effectDensity > normal.effectDensity);
assert.ok(motion.effectiveLayer(layer,0).lightStrength === 0);
assert.deepEqual(motion.cuts('workshop'),[.2,.4,.6,.8]);
assert.deepEqual(motion.cuts('featured'),[]);
close(motion.cuts('split')[0],506/606);
close(motion.loopClock(0,8,'pingpong'),0); close(motion.loopClock(4,8,'pingpong'),4);
close(motion.loopClock(6,8,'pingpong'),2); close(motion.loopClock(8,8,'pingpong'),0);
close(motion.loopClock(10,8,'blend'),2);
assert.equal(motion.lightPulse({effect:'lightning',effectSpeed:100},0),1);
assert.equal(motion.lightPulse({effect:'lightning',effectSpeed:100},1000),0);
const region={direction:90,strength:12};
const offset=motion.motionOffset(region,2000,8,1);close(offset.x,0);close(offset.y,12);
close(motion.motionOffset(region,8000,8,1).y,0);
close(motion.motionOffset(region,2000,8,0).y,0);
const geometry={x:100,y:200,w:80,h:160,rotation:Math.PI/2};
const point=motion.brushPoint(100,240,geometry);close(point.x,1);close(point.y,.5);
assert.equal(motion.bounded(NaN,0,1,.5),.5);assert.equal(motion.bounded(Infinity,0,1,.5),.5);
console.log('Builder motion calculations: passed');
