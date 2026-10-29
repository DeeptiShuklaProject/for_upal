# Architecture and extension contracts

## System shape

The MVP is one FastAPI runtime serving the API and a self-contained vanilla web client. Answer and speech integrations sit behind provider routers so local and cloud services remain interchangeable.

```text
Browser UI
  ├─ Web Speech Recognition (optional STT)
  ├─ Text question
  └─ Audio player + Web Audio spectrum
             │ JSON / same origin
             ▼
FastAPI routes
             │
             ▼
ProfessorService
  ├─ KnowledgeStore ─────────── data/knowledge.json
  ├─ AnswerRouter
  │    ├─ OfflineAnswerer
  │    └─ OpenAIAnswerer
  └─ SpeechRouter
       ├─ ElevenLabsProvider
       ├─ VoiceboxProvider ──── local/native REST
       ├─ VoiceStudioProvider ─ local/OpenAI-compatible REST
       └─ Browser fallback ──── no server audio returned
```

## Request sequence

1. `POST /api/ask` validates the typed request.
2. `KnowledgeStore.retrieve()` filters the selected module and ranks documents by weighted topic, keyword, and content overlap.
3. If retrieval returns no documents, the offline answerer returns a grounded refusal and no online model is called.
4. `AnswerRouter` selects offline or OpenAI-compatible generation. Online failure falls back to offline synthesis with a warning.
5. `SpeechRouter` attempts the selected provider or the configured automatic sequence.
6. The API returns answer text, source references, provider names, warnings, and optional base64 audio.
7. The browser appends safe text nodes, plays server audio or browser speech, and visualizes server audio through `AnalyserNode`.

CPU-blocking SDK and HTTP calls run through `asyncio.to_thread()` so they do not block FastAPI's event loop.

## Main contracts

### `KnowledgeStore`

```python
retrieve(query: str, knowledge_id: str = "all", top_k: int = 2) -> list[ScoredDocument]
```

A replacement BM25/vector store must preserve:

- module filtering;
- deterministic source IDs;
- score-ordered `ScoredDocument` results;
- an empty list when support is insufficient;
- `UnknownKnowledgeModule` for invalid selectors.

### `Answerer`

```python
answer(question, persona, documents) -> AnswerResult(text, engine, warnings)
```

A new answer provider must use the retrieved documents as its only factual context, return a non-empty answer, and let the router handle fallback. It must not silently answer from general knowledge when context is absent.

### `SpeechProvider`

```python
synthesize(text: str, persona_id: str) -> AudioResult(content, mime_type, engine)
```

Adapters must return actual audio bytes, reject empty or oversized responses, and raise `ProviderError` without exposing credentials. Browser speech is a router result with `audio=None`, not a fake audio provider.

## API surface

| Endpoint | Purpose |
|---|---|
| `GET /` | Serve the voice console |
| `GET /api/health` | Version and loaded corpus count |
| `GET /api/config` | Public personas, modules, and provider configuration state |
| `POST /api/ask` | Grounded answer, sources, warnings, optional audio |
| `GET /docs` | FastAPI interactive schema |

`/api/config` contains no secrets and does not probe external services. `configured=true` means the required settings exist, not that a provider is reachable.

## Fallback behavior

| Failure | Result |
|---|---|
| No retrieved context | Grounded refusal; no online answer call |
| OpenAI not configured | Offline answer + warning when explicitly selected |
| OpenAI request fails | Offline answer + warning |
| Selected TTS not configured | Browser speech + warning |
| Configured TTS fails | Next automatic provider or browser speech |
| Browser STT unsupported | Text input remains available |
| Browser TTS unsupported | Text answer remains available |
| Autoplay blocked | Native audio play button remains available |

## Security boundaries

- Only the backend reads API keys and voice-service credentials.
- `.env` is ignored by Git and Docker context.
- User/model text is inserted with `textContent`, not HTML.
- API request bodies are capped at 32 KB, including chunked bodies; streamed provider audio is capped at 25 MB while downloading.
- Provider calls have explicit timeouts; OpenAI retries are bounded and audio/answer failures degrade safely.
- The app emits CSP, anti-framing, MIME-sniffing, referrer, permissions, and API no-store policies; Swagger remains reachable without weakening the app CSP.
- Provider exceptions are converted to safe warnings rather than returned with raw request/secret details.
- The MVP has no authentication, tenant isolation, rate limiting, or audit persistence; add these before exposing it as a shared production service.

## Deliberate MVP simplifications

- Weighted token retrieval avoids a model download and makes tests fast/deterministic.
- JSON corpus replaces ingestion and persistent indexing.
- Base64 audio simplifies the single-request prototype; streaming is a production upgrade.
- In-page transcript state avoids pretending there is server persistence.
- FastAPI serves the same-origin UI, eliminating CORS from the prototype path.

These are replaceable layers, not hidden stubs. The production sequence is in `PRODUCTION_ROADMAP.md`.
