# Polyglot Benchmark Lab

Each language implements the same workloads. A lane must pass the same
contract tests before it is measured, and every published number keeps its
run record (commit, runner, runtime versions, settings).

Results page: <https://polyglot-benchmark-lab.vercel.app> (`site/`). Raw data: `results/`.

## Lanes

| Lane | Runtime | Framework |
|---|---|---|
| `python-fastapi` | Python 3.12 | FastAPI + uvicorn (one worker, no extras) |
| `typescript-fastify` | Node 22, compiled with `tsc` | Fastify |
| `go-nethttp` | Go (pinned in `impl/go/go.mod`) | stdlib `net/http`, pgx pool |
| `rust-axum` | Rust stable, `--release` | axum + tokio, deadpool-postgres |

All lanes use a pool of 10 PostgreSQL connections for W4. Adding a lane means one entry in
`runner/lanes.py`, a directory under `impl/`, and a passing contract.

## Workloads

See [workloads/README.md](workloads/README.md): `W1-json`, `W2-hash`,
`W3-http-read`, `W4-http-db`, `W5-cold-start`.

## Run it

Needs Python 3.12, Node 22, Go, Rust, `uv`, and GNU time (`/usr/bin/time`).
W4 needs `DATABASE_URL` pointing at a PostgreSQL you can drop a table in
(the runner seeds `bench_items`); without it, W4 is skipped. The runner
downloads `oha` 1.16.0 into `.tools/` if it is not on `PATH`.

```bash
uv sync --project impl/python
npm ci --prefix impl/typescript && npm run build --prefix impl/typescript
(cd impl/go && go build -o bin/ ./cmd/...)
(cd impl/rust && cargo build --release)
impl/python/.venv/bin/python runner/seed_db.py   # only with DATABASE_URL
python -m unittest discover -s tests       # contract, including a deliberately wrong lane
python runner/run.py --quick --out .cache/quick   # smoke run, never published
python runner/run.py                       # full run → results/<date>-<runner>/
python runner/build_site.py                # results → site/data.json
```

## How it measures

- **CLI workloads (W1, W2):** warm-up runs, then 5 measured runs. Wall time
  comes from the runner and peak RSS from GNU time. The child is not measured
  with our own `wait4`, because a process spawned from the runner inherits the
  runner's RSS high-water mark.
- **HTTP (W3):** the server is pinned to half the cores and `oha` to the other
  half. 10 s warm-up, then 5 × 30 s at 50 connections over random ids 1–9999.
  In-flight requests are allowed to finish at the deadline.
- **Cold start (W5):** 10 starts, measured from process spawn until `/health`
  returns 200.

The full run on GitHub-hosted runners is `.github/workflows/bench.yml`: manual
dispatch plus a weekly schedule. It commits the results back to this repository.

## Deploy

The Vercel project is connected to this repository with root directory
`site/`. Every push to `main`, including the bench workflow's results
commit, deploys the page; there is no manual step. A manual deploy, if ever
needed, runs from the repository root: `vercel deploy --prod`.

## Limits

Read the "What these results cannot tell you" section on the results page
before you quote a number.

## License

MIT
