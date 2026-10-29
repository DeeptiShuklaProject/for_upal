"""Small ASGI middleware for deployment safety and response policy."""

from __future__ import annotations

from typing import ClassVar

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyLimitMiddleware:
    """Buffer at most max_bytes and reject larger API bodies, including chunked ones."""

    BODY_METHODS: ClassVar[frozenset[str]] = frozenset(
        {"POST", "PUT", "PATCH", "DELETE"}
    )

    def __init__(self, app: ASGIApp, max_bytes: int = 32 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or not scope["path"].startswith("/api/")
            or scope["method"] not in self.BODY_METHODS
        ):
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                await self._error(
                    scope, receive, send, 400, "Invalid Content-Length header."
                )
                return
            if declared_size < 0:
                await self._error(
                    scope, receive, send, 400, "Invalid Content-Length header."
                )
                return
            if declared_size > self.max_bytes:
                await self._error(
                    scope, receive, send, 413, "Request body exceeds the 32 KB limit."
                )
                return

        received = 0
        messages: list[Message] = []
        more_body = True
        while more_body:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.disconnect":
                break
            if message["type"] != "http.request":
                continue
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                await self._error(
                    scope, receive, send, 413, "Request body exceeds the 32 KB limit."
                )
                return
            more_body = message.get("more_body", False)

        async def replay_receive() -> Message:
            if messages:
                return messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _error(
        scope: Scope, receive: Receive, send: Send, status: int, detail: str
    ) -> None:
        response = JSONResponse({"detail": detail}, status_code=status)
        await response(scope, receive, send)


class SecurityHeadersMiddleware:
    """Apply browser security and API cache policy without breaking Swagger docs."""

    APP_CSP = (
        "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; "
        "img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; "
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
    )

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message["headers"])
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
                headers.setdefault(
                    "Permissions-Policy", "microphone=(self), camera=(), geolocation=()"
                )
                headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
                if path == "/":
                    headers.setdefault("Cache-Control", "no-cache")
                    headers.setdefault("Content-Security-Policy", self.APP_CSP)
                elif path.startswith("/api/"):
                    headers.setdefault("Cache-Control", "no-store")
            await send(message)

        await self.app(scope, receive, send_with_headers)
