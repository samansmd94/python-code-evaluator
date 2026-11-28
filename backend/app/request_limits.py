"""Request body limits for submission endpoints."""

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_SUBMISSION_BODY_BYTES = 256 * 1024


class SubmissionBodyLimitMiddleware:
    """Bound submission request bytes before FastAPI parses JSON."""

    def __init__(
        self, app: ASGIApp, max_bytes: int = MAX_SUBMISSION_BODY_BYTES
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and scope.get("path") == "/api/submissions"
        ):
            await self.app(scope, receive, send)
            return

        content_length = _content_length(scope)
        if content_length is not None and content_length > self.max_bytes:
            await _send_too_large(send)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue

            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.max_bytes:
                await _send_too_large(send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        buffered_body = bytes(body)
        delivered = False

        async def replay_body() -> Message:
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return {
                "type": "http.request",
                "body": buffered_body,
                "more_body": False,
            }

        await self.app(scope, replay_body, send)


def _content_length(scope: Scope) -> int | None:
    raw_length = next(
        (value for key, value in scope.get("headers", []) if key.lower() == b"content-length"),
        None,
    )
    if raw_length is None:
        return None
    try:
        length = int(raw_length)
    except ValueError:
        return None
    return length if length >= 0 else None


async def _send_too_large(send: Send) -> None:
    body = json.dumps(
        {"detail": "Submission request body exceeds the configured size limit."}
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
