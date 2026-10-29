from __future__ import annotations

from fastapi.testclient import TestClient


def test_no_context_answer_respects_selected_module(client: TestClient):
    response = client.post(
        "/api/ask",
        json={
            "question": "Who wrote Hamlet?",
            "knowledge_id": "doc_cap",
            "answer_provider": "offline",
            "tts_provider": "browser",
        },
    )
    assert response.status_code == 200
    text = response.json()["answer_text"]
    assert "The CAP Theorem" in text
    assert "Raft" not in text
    assert "Neural Attention" not in text


def test_explicit_unconfigured_voice_has_one_actionable_warning(client: TestClient):
    response = client.post(
        "/api/ask",
        json={
            "question": "CAP",
            "answer_provider": "offline",
            "tts_provider": "elevenlabs",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tts_engine"] == "browser"
    assert len(body["warnings"]) == 1
    assert "no voice configured" in body["warnings"][0]
