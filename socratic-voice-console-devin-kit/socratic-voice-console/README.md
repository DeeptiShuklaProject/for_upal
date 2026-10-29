# Socratic Voice Console

A deployable prototype and Devin-ready codebase for a grounded, voice-enabled professor Q&A module. It implements the supplied FastAPI blueprint as a modular application rather than a single-file demo. Current release: **0.2.1**.

## What works now

- **Grounded local Q&A** over three supplied course modules: Raft, neural attention, and CAP.
- **Two educator personas**: Dr. Margaret Holloway and Dr. Christopher Brooks.
- **Offline-first answers** with explicit source references and a no-context refusal path.
- **Optional OpenAI-compatible answers** with automatic offline fallback.
- **Five speech paths**: automatic routing, browser speech, ElevenLabs, Voicebox, and VoiceStudio.
- **Responsive voice console** with speech recognition, transcript, sources, audio playback, and a real Web Audio spectrum for server-generated audio.
- **Safe provider degradation**: a failed cloud/local voice service does not discard the text answer.
- **Typed API, deployment middleware, locked dependencies, Dockerfile, Compose, and 34 contract tests**.
- **Browser regression coverage** for request cancellation, speech races, long-answer chunking, audio cleanup, and spectrum resizing.

No credentials, database, model download, or external CDN is required for the default offline experience.

## Quick start

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.lock   # reproducible runtime dependencies
cp .env.example .env               # optional; offline defaults work without it
python main.py
```

Open **http://localhost:8000**. Interactive API documentation is at **http://localhost:8000/docs**.

## Host-compatible preview and deployment

Hosts that expect a Node launcher can use the included wrapper; it starts the same FastAPI application and proxies requests without changing the UI or API.

```bash
npm install
npm run dev          # http://localhost:3000
```

For a self-contained deployment bundle:

```bash
npm run build        # creates dist/boot.js and a vendored Python runtime
npm start            # http://localhost:3000
```

`PORT` controls the public listener (default `3000`); `APP_INTERNAL_PORT` controls the private FastAPI listener. The build uses `requirements.lock`, removes unused optional server accelerators, and does not require global Python packages at runtime. The direct Python and Docker launch paths remain available.

The default route is:

```text
question → weighted local retrieval → grounded offline answer → browser speech
```

Select **Browser speech** explicitly if you want to bypass all server-side voice providers. Browser speech recognition support varies by browser; text input always remains available. Deployed microphone use requires HTTPS outside localhost.

## Run tests

```bash
pip install -r requirements-dev.txt
pytest
```

The 34 tests cover retrieval, grounded answers, API validation, secret handling, request limits, security headers, provider deadlines/fallback, audio limits, Voicebox's native stream contract, and VoiceStudio's OpenAI-compatible speech contract. External services are mocked; no API keys are consumed.

For browser regression checks, keep the app running and use:

```bash
pip install -r requirements-browser.txt
playwright install chromium
python tests/browser_smoke.py
```

These checks cover mobile layout, delayed-request cancellation, speech recognition segments, long-answer speech queuing, stale speech events, and live-spectrum resizing.

## Docker and Compose

```bash
docker compose up --build -d
# Open http://localhost:8000
```

Or use the container directly:

```bash
docker build -t socratic-voice-console:0.2.1 .
docker run --rm -p 8000:8000 --env-file .env socratic-voice-console:0.2.1
```

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for TLS, trusted proxies, public-demo safety, and operational checks.

If Voicebox or VoiceStudio runs on the Docker host, `127.0.0.1` inside the container refers to the container itself. Use `host.docker.internal` in the provider base URL. On Linux, add:

```bash
--add-host=host.docker.internal:host-gateway
```

Do not expose an unauthenticated local voice service to an untrusted network.

## API example

```bash
curl -s http://localhost:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Explain the CAP theorem",
    "persona_id": "christopher",
    "knowledge_id": "all",
    "answer_provider": "offline",
    "tts_provider": "browser"
  }'
```

The response includes the answer, source excerpts, engines used, warnings, and optional base64 audio. A production API should move large audio payloads to streamed responses or object storage; base64 is intentional MVP simplicity.

## Provider setup

Copy `.env.example` to `.env` and set only the integrations you need. See **[docs/VOICE_PROVIDERS.md](docs/VOICE_PROVIDERS.md)** for exact Voicebox and VoiceStudio configuration, endpoint contracts, authentication, and troubleshooting.

Provider priority in `auto` mode is:

- **Answers**: OpenAI-compatible when configured, otherwise offline.
- **Speech**: ElevenLabs → Voicebox → VoiceStudio → browser.

Explicit provider selection is available in the console. Unconfigured providers are disabled based on `/api/config`; this reports configuration, not a live health check.

## Codebase map

```text
.
├── main.py                         # FastAPI routes and app factory
├── professor_qa/
│   ├── answerers.py               # Offline + OpenAI-compatible answer routing
│   ├── config.py                  # Environment configuration and secret isolation
│   ├── knowledge.py               # Local corpus and weighted retrieval
│   ├── middleware.py              # Body limits and security/cache policy
│   ├── models.py                  # Typed API contracts
│   ├── personas.py                # Educator definitions
│   ├── service.py                 # End-to-end orchestration
│   └── tts.py                     # ElevenLabs/Voicebox/VoiceStudio adapters
├── data/knowledge.json             # Supplied sample corpus
├── static/                        # Self-hosted UI, fonts, and icons
├── tests/                         # Contract suite + browser regression checks
├── docs/                          # Architecture, voice setup, deployment, production plan
├── compose.yaml                   # One-command local container deployment
├── preview/server.mjs             # Host development/production launcher
├── scripts/build-preview.mjs      # Self-contained dist/boot.js build
├── package.json                   # Host build/start contract
├── requirements.lock              # Pinned runtime dependency set
├── .agents/skills/                # Devin-discoverable repository skills
├── AGENTS.md                      # Repository working agreement
└── DEVIN_PROMPT.md                # Copy-paste full-module implementation brief
```

## MVP boundaries

This is a tested vertical slice, not the complete production system:

- Retrieval is deterministic weighted token matching, not embeddings or persistent BM25/vector search.
- The corpus is JSON; there is no document-upload/chunking pipeline yet.
- Transcript state exists only in the current page. There is no account, database, or cross-device persistence.
- Public demos should use offline answers and browser speech; paid providers require an authenticated, quota-controlled deployment.
- Voicebox and VoiceStudio are external local services; their models and runtimes are not bundled.
- Browser speech synthesis does not expose samples, so the spectrum is real for server audio but not for browser speech.
- abogen is reserved for a future long-form audiobook/export worker, not the interactive low-latency chat path.

See **[docs/PRODUCTION_ROADMAP.md](docs/PRODUCTION_ROADMAP.md)** for feasibility, phases, risks, and acceptance gates.

## Continue in Devin

1. Put this repository in Devin's workspace.
2. Keep `AGENTS.md` and `.agents/skills/` at the repository root.
3. Configure secrets through Devin's environment/secret facility, never in committed files.
4. Paste **[DEVIN_PROMPT.md](DEVIN_PROMPT.md)** as the implementation brief.
5. Require Devin to preserve the offline path and run the full tests after every phase.

## Third-party notices

See **[CREDITS.md](CREDITS.md)** for bundled font licenses and external project references.
