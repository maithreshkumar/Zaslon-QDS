from pathlib import Path

from zaslon_shared.proxy import _allowed_path
import zaslon_shared.auth as auth


ROOT = Path(__file__).resolve().parents[3]


def test_role_proxies_expose_only_their_required_paths() -> None:
    assert _allowed_path("ALICE", "/api/v1/alice/sessions") is True
    assert _allowed_path("ALICE", "/api/v1/attacks/runs") is False
    assert _allowed_path("BOB", "/api/v1/bob/verify") is True
    assert _allowed_path("BOB", "/api/v1/sessions/QDS-1/quantum-status") is True
    assert _allowed_path("BOB", "/api/v1/attacks/runs") is False
    assert _allowed_path("ATTACK", "/api/v1/sessions") is True
    assert _allowed_path("ATTACK", "/api/v1/attacks/runs") is True
    assert _allowed_path("ATTACK", "/api/v1/bob/verify") is False


def test_browser_sources_do_not_read_or_send_role_credentials() -> None:
    for role in ("Alice", "Bob", "Attack"):
        source = (ROOT / role / "src" / "main.tsx").read_text(encoding="utf-8")
        assert "VITE_ZASLON_API_KEY" not in source
        assert "X-ZASLON-API-Key" not in source
        assert "API_KEY" not in source


def test_unchanged_template_credentials_are_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "_configured_keys",
        lambda: {
            "ALICE": "replace-with-a-unique-random-alice-key",
            "BOB": "b" * 32,
            "ATTACK": "c" * 32,
        },
    )
    try:
        auth.validate_auth_configuration()
    except RuntimeError as exc:
        assert "non-template" in str(exc)
    else:
        raise AssertionError("template credential was accepted")
