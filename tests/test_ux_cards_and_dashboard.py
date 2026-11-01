#!/usr/bin/env python3
"""Tests for UX card formatters and HTML dashboard generator."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import career_os_core
import career_os_dashboard


class TestUxCardsAndDashboard(unittest.TestCase):
    def test_format_evaluation_card(self):
        """Verify format_evaluation_card produces Markdown scorecard."""
        eval_data = {
            "fit_score": 88,
            "location_status": "VERIFIED_LOCATION",
            "location_notes": "Remote eligible",
            "is_safe": True,
            "verdict": "posting_guard: clean",
            "estimated_company": "Acme Labs",
            "estimated_role": "Senior AI Systems Engineer",
            "target_track": "ai-systems",
            "recommendation": "PROCEED_TO_DRAFT",
            "matched_strengths": ["AI Systems", "Go Backend"],
        }
        card = career_os_core.format_evaluation_card(eval_data)
        self.assertIn("### 📋 Job Audit & Fit Scorecard: Acme Labs — Senior AI Systems Engineer", card)
        self.assertIn("🟢 **88/100**", card)
        self.assertIn("🟢 Verified Remote/Location", card)
        self.assertIn("🛡️ Clean", card)
        self.assertIn("| Metric | Status | Details |", card)

    def test_format_package_card(self):
        """Verify format_package_card produces deliverable breakdown and next steps."""
        draft_data = {
            "company": "GitLab",
            "role": "Staff AI Engineer",
            "package_directory": "/tmp/test-package",
            "cv_verification": {"verified": True, "message": "2 pages verified"},
            "cover_letter_verification": {"verified": True, "message": "1 page verified"},
        }
        card = career_os_core.format_package_card(draft_data)
        self.assertIn("### 📦 Application Package Ready: GitLab — Staff AI Engineer", card)
        self.assertIn("🟢 Exactly 2 Pages (Verified)", card)
        self.assertIn("🟢 Exactly 1 Page (Verified)", card)
        self.assertIn("#### 🚀 Next Action: Manual Application Submission", card)

    def test_format_status_card(self):
        """Verify format_status_card produces summary counts."""
        status_data = {
            "total_tracker_rows": 5,
            "status_counts": {"active": 3, "interview": 2},
            "application_packages": [{"package_name": "acme_ai-engineer"}],
        }
        card = career_os_core.format_status_card(status_data)
        self.assertIn("### 📊 Career OS Pipeline & Tracker Status", card)
        self.assertIn("**Total Tracked Applications:** **5**", card)
        self.assertIn("Active", card)

    def test_generate_html_dashboard(self):
        """Verify HTML dashboard compiles offline with SVG donut."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            out = career_os_dashboard.generate_html_dashboard(output_path=tmp_path)
            self.assertTrue(out.exists())
            content = out.read_text(encoding="utf-8")
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("<svg", content)
            self.assertIn("Career OS", content)
            self.assertIn("Conversion Funnel", content)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_cli_dashboard_subcommand(self):
        """Verify CLI dashboard command runs with --json output."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / "tools" / "career_os_cli.py"), "dashboard", "--out", str(tmp_path), "--json"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('"status": "SUCCESS"', proc.stdout)
            self.assertTrue(tmp_path.exists())
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
