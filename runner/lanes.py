"""Lane registry: how to run each language/framework implementation.

Adding a lane = one entry here + a directory under impl/ + a passing contract.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / "impl/python/.venv/bin/python")
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
    ]
}


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
    return any((Path(p) / cmd).exists() for p in os.environ.get("PATH", "").split(os.pathsep))


class Server:
    """Start a lane's HTTP server and wait until /health answers 200."""

    def __init__(self, lane: Lane, records: Path, timeout_s: float = 30.0) -> None:
        self.lane = lane
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        env = {**os.environ, "PORT": str(self.port), "RECORDS_PATH": str(records)}
        self.started = time.perf_counter()
        self.proc = subprocess.Popen(
            server_cpus() + lane.server, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        self.ready_ms = self._wait(timeout_s)

    def _wait(self, timeout_s: float) -> float:
        deadline = self.started + timeout_s
        while time.perf_counter() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"{self.lane.id} server exited: {self.proc.stderr.read().decode()[-500:]}")
            try:
                with urllib.request.urlopen(f"{self.url}/health", timeout=1) as resp:
                    if resp.status == 200:
                        return (time.perf_counter() - self.started) * 1000
            except OSError:
                time.sleep(0.005)
        raise TimeoutError(f"{self.lane.id} server not ready in {timeout_s}s")

    def peak_rss_mib(self) -> float:
        status = Path(f"/proc/{self.proc.pid}/status").read_text()
        for line in status.splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) / 1024
        return 0.0

    def __enter__(self) -> "Server":
        return self

    def __exit__(self, *exc: object) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
