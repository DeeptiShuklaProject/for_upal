---
name: professor-qa
description: Implement, extend, debug, or verify the Socratic Voice Console professor Q&A module. Use when working on its FastAPI orchestration, browser console, personas, API contracts, offline fallback, production phases, or end-to-end module delivery in Devin.
---

# Professor Q&A module

Preserve a runnable, credential-free vertical slice while extending the module. Read `README.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, and the relevant phase in `docs/PRODUCTION_ROADMAP.md` before changing scope.

## Work vertically

1. Identify the user-visible outcome and the phase acceptance gate.
2. Trace the existing path: `main.py` → `ProfessorService` → retrieval/answer/speech routers → browser.
3. Reuse the current contracts; do not replace the application with a parallel stack or static mock.
4. Implement the smallest coherent slice across API, orchestration, UI, docs, and tests.
5. Keep offline answers and browser speech operational after every change.
6. Run the complete verification suite and exercise the primary flow in a real runtime.

## Preserve invariants

- Retrieve before answering; fail closed when no source context exists.
- Return source IDs and excerpts with grounded answers.
- Keep provider configuration and credentials on the server.
- Treat provider configuration and live provider health as different states.
- Degrade provider failures to offline answers and/or browser speech without losing the text answer.
- Keep transcript persistence claims aligned with actual storage. The MVP stores transcript state only in the page.
- Render user/model text safely with `textContent`.

## Verify

```bash
pip install -r requirements-dev.txt
pytest
node --check static/app.js
python tests/browser_smoke.py  # with Playwright installed and the app running
npm run build && npm start       # verify the host deployment launcher
```

For UI work, also check the primary question flow, source disclosure, clear/stop controls, unsupported-browser behavior, desktop/mobile layout, keyboard focus, and zero unexpected console/404 errors. For deployment work, build the Docker image and check `/api/health`.

## Report completion

State the implemented phase, tests actually run, live providers actually exercised (if any), and remaining limitations. Never convert mocked provider tests into claims of live voice generation.
