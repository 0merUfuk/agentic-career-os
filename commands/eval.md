# /career:eval - Audit and Evaluate a Job Posting for Fit and Security

Please audit the following job posting using the `career_os_evaluate_posting` MCP tool (or `python3 tools/career_os_cli.py evaluate --text "$ARGUMENTS"`):

"$ARGUMENTS"

Instructions:
1. The tool automatically sanitizes tracking pixels, strips CSS concealment, and checks for prompt injection vulnerabilities via `posting_guard.py`.
2. It matches the role against the candidate's Master Experience Document and calculates a fit score.
3. Review candidate location & work authorization (flagging unverified remote roles with ⚠ location FLAG).
4. Present the response using the `markdown_card` returned by the tool, including the Fit Scorecard, matched strengths, and clear recommendation.
