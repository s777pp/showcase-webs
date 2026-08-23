"""Structured logging setup."""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone


class JsonLikeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        level = record.levelname
        msg = record.getMessage()
        name = record.name
        extra = ""
        if hasattr(record, "extra_data") and record.extra_data:
            extra = f" | {record.extra_data}"
        return f"{ts} [{level}] {name}: {msg}{extra}"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    root = logging.getLogger("showcase")
    if root.handlers:
        return root
    root.setLevel(level)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonLikeFormatter())
    root.addHandler(h)
    # quiet noisy libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    return root


log = setup_logging()
