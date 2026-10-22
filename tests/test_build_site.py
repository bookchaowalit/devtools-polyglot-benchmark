"""site/data.json is built only from published (non-quick) runs, oldest first."""

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner import build_site


def _write_run(
    root: Path, name: str, started_at: str, quick: bool, results: dict
) -> None:
    run_dir = root / "results" / name
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps({"started_at": started_at, "settings": {"quick": quick}})
    )
    for filename, body in results.items():
        (run_dir / filename).write_text(json.dumps(body))


class BuildSiteTest(unittest.TestCase):
    def build(self, root: Path) -> dict:
        (root / "site").mkdir()
        with mock.patch.object(build_site, "ROOT", root), redirect_stdout(StringIO()):
            self.assertEqual(build_site.main(), 0)
        return json.loads((root / "site" / "data.json").read_text())

    def test_skips_quick_runs_and_sorts_by_start_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(
                root,
                "b-late",
                "2026-10-12T00:00:00Z",
                False,
                {"W1-json.x.json": {"v": 2}},
            )
            _write_run(
                root,
                "a-early",
                "2026-10-11T00:00:00Z",
                False,
                {"W1-json.x.json": {"v": 1}},
            )
            _write_run(
                root,
                "c-smoke",
                "2026-10-13T00:00:00Z",
                True,
                {"W1-json.x.json": {"v": 3}},
            )
            data = self.build(root)
        self.assertEqual(data["schema"], "polyglot-benchmark-lab.site.v1")
        self.assertEqual([r["id"] for r in data["runs"]], ["a-early", "b-late"])
        self.assertEqual(data["runs"][0]["results"], [{"v": 1}])

    def test_only_workload_files_become_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(
                root,
                "r1",
                "2026-10-11T00:00:00Z",
                False,
                {
                    "W2-hash.a.json": {"w": 2},
                    "W1-json.a.json": {"w": 1},
                    "notes.json": {"x": 0},
                },
            )
            data = self.build(root)
        self.assertEqual(data["runs"][0]["results"], [{"w": 1}, {"w": 2}])

    def test_no_results_gives_an_empty_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "results").mkdir()
            self.assertEqual(self.build(root)["runs"], [])


if __name__ == "__main__":
    unittest.main()
