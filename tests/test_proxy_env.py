"""NO_PROXY sanitisation tests (api/proxy_env.py).

httpx (via huggingface_hub) raises InvalidURL on bare-IPv6 NO_PROXY
entries, which broke model downloads in the 2026-10-31 sample test.
Only bare-IPv6 entries are dropped; everything else is preserved.
"""

import os

from api.proxy_env import sanitise_no_proxy, sanitise_no_proxy_value

VM_NO_PROXY = (
    "localhost,127.0.0.1,::1,[::1],198.19.0.1,198.19.0.2,"
    "fd8b:4f84:7d32:99::1,[fd8b:4f84:7d32:99::1],"
    "fd8b:4f84:7d32:99::2,[fd8b:4f84:7d32:99::2]"
)


def test_bare_ipv6_entries_dropped_bracketed_kept() -> None:
    out = sanitise_no_proxy_value(VM_NO_PROXY)
    assert out == (
        "localhost,127.0.0.1,[::1],198.19.0.1,198.19.0.2,"
        "[fd8b:4f84:7d32:99::1],[fd8b:4f84:7d32:99::2]"
    )


def test_plain_values_unchanged() -> None:
    assert sanitise_no_proxy_value("localhost,127.0.0.1,example.com") == (
        "localhost,127.0.0.1,example.com"
    )
    assert sanitise_no_proxy_value("") == ""


def test_sanitise_no_proxy_rewrites_env(monkeypatch) -> None:
    monkeypatch.setenv("NO_PROXY", VM_NO_PROXY)
    monkeypatch.setenv("no_proxy", VM_NO_PROXY)
    sanitise_no_proxy()
    assert os.environ["NO_PROXY"] == sanitise_no_proxy_value(VM_NO_PROXY)
    assert "::1," not in os.environ["NO_PROXY"]
    assert "fd8b:4f84:7d32:99::1," not in os.environ["NO_PROXY"]
