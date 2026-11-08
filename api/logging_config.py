"""Structured JSON logging. No audio, no text content, no API keys in logs.

Every request logs: timestamp, level, message, request id, voice_id,
character count, latency ms, status code, error code (if any).
Text content and audio are NEVER logged (PLAN-v2 §10 — recordings and
outputs are sensitive personal data).
"""

from __future__ import annotations

import json
import logging
import re
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


# ``?key=<api key>`` query parameters (the telephony WebSocket's browser
# auth) and anything that looks like one. Review fix 2026-11-08: uvicorn
# logs WebSocket paths WITH the query string ("WebSocket
# /v1/tts/stream?key=..." [accepted]) on its own loggers, so the plaintext
# API key landed in the server log on every connection.
_SECRET_QUERY = re.compile(r"(?i)([?&](?:key|token|api_key)=)[^&\s\"']*")


def redact_secrets(text: str) -> str:
    return _SECRET_QUERY.sub(r"\1[REDACTED]", text)


class SecretRedactionFilter(logging.Filter):
    """Rewrites a record so no ``key=`` / ``token=`` value survives."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = redact_secrets(message)
        if redacted != message:
            record.msg = redacted
            record.args = None
        return True


def install_secret_redaction(
    names: tuple[str, ...] = ("uvicorn", "uvicorn.error", "uvicorn.access", "xploclone"),
) -> None:
    """Attach the redaction filter to the server loggers (idempotent).

    A logger-level filter applies to records logged directly on that
    logger, which is how uvicorn logs its access and WebSocket lines.
    """
    for name in names:
        target = logging.getLogger(name)
        if not any(isinstance(f, SecretRedactionFilter) for f in target.filters):
            target.addFilter(SecretRedactionFilter())


install_secret_redaction()


def log_fields(**fields: object) -> dict[str, object]:
    return {"fields": fields}
