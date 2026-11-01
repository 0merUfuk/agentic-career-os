---
description: Generate interview preparation battle cards, anticipated questions, and candidate STAR stories.
arguments:
  - name: company
    description: Employer company name
    required: true
  - name: role
    description: Job title / role (optional)
    required: false
---

Generate an interview preparation brief using the `career_os_interview_prep` MCP tool for:
- Company: "$ARGUMENTS"

Instructions:
1. Provide company background, engineering philosophy, and architecture challenges.
2. Anticipate the 5 most likely technical and behavioral questions based on the candidate's profile and the role requirements.
3. Map candidate verified STAR stories (from `master-experience-document.md`) to each anticipated question.
4. Provide 3 thoughtful questions for the candidate to ask the interviewers.
