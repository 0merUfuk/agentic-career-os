#!/usr/bin/env python3
"""Career OS CLI Wrapper.

Provides command-line access to Career OS services for terminal users and AI agents (such as Codex,
Copilot, or script runners). Supports both human-readable text output and --json machine output.

Usage:
    career_os_cli.py status [--json]
    career_os_cli.py evaluate (--text "..." | --url "...") [--track TRACK] [--json]
    career_os_cli.py draft --company "..." --role "..." (--text "..." | --file PATH) [--track TRACK] [--json]
    career_os_cli.py record --company "..." --role "..." --confirm [--date YYYY-MM-DD] [--notes "..."] [--json]
    career_os_cli.py interview --company "..." [--role "..."] [--json]
    career_os_cli.py salary --company "..." [--city "..."] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Insert tools directory into sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import career_os_core


def cmd_status(args: argparse.Namespace) -> int:
    res = career_os_core.get_status()
    if args.json:
        print(json.dumps(res, indent=2))
        return 0
    print("=== Career OS Status ===")
    print(f"Workspace Root: {res['workspace_root']}")
    print(f"Tracker Rows: {res['total_tracker_rows']}")
    print(f"Draft Packages: {res['total_application_packages']}")
    for pkg in res["application_packages"]:
        flags = []
        if pkg["has_cv"]:
            flags.append("CV")
        if pkg["has_cover_letter"]:
            flags.append("CoverLetter")
        if pkg["has_outcome"]:
            flags.append("Outcome")
        print(f"  - {pkg['package_name']} [{', '.join(flags)}]")
    print(f"Available Resume PDFs: {', '.join(res['authoritative_sources']['available_cv_pdfs'])}")
    print(f"Submission Invariant: {res['submission_invariant']}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    text = args.text
    if not text and args.url:
        text = args.url
    if not text:
        sys.stderr.write("Error: Either --text or --url must be provided.\n")
        return 1

    res = career_os_core.evaluate_posting(text, target_track=args.track)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print("=== Posting Evaluation ===")
    print(f"Estimated Role: {res['estimated_role']} at {res['estimated_company']}")
    print(f"Security Verdict: {res['verdict']}")
    print(f"Fit Score: {res['fit_score']}/100 ({res['recommendation']})")
    print(f"Location Status: {res['location_status']} — {res['location_notes']}")
    print("Matched Strengths:")
    for s in res["matched_strengths"]:
        print(f"  ✓ {s}")
    print(f"Keywords: {', '.join(res['matched_keywords'])}")
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    posting_text = args.text
    if args.file:
        p = Path(args.file)
        if p.exists():
            posting_text = p.read_text(encoding="utf-8")
        else:
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 1

    if not posting_text:
        sys.stderr.write("Error: Posting text must be provided via --text or --file.\n")
        return 1

    res = career_os_core.draft_application(
        company=args.company,
        role=args.role,
        posting_text=posting_text,
        cv_track=args.track,
        custom_focus=args.custom_focus,
    )

    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print("=== Draft Package Created ===")
    print(f"Directory: {res['package_directory']}")
    print(f"CV: {res['cv_verification']['message']}")
    print(f"Cover Letter: {res['cover_letter_verification']['message']}")
    print(f"Tracker Modified: {res['tracker_updated']} (Drafts remain isolated)")
    print(f"\n{res['message']}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    if not args.confirm:
        sys.stderr.write("Error: You must provide --confirm to certify that you have actually submitted the application by hand.\n")
        return 1

    res = career_os_core.record_submission(
        company=args.company,
        role=args.role,
        submission_date=args.date,
        notes=args.notes or "Applied via portal",
        user_confirmed=True,
    )

    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print("=== Application Recorded ===")
    print(f"Action: {res['action']}")
    print(f"File: {res['tracker_file']}")
    print(f"Message: {res['message']}")
    return 0


def cmd_interview(args: argparse.Namespace) -> int:
    res = career_os_core.prepare_interview(company=args.company, role=args.role)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print(f"=== Interview Preparation: {res['company']} ({res['role']}) ===")
    print(f"Package: {res['application_package']}")
    print("\nCore Talking Points:")
    for tp in res["talking_points"]:
        print(f"\n• {tp['topic']}")
        print(f"  Summary:  {tp['summary']}")
        print(f"  Evidence: {tp['evidence']}")

    print("\nSuggested Reverse Questions to Ask Interviewers:")
    for q in res["suggested_reverse_questions"]:
        print(f"  ? {q}")
    return 0


def cmd_salary(args: argparse.Namespace) -> int:
    res = career_os_core.lookup_salary(company=args.company, city=args.city)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0
    print(f"=== Salary Lookup: {args.company} ===")
    print(json.dumps(res, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Career OS Unified Agent CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Show workspace status and draft packages")
    p_status.add_argument("--json", action="store_true", help="Output JSON")

    # evaluate
    p_eval = subparsers.add_parser("evaluate", help="Audit and evaluate a job posting")
    p_eval.add_argument("--text", type=str, help="Raw job posting text")
    p_eval.add_argument("--url", type=str, help="Job posting URL")
    p_eval.add_argument("--track", type=str, default="ai-systems", help="Target track (e.g. ai-systems, ai-engineering)")
    p_eval.add_argument("--json", action="store_true", help="Output JSON")

    # draft
    p_draft = subparsers.add_parser("draft", help="Draft an application package without modifying tracker")
    p_draft.add_argument("--company", required=True, type=str, help="Company name")
    p_draft.add_argument("--role", required=True, type=str, help="Role title")
    p_draft.add_argument("--text", type=str, help="Job posting text")
    p_draft.add_argument("--file", type=str, help="Path to job posting file")
    p_draft.add_argument("--track", type=str, default="ai-systems", help="CV track")
    p_draft.add_argument("--custom-focus", type=str, help="Custom technical focus")
    p_draft.add_argument("--json", action="store_true", help="Output JSON")

    # record
    p_rec = subparsers.add_parser("record", help="Record actual submission in tracker after confirmed by hand")
    p_rec.add_argument("--company", required=True, type=str, help="Company name")
    p_rec.add_argument("--role", required=True, type=str, help="Role title")
    p_rec.add_argument("--confirm", action="store_true", required=True, help="Certify actual submission completed")
    p_rec.add_argument("--date", type=str, help="Submission date YYYY-MM-DD")
    p_rec.add_argument("--notes", type=str, help="Notes (commas will be stripped)")
    p_rec.add_argument("--json", action="store_true", help="Output JSON")

    # interview
    p_int = subparsers.add_parser("interview", help="Generate interview briefing")
    p_int.add_argument("--company", required=True, type=str, help="Company name")
    p_int.add_argument("--role", type=str, help="Role title")
    p_int.add_argument("--json", action="store_true", help="Output JSON")

    # salary
    p_sal = subparsers.add_parser("salary", help="Query salary data")
    p_sal.add_argument("--company", required=True, type=str, help="Company name")
    p_sal.add_argument("--city", type=str, help="City filter")
    p_sal.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    commands = {
        "status": cmd_status,
        "evaluate": cmd_evaluate,
        "draft": cmd_draft,
        "record": cmd_record,
        "interview": cmd_interview,
        "salary": cmd_salary,
    }

    handler = commands.get(args.subcommand)
    if handler:
        return handler(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
