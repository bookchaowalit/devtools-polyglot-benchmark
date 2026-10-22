"""Summary maths and settings used for every published number."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.run import _headline, settings, spread


class SpreadTest(unittest.TestCase):
    def test_median_min_max_and_raw_runs(self):
        out = spread([3.0, 1.0, 2.0, 10.0])
        self.assertEqual(out["median"], 2.5)
        self.assertEqual((out["min"], out["max"]), (1.0, 10.0))
        self.assertEqual(out["runs"], [3.0, 1.0, 2.0, 10.0])

    def test_single_value(self):
        self.assertEqual(spread([4.0])["median"], 4.0)


class SettingsTest(unittest.TestCase):
    def test_quick_is_marked_and_smaller(self):
        quick, full = settings(True), settings(False)
        self.assertTrue(quick["quick"])
        self.assertFalse(full["quick"])
        self.assertEqual(set(quick), set(full))
        for key in ("repeats", "http_seconds", "cold_repeats"):
            self.assertLess(quick[key], full[key], key)
        # Same concurrency so a quick run exercises the same load shape.
        self.assertEqual(quick["concurrency"], full["concurrency"])


class HeadlineTest(unittest.TestCase):
    def test_http_workloads(self):
        m = {
            "rps": {"median": 1234.56},
            "p95_ms": {"median": 3.14159},
            "peak_rss_mib": 50.04,
            "error_rate": 0.0,
        }
        for wl in ("W3-http-read", "W4-http-db"):
            self.assertEqual(
                _headline(wl, m),
                {"rps": 1235, "p95_ms": 3.14, "rss_mib": 50.0, "errors": 0.0},
            )

    def test_cold_start(self):
        self.assertEqual(
            _headline("W5-cold-start", {"ready_ms": {"median": 81.26}}),
            {"ready_ms": 81.3},
        )

    def test_cli_workloads(self):
        m = {"wall_ms": {"median": 12.345}, "peak_rss_mib": 9.99}
        for wl in ("W1-json", "W2-hash"):
            self.assertEqual(_headline(wl, m), {"wall_ms": 12.3, "rss_mib": 10.0})


if __name__ == "__main__":
    unittest.main()
