---
description: Audit and evaluate a job posting for fit and security.
arguments:
  - name: posting
    description: URL or pasted text of the job posting
    required: true
---

Please audit the following job posting using the `career_os_evaluate_posting` MCP tool (or `python3 tools/career_os_cli.py eval "$ARGUMENTS"`):

"$ARGUMENTS"

Instructions:
1. The tool automatically sanitizes tracking pixels, strips CSS concealment, and checks for prompt injection vulnerabilities via `posting_guard.py`.
2. It matches the role against the candidate's Master Experience Document and calculates a fit score.
3. Review candidate location & work authorization (flagging unverified remote roles with ⚠ location FLAG).
4. Report:
   - Sanitized role title, company, location, and salary benchmark (if detected)
   - Match score (1-5), key matching strengths, and missing qualification gaps
   - Recommendation: Apply, Stretch, or Skip with clear rationale.
