import time
from unittest.mock import patch

import redis_store as rs
from smweb.routers import process


class FakeRedis:
    def __init__(self):
        self.lists = {}

    def lpush(self, key, value):
        self.lists.setdefault(key, []).insert(0, value)

    def ltrim(self, key, start, end):
        self.lists[key] = self.lists.get(key, [])[start:end + 1]

    def lrange(self, key, start, end):
        items = self.lists.get(key, [])
        return items[start:] if end == -1 else items[start:end + 1]


def test_queue_position_and_eta():
    fake = FakeRedis()
    with patch.object(rs, "_r", return_value=fake), patch.dict("os.environ", {"MAX_JOB_WORKERS": "2"}):
        for jid in ("a", "b", "c", "d"):  # "a" was queued first, so it is picked first
            fake.lpush(rs.JOB_QUEUE, jid)
        assert rs.queue_ahead("a") == 0
        assert rs.queue_ahead("d") == 3
        assert rs.queue_ahead("missing") is None
        assert rs.eta_typical("process") is None  # fewer than three samples
        for seconds in (40, 50, 45):
            rs.eta_record("process", seconds)
        assert rs.eta_typical("process") == 45
        queued = process._process_eta("d", {"status": "queued"})
        assert queued == {"queue_ahead": 3, "eta_seconds": 90}  # two workers: one round ahead + own
        running = process._process_eta("x", {"status": "running", "started": time.time() - 20})
        assert 24 <= running["eta_seconds"] <= 25
        assert process._process_eta("x", {"status": "done"}) == {}


def test_eta_per_kind_and_unit():
    """GIF / video jobs must not inherit the picture timings (owner: "5 s left, then 30 s more")."""
    from smweb import jobs
    fake = FakeRedis()
    with patch.object(rs, "_r", return_value=fake):
        # No history yet: built-in per-unit defaults, scaled by files x showcase types.
        motion = {"status": "running", "started": time.time() - 10, "eta_kind": "motion-max", "eta_units": 2}
        out = process._process_eta("x", motion)
        assert 69 <= out["eta_seconds"] <= 70          # 2 units x 40 s - 10 s
        assert 12 <= out["pct_time"] <= 13
        # Picture timings recorded for the generic key do not shorten the motion estimate.
        for seconds in (1, 1, 2):
            rs.eta_record("process", seconds)
        assert process._process_eta("x", motion)["eta_seconds"] >= 69
        # Own history per unit wins over the default.
        for seconds in (20, 22, 24):
            rs.eta_record("process:motion-max", seconds)
        assert 33 <= process._process_eta("x", motion)["eta_seconds"] <= 34   # 2 x 22 - 10
        # Past the estimate: "almost done", never a frozen small number.
        late = dict(motion, started=time.time() - 100)
        out = process._process_eta("x", late)
        assert out.get("eta_over") is True and "eta_seconds" not in out and out["pct_time"] == 95.0
    assert jobs.process_eta_kind([("a.png", b""), ("b.JPG", b"")], {}) == "still"
    assert jobs.process_eta_kind([("a.png", b"")], {}, animated_frame=True) == "motion-max"
    assert jobs.process_eta_kind([("a.gif", b"")], {"encode_profile": "standard"}) == "motion-standard"
    assert jobs.process_eta_kind([("clip.mp4", b"")], {"encode_profile": "weird"}) == "motion-max"
