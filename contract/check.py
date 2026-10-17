"""Contract checks every lane must pass before it is measured.

python contract/check.py                 # all lanes
python contract/check.py python-fastapi  # one lane
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contract.fixtures import ensure_blob, ensure_records, expected_w1
from runner.lanes import LANES, Lane, Server


def _get(url: str) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def check_lane(lane: Lane) -> list[str]:
    failures: list[str] = []
    records_path = ensure_records()
    records = json.loads(records_path.read_text())

    env = {**os.environ, **lane.env}
    out = subprocess.run(
        lane.w1 + [str(records_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if out.returncode != 0:
        failures.append(f"W1 exit {out.returncode}: {out.stderr[-300:]}")
    elif json.loads(out.stdout) != expected_w1(records):
        failures.append("W1 output differs from expected")

    blob = ensure_blob()
    with blob.open("rb") as fh:
        want = hashlib.file_digest(fh, "sha256").hexdigest()
    out = subprocess.run(
        lane.w2 + [str(blob)], check=False, capture_output=True, text=True, env=env
    )
    if out.returncode != 0:
        failures.append(f"W2 exit {out.returncode}: {out.stderr[-300:]}")
    elif out.stdout.strip() != want:
        failures.append("W2 digest differs from expected")

    try:
        with Server(lane, records_path) as srv:
            cases = [
                ("/health", 200, {"status": "ok"}),
                ("/items/1", 200, records[0]),
                (f"/items/{len(records)}", 200, records[-1]),
                ("/items/999999", 404, {"error": "not_found"}),
                ("/items/abc", 404, {"error": "not_found"}),
            ]
            for path, status, body in cases:
                got_status, got_body = _get(srv.url + path)
                if (got_status, got_body) != (status, body):
                    failures.append(
                        f"W3 {path}: got {got_status} {str(got_body)[:120]}"
                    )
            if os.environ.get("DATABASE_URL"):
                db_cases = [
                    ("/db/items?after=0&limit=3", 200, {"items": records[:3]}),
                    ("/db/items?after=9998", 200, {"items": records[9998:]}),
                    ("/db/items?after=5&limit=0", 400, {"error": "bad_request"}),
                    ("/db/items?limit=abc", 400, {"error": "bad_request"}),
                ]
                for path, status, body in db_cases:
                    got_status, got_body = _get(srv.url + path)
                    if (got_status, got_body) != (status, body):
                        failures.append(
                            f"W4 {path}: got {got_status} {str(got_body)[:120]}"
                        )
    except (RuntimeError, TimeoutError) as err:
        failures.append(f"W3 server: {err}")
    return failures


def main(argv: list[str]) -> int:
    lane_ids = argv or list(LANES)
    bad = 0
    for lane_id in lane_ids:
        failures = check_lane(LANES[lane_id])
        print(f"{'PASS' if not failures else 'FAIL'} {lane_id}")
        for f in failures:
            print(f"  - {f}")
        bad += bool(failures)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
