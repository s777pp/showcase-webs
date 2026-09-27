"""Steam profile relay: fetches one public Steam profile page from this host's IP.

Runs on a second server (Oracle) so Showcase Maker has another IP when Steam
rate-limits the main one.  Standard library only.  It is deliberately narrow:
a bearer token is required and only steamcommunity.com/id|profiles pages can
be requested, so it cannot be used as an open proxy.
"""
import hmac
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TOKEN = os.environ.get("STEAM_RELAY_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", "8787"))
PROFILE = re.compile(r"^https://steamcommunity\.com/(id|profiles)/[A-Za-z0-9_-]{2,64}/?$")
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "Steam_Language=english",
}
MAX_BYTES = 4 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="text/plain; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self._send(200, b"ok")
        if parsed.path != "/profile":
            return self._send(404, b"not found")
        got = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        if not TOKEN or not hmac.compare_digest(got, TOKEN):
            return self._send(401, b"unauthorized")
        url = (parse_qs(parsed.query).get("url") or [""])[0].strip()
        if not PROFILE.match(url):
            return self._send(400, b"only public steamcommunity.com profile URLs")
        request = urllib.request.Request(url.rstrip("/") + "/?l=english", headers=HEADERS)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    return self._send(502, b"page too large")
                return self._send(200, body, "text/html; charset=utf-8")
        except urllib.error.HTTPError as exc:
            extra = {"Retry-After": exc.headers.get("Retry-After") or "300"} if exc.code == 429 else None
            return self._send(429 if exc.code == 429 else 502, b"steam http %d" % exc.code, extra=extra)
        except Exception as exc:
            return self._send(502, ("steam unreachable: %s" % type(exc).__name__).encode())

    def log_message(self, fmt, *args):
        # One short line per request; no query strings (they hold the profile URL only,
        # but the Authorization header is never logged either way).
        print("%s %s" % (self.command, self.path.split("?")[0]), flush=True)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("STEAM_RELAY_TOKEN is not set")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
