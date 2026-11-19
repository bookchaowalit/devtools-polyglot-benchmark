"""The static results page stays on the Dashboard shell and the site floor (stdlib only)."""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"


class SiteTest(unittest.TestCase):
    def setUp(self):
        self.html = (SITE / "index.html").read_text()

    def test_uses_the_shell_and_a_self_hosted_font(self):
        self.assertIn('href="dashboard-shell.css"', self.html)
        self.assertIn('class="ds"', self.html)
        self.assertIn('href="#main"', self.html)
        self.assertIn('id="main"', self.html)
        self.assertTrue((SITE / "fonts" / "geist-latin.woff2").is_file())
        self.assertNotRegex(
            self.html, r"fonts\.googleapis|vercel-insights|speed-insights"
        )

    def test_font_ships_with_the_full_ofl_text(self):
        # OFL 1.1 condition 2: redistributed fonts carry the copyright notice and the license itself.
        text = (SITE / "fonts" / "LICENSE.txt").read_text()
        self.assertIn("Copyright (c) 2023 Vercel", text)
        for heading in (
            "PREAMBLE",
            "DEFINITIONS",
            "PERMISSION AND CONDITIONS",
            "TERMINATION",
            "DISCLAIMER",
        ):
            self.assertIn(heading, text)

    def test_shell_copy_has_the_selected_period_ring_and_forced_colors_edge(self):
        css = (SITE / "dashboard-shell.css").read_text()
        self.assertIn("box-shadow: inset 0 0 0 2px var(--ds-fg)", css)
        self.assertIn(".ds-segmented button { border: 1px solid ButtonText; }", css)

    def test_links_back_to_the_hub_and_redirects_more_projects(self):
        self.assertIn('href="https://bookchaowalit.com/"', self.html)
        redirects = json.loads((SITE / "vercel.json").read_text())["redirects"]
        self.assertIn(
            {
                "source": "/more-projects",
                "destination": "https://bookchaowalit.com/",
                "permanent": True,
            },
            redirects,
        )
        self.assertIn(
            "polyglot-benchmark-lab.vercel.app/sitemap.xml",
            (SITE / "robots.txt").read_text(),
        )

    def test_page_has_loading_and_failure_states(self):
        script = (SITE / "app.js").read_text()
        self.assertIn('role="status"', self.html)
        for text in (
            "could not be loaded",
            "No published runs yet",
            "data/index.json",
            "data/runs/",
        ):
            self.assertIn(text, script)
        # better / worse is written out, never colour alone
        self.assertRegex(script, r'word: better \? "better" : "worse"')

    @unittest.skipUnless(shutil.which("node"), "needs Node.js to run site/app.js")
    def test_only_the_run_picked_last_reaches_the_page(self):
        # A slower answer (or failure) for a run picked earlier must not replace the run picked last.
        out = subprocess.run(
            ["node", str(Path(__file__).with_name("site_open_run.mjs"))],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        seen = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertTrue(seen["late_success"].startswith("python · github runner"), seen)
        self.assertTrue(seen["late_failure"].startswith("python · github runner"), seen)

    def test_no_text_below_12px_in_site_css(self):
        css = (SITE / "site.css").read_text()
        sizes = [int(s) for s in re.findall(r"font(?:-size)?:[^;]*?(\d+)px", css)]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 12)


if __name__ == "__main__":
    unittest.main()
