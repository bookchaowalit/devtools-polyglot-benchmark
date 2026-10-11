# Workloads

Every lane implements the same behavior. The contract tests in `contract/`
check it before any measurement runs.

| ID | What a lane must do | Measured |
|---|---|---|
| `W1-json` | Read `.cache/records.json` (path in argv[1]), print one JSON object: `count`, `total_value_cents` (sum of `price_cents * qty`), `by_tag` (tag → record count), `top5` (ids of the five highest `price_cents * qty`, ties by lower id). | wall time, peak RSS |
| `W2-hash` | Stream `.cache/blob.bin` (path in argv[1]) in 1 MiB chunks, print the lowercase SHA-256 hex digest. | wall time, MiB/s, peak RSS |
| `W3-http-read` | Serve on `PORT`. `GET /health` → `200 {"status":"ok"}`. `GET /items/{id}` → `200` with the record from `RECORDS_PATH`, or `404 {"error":"not_found"}` for an unknown or non-numeric id. | RPS, p50/p95/p99, errors, peak RSS |
| `W5-cold-start` | Same server as W3. | ms from process start to the first `200` on `/health` |

`W4-http-db` (PostgreSQL) comes later; it needs a database service container,
which the owner's machine does not have.

Each lane uses its language's idiomatic default libraries (stdlib JSON and
hashing, one mainstream HTTP framework, one process). A lane that swaps in a
faster library is a new lane with its own name, not a silent change.
