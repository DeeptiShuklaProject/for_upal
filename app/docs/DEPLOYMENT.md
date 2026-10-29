# Deploy the prototype

## One-command local deployment

Requires Docker with the Compose plugin.

```bash
cp .env.example .env       # optional; offline defaults need no values
docker compose up --build -d
```

Open **http://localhost:8000**. The Compose service binds to `127.0.0.1` by default so it is not exposed to the LAN unintentionally.

```bash
docker compose ps
docker compose logs -f professor-console
docker compose down
```

The image installs the pinned `requirements.lock`, runs as a non-root user, uses a read-only root filesystem under Compose, and checks `/api/health` for readiness.

## Hosts that require a Node entry point

Use the included compatibility launcher when the deployment platform expects `package.json` and `dist/boot.js`:

```bash
npm install
npm run build
npm start
```

The build produces `dist/boot.js` plus `dist/runtime/` with the FastAPI source and locked Python dependencies. `npm start` listens on `PORT` (default `3000`) and proxies to a private Uvicorn listener on `APP_INTERNAL_PORT` (default `8000`, or `8001` when `PORT=8000`). For source development, `npm run dev` uses the same proxy without building `dist/`.

The launcher requires Node 20+ and Python 3.12+ during build/start. It does not need an npm dependency installation at runtime.

## Generic container

```bash
docker build -t socratic-voice-console:0.2.1 .
docker run --rm \
  -p 127.0.0.1:8000:8000 \
  --env-file .env \
  --add-host=host.docker.internal:host-gateway \
  socratic-voice-console:0.2.1
```

`PORT` defaults to `8000`. The container healthcheck honors a custom `PORT` value.

## Public preview or server deployment

1. Terminate TLS at the platform or reverse proxy. Browsers normally require a secure context for microphone access outside localhost.
2. Serve the application at the domain root. The current UI intentionally uses `/api/*` and `/static/*`; sub-path mounting requires a separate base-path change.
3. Set `FORWARDED_ALLOW_IPS` to the actual proxy IP/network, not `*`, so only trusted proxies can supply forwarded client/scheme headers.
4. Keep `.env` and all provider credentials in the platform's secret manager. Never place secrets in the image or client.
5. Check `GET /api/health` after startup and one offline `POST /api/ask` before routing traffic.

Example proxy environment:

```bash
FORWARDED_ALLOW_IPS=10.0.0.10
```

The container starts Uvicorn with proxy-header support. Without a reverse proxy, the default `127.0.0.1` trust setting is appropriate.

## Public-demo safety

The prototype has no account system or persistent quota service. The safest public-demo configuration is the default offline answerer plus browser speech. **Do not expose paid OpenAI/ElevenLabs providers directly to anonymous traffic.** Put those deployments behind authentication, server-side quotas, rate limiting, and cost alerts first.

API request bodies are capped at 32 KB, provider audio at 25 MB, and provider calls have explicit deadlines. These limits reduce accidental resource exhaustion but do not replace authorization or anti-abuse controls.

## Provider networking

When local voice services run on the Docker host, Compose supplies `host.docker.internal`. Set Voicebox/VoiceStudio credentials and profile/voice mappings in `.env` only when those services are intended to be reachable.

A hosted preview cannot access a voice service on your personal computer's loopback interface. Use a secured private endpoint or run the full stack on the same host/network.

## Operational notes

- The app has no database or uploaded files in this prototype, so replacement deployments do not require data migration.
- Transcript state is page-local and disappears on reload.
- Configuration exposure through `/api/config` does not indicate live provider health.
- Browser speech and speech recognition depend on the student's browser and installed voices.
- For reproducible deployments, rebuild from `requirements.lock`; use `requirements.txt` only when intentionally updating dependencies.
