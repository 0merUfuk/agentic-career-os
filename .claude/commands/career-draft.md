# /career:draft - Draft Tailored Application Package to Isolated Folder

Please prepare an application package using the `career_os_draft_application` MCP tool:
- Company: "$ARGUMENTS"
- Role: "$ARGUMENTS"

Safety Invariants to Maintain:
1. Ground all claims strictly in the Master Experience Document (`master-experience-document.md`). Do NOT hallucinate skills or metrics.
2. Output the package into the isolated application folder (`documents/applications/<company>_<role>/`).
3. Verify that the CV is exactly 2 pages and the cover letter is exactly 1 page using `verify_pdf.py`.
4. **DO NOT modify `job_search_tracker.csv` during drafting.** Application drafting must remain isolated until the user explicitly confirms manual submission.
5. Present the response using the `markdown_card` returned by the tool, highlighting the deliverable file links and the Next Action manual submission checklist.
