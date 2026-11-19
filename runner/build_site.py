"""Collect published results into site/data/ for the static page.

site/data/index.json lists every published run (oldest first) without its results, so the page can
show the run picker straight away; site/data/runs/<id>.json holds one run with its results and is
fetched only when that run is opened. Quick (smoke) runs are never published.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "polyglot-benchmark-lab.site.v2"


def collect() -> list[dict]:
    runs = []
    for run_file in sorted(
        (ROOT / "results").glob("*/run.json"),
        key=lambda f: json.loads(f.read_text())["started_at"],
    ):
        run = json.loads(run_file.read_text())
        if run["settings"].get("quick"):
            continue
        results = [
            json.loads(p.read_text()) for p in sorted(run_file.parent.glob("W*.json"))
        ]
        runs.append({"id": run_file.parent.name, **run, "results": results})
    return runs


def main() -> int:
    runs = collect()
    out = ROOT / "site" / "data"
    shutil.rmtree(out, ignore_errors=True)
    (out / "runs").mkdir(parents=True)
    index = [{k: v for k, v in run.items() if k != "results"} for run in runs]
    (out / "index.json").write_text(
        json.dumps({"schema": SCHEMA, "runs": index}, separators=(",", ":")) + "\n"
    )
    for run in runs:
        (out / "runs" / f"{run['id']}.json").write_text(
            json.dumps(run, separators=(",", ":")) + "\n"
        )
    print(f"{out.relative_to(ROOT)}: {len(runs)} run(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
