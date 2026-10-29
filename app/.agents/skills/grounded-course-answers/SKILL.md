---
name: grounded-course-answers
description: Build or modify course knowledge ingestion, retrieval, source citations, grounded professor answers, no-context handling, retrieval evaluation, or online/offline answer routing for the professor Q&A module. Use for knowledge-base, RAG, corpus, prompting, and answer-quality tasks.
---

# Grounded course answers

Treat source grounding as a correctness boundary, not a prompt suggestion. Read `docs/ARCHITECTURE.md` for the retrieval and answer contracts and `docs/PRODUCTION_ROADMAP.md` before replacing the MVP store.

## Preserve the response contract

1. Filter by the selected course/module before ranking.
2. Return score-ordered `ScoredDocument` items with stable source IDs.
3. Return an empty result when support is absent or below a justified threshold.
4. Bypass online generation when no context exists; return a useful grounded refusal listing available modules or next actions.
5. Generate answers only from retrieved context and the selected persona's pedagogical style.
6. Preserve source references through the API and UI.
7. Fall back to sourced offline content when an online answer provider fails.

## Replace retrieval incrementally

- Keep `KnowledgeStore.retrieve(query, knowledge_id, top_k)` or an explicit adapter with the same behavior while introducing chunking, BM25, embeddings, or hybrid search.
- Preserve document/chunk metadata needed for course, page, section, and source-viewer citations.
- Make ingestion/versioning failures visible; never answer from a partially deleted or stale index without disclosure.
- Build a representative evaluation set before tuning thresholds or declaring improved quality.

## Test quality and failure paths

Cover each course topic, ambiguous questions, irrelevant questions, module filters, missing/empty corpus, provider errors, unsupported citations, and history/prompt-injection attempts. Assert that unsupported questions do not trigger an online model call.

Run `pytest` and compare retrieval results against the previous baseline. Report evaluation evidence separately from anecdotal sample answers.
