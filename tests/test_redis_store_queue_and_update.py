"""job_update merges atomically (retrying on conflict) and queue_pop serves several queues."""
import json

import pytest
from redis.exceptions import WatchError

import redis_store as rs


class FakePipeline:
    def __init__(self, store, conflicts):
        self.store, self.conflicts = store, conflicts
        self.ops = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def watch(self, key):
        self.key = key

    def get(self, key):
        return self.store.data.get(key)

    def multi(self):
        pass

    def set(self, key, value, ex=None):
        self.ops.append(("set", key, value))

    def sadd(self, key, value):
        self.ops.append(("sadd", key, value))

    def expire(self, key, seconds):
        self.ops.append(("expire", key, seconds))

    def execute(self):
        if self.store.conflicts:
            self.store.conflicts -= 1
            # Another client changes the job between our read and EXEC.
            other = json.loads(self.store.data[self.key])
            other["cancel_requested"] = True
            self.store.data[self.key] = json.dumps(other)
            raise WatchError()
        for op in self.ops:
            if op[0] == "set":
                self.store.data[op[1]] = op[2]
            elif op[0] == "sadd":
                self.store.sets.setdefault(op[1], set()).add(op[2])


class FakeRedis:
    def __init__(self, conflicts=0):
        self.data, self.sets, self.conflicts = {}, {}, conflicts
        self.popped = []
        self.queue_items = {}

    def pipeline(self):
        return FakePipeline(self, self.conflicts)

    def brpop(self, keys, timeout=0):
        self.popped.append(list(keys))
        for key in keys:
            if self.queue_items.get(key):
                return key, self.queue_items[key].pop()
        return None


@pytest.fixture
def fake(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(rs, "_r", lambda: client)
    return client


def test_job_update_merges_fields_and_tracks_user(fake):
    key = rs.JOB_KEY.format("j1")
    fake.data[key] = json.dumps({"status": "queued", "user_key": "7", "pct": 1})
    rs.job_update("j1", pct=50, stage="running")
    stored = json.loads(fake.data[key])
    assert stored["status"] == "queued" and stored["pct"] == 50 and stored["stage"] == "running"
    assert "j1" in fake.sets[rs.USER_JOBS_KEY.format("7")]


def test_job_update_retries_and_keeps_concurrent_cancel_flag(fake):
    key = rs.JOB_KEY.format("j2")
    fake.data[key] = json.dumps({"status": "running", "user_key": "7"})
    fake.conflicts = 1
    rs.job_update("j2", pct=80)
    stored = json.loads(fake.data[key])
    assert stored["pct"] == 80
    assert stored["cancel_requested"] is True


def test_queue_pop_honours_order_and_reports_queue(fake):
    fake.queue_items[rs.JOB_QUEUE] = ["media-job"]
    fake.queue_items[rs.UPSCALE_JOB_QUEUE] = ["gpu-job"]
    assert rs.queue_pop(["profile", "media", "gpu"]) == ("media", "media-job")
    assert fake.popped[-1] == [rs.PROFILE_JOB_QUEUE, rs.JOB_QUEUE, rs.UPSCALE_JOB_QUEUE]
    assert rs.queue_pop(["gpu"]) == ("gpu", "gpu-job")
    assert rs.queue_pop(["profile"]) is None


def test_queue_pop_without_free_slots_does_nothing(fake):
    assert rs.queue_pop([]) is None
    assert fake.popped == []
