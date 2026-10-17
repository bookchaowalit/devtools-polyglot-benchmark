"""Lane registry: how to run each language/framework implementation.

Adding a lane = one entry here + a directory under impl/ + a passing contract.

A variant lane has a `parent` and changes exactly one thing (`change`). It runs
in the same job as its parent, so the two are measured on the same VM and the
page can show the variant as a percentage of its parent.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / "impl/python/.venv/bin/python")
PY313 = str(ROOT / "impl/python/.venv313/bin/python")
ALL = ("W1-json", "W2-hash", "W3-http-read", "W4-http-db", "W5-cold-start")
HTTP = ("W3-http-read", "W4-http-db", "W5-cold-start")
TS = ROOT / "impl/typescript/dist"
GO = ROOT / "impl/go/bin"
RS = ROOT / "impl/rust/target/release"


@dataclass(frozen=True)
class Lane:
    id: str
    language: str
    framework: str
    version_cmd: list[str]
    w1: list[str]
    w2: list[str]
    server: list[str]
    group: str = "core"
    parent: str | None = None
    change: str = ""
    env: dict[str, str] = field(default_factory=dict)
    workloads: tuple[str, ...] = ALL


def _python_variant(
    id: str,
    change: str,
    workloads: tuple[str, ...],
    env: dict[str, str] | None = None,
    python: str = PY,
    parent: str = "python-fastapi",
) -> Lane:
    return Lane(
        id=id,
        language="python",
        framework="fastapi+uvicorn",
        version_cmd=[python, "--version"],
        w1=[python, str(ROOT / "impl/python/w1_json.py")],
        w2=[python, str(ROOT / "impl/python/w2_hash.py")],
        server=[python, str(ROOT / "impl/python/server.py")],
        group="python-variants",
        parent=parent,
        change=change,
        env=env or {},
        workloads=workloads,
    )


LANES: dict[str, Lane] = {
    lane.id: lane
    for lane in [
        Lane(
            id="python-fastapi",
            language="python",
            framework="fastapi+uvicorn",
            version_cmd=[PY, "--version"],
            w1=[PY, str(ROOT / "impl/python/w1_json.py")],
            w2=[PY, str(ROOT / "impl/python/w2_hash.py")],
            server=[PY, str(ROOT / "impl/python/server.py")],
        ),
        Lane(
            id="typescript-fastify",
            language="typescript",
            framework="fastify",
            version_cmd=["node", "--version"],
            w1=["node", str(TS / "w1-json.js")],
            w2=["node", str(TS / "w2-hash.js")],
            server=["node", str(TS / "server.js")],
        ),
        Lane(
            id="go-nethttp",
            language="go",
            framework="net/http",
            version_cmd=["go", "version"],
            w1=[str(GO / "w1-json")],
            w2=[str(GO / "w2-hash")],
            server=[str(GO / "server")],
        ),
        Lane(
            id="rust-axum",
            language="rust",
            framework="axum+tokio",
            version_cmd=["rustc", "--version"],
            w1=[str(RS / "w1-json")],
            w2=[str(RS / "w2-hash")],
            server=[str(RS / "server")],
        ),
        _python_variant(
            "python-fastapi+uvloop",
            "uvloop event loop + httptools parser (uvicorn[standard])",
            HTTP,
            {"BENCH_LOOP": "uvloop"},
        ),
        _python_variant(
            "python-fastapi+orjson",
            "orjson for JSON (ORJSONResponse; orjson in W1)",
            ("W1-json", "W3-http-read", "W4-http-db"),
            {"BENCH_JSON": "orjson"},
        ),
        _python_variant(
            "python-fastapi+asyncpg",
            "asyncpg pool instead of psycopg_pool",
            ("W4-http-db",),
            {"BENCH_DB": "asyncpg"},
        ),
        # With the default h11 protocol, uvicorn's multi-worker mode never sets TCP_NODELAY on
        # connections, and h11 sends headers and body in two writes: Nagle + delayed ACK then add
        # ~40 ms to every request. Kept as measured, because that is what `--workers 2` does.
        _python_variant(
            "python-fastapi+2workers",
            "2 uvicorn workers (h11), 5 DB connections each",
            HTTP,
            {"BENCH_WORKERS": "2"},
        ),
        _python_variant(
            "python-fastapi+uvloop+2workers",
            "2 uvicorn workers on uvloop + httptools",
            HTTP,
            {"BENCH_LOOP": "uvloop", "BENCH_WORKERS": "2"},
            parent="python-fastapi+uvloop",
        ),
        _python_variant(
            "python-fastapi+py313", "CPython 3.13 instead of 3.12", ALL, python=PY313
        ),
    ]
}


def _ts_variant(
    id: str,
    change: str,
    workloads: tuple[str, ...],
    env: dict[str, str] | None = None,
    runtime: str = "node",
    server: str = "server.js",
    framework: str = "fastify",
) -> Lane:
    return Lane(
        id=id,
        language="typescript",
        framework=framework,
        version_cmd=[runtime, "--version"],
        w1=[runtime, str(TS / "w1-json.js")],
        w2=[runtime, str(TS / "w2-hash.js")],
        server=[runtime, str(TS / server)],
        group="typescript-variants",
        parent="typescript-fastify",
        change=change,
        env=env or {},
        workloads=workloads,
    )


LANES.update(
    {
        lane.id: lane
        for lane in [
            _ts_variant(
                "typescript-fastify+bun",
                "Bun runtime instead of Node (same compiled JS)",
                ALL,
                runtime="bun",
            ),
            _ts_variant(
                "typescript-hono",
                "Hono (@hono/node-server) instead of Fastify",
                HTTP,
                server="server-hono.js",
                framework="hono",
            ),
            _ts_variant(
                "typescript-fastify+postgresjs",
                "postgres.js instead of node-postgres (pg)",
                ("W4-http-db",),
                {"BENCH_DB": "postgresjs"},
            ),
            _ts_variant(
                "typescript-fastify+cluster",
                "node:cluster with 2 processes, 5 DB connections each",
                HTTP,
                {"BENCH_WORKERS": "2"},
            ),
        ]
    }
)


def _framework_variant(
    id: str, parent: str, language: str, framework: str, server: Path, change: str
) -> Lane:
    base = LANES[parent]
    return Lane(
        id=id,
        language=language,
        framework=framework,
        version_cmd=base.version_cmd,
        w1=base.w1,
        w2=base.w2,
        server=[str(server)],
        group="go-rust-variants",
        parent=parent,
        change=change,
        workloads=HTTP,
    )


LANES.update(
    {
        lane.id: lane
        for lane in [
            _framework_variant(
                "go-gin",
                "go-nethttp",
                "go",
                "gin",
                GO / "server-gin",
                "Gin instead of net/http",
            ),
            _framework_variant(
                "go-fiber",
                "go-nethttp",
                "go",
                "fiber (fasthttp)",
                GO / "server-fiber",
                "Fiber v2 on fasthttp instead of net/http",
            ),
            _framework_variant(
                "rust-actix",
                "rust-axum",
                "rust",
                "actix-web",
                RS / "server-actix",
                "actix-web instead of axum",
            ),
        ]
    }
)

GROUPS = sorted({lane.group for lane in LANES.values()})


def lanes_in(group: str) -> list[str]:
    """The group's lanes, plus the parents of its variants, parents first."""
    ids = [lane.id for lane in LANES.values() if lane.group == group]
    parents = [
        LANES[i].parent for i in ids if LANES[i].parent and LANES[i].parent not in ids
    ]
    return list(dict.fromkeys(parents + ids))


def runtime_version(lane: Lane) -> str:
    out = subprocess.run(lane.version_cmd, capture_output=True, text=True, check=True)
    return (out.stdout or out.stderr).strip()


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def server_cpus() -> list[str]:
    """Pin the server to half the cores so the load generator gets the rest."""
    cores = os.cpu_count() or 1
    if cores < 4 or not _has("taskset"):
        return []
    half = cores // 2
    return ["taskset", "-c", f"0-{half - 1}"]


def load_cpus() -> list[str]:
    cores = os.cpu_count() or 1
    if cores < 4 or not _has("taskset"):
        return []
    return ["taskset", "-c", f"{cores // 2}-{cores - 1}"]


def _has(cmd: str) -> bool:
    return any(
        (Path(p) / cmd).exists() for p in os.environ.get("PATH", "").split(os.pathsep)
    )


def _descendants(pid: int) -> list[int]:
    found = []
    try:
        children = Path(f"/proc/{pid}/task/{pid}/children").read_text().split()
    except OSError:
        return found
    for child in map(int, children):
        found += [child, *_descendants(child)]
    return found


class Server:
    """Start a lane's HTTP server and wait until /health answers 200."""

    def __init__(self, lane: Lane, records: Path, timeout_s: float = 30.0) -> None:
        self.lane = lane
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        env = {
            **os.environ,
            **lane.env,
            "PORT": str(self.port),
            "RECORDS_PATH": str(records),
        }
        self.started = time.perf_counter()
        self.proc = subprocess.Popen(
            server_cpus() + lane.server,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self.ready_ms = self._wait(timeout_s)

    def _wait(self, timeout_s: float) -> float:
        deadline = self.started + timeout_s
        while time.perf_counter() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f"{self.lane.id} server exited: {self.proc.stderr.read().decode()[-500:]}"
                )
            try:
                with urllib.request.urlopen(f"{self.url}/health", timeout=1) as resp:
                    if resp.status == 200:
                        return (time.perf_counter() - self.started) * 1000
            except OSError:
                time.sleep(0.005)
        raise TimeoutError(f"{self.lane.id} server not ready in {timeout_s}s")

    def peak_rss_mib(self) -> float:
        """Sum of peak RSS over the server and its descendants (uvicorn workers, taskset child)."""
        total = 0
        for pid in [self.proc.pid, *_descendants(self.proc.pid)]:
            try:
                for line in Path(f"/proc/{pid}/status").read_text().splitlines():
                    if line.startswith("VmHWM:"):
                        total += int(line.split()[1])
            except OSError:
                pass
        return total / 1024

    def __enter__(self) -> "Server":
        return self

    def __exit__(self, *exc: object) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
