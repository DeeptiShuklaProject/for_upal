from __future__ import annotations

import pytest

from professor_qa.knowledge import KnowledgeStore, UnknownKnowledgeModule


def test_retrieval_ranks_cap_document(store: KnowledgeStore):
    results = store.retrieve("What is the CAP theorem?")
    assert results[0].document.id == "doc_cap"
    assert results[0].score > 0


def test_retrieval_ranks_attention_document(store: KnowledgeStore):
    results = store.retrieve("How does scaled dot-product attention use softmax?")
    assert results[0].document.id == "doc_attention"


def test_retrieval_honors_module_filter(store: KnowledgeStore):
    results = store.retrieve("Explain distributed partition tolerance", "doc_cap")
    assert [item.document.id for item in results] == ["doc_cap"]


def test_ungrounded_question_returns_no_sources(store: KnowledgeStore):
    assert store.retrieve("What is the capital of France?") == []


def test_unknown_module_is_rejected(store: KnowledgeStore):
    with pytest.raises(UnknownKnowledgeModule):
        store.retrieve("CAP", "not-a-module")
