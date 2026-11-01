# Agent Guidelines: Agentic Career OS

This workspace is structured to manage job search activities, posting audits, ATS-compliant CVs, cover letters, and interview preparation through autonomous AI coding agents.

## Thin-Pointer Design & Integration

All agent runtimes (Claude Code, Google Antigravity, OpenAI Codex, Cursor) operate through a shared integration layer:

1. **Model Context Protocol (MCP)**:
   - Server: `tools/career_os_mcp.py`
   - Configs:
     - Claude Code: `.mcp.json`
     - Antigravity: `~/.gemini/config/mcp_config.json`
     - Codex / Cursor: `.cursor/mcp.json`
   - Available tools:
     - `career_os_status`: Inspect workspace status, active applications, and tracker statistics.
     - `career_os_evaluate_posting`: Sanitize posting (injection guard), evaluate candidate fit, and verify regional work eligibility.
     - `career_os_draft_application`: Prepare draft application package under `documents/applications/` (leaves tracker untouched).
     - `career_os_record_submission`: Safe outcome recording (requires explicit user confirmation).
     - `career_os_interview_prep`: Generate interview talking points and reverse questions grounded in submitted materials.
     - `career_os_salary_lookup`: Query compensation benchmarks.

2. **Unified CLI Fallback (Codex / Script-based agents)**:
   - Script: `python3 tools/career_os_cli.py <subcommand> --json`
   - Subcommands: `status`, `evaluate`, `draft`, `record`, `interview`, `salary`.
