from __future__ import annotations

from conftest import make_settings

from professor_qa.answerers import AnswerRouter, OfflineAnswerer
from professor_qa.config import Settings
from professor_qa.knowledge import KnowledgeStore
from professor_qa.personas import get_persona


class FailingOpenAI:
    def answer(self, question, persona, documents):
        raise RuntimeError("simulated provider failure")


def test_openai_failure_falls_back_to_grounded_offline(store: KnowledgeStore):
    settings = make_settings(openai_api_key="test-only-key")
    router = AnswerRouter(
        settings=settings,
        offline=OfflineAnswerer(store.topics()),
        openai=FailingOpenAI(),
    )
    documents = store.retrieve("Explain Raft log safety")
    result = router.answer(
        "auto", "Explain Raft log safety", get_persona("margaret"), documents
    )
    assert result.engine == "offline"
    assert "Raft" in result.text
    assert "online answer provider failed" in result.warnings[0]


def test_explicit_openai_without_configuration_uses_offline(store: KnowledgeStore):
    settings: Settings = make_settings()
    router = AnswerRouter(settings, OfflineAnswerer(store.topics()))
    documents = store.retrieve("CAP theorem")
    result = router.answer(
        "openai", "CAP theorem", get_persona("christopher"), documents
    )
    assert result.engine == "offline"
    assert "not configured" in result.warnings[0]
