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
