# Polyglot Benchmark Lab

What exists today. Lanes, workloads and run steps are in [README.md](README.md).

## Purpose

Implement the same five workloads (JSON, hashing, HTTP read, HTTP + PostgreSQL, cold start) in
Python, TypeScript, Go and Rust plus single-change variants, require every lane to pass one
contract, then measure them the same way and publish every number with its run record.

## Users

The owner, as evidence for language/framework choices and as a portfolio lab. No external users.

## What works

- 4 core lanes and 13 variant lanes (`runner/lanes.py`, code under `impl/`).
- `contract/check.py` checks each lane's output exactly; a lane that fails gets no metrics.
- `runner/run.py` measures (GNU time for RSS, `oha` for HTTP load, pinned CPU halves);
  `runner/build_site.py` builds `site/data.json` from non-quick runs.
- `.github/workflows/bench.yml` runs every group on GitHub-hosted runners, manually and every
  Monday 02:00 UTC, and commits results back. On 2026-10-22 the page held 21 published runs, the
  latest from the scheduled run of 2026-10-19 (all recent bench runs succeeded).
- Tests: `tests/test_contract.py` (starts every lane's server against PostgreSQL, including a
  deliberately wrong lane) runs in `contract.yml`; stdlib unit tests for the lane registry, the
  site builder and the summary maths run in `ci.yml` too, with Ruff, `tsc` for the TypeScript
  lanes and the shared security scans.

## Live

<https://polyglot-benchmark-lab.vercel.app> (Vercel, root `site/`, deploys on every push to
`main`, including the bench results commit). Answered HTTP 200 on 2026-10-22.

## Limits

- GitHub-hosted runners are shared VMs: numbers are comparable within one run/VM, not across
  runs or with other hardware. The page has a "What these results cannot tell you" section.
- Variants change one thing each; they say nothing about production tuning.
- No Sentry: the only "runtime" is the scheduled benchmark job. Lane servers live for seconds and
  an SDK would change what is measured; a failed run already fails the workflow.

Sentry waiver: the only runtime is the scheduled benchmark job; lane servers live for seconds and an SDK would change what is measured, while a failed run already fails the workflow.

## Disposition

Lab / showcase (product card verdict `showcase`). Keep; the weekly schedule keeps it current.
