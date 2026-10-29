# Devin implementation brief: complete professor Q&A module

Copy the brief below into Devin with this repository attached as the working codebase.

---

You are a senior full-stack and AI systems engineer working in an existing, runnable repository. Extend it into the complete production professor Q&A module. Do not restart from a prose-only design and do not replace the working MVP with mocks.

## Read and follow first

1. `AGENTS.md`
2. `README.md`
3. `docs/ARCHITECTURE.md`
4. `docs/VOICE_PROVIDERS.md`
5. `docs/PRODUCTION_ROADMAP.md`
6. Relevant `.agents/skills/*/SKILL.md`

These files are part of the task specification. Preserve the current offline path and provider contracts unless a documented migration preserves equivalent behavior.

## Existing baseline

The repository already contains:

- FastAPI API and same-origin responsive browser console;
- three local course documents with deterministic weighted retrieval and source excerpts;
- Margaret and Christopher professor personas;
- grounded offline answers and optional OpenAI-compatible answers;
- ElevenLabs, Voicebox native REST, VoiceStudio OpenAI-compatible, and browser-speech paths;
- safe provider fallback, typed contracts, deployment middleware, locked dependencies, Dockerfile/Compose, a self-contained `dist/boot.js` host launcher, 34 passing contract tests, and five browser regression scenarios.

Confirm the baseline with `pytest` and `node --check static/app.js` before changing code. Run the app and exercise one offline question end to end. When Playwright is available, also run `python tests/browser_smoke.py`.

## Goal

Deliver the production phases in `docs/PRODUCTION_ROADMAP.md` as reviewed, tested vertical slices:

1. Corpus ingestion, persistent metadata/files, chunking, hybrid retrieval, reindexing, and retrieval evaluation.
2. Authenticated persistent conversations, bounded history, streaming answers, citation validation, observability, budgets, and caching.
3. Server STT, streamed/interruption-safe TTS, provider health/discovery, consent-aware voice mapping, and asynchronous abogen long-form exports.
4. Student/instructor/admin product workflows, authorization, quotas, feedback, accessibility, privacy controls, and expanded CI.
5. Reproducible deployment, worker separation where justified, secrets/TLS, migrations, backups, metrics, alerts, and rollback.

Keep the FastAPI backend and current web client unless a concrete requirement justifies a stack change. Keep Voicebox and VoiceStudio as first-class local providers, ElevenLabs as a cloud option, and browser speech as a no-credential fallback. Do not route interactive Q&A through abogen; use it only for asynchronous long-form export.

## Required engineering behavior

- Start each phase with a short plan mapped to its acceptance gate, then implement the complete vertical slice rather than broad stubs.
- Preserve or extend existing contracts; use migrations and adapters instead of breaking unrelated code.
- Add tests for every new success and failure path. Keep default CI credential-free with provider mocks/fakes.
- Never invent an answer when retrieval has no support. Preserve source-level citations and no-context refusal behavior.
- Keep secrets server-side and out of source control, logs, screenshots, test fixtures, and reports.
- Do not claim persistence, health, streaming, or live provider quality unless the actual implementation and runtime evidence demonstrate it.
- Use safe DOM construction, accessible controls, responsive layouts, and honest unsupported-browser states.
- Keep the application runnable after every phase and update README/docs whenever setup or architecture changes.
- If an external provider contract is uncertain, inspect its current official docs/source before coding the adapter.

## Verification required

For every phase:

1. Run the entire automated test suite, not only new tests.
2. Run JavaScript syntax checks and relevant type/static checks added later.
3. Exercise the changed flow in the real application, including a primary success path and a failure/fallback path.
4. Verify no unexpected browser console errors, missing assets, or unauthorized data access.
5. For Docker/deployment changes, perform a clean build/start and check health plus one real API request.
6. Use mocks in CI; perform separately authorized live checks for configured providers and label those results distinctly.

## Delivery report

After each phase, provide:

- implemented capabilities and changed architecture;
- migrations/setup required;
- automated and runtime verification evidence;
- providers tested with mocks versus live services;
- remaining risks and the next acceptance gate.

At the end, give a precise capability matrix showing what is complete, partial, or intentionally excluded. Do not call the whole module production-complete while any acceptance gate remains unmet.
