"""Shared profile cache and request gate for all Uvicorn processes."""
import copy
import json
import sqlite3
import time
from email.utils import parsedate_to_datetime


class RateLimited(Exception):
    def __init__(self, retry_after=None):
        try:
            delay = float(retry_after)
        except (TypeError, ValueError):
            try:
                delay = parsedate_to_datetime(retry_after).timestamp() - time.time()
            except (TypeError, ValueError, OverflowError):
                delay = 900
        self.delay = max(60, delay)


def run(path, key, fetch, use_global_gate=True, fresh=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=5)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS gate (id INTEGER PRIMARY KEY, until REAL)')
        db.execute('CREATE TABLE IF NOT EXISTS profiles (key TEXT PRIMARY KEY, stamp REAL, payload TEXT)')
        db.commit()
        db.execute('BEGIN IMMEDIATE')
        now = time.time()
        cached = db.execute('SELECT stamp,payload FROM profiles WHERE key=?', (key,)).fetchone()
        if cached and not fresh and now - cached[0] < 900:
            db.commit()
            return json.loads(cached[1])
        gate = db.execute('SELECT until FROM gate WHERE id=1').fetchone() if use_global_gate else None
        if gate and gate[0] > now:
            db.commit()
            return _fallback(cached, now, int(gate[0] - now) + 1)
        # Direct Steam requests share one VPS IP. Browser API sessions already
        # have queue/concurrency controls and must not block unrelated imports.
        if use_global_gate:
            db.execute('INSERT OR REPLACE INTO gate VALUES (1,?)', (now + 180,))
        db.commit()
        try:
            result = fetch()
            delay = 10 if result.get('ok') else 60
        except RateLimited as exc:
            result = None
            delay = exc.delay
        except Exception:
            result = {'ok': False, 'code': 'steam_profile_unavailable', 'msg': 'Steam profile could not be loaded'}
            delay = 60
        db.execute('BEGIN IMMEDIATE')
        if use_global_gate:
            db.execute('UPDATE gate SET until=? WHERE id=1', (time.time() + delay,))
        if result and result.get('ok'):
            db.execute('INSERT OR REPLACE INTO profiles VALUES (?,?,?)', (key, time.time(), json.dumps(result)))
            db.execute('DELETE FROM profiles WHERE key NOT IN (SELECT key FROM profiles ORDER BY stamp DESC LIMIT 200)')
        db.commit()
        if result is None:
            return _fallback(cached, now, int(delay))
        return result
    finally:
        db.close()


def _fallback(cached, now, delay):
    if cached and now - cached[0] < 7 * 86400:
        result = copy.deepcopy(json.loads(cached[1]))
        result.update(cached=True, stale=True, warning_code='steam_profile_cached', retry_after=delay)
        return result
    return {'ok': False, 'code': 'steam_profile_cooldown', 'retry_after': delay,
            'msg': 'Steam profile requests are temporarily paused. Try later or use the extension.'}


# Each way of reaching Steam (this server, the Oracle relay, Browser API) has
# its own IP and therefore its own Steam rate limit.  A 429 pauses only the
# route that received it, so the next import goes straight to another route.
def _route_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=5)
    db.execute('CREATE TABLE IF NOT EXISTS route_gate (name TEXT PRIMARY KEY, until REAL)')
    return db


def route_wait(path, name):
    """Seconds until ``name`` may be used again (0 when it is open)."""
    db = _route_db(path)
    try:
        row = db.execute('SELECT until FROM route_gate WHERE name=?', (name,)).fetchone()
        return max(0, int(row[0] - time.time())) if row else 0
    finally:
        db.close()


def route_pause(path, name, seconds):
    db = _route_db(path)
    try:
        db.execute('INSERT OR REPLACE INTO route_gate VALUES (?,?)', (name, time.time() + max(0, seconds)))
        db.commit()
    finally:
        db.close()
