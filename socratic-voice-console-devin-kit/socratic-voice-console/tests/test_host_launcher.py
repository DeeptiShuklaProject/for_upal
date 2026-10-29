from __future__ import annotations

import json
from pathlib import Path

from professor_qa import __version__

ROOT = Path(__file__).resolve().parent.parent


def test_host_launcher_contract_and_version_are_present():
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["version"] == __version__
    assert package["scripts"]["dev"] == "node preview/server.mjs"
    assert package["scripts"]["build"] == "node scripts/build-preview.mjs"
    assert package["scripts"]["start"] == "node dist/boot.js"
    assert (ROOT / "preview" / "server.mjs").is_file()
    assert (ROOT / "scripts" / "build-preview.mjs").is_file()
