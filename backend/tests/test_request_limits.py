"""Request-size checks for the submission API."""

import asyncio

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.request_limits import (
    MAX_SUBMISSION_BODY_BYTES,
    SubmissionBodyLimitMiddleware,
)


def test_large_unexpected_field_is_rejected_before_schema_parsing(migrated_database):
    app = create_app(migrated_database)
    with TestClient(app) as client:
        response = client.post(
            "/api/submissions",
            json={
                "test_suite_slug": "addition-default-v1",
                "source_code": "def add(a, b): return a + b",
                "unexpected": "x" * MAX_SUBMISSION_BODY_BYTES,
            },
        )
        assert response.status_code == 413
        assert "size limit" in response.json()["detail"]


def test_stream_without_content_length_is_counted_incrementally():
    app_was_called = False
    sent_messages = []
    chunks = iter(
        [
            {"type": "http.request", "body": b"a" * 10, "more_body": True},
            {"type": "http.request", "body": b"b" * 10, "more_body": False},
        ]
    )

    async def downstream(_scope, _receive, _send):
        nonlocal app_was_called
        app_was_called = True

    async def receive():
        return next(chunks)

    async def send(message):
        sent_messages.append(message)

    middleware = SubmissionBodyLimitMiddleware(downstream, max_bytes=15)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/submissions",
        "headers": [(b"content-type", b"application/json")],
    }
    asyncio.run(middleware(scope, receive, send))

    assert not app_was_called
    assert sent_messages[0]["status"] == 413


def test_body_limit_does_not_change_unrelated_endpoints(migrated_database):
    app = create_app(migrated_database)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/exercises").status_code == 200
