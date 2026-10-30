"""Engine tests — revision pin enforcement (M3) and generic load errors (m9).

No GPU, no torch, no network: the download / load steps are stubbed and
the test asserts the *wiring* — that the pinned revision is passed
through and mismatches fail loudly. A real GPU run is still required
before Gate 1.
"""

import sys
import types
from pathlib import Path

from api.config import SETTINGS
from api.engine import REPO_ID, EngineRegistry, EngineUnavailable


def _fresh_registry() -> EngineRegistry:
    reg = EngineRegistry()
    reg._loaded = False
    reg._turbo = None
    reg.resolved_revision = None
    reg._load_error = None
    return reg


def test_download_passes_pinned_revision(monkeypatch) -> None:
    """M3: snapshot_download must be called with the pinned repo + revision."""
    captured: dict[str, str] = {}

    fake = types.ModuleType("huggingface_hub")

    def fake_download(repo_id: str, revision: str) -> str:
        captured["repo_id"] = repo_id
        captured["revision"] = revision
        return f"/tmp/fake-ckpt/{revision}"

    fake.snapshot_download = fake_download  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)

    reg = _fresh_registry()
    path = reg._download_checkpoint()
    assert captured["repo_id"] == REPO_ID
    assert captured["revision"] == SETTINGS.chatterbox_revision
    assert path == Path(f"/tmp/fake-ckpt/{SETTINGS.chatterbox_revision}")


def test_load_enforces_revision_match(monkeypatch) -> None:
    """M3: a matching snapshot loads and records the resolved revision."""
    reg = _fresh_registry()
    monkeypatch.setattr(
        reg,
        "_download_checkpoint",
        lambda: Path(f"/tmp/fake-ckpt/{SETTINGS.chatterbox_revision}"),
    )
    monkeypatch.setattr(reg, "_load_turbo", lambda ckpt_dir: object())
    reg.load_english()
    assert reg._loaded is True
    assert reg.resolved_revision == SETTINGS.chatterbox_revision


def test_load_rejects_revision_mismatch(monkeypatch) -> None:
    """M3: a snapshot whose commit differs from the pin must fail loudly."""
    reg = _fresh_registry()
    wrong = Path("/tmp/fake-ckpt/" + "0" * 40)
    monkeypatch.setattr(reg, "_download_checkpoint", lambda: wrong)
    monkeypatch.setattr(reg, "_load_turbo", lambda ckpt_dir: object())
    reg.load_english()
    assert reg._loaded is False
    assert reg.resolved_revision is None
    assert reg._load_error is not None
    assert "mismatch" in reg._load_error


def test_load_failure_message_is_generic(monkeypatch) -> None:
    """m9: a load failure must not leak internal details to the client."""
    reg = _fresh_registry()
    monkeypatch.setattr(reg, "has_reference", lambda voice_id: True)

    def boom() -> Path:
        raise RuntimeError("secret internal path /tmp/xyz, network down")

    monkeypatch.setattr(reg, "_download_checkpoint", boom)
    try:
        reg.synthesize("mubashir-en-gb", ["Hello."])
    except EngineUnavailable as exc:
        assert exc.reason == "Chatterbox Turbo failed to load. Check the server logs."
        assert "secret" not in exc.reason
        assert "/tmp/xyz" not in exc.reason
    else:  # pragma: no cover
        raise AssertionError("expected EngineUnavailable")
