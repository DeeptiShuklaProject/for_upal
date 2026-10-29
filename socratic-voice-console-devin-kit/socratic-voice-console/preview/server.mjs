import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const bundledRuntime = path.join(here, "runtime");
const runtime = existsSync(path.join(bundledRuntime, "main.py"))
  ? bundledRuntime
  : path.resolve(here, "..");
const host = process.env.HOST || "0.0.0.0";
const port = Number(process.env.PORT || 3000);
const internalPort = Number(process.env.APP_INTERNAL_PORT || (port === 8000 ? 8001 : 8000));
const internalHost = "127.0.0.1";
const python = process.env.PYTHON_BIN || "python3";
const packages = path.join(runtime, "_packages");
let shuttingDown = false;

const backend = spawn(
  python,
  [
    "-m",
    "uvicorn",
    "main:app",
    "--host",
    internalHost,
    "--port",
    String(internalPort),
    "--loop",
    "asyncio",
    "--http",
    "h11",
    "--proxy-headers",
    "--forwarded-allow-ips",
    internalHost,
  ],
  {
    cwd: runtime,
    env: {
      ...process.env,
      PYTHONPATH: [packages, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
      PYTHONUNBUFFERED: "1",
      PYTHONDONTWRITEBYTECODE: "1",
    },
    stdio: ["ignore", "inherit", "inherit"],
  },
);

backend.on("exit", (code, signal) => {
  if (!shuttingDown) {
    console.error(`FastAPI exited unexpectedly (code=${code}, signal=${signal}).`);
    process.exit(code || 1);
  }
});
backend.on("error", (error) => {
  console.error(`Unable to start Python: ${error.message}`);
  process.exit(1);
});

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function waitForBackend() {
  const healthUrl = `http://${internalHost}:${internalPort}/api/health`;
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (backend.exitCode !== null) throw new Error("FastAPI exited before becoming ready.");
    try {
      const response = await fetch(healthUrl, { signal: AbortSignal.timeout(1000) });
      if (response.ok) return;
    } catch {
      // Backend is still starting.
    }
    await sleep(250);
  }
  throw new Error("FastAPI did not become healthy within 30 seconds.");
}

const server = http.createServer((request, response) => {
  const forwardedFor = [request.headers["x-forwarded-for"], request.socket.remoteAddress]
    .filter(Boolean)
    .join(", ");
  const proxy = http.request(
    {
      hostname: internalHost,
      port: internalPort,
      path: request.url,
      method: request.method,
      headers: {
        ...request.headers,
        host: `${internalHost}:${internalPort}`,
        "x-forwarded-for": forwardedFor,
        "x-forwarded-host": request.headers.host || "",
        "x-forwarded-proto": request.headers["x-forwarded-proto"] || "http",
      },
    },
    (backendResponse) => {
      response.writeHead(backendResponse.statusCode || 502, backendResponse.headers);
      backendResponse.pipe(response);
    },
  );
  proxy.on("error", (error) => {
    if (!response.headersSent) {
      response.writeHead(502, { "Content-Type": "application/json", "Cache-Control": "no-store" });
      response.end(JSON.stringify({ detail: "The application backend is unavailable." }));
    } else {
      response.destroy(error);
    }
  });
  request.on("aborted", () => proxy.destroy());
  request.pipe(proxy);
});

function shutdown() {
  if (shuttingDown) return;
  shuttingDown = true;
  server.close(() => process.exit(0));
  backend.kill("SIGTERM");
  setTimeout(() => {
    backend.kill("SIGKILL");
    process.exit(0);
  }, 5000).unref();
}

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);

try {
  await waitForBackend();
  server.listen(port, host, () => {
    console.log(`Socratic Voice Console listening on http://${host}:${port}`);
  });
} catch (error) {
  console.error(error.message);
  backend.kill("SIGTERM");
  process.exit(1);
}
