(function (root) {
  'use strict';
  var ranges = { brightness:[50,150,100], contrast:[50,150,100], saturation:[0,200,100], hue:[-180,180,0] };
  function normalize(value) {
    var source = value && typeof value === 'object' ? value : {}, result = {};
    Object.keys(ranges).forEach(function (key) {
      var range = ranges[key], number = Number(source[key]);
      result[key] = Number.isFinite(number) ? Math.max(range[0], Math.min(range[1], Math.round(number))) : range[2];
    });
    return result;
  }
  function filter(value) {
    var grade = normalize(value);
    return 'brightness(' + grade.brightness + '%) contrast(' + grade.contrast + '%) saturate(' + grade.saturation + '%) hue-rotate(' + grade.hue + 'deg)';
  }
  var api = { ranges:ranges, normalize:normalize, filter:filter };
  root.SMColorGrade = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
