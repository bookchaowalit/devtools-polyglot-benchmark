import json
import sys


def main(path: str) -> None:
    with open(path, encoding="utf-8") as fh:
        records = json.load(fh)
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
    sys.stdout.write(json.dumps(out, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
