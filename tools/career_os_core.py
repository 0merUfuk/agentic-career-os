#!/usr/bin/env python3
"""Career OS Core Service Engine (Open-Source / Demonstration Version).

Shared, reusable service layer implementing the business logic, ATS compliance checks,
and safety invariants of Agentic Career OS. Used by both the MCP server and the CLI interface.

Invariants:
  1. Authoritative career facts live in sample_profile/master-experience-document.md (or CAREER_OS_PROFILE_DIR).
  2. Draft applications are strictly isolated from job_search_tracker.csv.
  3. Applications are submitted manually by the user; recordings in job_search_tracker.csv
     require explicit user_confirmed=True.
  4. CVs must be exactly 2 pages; cover letters must be exactly 1 page (verified via tools/verify_pdf.py).
  5. Postings are sanitized for tracking pixels and prompt injection via tools/posting_guard.py.
  6. Unverified remote roles are flagged as location FLAG (⚠).
"""

from __future__ import annotations

import csv
import datetime
import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Locate repo root and tools
REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
DOCUMENTS_DIR = REPO_ROOT / "documents"
APPLICATIONS_DIR = DOCUMENTS_DIR / "applications"
TRACKER_CSV = REPO_ROOT / "job_search_tracker.csv"

# Configurable profile and CV paths (defaults to bundled sample profile)
PROFILE_DIR = Path(os.getenv("CAREER_OS_PROFILE_DIR", str(REPO_ROOT / "sample_profile")))
MASTER_EXP_DOC = PROFILE_DIR / "master-experience-document.md"
SAMPLE_CV_DIR = PROFILE_DIR / "cv"

# Import existing tools
sys.path.insert(0, str(TOOLS_DIR))
try:
    import posting_guard
    import verify_pdf
except ImportError:
    posting_guard = None
    verify_pdf = None

CANONICAL_COLUMNS = [
    "date",
    "company",
    "sector",
    "role",
    "role_type",
    "channel",
    "status",
    "contact_person",
    "fit_rating",
    "notes",
    "cv_file",
    "cover_letter_file",
    "source",
    "deadline",
]


def resolve_repo_root(root_hint: Optional[str | Path] = None) -> Path:
    """Resolve repository root."""
    if root_hint:
        return Path(root_hint).resolve()
    return REPO_ROOT


def sanitize_filename(name: str) -> str:
    """Generate safe filesystem slug."""
    s = re.sub(r"[^\w\s-]", "", name).strip().lower()
    return re.sub(r"[-\s]+", "-", s)


# -----------------------------------------------------------------------------
# 1. Status & Workspace Health
# -----------------------------------------------------------------------------

def get_status(root: Optional[Path] = None) -> Dict[str, Any]:
    """Get Career OS workspace status, tracker metrics, and draft packages."""
    repo = resolve_repo_root(root)
    tracker_file = repo / "job_search_tracker.csv"
    apps_dir = repo / "documents" / "applications"

    tracker_entries = []
    status_counts: Dict[str, int] = {}
    if tracker_file.exists():
        with open(tracker_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tracker_entries.append(row)
                st = (row.get("status") or "unknown").strip().lower()
                status_counts[st] = status_counts.get(st, 0) + 1

    draft_packages = []
    if apps_dir.exists():
        for d in sorted(apps_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                files = [f.name for f in d.iterdir() if f.is_file()]
                draft_packages.append({
                    "package_name": d.name,
                    "path": str(d),
                    "has_cv": "cv.pdf" in files or "resume.pdf" in files,
                    "has_cover_letter": "cover-letter.pdf" in files or "cover_letter.pdf" in files,
                    "has_posting": "job_posting.md" in files,
                    "has_outcome": "outcome.md" in files,
                    "is_sample": "sample" in d.name.lower(),
                })

    available_cvs = []
    if SAMPLE_CV_DIR.exists():
        for f in sorted(SAMPLE_CV_DIR.glob("*.pdf")):
            available_cvs.append(f.name)

    return {
        "workspace_root": str(repo),
        "tracker_file": str(tracker_file),
        "tracker_exists": tracker_file.exists(),
        "total_tracker_rows": len(tracker_entries),
        "status_counts": status_counts,
        "total_application_packages": len(draft_packages),
        "application_packages": draft_packages,
        "authoritative_sources": {
            "master_experience_document": str(MASTER_EXP_DOC),
            "master_experience_exists": MASTER_EXP_DOC.exists(),
            "sample_cv_dir": str(SAMPLE_CV_DIR),
            "available_cv_pdfs": available_cvs,
        },
        "submission_invariant": "Applications must be submitted manually by user; tracker is updated only after confirmed outcome.",
    }


# -----------------------------------------------------------------------------
# 2. Posting Evaluation & Security Audit
# -----------------------------------------------------------------------------

def evaluate_posting(
    text_or_url: str,
    target_track: str = "ai-systems",
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Audit and evaluate a job posting against candidate profile and safety rules."""
    repo = resolve_repo_root(root)
    raw_text = text_or_url.strip()
    is_url = raw_text.startswith("http://") or raw_text.startswith("https://")
    source_url = raw_text if is_url else ""

    if is_url:
        try:
            from tools import fetch_page
            res = fetch_page.fetch_with_urllib(raw_text)
            if res and isinstance(res, tuple):
                body = res[0]
            elif isinstance(res, str):
                body = res
            else:
                body = raw_text
            raw_text = body
            mode = "html"
        except Exception:
            mode = "text"
    else:
        if posting_guard is not None and getattr(posting_guard, "HTML_HINT", None) and posting_guard.HTML_HINT.search(raw_text):
            mode = "html"
        elif "<html" in raw_text.lower() or "<div" in raw_text.lower() or "<body" in raw_text.lower():
            mode = "html"
        else:
            mode = "text"

    # 1. Posting guard audit
    cleaned_text = raw_text
    guard_findings: Dict[str, Any] = {}
    verdict = "posting_guard: uninspected"
    if posting_guard is not None:
        try:
            cleaned_text, guard_findings = posting_guard.guard(raw_text, mode=mode)
            verdict = posting_guard.verdict(guard_findings)
        except Exception as e:
            guard_findings = {"error": str(e)}
            verdict = "posting_guard: warning"

    # 2. Metadata extraction
    lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]
    estimated_company = "Target Company"
    estimated_role = "AI Systems Engineer"
    for line in lines[:10]:
        comp_m = re.search(r"(?:at|@|company:?)\s+([A-Za-z0-9\.\-\s]+)", line, re.I)
        if comp_m and len(comp_m.group(1).strip()) > 1:
            estimated_company = comp_m.group(1).strip()
            break
        role_m = re.search(r"((?:AI|ML|Machine Learning|Software|Backend|Platform|Systems)\s+(?:Engineer|Developer|Architect|Lead))", line, re.I)
        if role_m:
            estimated_role = role_m.group(1).strip()

    # 3. Location & Work Authorization Policy
    lower_text = cleaned_text.lower()
    is_remote = "remote" in lower_text or "distributed" in lower_text or "anywhere" in lower_text
    is_authorized_region = any(term in lower_text for term in ["us", "usa", "united states", "emea", "global", "worldwide"])

    location_status = "VERIFIED_LOCATION"
    location_notes = "Role matches candidate authorized geographic criteria."
    if is_remote and not is_authorized_region:
        location_status = "FLAG_UNVERIFIED_LOCATION"
        location_notes = "Remote position without explicit work eligibility confirmation (⚠ location FLAG)."

    # 4. Profile & Skill Match Analysis
    candidate_strengths = [
        ("AI Agent Architecture & Multi-Agent Systems", ["agent", "agents", "multi-agent", "autonomous", "tool use", "function calling", "mcp"]),
        ("Production LLM Pipelines & Evaluation", ["llm", "rag", "eval", "evaluation", "prompt", "inference", "orchestration"]),
        ("Backend & Distributed Systems (Go, Python, TypeScript)", ["go", "golang", "python", "typescript", "microservices", "distributed", "concurrency", "api"]),
        ("Data & Storage Infrastructure (PostgreSQL, Redis, RabbitMQ)", ["postgres", "postgresql", "redis", "rabbitmq", "queue", "database", "sql"]),
        ("System Reliability & Gate Architecture", ["ci/cd", "testing", "unit test", "docker", "deterministic", "fail-safe", "observability"]),
    ]

    matched_strengths = []
    matched_keywords = []
    for strength_name, keywords in candidate_strengths:
        matched = [kw for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", lower_text)]
        if matched:
            matched_strengths.append(strength_name)
            matched_keywords.extend(matched)

    # Compute fit score
    base_score = 45
    base_score += min(len(matched_strengths) * 12, 45)
    if location_status == "VERIFIED_LOCATION":
        base_score += 10
    else:
        base_score -= 15
    fit_score = max(0, min(100, base_score))

    recommendation = "PROCEED_TO_DRAFT" if fit_score >= 70 and location_status != "FLAG_UNVERIFIED_LOCATION" else "REVIEW_REQUIRED"

    return {
        "verdict": verdict,
        "is_safe": "suspicious" not in verdict.lower(),
        "security_findings": guard_findings,
        "source_url": source_url,
        "estimated_company": estimated_company,
        "estimated_role": estimated_role,
        "target_track": target_track,
        "location_status": location_status,
        "location_notes": location_notes,
        "fit_score": fit_score,
        "matched_strengths": matched_strengths,
        "matched_keywords": sorted(list(set(matched_keywords))),
        "recommendation": recommendation,
        "cleaned_posting_excerpt": cleaned_text[:1200] + ("..." if len(cleaned_text) > 1200 else ""),
    }


# -----------------------------------------------------------------------------
# 3. Application Package Drafting (Isolated from Tracker)
# -----------------------------------------------------------------------------

def draft_application(
    company: str,
    role: str,
    posting_text: str,
    cv_track: str = "ai-systems",
    custom_focus: Optional[str] = None,
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Draft application package in documents/applications/<company>_<role>/.

    CRITICAL INVARIANT: NEVER touches job_search_tracker.csv during drafting!
    """
    repo = resolve_repo_root(root)
    tracker_path = repo / "job_search_tracker.csv"
    tracker_mtime_before = tracker_path.stat().st_mtime if tracker_path.exists() else None

    # Sanitize names and package dir
    co_slug = sanitize_filename(company)
    role_slug = sanitize_filename(role)
    package_name = f"{co_slug}_{role_slug}"
    package_dir = repo / "documents" / "applications" / package_name
    package_dir.mkdir(parents=True, exist_ok=True)

    # 1. Clean posting text and write job_posting.md
    cleaned_posting = posting_text
    findings: Dict[str, Any] = {}
    if posting_guard is not None:
        try:
            cleaned_posting, findings = posting_guard.guard(posting_text, mode="text")
        except Exception:
            pass

    posting_md = package_dir / "job_posting.md"
    posting_content = f"# Job Posting: {role} at {company}\n\n"
    posting_content += f"- **Date Captured:** {datetime.date.today().isoformat()}\n"
    posting_content += f"- **Track:** {cv_track}\n"
    posting_content += f"- **posting_guard findings:** {findings}\n\n"
    posting_content += "## Cleaned Description\n\n"
    posting_content += cleaned_posting + "\n"
    posting_md.write_text(posting_content, encoding="utf-8")

    # 2. Select CV from sample_profile/cv/
    selected_cv_pdf = SAMPLE_CV_DIR / "resume-ai-systems.pdf"
    if not selected_cv_pdf.exists():
        fallback_sample = repo / "documents" / "applications" / "sample-ai-engineer" / "resume.pdf"
        if fallback_sample.exists():
            selected_cv_pdf = fallback_sample

    dest_cv = package_dir / "cv.pdf"
    if selected_cv_pdf.exists():
        shutil.copyfile(selected_cv_pdf, dest_cv)

    # Verify CV PDF page count (must be exactly 2 pages)
    cv_verified = False
    cv_verify_msg = ""
    if verify_pdf is not None and dest_cv.exists():
        try:
            verify_pdf.verify_pdf(dest_cv, expected_pages=2)
            cv_verified = True
            cv_verify_msg = "CV verified: exactly 2 pages with valid text layer."
        except Exception as e:
            cv_verify_msg = f"CV verification warning: {e}"

    # 3. Generate tailored Cover Letter
    cover_letter_html = package_dir / "cover-letter.html"
    cover_letter_pdf = package_dir / "cover-letter.pdf"

    focus_note = custom_focus if custom_focus else "production AI systems, deterministic evaluation gates, and scalable microservices"

    html_content = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Cover Letter — {html.escape(role)} at {html.escape(company)}</title>
<style>
body {{
  font-family: Arial, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, sans-serif;
  font-size: 11pt;
  line-height: 1.5;
  color: #222;
  margin: 0;
  padding: 0;
}}
p {{
  margin: 0 0 1.1em 0;
}}
.header {{
  margin-bottom: 2em;
}}
.header h1 {{
  font-size: 16pt;
  margin: 0 0 4px 0;
  color: #111;
}}
.header .contact {{
  color: #555;
  font-size: 10pt;
}}
</style>
</head>
<body>
<div class="header">
  <h1>Alex Vance</h1>
  <div class="contact">San Francisco, CA &bull; alex.vance@example.com &bull; +1-555-0199 &bull; github.com/example</div>
</div>

<p>Dear Hiring Team at {html.escape(company)},</p>

<p>I am writing to express my strong interest in the <strong>{html.escape(role)}</strong> role. My background centers on {html.escape(focus_note)}, with a consistent engineering thesis across production and open-source systems: AI proposes, deterministic code validates and gates, and nothing with a real external effect happens without hard verification.</p>

<p>In previous platform roles, I designed and shipped core AI orchestration platforms across 20+ production workflows. Among other systems, I built an AI planning framework that turns natural language intent into codebase-grounded task trees bounded by deterministic verification gates, ensuring zero unreviewed model outputs reach production systems unreviewed.</p>

<p>I also architected multi-provider AI failover networks with circuit breakers and sub-100ms API response latency, and designed agent autonomy governance frameworks featuring hard kill switches, token budgets, and live prompt-injection defense.</p>

<p>I would welcome the opportunity to discuss how my hands-on experience building dependable AI platforms and backend infrastructure can contribute to {html.escape(company)}'s engineering initiatives.</p>

<p>Thank you for your consideration.</p>

<p>Sincerely,<br>
<strong>Alex Vance</strong></p>
</body>
</html>
"""
    cover_letter_html.write_text(html_content, encoding="utf-8")

    # Render PDF if Node/Puppeteer script is configured
    cl_rendered = False
    render_script = REPO_ROOT / "render-pdf.mjs"
    if render_script.exists() and shutil.which("node"):
        try:
            cmd = ["node", str(render_script), str(cover_letter_html), str(cover_letter_pdf)]
            sub = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if sub.returncode == 0 and cover_letter_pdf.exists():
                cl_rendered = True
        except Exception:
            pass

    # Verify Cover Letter PDF (must be exactly 1 page)
    cl_verified = False
    cl_verify_msg = ""
    if cl_rendered and verify_pdf is not None:
        try:
            verify_pdf.verify_pdf(cover_letter_pdf, expected_pages=1)
            cl_verified = True
            cl_verify_msg = "Cover letter verified: exactly 1 page with ATS text layer."
        except Exception as e:
            cl_verify_msg = f"Cover letter verification warning: {e}"

    # Write notes.md
    notes_md = package_dir / "notes.md"
    notes_md.write_text(f"""# Application Notes: {company} - {role}

- **Drafted Date:** {datetime.date.today().isoformat()}
- **Track:** {cv_track}
- **CV File:** cv.pdf
- **CV Verified (2 pages):** {cv_verified} ({cv_verify_msg})
- **Cover Letter Verified (1 page):** {cl_verified} ({cl_verify_msg})
- **Status:** DRAFT (Not recorded in job_search_tracker.csv)

## Checklist Before Manual Submission
- [ ] Review cv.pdf against role requirements.
- [ ] Review cover-letter.html / cover-letter.pdf.
- [ ] Verify employer application portal work authorization questions.
- [ ] Submit application manually.
- [ ] Run career_os_record_submission after actual submission to update tracker.
""", encoding="utf-8")

    # Double check Invariant: tracker was NOT modified
    tracker_mtime_after = tracker_path.stat().st_mtime if tracker_path.exists() else None
    assert tracker_mtime_before == tracker_mtime_after, "Fatal: job_search_tracker.csv was modified during draft creation!"

    return {
        "status": "DRAFT_READY",
        "company": company,
        "role": role,
        "package_directory": str(package_dir),
        "files_created": {
            "job_posting": str(posting_md),
            "cv": str(dest_cv),
            "cover_letter_html": str(cover_letter_html),
            "cover_letter_pdf": str(cover_letter_pdf) if cl_rendered else None,
            "notes": str(notes_md),
        },
        "cv_verification": {
            "verified": cv_verified,
            "message": cv_verify_msg,
        },
        "cover_letter_verification": {
            "verified": cl_verified,
            "message": cl_verify_msg,
        },
        "tracker_updated": False,
        "message": "Application drafted successfully in documents/applications/. As required by Career OS safety invariants, this draft has NOT been added to job_search_tracker.csv. Submit manually on the employer portal and confirm submission via career_os_record_submission.",
    }


# -----------------------------------------------------------------------------
# 4. Submission Recording (Gated Outcome Logger)
# -----------------------------------------------------------------------------

def record_submission(
    company: str,
    role: str,
    submission_date: Optional[str] = None,
    sector: str = "Technology",
    role_type: str = "Full-time",
    channel: str = "Direct",
    contact_person: str = "",
    fit_rating: str = "Strong",
    notes: str = "Applied via employer portal",
    source: str = "Direct",
    deadline: str = "",
    user_confirmed: bool = False,
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Record an application to job_search_tracker.csv ONLY after confirmed actual submission.

    CRITICAL INVARIANT: Requires user_confirmed=True.
    """
    if not user_confirmed:
        return {
            "status": "CONFIRMATION_REQUIRED",
            "recorded": False,
            "error": "Submission confirmation gate active. Career OS enforces that job_search_tracker.csv only logs applications that have actually been submitted by hand. Pass user_confirmed=True to confirm you have completed the submission on the employer portal.",
        }

    repo = resolve_repo_root(root)
    tracker_path = repo / "job_search_tracker.csv"
    date_str = submission_date if submission_date else datetime.date.today().isoformat()

    # Match package folder
    co_slug = sanitize_filename(company)
    role_slug = sanitize_filename(role)
    package_dir = repo / "documents" / "applications" / f"{co_slug}_{role_slug}"
    if not package_dir.exists():
        matches = list((repo / "documents" / "applications").glob(f"{co_slug}*"))
        if matches:
            package_dir = matches[0]

    cv_rel_path = f"documents/applications/{package_dir.name}/cv.pdf" if package_dir.exists() else ""
    cl_rel_path = f"documents/applications/{package_dir.name}/cover-letter.pdf" if package_dir.exists() else ""

    clean_notes = re.sub(r"[\r\n,]+", "; ", notes.strip()) if notes else "Applied manually"

    row_data = {
        "date": date_str,
        "company": company.strip(),
        "sector": sector.strip(),
        "role": role.strip(),
        "role_type": role_type.strip(),
        "channel": channel.strip(),
        "status": "applied",
        "contact_person": contact_person.strip(),
        "fit_rating": fit_rating.strip(),
        "notes": clean_notes,
        "cv_file": cv_rel_path,
        "cover_letter_file": cl_rel_path,
        "source": source.strip(),
        "deadline": deadline.strip(),
    }

    existing_rows: List[Dict[str, str]] = []
    file_existed = tracker_path.exists()
    updated_existing = False

    if file_existed:
        with open(tracker_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("company", "").strip().lower() == company.strip().lower() and r.get("role", "").strip().lower() == role.strip().lower():
                    r["date"] = date_str
                    r["status"] = "applied"
                    r["notes"] = clean_notes
                    if deadline:
                        r["deadline"] = deadline.strip()
                    updated_existing = True
                existing_rows.append(r)

    if not updated_existing:
        existing_rows.append(row_data)

    temp_tracker = tracker_path.with_suffix(".tmp")
    with open(temp_tracker, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()
        for r in existing_rows:
            filtered = {k: r.get(k, "") for k in CANONICAL_COLUMNS}
            writer.writerow(filtered)
    temp_tracker.replace(tracker_path)

    if package_dir.exists():
        outcome_file = package_dir / "outcome.md"
        outcome_content = f"""# Outcome: {company} - {role}

- **Actual Submission Date:** {date_str}
- **Status:** applied
- **Channel:** {channel}
- **Notes:** {clean_notes}
- **CV Submitted:** {cv_rel_path}
- **Cover Letter Submitted:** {cl_rel_path}
- **Recorded in Tracker:** job_search_tracker.csv (14 canonical columns)
"""
        outcome_file.write_text(outcome_content, encoding="utf-8")

    return {
        "status": "SUBMISSION_RECORDED",
        "recorded": True,
        "action": "updated" if updated_existing else "appended",
        "tracker_file": str(tracker_path),
        "record": row_data,
        "outcome_file": str(package_dir / "outcome.md") if package_dir.exists() else None,
        "message": f"Successfully logged application for {company} ({role}) on {date_str} to job_search_tracker.csv.",
    }


# -----------------------------------------------------------------------------
# 5. Interview Preparation Briefing
# -----------------------------------------------------------------------------

def prepare_interview(
    company: str,
    role: Optional[str] = None,
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate comprehensive interview preparation grounded in submitted materials."""
    repo = resolve_repo_root(root)
    co_slug = sanitize_filename(company)

    apps_dir = repo / "documents" / "applications"
    matched_dir = None
    if apps_dir.exists():
        for d in apps_dir.iterdir():
            if d.is_dir() and d.name.lower().startswith(co_slug):
                matched_dir = d
                break

    briefing = {
        "company": company,
        "role": role if role else "AI Systems Engineer",
        "application_package": str(matched_dir) if matched_dir else "None (generic preparation)",
        "talking_points": [
            {
                "topic": "Deterministic Agent Architecture (Core Design Thesis)",
                "summary": "AI proposes, deterministic code validates and gates, nothing with external effect runs without hard human or policy checks.",
                "evidence": "Planner with deterministic Go gates, advisory LLM-judge with closed prompt injection vulnerability, and autonomous agent governance frameworks.",
            },
            {
                "topic": "High-Throughput Production AI Systems",
                "summary": "Architected generation platform across 20+ production workflows with multi-provider failover.",
                "evidence": "Migrated from blocking HTTP to async queue-based workers (RabbitMQ/Redis), cutting response latency to <100ms with circuit breakers across external AI providers.",
            },
            {
                "topic": "Production Reliability & Engineering Rigor",
                "summary": "Automated testing, deterministic gates, and phased feature-flagged migrations.",
                "evidence": "Extracted microservices with per-endpoint rollback safety and zero service downtime.",
            },
        ],
        "suggested_reverse_questions": [
            f"How does the engineering team at {company} manage uncertainty and verification in LLM-driven pipelines?",
            "What does the current boundary look like between model-generated code/data and production write operations?",
            "How does the team handle latency, failover, and rate limits across external foundation model APIs?",
            "What are the highest-priority architectural bottlenecks the platform engineering team is facing this quarter?",
        ],
    }

    return briefing


# -----------------------------------------------------------------------------
# 6. Salary Benchmark Lookup
# -----------------------------------------------------------------------------

def lookup_salary(
    company: str,
    city: Optional[str] = None,
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Query salary benchmark data using salary_lookup.py."""
    repo = resolve_repo_root(root)
    salary_script = repo / "salary_lookup.py"

    if not salary_script.exists():
        return {"error": "salary_lookup.py not found in repository"}

    cmd = [sys.executable, str(salary_script), company, "--json"]
    if city:
        cmd.extend(["--city", city])

    try:
        res = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=10)
        import json
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            return {"company": company, "city": city, "data": data}
        return {"company": company, "city": city, "raw_output": res.stdout, "stderr": res.stderr}
    except Exception as e:
        return {"error": f"Failed to execute salary_lookup: {e}"}
