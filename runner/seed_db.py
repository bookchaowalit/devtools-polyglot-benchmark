"""Load the W1 records into PostgreSQL for W4. Runs with the Python lane's venv (psycopg).

    impl/python/.venv/bin/python runner/seed_db.py   # uses DATABASE_URL

The seed drops and recreates a table, so it only runs against a database
named `bench`. Point DATABASE_URL at a dedicated database, never a shared one.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contract.fixtures import ensure_records  # noqa: E402

DDL = """
DROP TABLE IF EXISTS bench_items;
CREATE TABLE bench_items (
    id          integer PRIMARY KEY,
    name        text    NOT NULL,
    price_cents integer NOT NULL,
    qty         integer NOT NULL,
    tags        text[]  NOT NULL
);
"""


def main() -> int:
    records = json.loads(ensure_records().read_text())
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        database = conn.execute("SELECT current_database()").fetchone()[0]
        if database != "bench":
            print(f"refusing to seed database {database!r}: use a dedicated database named 'bench'", file=sys.stderr)
            return 2
        conn.execute(DDL)
        with conn.cursor().copy("COPY bench_items (id, name, price_cents, qty, tags) FROM STDIN") as copy:
            for r in records:
                copy.write_row((r["id"], r["name"], r["price_cents"], r["qty"], r["tags"]))
        conn.execute("ANALYZE bench_items")
        count = conn.execute("SELECT count(*) FROM bench_items").fetchone()[0]
    print(f"bench_items: {count} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
