import json
import os
import sys

if os.environ.get("BENCH_JSON") == "orjson":
    import orjson

    def load(fh):
        return orjson.loads(fh.read())

    def dump(obj) -> str:
        return orjson.dumps(obj).decode()
else:

    def load(fh):
        return json.load(fh)

    def dump(obj) -> str:
        return json.dumps(obj, separators=(",", ":"))


def main(path: str) -> None:
    with open(path, "rb") as fh:
        records = load(fh)
    by_tag: dict[str, int] = {}
    total = 0
    for r in records:
        total += r["price_cents"] * r["qty"]
        for t in r["tags"]:
            by_tag[t] = by_tag.get(t, 0) + 1
    ranked = sorted(records, key=lambda r: (-(r["price_cents"] * r["qty"]), r["id"]))
    out = {
        "count": len(records),
        "total_value_cents": total,
        "by_tag": dict(sorted(by_tag.items())),
        "top5": [r["id"] for r in ranked[:5]],
    }
    sys.stdout.write(dump(out) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
