import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

import steam_catalog
import steam_profile_guard as guard


class ProfileGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'profiles.sqlite3'

    def test_success_cached_and_separate_profiles_gated(self):
        fetch = Mock(return_value={'ok': True, 'profile': {'name': 'A'}})
        self.assertTrue(guard.run(self.path, 'a', fetch)['ok'])
        self.assertTrue(guard.run(self.path, 'a', fetch)['ok'])
        self.assertFalse(guard.run(self.path, 'b', fetch)['ok'])
        self.assertEqual(fetch.call_count, 1)

    def test_rate_limit_persisted_between_connections(self):
        fetch = Mock(side_effect=guard.RateLimited('1200'))
        result = guard.run(self.path, 'a', fetch)
        self.assertEqual(result['retry_after'], 1200)
        self.assertEqual(guard.run(self.path, 'b', fetch)['code'], 'steam_profile_cooldown')
        self.assertEqual(fetch.call_count, 1)

    def test_expired_success_used_on_429(self):
        with patch.object(guard.time, 'time', return_value=1000):
            guard.run(self.path, 'a', lambda: {'ok': True, 'profile': {'showcases': ['saved']}})
        with patch.object(guard.time, 'time', return_value=2000):
            result = guard.run(self.path, 'a', Mock(side_effect=guard.RateLimited()))
        self.assertTrue(result['stale'])
        self.assertEqual(result['profile']['showcases'], ['saved'])

    def test_no_partial_profile_cached(self):
        result = guard.run(self.path, 'a', lambda: {'ok': False, 'code': 'steam_profile_incomplete'})
        self.assertFalse(result['ok'])
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM profiles').fetchone()[0], 0)

    def test_concurrent_request_does_not_fetch(self):
        second = Mock()
        def fetch():
            self.assertFalse(guard.run(self.path, 'a', second)['ok'])
            return {'ok': True, 'profile': {}}
        guard.run(self.path, 'a', fetch)
        second.assert_not_called()

    def test_retry_after_http_date(self):
        with patch.object(guard.time, 'time', return_value=0):
            self.assertEqual(guard.RateLimited('Thu, 01 Jan 1970 00:20:00 GMT').delay, 1200)
        self.assertEqual(guard.RateLimited('invalid').delay, 900)

    @patch.object(steam_catalog.requests, 'get')
    def test_429_does_not_retry_or_try_alternate_url(self, get):
        get.return_value = Mock(status_code=429, headers={'Retry-After': '600'})
        with self.assertRaises(guard.RateLimited):
            steam_catalog._load_profile('https://steamcommunity.com/id/test')
        self.assertEqual(get.call_count, 1)

    @patch.object(steam_catalog.requests, 'get')
    def test_xml_success_html_failure_is_not_success(self, get):
        xml = Mock(status_code=200, content=b'<profile><steamID64>76561198000000000</steamID64></profile>')
        get.side_effect = [xml, Mock(status_code=503)]
        result = steam_catalog._load_profile('https://steamcommunity.com/id/test')
        self.assertFalse(result['ok'])
        self.assertEqual(result['code'], 'steam_profile_incomplete')


if __name__ == '__main__':
    unittest.main()
