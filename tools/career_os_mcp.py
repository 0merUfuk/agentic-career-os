#!/usr/bin/env python3
"""Career OS Model Context Protocol (MCP) Server.

Exposes Career OS capabilities (posting audit, fit evaluation, application drafting,
consequential submission recording, interview prep, salary benchmark) as standard MCP tools
over stdio JSON-RPC 2.0.

Compatible with Claude Code, Google Antigravity, OpenAI Codex, Cursor, Zed, and any MCP client.
Zero external runtime dependencies: runs natively on standard Python 3.10+.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Insert tools directory into sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import career_os_core

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "career-os"
SERVER_VERSION = "1.0.0"

# -----------------------------------------------------------------------------
# Tool Definitions (Schemas & Descriptions)
# -----------------------------------------------------------------------------

TOOLS_REGISTRY: List[Dict[str, Any]] = [
    {
        "name": "career_os_status",
        "description": (
            "Inspect Career OS workspace status, application tracker statistics, pending draft packages, "
            "and authoritative resume data sources."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "career_os_evaluate_posting",
        "description": (
            "Audit and evaluate a job posting for fit and security. Sanitizes tracking pixels and prompt injection "
            "risks via posting_guard, matches requirements against candidate profile and master experience document, "
            "and checks Türkiye/remote work authorization (flagging unverified remote roles with ⚠ location FLAG)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text_or_url": {
                    "type": "string",
                    "description": "Job posting URL or raw posting text to evaluate.",
                },
                "target_track": {
                    "type": "string",
                    "description": "Candidate CV track to evaluate against: 'ai-systems' (default) or 'ai-engineering'.",
                    "default": "ai-systems",
                },
            },
            "required": ["text_or_url"],
            "additionalProperties": False,
        },
    },
    {
        "name": "career_os_draft_application",
        "description": (
            "Prepare a complete draft application package in documents/applications/<company>_<role>/. "
            "Copies verified 2-page CV from Resume repository, generates tailored evidence-first cover letter, "
            "and verifies PDFs with verify_pdf.py (CV exactly 2 pages, cover letter exactly 1 page). "
            "CRITICAL INVARIANT: Draft packages are strictly isolated and NEVER modify job_search_tracker.csv."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name.",
                },
                "role": {
                    "type": "string",
                    "description": "Role title.",
                },
                "posting_text": {
                    "type": "string",
                    "description": "Job posting description or cleaned text.",
                },
                "cv_track": {
                    "type": "string",
                    "description": "CV track to select: 'ai-systems' (default) or 'ai-engineering'.",
                    "default": "ai-systems",
                },
                "custom_focus": {
                    "type": "string",
                    "description": "Specific technical strengths, systems, or projects to emphasize in the cover letter.",
                },
            },
            "required": ["company", "role", "posting_text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "career_os_record_submission",
        "description": (
            "Consequential Action Gate: Log an application to job_search_tracker.csv with the canonical 14 columns "
            "and write outcome.md. Enforces invariant that tracker entries only occur AFTER confirmed manual submission. "
            "Fails if user_confirmed is false."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name.",
                },
                "role": {
                    "type": "string",
                    "description": "Role title.",
                },
                "user_confirmed": {
                    "type": "boolean",
                    "description": "Explicit confirmation that the user has already manually submitted the application on the employer portal.",
                },
                "submission_date": {
                    "type": "string",
                    "description": "Submission date in YYYY-MM-DD format (defaults to current date).",
                },
                "notes": {
                    "type": "string",
                    "description": "Application notes. Commas will be automatically replaced with semicolons to preserve CSV formatting.",
                },
                "sector": {
                    "type": "string",
                    "description": "Industry sector (default: Technology).",
                    "default": "Technology",
                },
                "role_type": {
                    "type": "string",
                    "description": "Job role type (default: Full-time).",
                    "default": "Full-time",
                },
                "channel": {
                    "type": "string",
                    "description": "Submission channel (default: Direct).",
                    "default": "Direct",
                },
                "deadline": {
                    "type": "string",
                    "description": "Application deadline if specified.",
                },
            },
            "required": ["company", "role", "user_confirmed"],
            "additionalProperties": False,
        },
    },
    {
        "name": "career_os_interview_prep",
        "description": (
            "Generate a structured interview preparation briefing grounded in submitted application materials "
            "(cv.pdf, cover-letter.pdf), cached company research, and the master experience document. "
            "Returns core thesis talking points, STAR examples, and reverse interview questions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name.",
                },
                "role": {
                    "type": "string",
                    "description": "Role title (optional).",
                },
            },
            "required": ["company"],
            "additionalProperties": False,
        },
    },
    {
        "name": "career_os_salary_lookup",
        "description": "Query local compensation benchmark data for a company and city.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name.",
                },
                "city": {
                    "type": "string",
                    "description": "City filter (optional).",
                },
            },
            "required": ["company"],
            "additionalProperties": False,
        },
    },
]


# -----------------------------------------------------------------------------
# Tool Execution Handlers
# -----------------------------------------------------------------------------

def handle_status(args: Dict[str, Any]) -> str:
    res = career_os_core.get_status()
    return json.dumps(res, indent=2)


def handle_evaluate(args: Dict[str, Any]) -> str:
    text_or_url = args.get("text_or_url", "")
    target_track = args.get("target_track", "ai-systems")
    res = career_os_core.evaluate_posting(text_or_url, target_track=target_track)
    return json.dumps(res, indent=2)


def handle_draft(args: Dict[str, Any]) -> str:
    res = career_os_core.draft_application(
        company=args["company"],
        role=args["role"],
        posting_text=args["posting_text"],
        cv_track=args.get("cv_track", "ai-systems"),
        custom_focus=args.get("custom_focus"),
    )
    return json.dumps(res, indent=2)


def handle_record(args: Dict[str, Any]) -> str:
    res = career_os_core.record_submission(
        company=args["company"],
        role=args["role"],
        submission_date=args.get("submission_date"),
        sector=args.get("sector", "Technology"),
        role_type=args.get("role_type", "Full-time"),
        channel=args.get("channel", "Direct"),
        notes=args.get("notes", "Applied via employer portal"),
        deadline=args.get("deadline", ""),
        user_confirmed=args.get("user_confirmed", False),
    )
    return json.dumps(res, indent=2)


def handle_interview(args: Dict[str, Any]) -> str:
    res = career_os_core.prepare_interview(
        company=args["company"],
        role=args.get("role"),
    )
    return json.dumps(res, indent=2)


def handle_salary(args: Dict[str, Any]) -> str:
    res = career_os_core.lookup_salary(
        company=args["company"],
        city=args.get("city"),
    )
    return json.dumps(res, indent=2)


HANDLERS: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "career_os_status": handle_status,
    "career_os_evaluate_posting": handle_evaluate,
    "career_os_draft_application": handle_draft,
    "career_os_record_submission": handle_record,
    "career_os_interview_prep": handle_interview,
    "career_os_salary_lookup": handle_salary,
}


# -----------------------------------------------------------------------------
# JSON-RPC 2.0 Protocol Engine
# -----------------------------------------------------------------------------

def send_response(response: Dict[str, Any]) -> None:
    """Send a JSON-RPC response to stdout followed by newline and flush."""
    encoded = json.dumps(response)
    sys.stdout.write(encoded + "\n")
    sys.stdout.flush()


def process_message(msg: Dict[str, Any]) -> None:
    """Process a single JSON-RPC message."""
    method = msg.get("method")
    msg_id = msg.get("id")

    # Notifications (no response expected)
    if msg_id is None:
        if method == "notifications/initialized":
            sys.stderr.write("[MCP] Client initialized successfully.\n")
            sys.stderr.flush()
        return

    # Requests
    if method == "initialize":
        send_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            },
        })
    elif method == "ping":
        send_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {},
        })
    elif method == "tools/list":
        send_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": TOOLS_REGISTRY,
            },
        })
    elif method == "tools/call":
        params = msg.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        handler = HANDLERS.get(tool_name)

        if not handler:
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool '{tool_name}' not found.",
                },
            })
            return

        try:
            output_text = handler(args)
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": output_text,
                        }
                    ],
                    "isError": False,
                },
            })
        except Exception as e:
            sys.stderr.write(f"[MCP] Tool {tool_name} error: {e}\n")
            sys.stderr.flush()
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error executing {tool_name}: {e}",
                        }
                    ],
                    "isError": True,
                },
            })
    else:
        send_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found.",
            },
        })


def run_stdio_server() -> None:
    """Read JSON-RPC messages from stdin (handling both raw JSON lines and Content-Length headers)."""
    sys.stderr.write(f"[MCP] Starting {SERVER_NAME} v{SERVER_VERSION} on stdio...\n")
    sys.stderr.flush()

    while True:
        line = sys.stdin.readline()
        if not line:
            break

        line_str = line.strip()
        if not line_str:
            continue

        # Handle HTTP-style Content-Length header framing if present
        if line_str.lower().startswith("content-length:"):
            try:
                parts = line_str.split(":", 1)
                content_len = int(parts[1].strip())
                # Read until empty line separating headers from body
                while True:
                    hdr = sys.stdin.readline()
                    if not hdr or hdr.strip() == "":
                        break
                # Read exact content length bytes
                body = sys.stdin.read(content_len)
                msg = json.loads(body)
                process_message(msg)
            except Exception as e:
                sys.stderr.write(f"[MCP] Error reading header-framed message: {e}\n")
                sys.stderr.flush()
            continue

        # Standard line-delimited JSON
        try:
            msg = json.loads(line_str)
            process_message(msg)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[MCP] JSON decode error: {e} for line: {line_str[:100]}\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"[MCP] Unexpected error: {e}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    run_stdio_server()
