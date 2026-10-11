"""The contract must reject wrong lanes, not only accept right ones."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contract.check import check_lane  # noqa: E402
from contract.fixtures import Lcg, build_records, expected_w1  # noqa: E402
from runner.lanes import LANES, Lane  # noqa: E402

PY = sys.executable
WRONG = Lane(
    id="wrong",
    language="python",
    framework="none",
    version_cmd=[PY, "--version"],
    w1=[PY, "-c", "print('{\"count\": 0}')"],
    w2=[PY, "-c", "print('0' * 64)"],
    server=[PY, "-c", "import sys; sys.exit(3)"],
)


class FixtureTest(unittest.TestCase):
    def test_lcg_is_stable(self):
        rng = Lcg(1)
        self.assertEqual([rng.next() for _ in range(3)], [1015568748, 1586005467, 2165703038])

    def test_expected_w1_shape(self):
        out = expected_w1(build_records())
        self.assertEqual(out["count"], 10_000)
        self.assertEqual(len(out["top5"]), 5)
        self.assertEqual(list(out["by_tag"]), sorted(out["by_tag"]))


class ContractTest(unittest.TestCase):
    def test_wrong_lane_fails_every_workload(self):
        failures = check_lane(WRONG)
        self.assertTrue(any(f.startswith("W1") for f in failures))
        self.assertTrue(any(f.startswith("W2") for f in failures))
        self.assertTrue(any(f.startswith("W3") for f in failures))

    def test_registered_lanes_pass(self):
        for lane in LANES.values():
            with self.subTest(lane=lane.id):
                self.assertEqual(check_lane(lane), [])


if __name__ == "__main__":
    unittest.main()
