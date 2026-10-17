"""Build nothing, check the contract, then measure.

    python runner/run.py                       # all lanes, all workloads, full settings
    python runner/run.py --quick               # smoke run: short, one repeat, not for publishing
    python runner/run.py --group python-variants   # variants + their parent, same VM
    python runner/run.py --lanes python-fastapi --workloads W3-http-read

Writes results/<YYYY-MM-DDTHHMMZ>-<runner>-<group>/<workload>.<lane>.json and run.json.
A lane that fails its contract gets a result with contract_passed=false and no metrics.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contract.check import check_lane
from contract.fixtures import BLOB_BYTES, ensure_blob, ensure_records
from runner.lanes import (
    GROUPS,
    LANES,
    Lane,
    Server,
    lanes_in,
    load_cpus,
    runtime_version,
)

ROOT = Path(__file__).resolve().parent.parent
OHA_VERSION = "1.16.0"
GNU_TIME = "/usr/bin/time"
WORKLOADS = ["W1-json", "W2-hash", "W3-http-read", "W4-http-db", "W5-cold-start"]
SCHEMA = "polyglot-benchmark-lab.result.v1"


def oha_path() -> str:
    found = shutil.which("oha")
    if found:
        return found
    local = ROOT / ".tools" / "oha"
    if not local.exists():
        local.parent.mkdir(exist_ok=True)
        url = f"https://github.com/hatoo/oha/releases/download/v{OHA_VERSION}/oha-linux-amd64"
        urllib.request.urlretrieve(url, local)
        local.chmod(0o755)
    return str(local)


def git_commit() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip() or "uncommitted"


def runner_info() -> dict:
    return {
        "kind": os.environ.get(
            "BENCH_RUNNER",
            "github-hosted" if os.environ.get("GITHUB_ACTIONS") else "local",
        ),
        "os": platform.platform(),
        "machine": platform.machine(),
        "vcpu": os.cpu_count(),
        "cpu_model": _cpu_model(),
    }


def _cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def run_child(cmd: list[str], env: dict[str, str]) -> tuple[float, float]:
    """Return (wall seconds, peak RSS MiB) for one child process.

    Peak RSS comes from GNU time, not from our own wait4: a child spawned from
    this Python process inherits our RSS high-water mark across exec, which
    would hide the real footprint of small runtimes.
    """
    with tempfile.NamedTemporaryFile("r", suffix=".rss") as rss_file:
        start = time.perf_counter()
        proc = subprocess.run(
            [GNU_TIME, "-f", "%M", "-o", rss_file.name, *cmd],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env={**os.environ, **env},
        )
        wall = time.perf_counter() - start
        if proc.returncode != 0:
            raise RuntimeError(f"{cmd} failed: {proc.stderr.decode()[-300:]}")
        return wall, int(rss_file.read().split()[-1]) / 1024


def spread(values: list[float]) -> dict:
    return {
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "runs": values,
    }


def measure_cli(
    cmd: list[str], env: dict[str, str], warmup: int, repeats: int
) -> tuple[list[float], list[float]]:
    for _ in range(warmup):
        run_child(cmd, env)
    walls, rss = [], []
    for _ in range(repeats):
        w, r = run_child(cmd, env)
        walls.append(w)
        rss.append(r)
    return walls, rss


def w1(lane: Lane, s: dict) -> dict:
    walls, rss = measure_cli(
        lane.w1 + [str(ensure_records())], lane.env, s["cli_warmup"], s["repeats"]
    )
    return {"wall_ms": spread([w * 1000 for w in walls]), "peak_rss_mib": max(rss)}


def w2(lane: Lane, s: dict) -> dict:
    walls, rss = measure_cli(
        lane.w2 + [str(ensure_blob())], lane.env, s["cli_warmup"], s["repeats"]
    )
    mib = BLOB_BYTES / (1024 * 1024)
    return {
        "wall_ms": spread([w * 1000 for w in walls]),
        "throughput_mib_s": spread([mib / w for w in walls]),
        "peak_rss_mib": max(rss),
    }


def oha(url: str, seconds: int, concurrency: int) -> dict:
    cmd = load_cpus() + [
        oha_path(),
        "-z",
        f"{seconds}s",
        "-c",
        str(concurrency),
        "--no-tui",
        "--output-format",
        "json",
        "-w",
        "--rand-regex-url",
        url,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def w3(lane: Lane, s: dict) -> dict:
    # ids 1..9999 all exist, so every request should be a 200
    return http_load(lane, s, r"/items/[1-9][0-9]{0,3}")


def w4(lane: Lane, s: dict) -> dict:
    # pages of 50 rows from a random starting id; "?" is escaped for oha's regex
    return http_load(lane, s, r"/db/items\?after=[0-9]{1,4}&limit=50")


def http_load(lane: Lane, s: dict, path_regex: str) -> dict:
    rps, p50, p95, p99, errors = [], [], [], [], []
    with Server(lane, ensure_records()) as srv:
        url = srv.url + path_regex
        oha(url, s["http_warmup_s"], s["concurrency"])
        for _ in range(s["repeats"]):
            r = oha(url, s["http_seconds"], s["concurrency"])
            codes = r.get("statusCodeDistribution", {})
            total = sum(codes.values()) + sum(r.get("errorDistribution", {}).values())
            rps.append(r["summary"]["requestsPerSec"])
            p50.append(r["latencyPercentiles"]["p50"] * 1000)
            p95.append(r["latencyPercentiles"]["p95"] * 1000)
            p99.append(r["latencyPercentiles"]["p99"] * 1000)
            errors.append(1 - codes.get("200", 0) / total if total else 1.0)
        peak = srv.peak_rss_mib()
    return {
        "rps": spread(rps),
        "p50_ms": spread(p50),
        "p95_ms": spread(p95),
        "p99_ms": spread(p99),
        "error_rate": max(errors),
        "peak_rss_mib": peak,
    }


def w5(lane: Lane, s: dict) -> dict:
    ready = []
    for _ in range(s["cold_repeats"]):
        with Server(lane, ensure_records()) as srv:
            ready.append(srv.ready_ms)
    return {"ready_ms": spread(ready)}


MEASURES = {
    "W1-json": w1,
    "W2-hash": w2,
    "W3-http-read": w3,
    "W4-http-db": w4,
    "W5-cold-start": w5,
}


def settings(quick: bool) -> dict:
    if quick:
        return {
            "repeats": 1,
            "cli_warmup": 1,
            "http_seconds": 3,
            "http_warmup_s": 1,
            "concurrency": 50,
            "cold_repeats": 3,
            "quick": True,
        }
    return {
        "repeats": 5,
        "cli_warmup": 2,
        "http_seconds": 30,
        "http_warmup_s": 10,
        "concurrency": 50,
        "cold_repeats": 10,
        "quick": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--group",
        choices=GROUPS,
        default="core",
        help="lane group; a variant group also runs its parents, in the same job",
    )
    ap.add_argument("--lanes", nargs="*", help="override the group's lanes")
    ap.add_argument("--workloads", nargs="*", default=WORKLOADS)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    args.lanes = args.lanes or lanes_in(args.group)

    s = settings(args.quick)
    info = runner_info()
    stamp = dt.datetime.now(dt.UTC)
    out = (
        args.out
        or ROOT
        / "results"
        / f"{stamp:%Y-%m-%dT%H%MZ}-{info['kind']}-{args.group}{'-quick' if args.quick else ''}"
    )
    out.mkdir(parents=True, exist_ok=True)
    commit = git_commit()
    workloads = list(args.workloads)
    if "W4-http-db" in workloads:
        if os.environ.get("DATABASE_URL"):
            subprocess.run(
                [
                    str(ROOT / "impl/python/.venv/bin/python"),
                    str(ROOT / "runner/seed_db.py"),
                ],
                check=True,
            )
        else:
            print("W4-http-db skipped: DATABASE_URL is not set", flush=True)
            workloads.remove("W4-http-db")

    db = os.environ.get("DATABASE_URL")
    (out / "run.json").write_text(
        json.dumps(
            {
                "schema": "polyglot-benchmark-lab.run.v1",
                "started_at": stamp.isoformat(),
                "commit": commit,
                "runner": info,
                "settings": s,
                "load_generator": f"oha {OHA_VERSION}",
                "group": args.group,
                "lanes": args.lanes,
                "workloads": workloads,
                "database": (
                    (
                        "postgres service container"
                        if os.environ.get("GITHUB_ACTIONS")
                        else "local postgres"
                    )
                    if db
                    else None
                ),
            },
            indent=2,
        )
        + "\n"
    )

    for lane_id in args.lanes:
        lane = LANES[lane_id]
        failures = check_lane(lane)
        version = runtime_version(lane)
        print(
            f"{lane_id} ({version}): contract {'PASS' if not failures else 'FAIL'}",
            flush=True,
        )
        for wl in [w for w in workloads if w in lane.workloads]:
            result = {
                "schema": SCHEMA,
                "workload": wl,
                "lane": lane_id,
                "commit": commit,
                "runner": info,
                "group": args.group,
                "parent": lane.parent,
                "change": lane.change,
                "runtime": {
                    "language": lane.language,
                    "version": version,
                    "framework": lane.framework,
                },
                "settings": s,
                "contract_passed": not failures,
            }
            if failures:
                result["contract_failures"] = failures
            else:
                result["metrics"] = MEASURES[wl](lane, s)
                print(
                    f"  {wl}: {json.dumps(_headline(wl, result['metrics']))}",
                    flush=True,
                )
            (out / f"{wl}.{lane_id}.json").write_text(
                json.dumps(result, indent=2) + "\n"
            )
    print(f"results: {out}")
    return 0


def _headline(wl: str, m: dict) -> dict:
    if wl in ("W3-http-read", "W4-http-db"):
        return {
            "rps": round(m["rps"]["median"]),
            "p95_ms": round(m["p95_ms"]["median"], 2),
            "rss_mib": round(m["peak_rss_mib"], 1),
            "errors": m["error_rate"],
        }
    if wl == "W5-cold-start":
        return {"ready_ms": round(m["ready_ms"]["median"], 1)}
    return {
        "wall_ms": round(m["wall_ms"]["median"], 1),
        "rss_mib": round(m["peak_rss_mib"], 1),
    }


if __name__ == "__main__":
    raise SystemExit(main())
