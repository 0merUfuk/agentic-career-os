# Agentic Career OS — Operator & Agent Handbook
*Operating Career OS via Natural Language across Claude Code, Antigravity, and Codex*

---

## 1. Executive Summary & Design Philosophy

Agentic Career OS is designed to be operated entirely through natural language by AI coding agents (**Claude Code**, **Google Antigravity**, and **Codex/Cursor**), eliminating the need for manual slash commands or complex multi-step prompt orchestration.

### The Core Architectural Thesis
> **"AI proposes, deterministic code validates and gates, nothing with a real external effect happens without a hard policy check or human approval — fail closed on uncertainty, never fail open."**

Under this architecture:
1. **Natural Language Interface**: You describe what you want (*"Evaluate this job posting"*, *"Draft an application for Acme"*, *"Record my submission"*), and the agent autonomously selects and executes the appropriate tool.
2. **Draft Isolation Invariant**: Creating an application package drafts files exclusively inside `documents/applications/<company>_<role>/`. **The central `job_search_tracker.csv` is NEVER modified during drafting.**
3. **Consequential Action Gate**: Applications are submitted to employer portals manually by the user. The tracker is only updated when you explicitly confirm actual submission (`user_confirmed=True`).
4. **Deterministic ATS Verification**: Generated packages automatically run `tools/verify_pdf.py` to assert that the CV is **exactly 2 pages** and the cover letter is **exactly 1 page** with an ATS-readable text layer.
5. **Prompt Injection & Sanitization**: All job postings pass through `tools/posting_guard.py` to strip tracking pixels and neutralize prompt injection attempts.
6. **Location Eligibility Verification**: Roles matching candidate authorized regions are verified; unverified remote roles are flagged with **`FLAG (⚠)`** to prevent accidental misapplication.

---

## 2. Shared Integration Architecture

Career OS uses a unified, standards-compliant integration architecture:

```
                      User (Natural Language in English or Turkish)
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
        Claude Code             Google Antigravity              Codex / Cursor
      (.mcp.json)             (mcp_config.json)               (.cursor/mcp.json)
             │                          │                          │
             └──────────────────────────┼──────────────────────────┘
                                        │
                                        ▼ (Stdio JSON-RPC 2.0)
                         tools/career_os_mcp.py
                         (Zero-Dependency MCP Server)
                                        │
                                        ▼
                         tools/career_os_core.py
                         (Shared Business Logic Engine)
                                        │
           ┌──────────────┬─────────────┴─────────────┬──────────────┐
           ▼              ▼                           ▼              ▼
     posting_guard   verify_pdf                  Tracker Gate    Profile Source
   (Security Audit) (Page Checks)             (14-Col Safety)   (CV & Facts)
```

### Components:
- **`tools/career_os_mcp.py`**: Model Context Protocol (MCP) server implementing JSON-RPC 2.0 over stdio. Runs on Python 3 standard library with **zero external dependencies** and starts in under 50ms.
- **`tools/career_os_core.py`**: Central engine enforcing ATS page constraints, prompt sanitization, tracker immutability during drafts, and profile alignment.
- **`tools/career_os_cli.py`**: Command-line wrapper providing `--json` output for headless scripting, automated testing, or terminal use.

---

## 3. Environment Configuration Guides

### 3.1. 60-Second Automated Setup
Run the interactive onboarding wizard:
```bash
python3 init.py
```
This initializes your personal profile templates and configures Claude Code, Claude Desktop, Cursor, and Google Antigravity.

### 3.2. Claude Code Setup (Natural Language & Slash Commands)
Claude Code automatically discovers project-level MCP servers and plugin commands.

1. **Direct Natural Language**:
   Simply launch Claude Code in the repo:
   ```bash
   claude
   ```
   Type natural language queries (*"Check my status"*, *"Evaluate this job posting: https://..."*).

2. **Slash Commands**:
   You can also trigger explicit commands:
   - `/career:status` — Inspect pipeline stages, pending drafts, and profile paths.
   - `/career:eval <url_or_text>` — Audit and evaluate a job posting for fit and security.
   - `/career:draft <company> <role>` — Draft tailored 2-page CV and 1-page cover letter.
   - `/career:log <company> <role>` — Record a manual application submission with safety gate.
   - `/career:interview <company>` — Generate company battle cards and STAR stories.

---

### 3.3. Claude Desktop (Connectors 🔌)
Claude Desktop supports Career OS directly as an MCP tool connector:
1. Ensure your `claude_desktop_config.json` contains:
   ```json
   {
     "mcpServers": {
       "career-os": {
         "command": "python3",
         "args": ["/ABSOLUTE/PATH/TO/agentic-career-os/tools/career_os_mcp.py"]
       }
     }
   }
   ```
2. Restart Claude Desktop.
3. In any chat window, click the **🔌 (Connectors / Tools)** icon to see the Career OS tools available.

---

### 3.4. Google Antigravity Setup
Add the server to your Antigravity configuration in `~/.gemini/config/mcp_config.json`:
```json
{
  "mcpServers": {
    "career-os": {
      "command": "python3",
      "args": ["/absolute/path/to/agentic-career-os/tools/career_os_mcp.py"]
    }
  }
}
```

---

### 3.3. OpenAI Codex & Cursor Setup
For Cursor, `.cursor/mcp.json` is pre-configured.
For Codex or script-based runners, use the unified CLI wrapper:
```bash
python3 tools/career_os_cli.py status --json
python3 tools/career_os_cli.py evaluate --text "..." --json
python3 tools/career_os_cli.py draft --company "Acme" --role "AI Engineer" --file posting.txt --json
python3 tools/career_os_cli.py record --company "Acme" --role "AI Engineer" --confirm --json
```

---

## 4. Realistic Natural-Language Operations

### 1. Checking Workspace Status
- **User**: *"What's the status of my job search workspace?"*
- **Action**: Invokes `career_os_status`.

### 2. Evaluating a Posting
- **User**: *"Check this Senior AI Engineer posting at Acme: [link or text]"*
- **Action**: Invokes `career_os_evaluate_posting`. Sanitizes text, checks regional authorization, matches skills, and returns fit score (0–100).

### 3. Drafting Application Package
- **User**: *"Draft an application for Acme as an AI Engineer."*
- **Action**: Invokes `career_os_draft_application`. Creates `documents/applications/acme_ai-engineer/`, copies verified 2-page CV, renders 1-page cover letter, runs `verify_pdf.py`. Tracker remains untouched.

### 4. Consequential Submission Logging
- **User**: *"I just submitted the application on Acme's careers portal, please record it."*
- **Action**: Invokes `career_os_record_submission(company="Acme", role="AI Engineer", user_confirmed=True)`. Writes canonical 14-column row to `job_search_tracker.csv`.

### 5. Interview Preparation
- **User**: *"I have an interview with Acme! Prepare talking points and questions."*
- **Action**: Invokes `career_os_interview_prep(company="Acme")`. Returns structured briefing with core thesis, STAR points, and reverse interview questions.
