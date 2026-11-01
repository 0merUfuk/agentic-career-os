#!/usr/bin/env python3
"""Tests for the Career OS init onboarding wizard."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestInitWizard(unittest.TestCase):
    def setUp(self):
        # Save copies of mcp.json files if they exist
        self.mcp_json = REPO_ROOT / ".mcp.json"
        self.cursor_json = REPO_ROOT / ".cursor" / "mcp.json"
        self.mcp_bak = self.mcp_json.read_text(encoding="utf-8") if self.mcp_json.exists() else None
        self.cursor_bak = self.cursor_json.read_text(encoding="utf-8") if self.cursor_json.exists() else None

    def tearDown(self):
        # Restore clean files so tests don't leave untracked changes
        if self.mcp_bak is not None:
            self.mcp_json.write_text(self.mcp_bak, encoding="utf-8")
        if self.cursor_bak is not None:
            self.cursor_json.write_text(self.cursor_bak, encoding="utf-8")
        profile_dir = REPO_ROOT / "profile"
        if profile_dir.exists():
            shutil.rmtree(profile_dir, ignore_errors=True)

    def test_init_help(self):
        """Verify init.py --help outputs usage cleanly."""
        res = subprocess.run(
            [sys.executable, str(REPO_ROOT / "init.py"), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Career OS Onboarding & Agent Setup Wizard", res.stdout)
        self.assertIn("--non-interactive", res.stdout)

    def test_init_non_interactive(self):
        """Verify init.py executes smoothly in non-interactive mode."""
        res = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "init.py"),
                "--non-interactive",
                "--name",
                "Test Candidate",
                "--email",
                "test@example.com",
                "--skip-desktop",
                "--skip-global",
                "--skip-tests",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"init.py failed with: {res.stderr}\n{res.stdout}")
        self.assertIn("Setup Complete!", res.stdout)
        self.assertTrue((REPO_ROOT / ".mcp.json").exists())
        self.assertTrue((REPO_ROOT / ".cursor" / "mcp.json").exists())

    def test_global_claude_commands_dry_run(self):
        """Verify global command installer executes dry run cleanly."""
        import init
        init.configure_global_claude_commands(dry_run=True)
        init.configure_global_antigravity_skill(dry_run=True)


if __name__ == "__main__":
    unittest.main()
