from __future__ import annotations

from conftest import make_settings
from fastapi.testclient import TestClient

from main import create_app
from professor_qa.knowledge import KnowledgeStore
from professor_qa.service import ProfessorService


def test_health_and_index(client: TestClient):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "version": "0.2.1",
        "knowledge_documents": 3,
    }
    index = client.get("/")
    assert index.status_code == 200
    assert "Socratic Voice Console" in index.text


def test_offline_question_returns_grounded_sources(client: TestClient):
    response = client.post(
        "/api/ask",
        json={
            "question": "Explain the CAP theorem",
            "persona_id": "christopher",
            "knowledge_id": "all",
            "answer_provider": "offline",
            "tts_provider": "browser",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["educator_name"] == "Dr. Christopher Brooks"
    assert body["answer_engine"] == "offline"
    assert body["tts_engine"] == "browser"
    assert body["audio_base64"] is None
    assert body["sources"][0]["id"] == "doc_cap"
    assert "Consistency" in body["answer_text"]


def test_ungrounded_question_is_not_answered_from_imagination(client: TestClient):
    response = client.post(
        "/api/ask",
        json={
            "question": "Who wrote Hamlet?",
            "answer_provider": "offline",
            "tts_provider": "browser",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == []
    assert "not have enough grounding" in body["answer_text"]


def test_invalid_requests_are_handled(client: TestClient):
    blank = client.post("/api/ask", json={"question": "   "})
    assert blank.status_code == 422
    unknown = client.post(
        "/api/ask", json={"question": "CAP", "knowledge_id": "missing"}
    )
    assert unknown.status_code == 400
    assert "Unknown knowledge module" in unknown.json()["detail"]


def test_configuration_never_exposes_keys():
    settings = make_settings(
        openai_api_key="test-only-secret", elevenlabs_api_key="another-test-secret"
    )
    service = ProfessorService(
        settings=settings, store=KnowledgeStore(settings.knowledge_path)
    )
    client = TestClient(create_app(service))
    response = client.get("/api/config")
    assert response.status_code == 200
    assert "test-only-secret" not in response.text
    assert "another-test-secret" not in response.text
    assert "api_key" not in response.text
    assert response.json()["tts_providers"][1]["id"] == "browser"
