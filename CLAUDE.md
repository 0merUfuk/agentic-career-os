# Agentic Career OS — AI Coding Assistant Workspace

Local-first, agentic job search and application preparation system powered by the Model Context Protocol (MCP).

## Natural Language Agent Operation (MCP Tools)
Operate this workspace entirely via natural language requests. Claude Code automatically discovers the `career-os` MCP tools configured in `.mcp.json`. Do not require the user to invoke slash commands or manual skills during normal usage:
- When the user asks about job status, active applications, or tracker health, invoke `career_os_status`.
- When the user shares a job posting (URL or text) or asks about a role, invoke `career_os_evaluate_posting` to sanitize the posting, assess candidate fit, and verify work authorization.
- When the user asks to prepare or draft an application, invoke `career_os_draft_application`. Draft packages are created under `documents/applications/<company>_<role>/` with verified 2-page CV and 1-page cover letter, leaving `job_search_tracker.csv` untouched.
- When the user states they have submitted an application, invoke `career_os_record_submission` with `user_confirmed: true` to record the canonical 14-column row and update `outcome.md`.
- When the user asks for interview preparation, invoke `career_os_interview_prep`.
- When the user inquires about compensation, invoke `career_os_salary_lookup`.

## Core Invariants
1. Candidate facts live in `sample_profile/master-experience-document.md` (or `CAREER_OS_PROFILE_DIR`). Never invent claims or credentials.
2. Draft isolation: `job_search_tracker.csv` is never modified during drafting.
3. Consequential action gate: Submissions require manual user execution and explicit confirmation before recording.
