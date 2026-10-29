"""Small, deterministic retrieval over local course modules.

The MVP deliberately avoids downloading an embedding model. Its weighted token
retrieval is transparent, testable, and replaceable by a persistent vector/BM25
store without changing the orchestration contract.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "could",
    "do",
    "does",
    "explain",
    "for",
    "from",
    "give",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "please",
    "tell",
    "that",
    "the",
    "their",
    "this",
    "to",
    "us",
    "was",
    "what",
    "when",
    "where",
    "which",
    "why",
    "with",
    "would",
    "you",
    "your",
}


def _tokens(text: str) -> set[str]:
    return {
        token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOP_WORDS
    }


@dataclass(frozen=True)
class Document:
    id: str
    topic: str
    summary: str
    source: str
    keywords: tuple[str, ...]
    check_question: str
    content: str


@dataclass(frozen=True)
class ScoredDocument:
    document: Document
    score: float

    def reference(self) -> dict:
        excerpt = self.document.content.strip()
        if len(excerpt) > 420:
            excerpt = excerpt[:417].rstrip() + "..."
        return {
            "id": self.document.id,
            "topic": self.document.topic,
            "source": self.document.source,
            "excerpt": excerpt,
            "score": round(self.score, 3),
        }


class UnknownKnowledgeModule(ValueError):
    """Raised when a client selects a module that does not exist."""


class KnowledgeStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.documents = tuple(
            Document(
                id=item["id"],
                topic=item["topic"],
                summary=item["summary"],
                source=item["source"],
                keywords=tuple(item.get("keywords", [])),
                check_question=item["check_question"],
                content=item["content"],
            )
            for item in raw
        )
        if not self.documents:
            raise ValueError("The knowledge store must contain at least one document.")
        ids = [document.id for document in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("Knowledge document IDs must be unique.")

    def public_modules(self) -> list[dict]:
        return [
            {"id": document.id, "topic": document.topic, "summary": document.summary}
            for document in self.documents
        ]

    def topics(self) -> list[str]:
        return [document.topic for document in self.documents]

    def topics_for(self, knowledge_id: str) -> list[str]:
        if knowledge_id == "all":
            return self.topics()
        return [
            document.topic for document in self.documents if document.id == knowledge_id
        ]

    def retrieve(
        self, query: str, knowledge_id: str = "all", top_k: int = 2
    ) -> list[ScoredDocument]:
        if knowledge_id != "all" and knowledge_id not in {
            document.id for document in self.documents
        }:
            raise UnknownKnowledgeModule(f"Unknown knowledge module: {knowledge_id}")

        candidates = [
            document
            for document in self.documents
            if knowledge_id in ("all", document.id)
        ]
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        normalized_query = " ".join(_TOKEN_RE.findall(query.lower()))
        scored: list[ScoredDocument] = []
        for document in candidates:
            topic_tokens = _tokens(document.topic)
            keyword_tokens = _tokens(" ".join(document.keywords))
            content_tokens = _tokens(document.content)
            score = (
                3.0 * len(query_tokens & topic_tokens)
                + 2.0 * len(query_tokens & (keyword_tokens - topic_tokens))
                + 1.0
                * len(query_tokens & (content_tokens - topic_tokens - keyword_tokens))
            )
            if document.topic.lower() in normalized_query:
                score += 4.0
            score += (
                2.0
                * len(query_tokens & (topic_tokens | keyword_tokens | content_tokens))
                / len(query_tokens)
            )
            if score > 0:
                scored.append(ScoredDocument(document=document, score=score))

        scored.sort(key=lambda item: (-item.score, item.document.id))
        return scored[:top_k]
