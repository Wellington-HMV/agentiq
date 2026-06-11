"""Build the static GitHub Pages demo of the AGENTIQ factory.

Copies the web front-end into ``docs/demo/`` and embeds real run data from the
local store as ``demo-data.js``. A tiny ``fetch`` shim serves the embedded data
in place of the API, so the exact same modules (reducer/scene/app) that power
the live product power the demo — cinema mode only, no server.

Usage:
    python -m uv run python scripts/build_demo.py <run_id> [<run_id> ...]
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from agentiq.core.run import find_run_dir
from agentiq.events.reader import read_events

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "src" / "agentiq" / "web" / "static"
OUT = ROOT / "docs" / "demo"

_SHIM = """\
<script src="./demo-data.js"></script>
<script>
  // Static demo: serve the embedded run data instead of the API.
  const realFetch = window.fetch.bind(window);
  window.fetch = (url, opts) => {
    const path = String(url);
    const json = (body, status = 200) =>
      Promise.resolve(new Response(JSON.stringify(body), { status }));
    if (path.endsWith("/api/runs") && (!opts || !opts.method || opts.method === "GET"))
      return json(window.DEMO.runs);
    let m = path.match(/\\/api\\/runs\\/([^/]+)\\/events$/);
    if (m) {
      const run = window.DEMO.data[m[1]];
      return run ? json(run.events) : json({ detail: "no run" }, 404);
    }
    m = path.match(/\\/api\\/runs\\/([^/]+)\\/summary$/);
    if (m) {
      const run = window.DEMO.data[m[1]];
      return run && run.summary ? json(run.summary) : json({ detail: "none" }, 404);
    }
    if (path.includes("/api/")) return json({ detail: "demo" }, 404);
    return realFetch(url, opts);
  };
  // No live runs in a static demo: WebSocket connections just stay silent.
  window.WebSocket = class { close() {} };
</script>
"""


def export_run(run_id: str) -> dict[str, object]:
    run_dir = find_run_dir(run_id)
    if run_dir is None:
        raise SystemExit(f"no run {run_id!r} in the store")
    events = [e.model_dump() for e in read_events(run_dir / "events.jsonl")]
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    summary = None
    if (run_dir / "summary.json").is_file():
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    cost = (summary or {}).get("cost_usd")
    listing = {
        "run_id": run_id,
        "goal": meta.get("goal", ""),
        "status": meta.get("status", "completed"),
        "cost_usd": cost,
        "duration_seconds": (summary or {}).get("duration_seconds"),
    }
    return {"listing": listing, "events": events, "summary": summary}


def main() -> None:
    run_ids = sys.argv[1:]
    if not run_ids:
        raise SystemExit("usage: build_demo.py <run_id> [<run_id> ...]")

    OUT.mkdir(parents=True, exist_ok=True)
    for asset in STATIC.iterdir():
        if asset.is_file():
            shutil.copy2(asset, OUT / asset.name)

    runs = []
    data = {}
    for run_id in run_ids:
        exported = export_run(run_id)
        runs.append(exported["listing"])
        data[run_id] = {"events": exported["events"], "summary": exported["summary"]}
    (OUT / "demo-data.js").write_text(
        "window.DEMO = " + json.dumps({"runs": runs, "data": data}) + ";\n",
        encoding="utf-8",
    )

    index = (STATIC / "index.html").read_text(encoding="utf-8")
    index = index.replace("/static/", "./")
    index = index.replace(
        '<script type="module" src="./app.js"></script>',
        _SHIM + '\n  <script type="module" src="./app.js"></script>',
    )
    index = index.replace(
        "Pick a run ▸ &nbsp;(● LIVE = watch in real time)",
        "Demo estática — escolha um run real ao lado e assista ▸",
    )
    index = index.replace(
        "● tempo real — runs ativos entram como LIVE; runs antigos reproduzem sozinhos",
        "demo gravada de runs reais — o produto completo roda local: "
        "<code>agentiq web</code>",
    )
    (OUT / "index.html").write_text(index, encoding="utf-8")
    print(f"demo built at {OUT} ({len(runs)} runs embedded)")


if __name__ == "__main__":
    main()
