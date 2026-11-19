"""The static results page stays on the Dashboard shell and the site floor (stdlib only)."""

import json
import re
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

    def test_no_text_below_12px_in_site_css(self):
        css = (SITE / "site.css").read_text()
        sizes = [int(s) for s in re.findall(r"font(?:-size)?:[^;]*?(\d+)px", css)]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 12)


if __name__ == "__main__":
    unittest.main()
