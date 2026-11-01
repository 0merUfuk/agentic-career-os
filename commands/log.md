# /career:log - Record Manual Job Application Submission

Please record an application submission into `job_search_tracker.csv` using the `career_os_record_submission` MCP tool:
- Company: "$ARGUMENTS"
- Role: "$ARGUMENTS"

Safety Gate Invariant:
- Applications must be submitted manually by the candidate on the employer portal.
- Verify with the user that the application was indeed manually submitted (`user_confirmed=True`).
- Only record once the user confirms manual submission.
