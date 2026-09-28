import math

import processor


def _curve(base, slope):
    return lambda q: int(base * math.exp(slope * (q - 100)))


def test_predictive_search_matches_exhaustive_and_is_cheap():
    limit = 5 * 1024 * 1024
    for base, slope in ((18e6, .037), (9e6, .03), (40e6, .05), (6e6, .02), (80e6, .045)):
        size = _curve(base, slope)
        probes = []
        best = processor._best_quality(lambda q: probes.append(q) or size(q), limit)
        exhaustive = max(q for q in range(1, 101) if size(q) <= limit)
        # Stops once within 6 % of the limit, i.e. at most a couple of quality steps lower.
        assert exhaustive - 3 <= best <= exhaustive
        assert size(best) <= limit
        assert len(probes) <= 5, (base, slope, probes)


def test_nothing_fits_returns_zero():
    assert processor._best_quality(lambda q: 10 ** 9, 1000) == 0
