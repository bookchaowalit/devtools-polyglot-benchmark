"""The lane registry must stay consistent with the bench matrix and its own rules."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runner.lanes import ALL, GROUPS, LANES, lanes_in


class RegistryTest(unittest.TestCase):
    def test_ids_match_keys(self):
        for key, lane in LANES.items():
            self.assertEqual(key, lane.id)

    def test_every_variant_names_an_existing_parent_and_a_change(self):
        for lane in LANES.values():
            if lane.parent is None:
                self.assertEqual(lane.group, "core", lane.id)
                continue
            with self.subTest(lane=lane.id):
                self.assertIn(lane.parent, LANES)
                self.assertTrue(
                    lane.change.strip(), "a variant must say what it changes"
                )
                self.assertEqual(LANES[lane.parent].language, lane.language)

    def test_variant_workloads_are_a_subset_of_its_parent(self):
        # The page shows a variant as a percentage of its parent, so the parent must run it too.
        for lane in LANES.values():
            self.assertTrue(set(lane.workloads) <= set(ALL), lane.id)
            if lane.parent:
                parent = LANES[lane.parent]
                self.assertTrue(set(lane.workloads) <= set(parent.workloads), lane.id)

    def test_bench_matrix_runs_every_group(self):
        bench = (ROOT / ".github/workflows/bench.yml").read_text()
        match = re.search(r"group:\s*\[([^\]]+)\]", bench)
        self.assertIsNotNone(match)
        matrix = sorted(g.strip() for g in match.group(1).split(","))
        self.assertEqual(matrix, GROUPS)


class LanesInTest(unittest.TestCase):
    def test_group_includes_its_lanes_and_their_parents_first(self):
        for group in GROUPS:
            with self.subTest(group=group):
                ids = lanes_in(group)
                self.assertEqual(len(ids), len(set(ids)), "no duplicates")
                own = [i for i in LANES if LANES[i].group == group]
                self.assertTrue(set(own) <= set(ids))
                for i in ids:
                    parent = LANES[i].parent
                    if parent:
                        self.assertIn(parent, ids)
                        self.assertLess(ids.index(parent), ids.index(i))

    def test_core_has_one_lane_per_language(self):
        core = lanes_in("core")
        self.assertEqual(
            sorted(LANES[i].language for i in core),
            ["go", "python", "rust", "typescript"],
        )

    def test_unknown_group_is_empty(self):
        self.assertEqual(lanes_in("no-such-group"), [])


if __name__ == "__main__":
    unittest.main()
