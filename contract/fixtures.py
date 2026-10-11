"""Deterministic fixtures shared by every lane.

A small LCG keeps the bytes identical on every machine and Python version, so
a fixture hash mismatch means the generator changed, not the platform.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
RECORDS = CACHE / "records.json"
BLOB = CACHE / "blob.bin"

RECORD_COUNT = 10_000
BLOB_BYTES = 100 * 1024 * 1024
TAGS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]


class Lcg:
    def __init__(self, seed: int) -> None:
        self.state = seed & 0xFFFFFFFF

    def next(self) -> int:
        self.state = (1664525 * self.state + 1013904223) & 0xFFFFFFFF
        return self.state


def build_records() -> list[dict]:
    rng = Lcg(20261010)
    records = []
    for i in range(1, RECORD_COUNT + 1):
        tag_count = 1 + rng.next() % 3
        tags = sorted({TAGS[rng.next() % len(TAGS)] for _ in range(tag_count)})
        records.append(
            {
                "id": i,
                "name": f"item-{i:05d}",
                "price_cents": 100 + rng.next() % 99_900,
                "qty": 1 + rng.next() % 50,
                "tags": tags,
            }
        )
    return records


def ensure_records() -> Path:
    if not RECORDS.exists():
        CACHE.mkdir(exist_ok=True)
        RECORDS.write_text(json.dumps(build_records(), separators=(",", ":")))
    return RECORDS


def ensure_blob() -> Path:
    if not BLOB.exists() or BLOB.stat().st_size != BLOB_BYTES:
        CACHE.mkdir(exist_ok=True)
        rng = Lcg(42)
        chunk = bytes(rng.next() & 0xFF for _ in range(1024 * 1024))
        with BLOB.open("wb") as fh:
            for _ in range(BLOB_BYTES // len(chunk)):
                fh.write(chunk)
    return BLOB


def expected_w1(records: list[dict]) -> dict:
    by_tag: dict[str, int] = {}
    for r in records:
        for t in r["tags"]:
            by_tag[t] = by_tag.get(t, 0) + 1
    ranked = sorted(records, key=lambda r: (-(r["price_cents"] * r["qty"]), r["id"]))
    return {
        "count": len(records),
        "total_value_cents": sum(r["price_cents"] * r["qty"] for r in records),
        "by_tag": dict(sorted(by_tag.items())),
        "top5": [r["id"] for r in ranked[:5]],
    }


if __name__ == "__main__":
    print(ensure_records())
    print(ensure_blob())
