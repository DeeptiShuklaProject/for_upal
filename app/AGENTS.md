# Repository working agreement

## Mission

Build a grounded, low-latency professor Q&A module with local and cloud answer/voice providers. Preserve a credential-free offline path at all times.

## Read first

1. `README.md` — run commands, current scope, and boundaries.
2. `docs/ARCHITECTURE.md` — component contracts and request flow.
3. `docs/VOICE_PROVIDERS.md` — external speech API contracts.
4. `docs/DEPLOYMENT.md` — container, TLS, proxy, and public-demo rules.
5. `docs/PRODUCTION_ROADMAP.md` — target phases and acceptance gates.
6. Relevant `.agents/skills/*/SKILL.md` before changing that subsystem.

## Commands

```bash
pip install -r requirements-dev.txt
python main.py                    # http://localhost:8000
pytest                           # 34 offline contract/deployment tests
node --check static/app.js        # browser JavaScript syntax
python tests/browser_smoke.py     # optional; requires Playwright + running app
docker compose up --build -d      # reproducible local container deployment
npm run check                     # launcher and browser JavaScript syntax
npm run build && npm start        # self-contained host deployment on port 3000
```

## Non-negotiables

- Do not return an invented answer when retrieval has no supporting context.
- Keep API keys and voice-service credentials server-side; never commit `.env` or print secrets in logs/tests.
- A provider outage must not discard a grounded text answer. Degrade to offline answers and/or browser speech with a visible warning.
- Keep provider-specific HTTP details inside adapters. The orchestrator depends on provider-agnostic result contracts.
- Do not claim a provider is healthy merely because environment variables exist. Configuration and live health are different states.
- Do not replace the working offline application with a mock, screenshot, or API-only shell.
- Do not add persistence, accounts, usage tracking, or external calls without documenting them.
- Use safe DOM construction (`textContent`) for user/model content; do not inject it with `innerHTML`.
- Keep the UI keyboard-operable, responsive, and honest about unsupported browser capabilities.

## Change protocol

1. Make the smallest coherent vertical change.
2. Add or update offline tests before considering the change complete.
3. Run `pytest` and `node --check static/app.js`.
4. For UI changes, verify desktop and mobile in a real browser, including the primary ask flow and error states.
5. For deployment changes, run `npm run build && npm start` and check `/api/health` through `dist/boot.js`; build the Docker image when available.
6. For provider changes, use `httpx.MockTransport` or provider fakes in tests. Live credentials are not required for CI.
7. Update README/docs when contracts, setup, or limitations change.
8. Report what was tested and what remains unimplemented; never imply live provider tests occurred when only mocks ran.

## Current test baseline

34 contract/deployment tests pass without credentials or local voice services. The browser regression script covers five additional end-to-end scenarios. Increase these baselines as functionality grows.
