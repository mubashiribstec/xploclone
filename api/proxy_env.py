"""Sanitise NO_PROXY / no_proxy for httpx (used by huggingface_hub).

Found in the 2026-10-31 sample test: this VM's NO_PROXY contains bare
IPv6 entries (``fd8b:4f84:7d32:99::1`` — no brackets). httpx parses
no_proxy entries as URL hosts and raises ``InvalidURL`` on a bare
IPv6 address, which breaks ``snapshot_download`` (model download) even
though no proxy is involved at all. The fix is to drop exactly the
entries httpx cannot parse — bare IPv6 literals — and keep everything
else (localhost, 127.0.0.1, bracketed ``[::1]``, hostnames, CIDRs).

Called from ``api/__init__.py`` (every entry point imports the api
package) and again in ``EngineRegistry._download_checkpoint`` right
before the download, so the sanitisation holds even if the process
environment is changed after import. Pure function + side-effect
wrapper are both tested in ``tests/test_proxy_env.py``.
"""

from __future__ import annotations

import os


def sanitise_no_proxy_value(value: str) -> str:
    """Return *value* with bare-IPv6 no_proxy entries removed.

    An entry is dropped only if it contains ``::`` (an IPv6 literal)
    and is not bracketed (``[::1]``) and is not a CIDR/hostname that
    merely contains colons for another reason — in practice no_proxy
    entries with ``::`` are bare IPv6 addresses. Empty entries and
    whitespace are also dropped. Order of the surviving entries is
    preserved.
    """
    kept: list[str] = []
    for raw in value.split(","):
        entry = raw.strip()
        if not entry:
            continue
        if "::" in entry and not entry.startswith("["):
            continue
        kept.append(entry)
    return ",".join(kept)


def sanitise_no_proxy() -> None:
    """Rewrite NO_PROXY / no_proxy in-process, dropping bare IPv6 entries."""
    for name in ("NO_PROXY", "no_proxy"):
        value = os.environ.get(name)
        if value:
            os.environ[name] = sanitise_no_proxy_value(value)
