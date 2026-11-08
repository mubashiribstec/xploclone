"""Structured JSON logging. No audio, no text content, no API keys in logs.

Every request logs: timestamp, level, message, request id, voice_id,
character count, latency ms, status code, error code (if any).
Text content and audio are NEVER logged (PLAN-v2 §10 — recordings and
outputs are sensitive personal data).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("xploclone")
    root.handlers = [handler]
    root.setLevel(level)
    root.propagate = False
    return root


logger = configure_logging()


def log_fields(**fields: object) -> dict[str, object]:
    return {"fields": fields}
