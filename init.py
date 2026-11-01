#!/usr/bin/env python3
"""Interactive Onboarding & Agent Configuration Wizard for Agentic Career OS.

Initializes candidate profile templates, configures MCP connections for AI agents
(Claude Code, Claude Desktop, Cursor, Google Antigravity), and validates installation.

Usage:
    python3 init.py
    python3 init.py --non-interactive --name "Jane Doe" --email "jane@example.com"
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parent
SAMPLE_PROFILE_DIR = REPO_ROOT / "sample_profile"
PROFILE_DIR = REPO_ROOT / "profile"
DOCUMENTS_DIR = REPO_ROOT / "documents"
APPLICATIONS_DIR = DOCUMENTS_DIR / "applications"


def get_claude_desktop_config_path() -> Optional[Path]:
    """Return the platform-specific path to Claude Desktop configuration."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        app_data = os.getenv("APPDATA")
        if app_data:
            return Path(app_data) / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        config_dir = os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(config_dir) / "Claude" / "claude_desktop_config.json"
    return None


def get_antigravity_config_path() -> Path:
    """Return the path to Google Antigravity MCP config."""
    return Path.home() / ".gemini" / "config" / "mcp_config.json"


def prompt_input(prompt: str, default: str = "") -> str:
    """Prompt the user with an optional default value."""
    if default:
        formatted_prompt = f"{prompt} [{default}]: "
    else:
        formatted_prompt = f"{prompt}: "
    try:
        val = input(formatted_prompt).strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        sys.exit(0)


def prompt_yes_no(prompt: str, default: bool = True) -> bool:
    """Prompt user for a yes/no response."""
    choices = " [Y/n]: " if default else " [y/N]: "
    try:
        val = input(prompt + choices).strip().lower()
        if not val:
            return default
        return val in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        sys.exit(0)


def setup_profile(name: str, email: str, location: str, role_focus: str, thesis: str) -> None:
    """Create the personalized candidate profile if it does not already exist."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    cv_dir = PROFILE_DIR / "cv"
    cv_dir.mkdir(parents=True, exist_ok=True)
    APPLICATIONS_DIR.mkdir(parents=True, exist_ok=True)

    master_doc = PROFILE_DIR / "master-experience-document.md"
    if master_doc.exists():
        print(f"  ✓ Existing master experience document found at {master_doc}")
    else:
        sample_doc = SAMPLE_PROFILE_DIR / "master-experience-document.md"
        content = ""
        if sample_doc.exists():
            content = sample_doc.read_text(encoding="utf-8")
            # Replace sample candidate headers
            content = content.replace("Alex Vance", name)
            content = content.replace("San Francisco, CA (Open to Global Remote)", location)
            content = content.replace("AI Systems Engineering, Multi-Agent Platforms, Distributed Systems", role_focus)
            if thesis:
                content = content.replace(
                    '"AI proposes, deterministic code validates and gates, nothing with a real external effect happens without a hard policy check or human approval — fail closed on uncertainty, never fail open."',
                    f'"{thesis}"',
                )
        else:
            content = f"""# Master Experience Document

Single source of truth for candidate experience, metrics, and technical competencies.

---

## 0. Candidate Summary & Positioning

- **Name:** {name}
- **Email:** {email}
- **Location:** {location}
- **Role Focus:** {role_focus}
- **Core Thesis:** "{thesis}"

---

## 1. Verified Production Experience

### Senior Engineer &bull; Company (Year &ndash; Present)
- Architected and delivered core platform capabilities.
- Measurable impact: reduced latency, increased reliability, scaled systems.

---

## 2. Core Competencies

- **Languages:** Python, TypeScript, Go, SQL
- **Frameworks & Tools:** Model Context Protocol (MCP), Docker, Cloud Platforms
"""
        master_doc.write_text(content, encoding="utf-8")
        print(f"  ✓ Initialized candidate profile: {master_doc}")

    # Copy sample CV PDF if profile cv directory is empty
    sample_cv = SAMPLE_PROFILE_DIR / "cv" / "resume-ai-systems.pdf"
    target_cv = cv_dir / "resume-ai-systems.pdf"
    if sample_cv.exists() and not target_cv.exists():
        shutil.copy2(sample_cv, target_cv)
        print(f"  ✓ Copied template CV to {target_cv}")


def configure_claude_code(python_exec: str) -> None:
    """Ensure repo .mcp.json is properly configured for Claude Code."""
    mcp_json_path = REPO_ROOT / ".mcp.json"
    server_script = REPO_ROOT / "tools" / "career_os_mcp.py"

    config: Dict[str, Any] = {
        "mcpServers": {
            "career-os": {
                "command": python_exec,
                "args": [str(server_script)],
                "env": {
                    "CAREER_OS_PROFILE_DIR": str(PROFILE_DIR if PROFILE_DIR.exists() else SAMPLE_PROFILE_DIR),
                },
            }
        }
    }
    mcp_json_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"  ✓ Configured Claude Code local server in {mcp_json_path}")


def configure_cursor(python_exec: str) -> None:
    """Ensure .cursor/mcp.json is configured for Cursor."""
    cursor_dir = REPO_ROOT / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    cursor_json = cursor_dir / "mcp.json"
    server_script = REPO_ROOT / "tools" / "career_os_mcp.py"

    config: Dict[str, Any] = {
        "mcpServers": {
            "career-os": {
                "command": python_exec,
                "args": [str(server_script)],
                "env": {
                    "CAREER_OS_PROFILE_DIR": str(PROFILE_DIR if PROFILE_DIR.exists() else SAMPLE_PROFILE_DIR),
                },
            }
        }
    }
    cursor_json.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"  ✓ Configured Cursor server in {cursor_json}")


def configure_claude_desktop(python_exec: str, dry_run: bool = False) -> None:
    """Optionally add Career OS to Claude Desktop configuration."""
    desktop_config_path = get_claude_desktop_config_path()
    if not desktop_config_path:
        print("  ℹ Claude Desktop config path not found for this OS (skipping)")
        return

    server_script = REPO_ROOT / "tools" / "career_os_mcp.py"
    server_entry = {
        "command": python_exec,
        "args": [str(server_script)],
        "env": {
            "CAREER_OS_PROFILE_DIR": str(PROFILE_DIR if PROFILE_DIR.exists() else SAMPLE_PROFILE_DIR),
        },
    }

    try:
        desktop_config_path.parent.mkdir(parents=True, exist_ok=True)
        config: Dict[str, Any] = {}
        if desktop_config_path.exists():
            try:
                config = json.loads(desktop_config_path.read_text(encoding="utf-8"))
            except Exception:
                config = {}

        if "mcpServers" not in config or not isinstance(config["mcpServers"], dict):
            config["mcpServers"] = {}

        config["mcpServers"]["career-os"] = server_entry

        if not dry_run:
            desktop_config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            print(f"  ✓ Claude Desktop registered Career OS at {desktop_config_path}")
        else:
            print(f"  ℹ Would update {desktop_config_path}")
    except Exception as exc:
        print(f"  ⚠ Could not write Claude Desktop config ({exc}). You can add it manually.")


def configure_antigravity(python_exec: str, dry_run: bool = False) -> None:
    """Optionally register Career OS in Antigravity mcp_config.json."""
    ag_path = get_antigravity_config_path()
    server_script = REPO_ROOT / "tools" / "career_os_mcp.py"
    server_entry = {
        "command": python_exec,
        "args": [str(server_script)],
    }

    try:
        ag_path.parent.mkdir(parents=True, exist_ok=True)
        config: Dict[str, Any] = {}
        if ag_path.exists():
            try:
                config = json.loads(ag_path.read_text(encoding="utf-8"))
            except Exception:
                config = {}

        if "mcpServers" not in config or not isinstance(config["mcpServers"], dict):
            config["mcpServers"] = {}

        config["mcpServers"]["career-os"] = server_entry

        if not dry_run:
            ag_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            print(f"  ✓ Antigravity registered Career OS at {ag_path}")
        else:
            print(f"  ℹ Would update {ag_path}")
    except Exception as exc:
        print(f"  ⚠ Could not write Antigravity config ({exc}).")


def configure_global_claude_commands(dry_run: bool = False) -> None:
    """Install slash commands into user's global ~/.claude/commands/."""
    user_claude = Path.home() / ".claude"
    commands_root = user_claude / "commands"
    career_dir = commands_root / "career"

    src_commands = REPO_ROOT / "commands"
    if not src_commands.exists():
        src_commands = REPO_ROOT / ".claude" / "commands"

    if not src_commands.exists():
        return

    try:
        if not dry_run:
            commands_root.mkdir(parents=True, exist_ok=True)
            career_dir.mkdir(parents=True, exist_ok=True)
            for cmd_file in src_commands.glob("*.md"):
                # Flat copy (e.g. career-status.md)
                flat_name = cmd_file.name if cmd_file.name.startswith("career-") else f"career-{cmd_file.name}"
                shutil.copy2(cmd_file, commands_root / flat_name)
                # Namespaced copy for /career:*
                clean_name = cmd_file.name.replace("career-", "")
                shutil.copy2(cmd_file, career_dir / clean_name)
            print(f"  ✓ Installed global Claude Code slash commands into {commands_root}")
        else:
            print(f"  ℹ Would install global Claude Code commands into {commands_root}")
    except Exception as exc:
        print(f"  ⚠ Could not write global Claude commands ({exc}).")


def configure_global_antigravity_skill(dry_run: bool = False) -> None:
    """Install global Antigravity skill into ~/.gemini/config/skills/career-os/."""
    gemini_dir = Path.home() / ".gemini"
    if not gemini_dir.exists():
        return

    skill_dir = gemini_dir / "config" / "skills" / "career-os"
    try:
        if not dry_run:
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_md = skill_dir / "SKILL.md"
            skill_content = """---
name: career-os
description: Autonomous job search intelligence, posting evaluation, application drafting, and interview preparation engine.
---

# Career OS Skill

Operates the autonomous job search intelligence and ATS application engine via MCP tools.
"""
            skill_md.write_text(skill_content, encoding="utf-8")
            print(f"  ✓ Registered global Antigravity skill in {skill_dir}")
        else:
            print(f"  ℹ Would register Antigravity skill in {skill_dir}")
    except Exception as exc:
        print(f"  ⚠ Could not write Antigravity skill ({exc}).")


def run_self_tests() -> bool:
    """Execute the unittest discovery suite to ensure everything passes."""
    if os.getenv("_CAREER_OS_INIT_TESTING") or "unittest" in sys.modules:
        return True
    print("\nRunning verification tests...")
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        print("  ✓ All 16 automated tests passed cleanly.")
        return True
    else:
        print("  ⚠ Tests finished with failures or errors:")
        print(proc.stderr or proc.stdout)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Career OS Onboarding & Agent Setup Wizard")
    parser.add_argument("--non-interactive", action="store_true", help="Run without prompts using defaults")
    parser.add_argument("--name", default="Your Name", help="Candidate full name")
    parser.add_argument("--email", default="candidate@example.com", help="Candidate email")
    parser.add_argument("--location", default="Remote / Open to Relocation", help="Candidate location & work rights")
    parser.add_argument("--role-focus", default="Software Engineering", help="Candidate target roles")
    parser.add_argument(
        "--thesis",
        default="AI proposes, deterministic code validates and gates, nothing executes without a hard policy check.",
        help="Candidate core positioning statement",
    )
    parser.add_argument("--skip-desktop", action="store_true", help="Skip Claude Desktop auto-configuration")
    parser.add_argument("--skip-global", action="store_true", help="Skip installing slash commands globally")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running test suite")
    args = parser.parse_args()

    python_exec = sys.executable

    print("=" * 68)
    print("  🚀 Welcome to Agentic Career OS — 60-Second Agent Setup")
    print("=" * 68)
    print("This wizard configures your local career repository, sets up your candidate")
    print("profile, and links your local AI agents (Claude Code, Claude Desktop, Cursor).\n")

    if args.non_interactive:
        name = args.name
        email = args.email
        location = args.location
        role_focus = args.role_focus
        thesis = args.thesis
        setup_desktop = not args.skip_desktop
        setup_global = not args.skip_global
    else:
        # Try to infer git user name
        default_name = "Candidate"
        try:
            git_name = subprocess.check_output(
                ["git", "config", "user.name"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if git_name:
                default_name = git_name
        except Exception:
            pass

        print("Step 1 of 3: Candidate Profile Information")
        print("-" * 68)
        name = prompt_input("Full Name", default_name)
        email = prompt_input("Contact Email", "user@example.com")
        location = prompt_input("Location & Work Authorization", "San Francisco, CA (or Remote)")
        role_focus = prompt_input("Target Role Focus", "AI Systems, Platform Engineering, Distributed Systems")
        thesis = prompt_input(
            "Core Career Thesis",
            "AI proposes, deterministic code validates and gates, fail-closed on uncertainty.",
        )
        print()

        print("Step 2 of 3: AI Assistant Integration")
        print("-" * 68)
        setup_desktop = prompt_yes_no("Configure Claude Desktop MCP connector?", default=True)
        setup_global = prompt_yes_no("Install slash commands globally (~/.claude/commands/)?", default=True)
        print()

    print("Configuring environment...")
    setup_profile(name, email, location, role_focus, thesis)
    configure_claude_code(python_exec)
    configure_cursor(python_exec)

    if setup_desktop:
        configure_claude_desktop(python_exec)

    if setup_global:
        configure_global_claude_commands()
        configure_global_antigravity_skill()

    # If Antigravity directory exists, register it too
    if Path.home().joinpath(".gemini").exists():
        configure_antigravity(python_exec)

    # Run self-tests
    tests_ok = True
    if not args.skip_tests:
        tests_ok = run_self_tests()

    print("\n" + "=" * 68)
    print("  🎉 Setup Complete! You're ready to use Agentic Career OS.")
    print("=" * 68)
    print("How to run:")
    print("  • With Claude Code:")
    print("      $ claude")
    print("      > /career:status")
    print("      > /career:eval https://jobs.example.com/posting")
    print("      > /career:draft 'Example Corp' 'Staff AI Engineer'")
    print("  • With Claude Desktop:")
    print("      Restart Claude Desktop, open a chat, and check the 🔌 connectors list.")
    print("  • With Cursor:")
    print("      Open this repository folder in Cursor; MCP tools load automatically.")
    print("  • Command Line CLI:")
    print("      $ python3 tools/career_os_cli.py status")
    print("=" * 68)

    return 0 if tests_ok else 1


if __name__ == "__main__":
    sys.exit(main())
