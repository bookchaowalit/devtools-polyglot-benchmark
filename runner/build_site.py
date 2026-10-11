"""Collect published results into site/data.json for the static page.

Quick (smoke) runs are never published.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    runs = []
    for run_file in sorted((ROOT / "results").glob("*/run.json"), key=lambda f: json.loads(f.read_text())["started_at"]):
        run = json.loads(run_file.read_text())
        if run["settings"].get("quick"):
            continue
        results = [
            json.loads(p.read_text())
            for p in sorted(run_file.parent.glob("W*.json"))
        ]
        runs.append({"id": run_file.parent.name, **run, "results": results})
    out = ROOT / "site" / "data.json"
    out.write_text(json.dumps({"schema": "polyglot-benchmark-lab.site.v1", "runs": runs}, indent=1) + "\n")
    print(f"{out.relative_to(ROOT)}: {len(runs)} run(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
