# Full-module feasibility and production roadmap

## Feasibility verdict

**The complete module is highly feasible to implement in Devin using this repository as the starting point.** The difficult integration seams—grounded orchestration, provider isolation, local/cloud speech contracts, fallback behavior, a working UI, and offline tests—already exist as a runnable vertical slice.

Devin can extend the codebase incrementally without needing to infer the architecture from a prose blueprint. The remaining work is primarily production depth: corpus ingestion, persistent retrieval, conversation state, streaming, administration, security, evaluation, and deployment.

## Current coverage

| Capability | MVP status | Production target |
|---|---|---|
| Local sample corpus | Complete | Versioned multi-course corpus |
| Retrieval | Weighted in-memory ranking | Chunked BM25 + vector hybrid with evaluation |
| Offline answer | Complete | Maintained as deterministic fallback |
| Online answer | Optional adapter | Streaming, caching, budgets, policy controls |
| Personas | Two configured educators | Database-backed, administrable persona registry |
| Browser STT/TTS | Complete fallback | Whisper/server STT option and streamed TTS |
| Voicebox | Native REST adapter | Health checks, streaming UX, authenticated private networking |
| VoiceStudio | OpenAI-compatible adapter | Model discovery, health checks, streaming UX |
| abogen | Roadmap only | Queued long-form audio/subtitle exports |
| Transcript | Current page only | Authenticated persistent conversations |
| Sources | Visible excerpts | Chunk-level citations and source viewer |
| Security | Basic input/secret boundaries | Auth, authorization, quotas, rate limits, audit logs |
| Operations | Dockerfile + health endpoint | Metrics, tracing, alerts, deployment automation |

## Phase 1 — Corpus ingestion and persistent retrieval

### Build

- Add TXT/Markdown/PDF upload APIs with file-type, size, malware, and parser-error handling.
- Extract text, normalize structure, chunk by headings/token budget, and preserve course/document/page/section metadata.
- Store source files in object storage and metadata in a database.
- Add embeddings plus BM25/hybrid retrieval (Qdrant, pgvector, or an equivalent managed/private store).
- Introduce corpus versioning, reindex jobs, deletion, and retry states.
- Preserve `KnowledgeStore.retrieve()` as the orchestration-facing contract during migration.
- Add a retrieval evaluation set covering each course, ambiguous queries, no-context queries, and module filters.

### Acceptance gate

- Uploaded documents survive restart and can be reindexed/deleted.
- Answers cite the exact chunk and source location used.
- Retrieval regression tests beat the MVP baseline on the evaluation set.
- Empty/irrelevant corpus results still produce grounded refusals.

## Phase 2 — Conversation and answer hardening

### Build

- Add authenticated conversation and message persistence with course-scoped authorization.
- Add bounded conversation history to the answer prompt without allowing history to override source grounding.
- Support streaming text (SSE or WebSocket) while retaining the synchronous API for compatibility.
- Add token budgets, model timeouts, caching, usage accounting, and structured observability.
- Add answer validation for empty output, unsupported citations, excessive length, and provider refusal.
- Expand offline fallback to return useful sourced excerpts even when every online model is unavailable.

### Acceptance gate

- Conversation history is isolated per user and survives restart.
- Every factual answer maps to stored source chunks; unsupported answers fail closed.
- Streaming can be cancelled and resumes into a valid saved message state.
- No secrets, raw credentials, or full sensitive prompts appear in logs.

## Phase 3 — Real-time voice and long-form audio

### Build

- Add server STT (Whisper/faster-whisper or Voicebox transcription) with browser STT retained as an option.
- Move answer audio to streamed responses; support playback interruption and cancellation.
- Add provider health checks with timeouts and cooldowns, distinct from configuration checks.
- Add Voicebox/VoiceStudio voice discovery and an admin-only persona-to-profile mapping UI.
- Add explicit consent and attribution controls for cloned voices.
- Create a background export worker for abogen audiobook/subtitle generation; store outputs in object storage and track job status.

### Acceptance gate

- Interruption stops current generation/playback without corrupting the next turn.
- Provider outages produce timely fallback and visible health status.
- Voice cloning cannot be initiated without an authorized reference/consent record.
- abogen exports are asynchronous, resumable, and never block interactive Q&A.

## Phase 4 — Product and administration

### Build

- Add authentication, roles (student/instructor/admin), course enrollment, and tenant isolation where needed.
- Add instructor tools for corpus review, persona tuning, answer feedback, and source correction.
- Add rate limiting, quotas, content moderation appropriate to the deployment, and audit events.
- Add student history, export/delete controls, accessibility review, and privacy disclosures.
- Add unit, integration, end-to-end, load, and failure-injection suites in CI.

### Acceptance gate

- Authorization tests cover cross-course and cross-tenant access attempts.
- Usage limits and provider budgets fail gracefully.
- Keyboard, screen-reader, reduced-motion, mobile, and error-state checks pass.
- Load tests establish capacity for the target concurrent voice workload.

## Phase 5 — Deployment and operations

### Build

- Separate web/API, CPU workers, and GPU voice workers where scale requires it.
- Add managed secrets, TLS/private service networking, database migrations, backups, and disaster recovery.
- Add metrics/traces for retrieval latency, answer latency, time-to-first-audio, fallback rate, provider errors, and cost.
- Pin dependencies and model versions; create rollback procedures and provider upgrade contract checks.

### Acceptance gate

- A clean environment deploys from documented automation.
- Backup/restore and rollback are rehearsed.
- Dashboards and alerts distinguish configuration, reachability, generation failure, and quality regression.

## Main risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Retrieval looks fluent but selects the wrong context | Incorrect teaching | Hybrid retrieval, evaluation set, source inspector, no-context threshold |
| Online model adds unsupported facts | Loss of grounding | Context-only prompts, citation validation, fail-closed fallback |
| Local model latency or GPU memory | Poor conversation cadence | Small/default models, worker queues, timeouts, health/cooldown, browser fallback |
| Voice API/version drift | Broken provider | Adapter isolation, mocked contract tests, upstream version pinning |
| Voice cloning misuse | Legal/ethical exposure | Consent records, authorization, clear AI-audio labeling, abuse controls |
| Base64 audio and large responses | Memory/latency pressure | Streaming and object storage in Phases 2–3 |
| Devin produces broad but shallow phase output | Unverified system | One vertical phase at a time, acceptance gates, real runtime evidence |

## Recommended Devin execution strategy

1. Start with `DEVIN_PROMPT.md` and require an implementation plan mapped to the phase gates.
2. Implement one phase per reviewable change set; keep the offline MVP runnable throughout.
3. Require automated tests and real runtime evidence for each phase, not only generated code.
4. Use mocks for paid/external provider CI and a separate authorized live-provider checklist.
5. Do not declare the full module complete until every target capability is either implemented and tested or explicitly accepted as out of scope.
