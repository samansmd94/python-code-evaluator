"""CORS is opt-in and limited to explicitly configured origins."""

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_configured_origin_is_allowed_and_unlisted_origin_is_not(
    migrated_database, monkeypatch
):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    app = create_app(migrated_database)
    with TestClient(app) as client:
        allowed = client.get(
            "/api/exercises", headers={"Origin": "http://localhost:5173"}
        )
        blocked = client.get(
            "/api/exercises", headers={"Origin": "http://example.invalid"}
        )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in blocked.headers
