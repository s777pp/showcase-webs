import redis_store as rs


def test_calendar_cap_does_not_reset_at_epoch_window_boundary(monkeypatch):
    class Counter:
        def __init__(self):
            self.values = {}
        def incr(self, key):
            self.values[key] = self.values.get(key, 0) + 1
            return self.values[key]
        def expire(self, key, seconds):
            assert seconds == 32 * 86400 + 1
        def get(self, key):
            return self.values.get(key)
    counter = Counter()
    monkeypatch.setattr(rs, "_r", lambda: counter)
    window = 32 * 86400
    clock = {"now": window * 100 - 1}
    monkeypatch.setattr(rs.time, "time", lambda: clock["now"])
    assert rs.rate_limit("month:2026-09", 1, window, fixed_bucket=True) == (True, 0)
    clock["now"] += 2
    assert rs.rate_limit("month:2026-09", 1, window, fixed_bucket=True) == (False, 0)
    assert rs.rate_limit("month:2026-10", 1, window, fixed_bucket=True) == (True, 0)

    counter.values["sm:rl:existing-month:99"] = 2
    counter.values["sm:rl:existing-month:100"] = 3
    assert rs.rate_limit("existing-month", 6, window, fixed_bucket=True) == (True, 0)
    assert rs.rate_limit("existing-month", 6, window, fixed_bucket=True) == (False, 0)


def test_calendar_cap_fails_closed_when_configured_redis_is_down(monkeypatch):
    monkeypatch.setattr(rs, "_r", lambda: None)
    monkeypatch.setattr(rs, "configured", lambda: True)
    assert rs.rate_limit("month:2026-09", 50, 32 * 86400,
                         fixed_bucket=True, fail_closed=True) == (False, 0)
