from __future__ import annotations

from fastapi.testclient import TestClient


def test_security_and_cache_headers(client: TestClient):
    index = client.get("/")
    assert index.headers["x-content-type-options"] == "nosniff"
    assert index.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in index.headers["content-security-policy"]
    assert index.headers["cache-control"] == "no-cache"

    health = client.get("/api/health")
    assert health.headers["cache-control"] == "no-store"
    assert (
        health.headers["permissions-policy"]
        == "microphone=(self), camera=(), geolocation=()"
    )


def test_declared_oversized_body_is_rejected(client: TestClient):
    response = client.post(
        "/api/ask",
        content=b" " * (32 * 1024 + 1),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "Request body exceeds the 32 KB limit."


def test_chunked_oversized_body_is_rejected(client: TestClient):
    def chunks():
        yield b"x" * 16000
        yield b"x" * 16000
        yield b"x" * 16000

    response = client.post(
        "/api/ask", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413


def test_root_supports_head_for_load_balancer_checks(client: TestClient):
    response = client.head("/")
    assert response.status_code == 200
    assert "content-security-policy" in response.headers


def test_docs_remain_reachable_with_app_csp_enabled(client: TestClient):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text
