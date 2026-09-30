"""Route rate limits: the first matching prefix decides the bucket."""
from smweb.middleware import RateLimitMiddleware


def _rule(path: str):
    return next((prefix for prefix, _limit, _window in RateLimitMiddleware.RULES if path.startswith(prefix)), None)


def test_specific_process_routes_get_their_own_bucket():
    assert _rule("/api/process/start") == "/api/process/start"
    assert _rule("/api/process/profile-preview/" + "a" * 32) == "/api/process/profile-preview/"
    assert _rule("/api/process") == "/api/process"


def test_expensive_routes_are_limited():
    for path in ("/api/workshop-studio/start", "/api/upscale/start", "/api/loop/preview",
                 "/api/loop/start", "/api/compose/start", "/api/preview/" + "b" * 32 + "/share"):
        assert _rule(path) is not None, path


def test_no_rule_is_shadowed_by_an_earlier_prefix():
    prefixes = [prefix for prefix, _limit, _window in RateLimitMiddleware.RULES]
    for index, prefix in enumerate(prefixes):
        earlier = [other for other in prefixes[:index] if prefix.startswith(other)]
        assert not earlier, f"{prefix} is unreachable behind {earlier}"
