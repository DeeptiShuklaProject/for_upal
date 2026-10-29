import { execFileSync } from "node:child_process";
import { cpSync, copyFileSync, existsSync, mkdirSync, readdirSync, unlinkSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");
const runtime = path.join(dist, "runtime");
const python = process.env.PYTHON_BIN || "python3";

function removeTree(target) {
  if (existsSync(target)) {
    const cleanup = [
      "import shutil,sys,time",
      "path=sys.argv[1]",
      "for attempt in range(20):",
      "    try:",
      "        shutil.rmtree(path)",
      "        break",
      "    except FileNotFoundError:",
      "        break",
      "    except OSError:",
      "        if attempt == 19:",
      "            raise",
      "        time.sleep(0.25)",
    ].join("\n");
    execFileSync(python, ["-c", cleanup, target], { stdio: "inherit" });
  }
}

function removeBytecode(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      removeBytecode(target);
    } else if (entry.name.endsWith(".pyc")) {
      unlinkSync(target);
    }
  }
}

removeTree(dist);
mkdirSync(runtime, { recursive: true });

for (const file of ["main.py", "index.html", "requirements.lock"]) {
  copyFileSync(path.join(root, file), path.join(runtime, file));
}
for (const directory of ["professor_qa", "data", "static"]) {
  cpSync(path.join(root, directory), path.join(runtime, directory), {
    recursive: true,
    filter: (source) => !source.includes("__pycache__") && !source.endsWith(".pyc"),
  });
}
copyFileSync(path.join(root, "preview", "server.mjs"), path.join(dist, "boot.js"));

execFileSync(
  python,
  [
    "-m",
    "pip",
    "install",
    "--disable-pip-version-check",
    "--no-cache-dir",
    "--no-compile",
    "--target",
    path.join(runtime, "_packages"),
    "-r",
    path.join(root, "requirements.lock"),
  ],
  { cwd: root, stdio: "inherit" },
);

const packages = path.join(runtime, "_packages");
for (const entry of readdirSync(packages)) {
  if (
    ["uvloop", "httptools", "watchfiles", "websockets", "yaml", "bin"].includes(entry) ||
    /^(uvloop|httptools|watchfiles|websockets|pyyaml)-.*\.dist-info$/.test(entry)
  ) {
    removeTree(path.join(packages, entry));
  }
}
removeBytecode(packages);

console.log("Built dist/boot.js with the FastAPI runtime and locked Python dependencies.");
