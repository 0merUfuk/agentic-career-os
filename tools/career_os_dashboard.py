#!/usr/bin/env python3
"""Interactive Zero-Dependency HTML Application Dashboard Generator for Career OS.

Reads job_search_tracker.csv and application folders to generate a self-contained,
offline, responsive HTML Kanban and analytics dashboard.

Usage:
    python3 tools/career_os_dashboard.py
    python3 tools/career_os_dashboard.py --open
    python3 tools/career_os_dashboard.py --out reports/dashboard.html
"""

from __future__ import annotations

import argparse
import csv
import datetime
import html
import os
import sys
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACKER_CSV = REPO_ROOT / "job_search_tracker.csv"
DOCUMENTS_DIR = REPO_ROOT / "documents"
APPLICATIONS_DIR = DOCUMENTS_DIR / "applications"
DEFAULT_OUTPUT_HTML = REPO_ROOT / "reports" / "application-dashboard.html"

STATUS_COLORS = {
    "Drafted": "#64748b",
    "Active": "#3b82f6",
    "Interview": "#f59e0b",
    "Offer": "#8b5cf6",
    "Hired": "#10b981",
    "Rejected/Closed": "#ef4444",
}


def normalize_status(raw_status: str) -> str:
    """Map raw tracker status into standard visual categories."""
    st = raw_status.strip().lower().replace("-", "_").replace(" ", "_")
    if st in ("draft", "drafted"):
        return "Drafted"
    elif st in ("applied", "active", "submitted"):
        return "Active"
    elif any(k in st for k in ("interview", "screen", "technical", "take_home", "recruiter", "manager")):
        return "Interview"
    elif st in ("offer", "offered"):
        return "Offer"
    elif st in ("hired", "accepted"):
        return "Hired"
    elif any(k in st for k in ("reject", "no_response", "declined", "withdrawn", "closed")):
        return "Rejected/Closed"
    return "Rejected/Closed"


def parse_tracker_data(tracker_path: Path) -> List[Dict[str, str]]:
    """Parse rows from job_search_tracker.csv with safe defaults."""
    rows: List[Dict[str, str]] = []
    if not tracker_path.exists():
        return rows

    with open(tracker_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return rows

        # Clean header keys
        keys = [h.strip().lower() for h in header]
        for line_num, raw_row in enumerate(reader, start=2):
            if not raw_row or not any(raw_row):
                continue
            row_dict: Dict[str, str] = {}
            for i, k in enumerate(keys):
                val = raw_row[i].strip() if i < len(raw_row) else ""
                row_dict[k] = val
            rows.append(row_dict)
    return rows


def generate_svg_donut(status_counts: Dict[str, int]) -> str:
    """Generate hand-crafted inline SVG donut chart."""
    total = sum(status_counts.values())
    if total == 0:
        return '<svg width="200" height="200" viewBox="0 0 42 42"><circle cx="21" cy="21" r="15.9" fill="transparent" stroke="#e2e8f0" stroke-width="4"/><text x="21" y="22" font-size="3" text-anchor="middle" fill="#64748b">No Data</text></svg>'

    size = 42
    r = 15.91549430918954
    cx, cy = 21, 21
    svg_parts = [
        f'<svg width="220" height="220" viewBox="0 0 {size} {size}" role="img" aria-label="Status Distribution">'
    ]

    offset = 25.0
    for st, count in status_counts.items():
        if count == 0:
            continue
        pct = (count / total) * 100
        dash = f"{pct:.2f} {100.0 - pct:.2f}"
        color = STATUS_COLORS.get(st, "#94a3b8")
        svg_parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="transparent" '
            f'stroke="{color}" stroke-width="4" stroke-dasharray="{dash}" '
            f'stroke-dashoffset="{offset:.2f}"><title>{html.escape(st)}: {count} ({pct:.1f}%)</title></circle>'
        )
        offset = (offset - pct) % 100.0

    svg_parts.append(
        f'<text x="{cx}" y="{cy - 1}" font-size="5" font-weight="700" text-anchor="middle" fill="#0f172a">{total}</text>'
    )
    svg_parts.append(
        f'<text x="{cx}" y="{cy + 4}" font-size="2.5" text-anchor="middle" fill="#64748b">TOTAL</text>'
    )
    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def generate_html_dashboard(
    tracker_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    apps_dir: Optional[Path] = None,
) -> Path:
    """Compile job search tracker and application records into an offline HTML dashboard."""
    t_path = tracker_path or TRACKER_CSV
    out_path = output_path or DEFAULT_OUTPUT_HTML
    a_dir = apps_dir or APPLICATIONS_DIR

    rows = parse_tracker_data(t_path)

    # Calculate status buckets
    bucket_counts: Dict[str, int] = {
        "Drafted": 0,
        "Active": 0,
        "Interview": 0,
        "Offer": 0,
        "Hired": 0,
        "Rejected/Closed": 0,
    }
    sectors: Dict[str, int] = {}
    channels: Dict[str, int] = {}

    for r in rows:
        cat = normalize_status(r.get("status", ""))
        bucket_counts[cat] = bucket_counts.get(cat, 0) + 1
        sec = r.get("sector") or "Unclassified"
        sectors[sec] = sectors.get(sec, 0) + 1
        ch = r.get("channel") or "Direct"
        channels[ch] = channels.get(ch, 0) + 1

    total_submitted = sum(count for cat, count in bucket_counts.items() if cat != "Drafted")
    interview_count = bucket_counts["Interview"] + bucket_counts["Offer"] + bucket_counts["Hired"]
    interview_rate = (interview_count / total_submitted * 100) if total_submitted > 0 else 0.0

    donut_svg = generate_svg_donut(bucket_counts)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Table rows HTML
    table_rows_html = []
    for r in rows:
        company = html.escape(r.get("company", "—"))
        role = html.escape(r.get("role", "—"))
        sector = html.escape(r.get("sector", "—"))
        date = html.escape(r.get("date", "—"))
        raw_st = r.get("status", "drafted")
        norm_st = normalize_status(raw_st)
        fit = html.escape(r.get("fit_rating", "—"))
        notes = html.escape(r.get("notes", "—"))
        source = r.get("source", "").strip()

        color = STATUS_COLORS.get(norm_st, "#94a3b8")
        status_badge = f'<span class="badge" style="background-color: {color}20; color: {color}; border: 1px solid {color}50;">{norm_st}</span>'

        source_link = "—"
        if source.startswith("http://") or source.startswith("https://"):
            source_link = f'<a href="{html.escape(source)}" target="_blank" rel="noopener" class="link-portal">Portal ↗</a>'
        elif source:
            source_link = html.escape(source)

        table_rows_html.append(f"""
        <tr data-status="{norm_st}" data-sector="{sector}">
            <td><strong>{company}</strong></td>
            <td>{role}</td>
            <td><span class="sector-tag">{sector}</span></td>
            <td>{status_badge}</td>
            <td>{fit}</td>
            <td class="date-cell">{date}</td>
            <td class="notes-cell" title="{notes}">{notes}</td>
            <td>{source_link}</td>
        </tr>
        """)

    table_body = "\n".join(table_rows_html) if table_rows_html else '<tr><td colspan="8" class="empty">No applications tracked yet. Run <code>career draft</code> to prepare your first application.</td></tr>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Career OS — Application Intelligence Dashboard</title>
<style>
:root {{
  --bg-primary: #0f172a;
  --bg-card: #1e293b;
  --bg-subtle: #334155;
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --border: #334155;
  --accent: #38bdf8;
  --drafted: {STATUS_COLORS['Drafted']};
  --active: {STATUS_COLORS['Active']};
  --interview: {STATUS_COLORS['Interview']};
  --offer: {STATUS_COLORS['Offer']};
  --hired: {STATUS_COLORS['Hired']};
  --rejected: {STATUS_COLORS['Rejected/Closed']};
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background-color: var(--bg-primary);
  color: var(--text-main);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  padding: 24px;
}}

.dashboard-container {{
  max-width: 1240px;
  margin: 0 auto;
}}

header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}}

header h1 {{
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
}}

header .meta {{
  color: var(--text-muted);
  font-size: 13px;
}}

.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}}

.stat-card {{
  background: var(--bg-card);
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--border);
  border-left: 4px solid var(--accent);
}}
.stat-card.active {{ border-left-color: var(--active); }}
.stat-card.interview {{ border-left-color: var(--interview); }}
.stat-card.offer {{ border-left-color: var(--offer); }}
.stat-card.drafted {{ border-left-color: var(--drafted); }}
.stat-card.rejected {{ border-left-color: var(--rejected); }}

.stat-card .val {{
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
  margin-bottom: 4px;
}}
.stat-card .lbl {{
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}

.charts-row {{
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  margin-bottom: 24px;
}}
@media (max-width: 860px) {{
  .charts-row {{ grid-template-columns: 1fr; }}
}}

.card {{
  background: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
  padding: 20px;
}}

.card h2 {{
  font-size: 16px;
  margin-bottom: 16px;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}}

.chart-center {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}}

.funnel-list {{
  display: flex;
  flex-direction: column;
  gap: 12px;
  justify-content: center;
  height: 100%;
}}

.funnel-step {{
  display: flex;
  align-items: center;
  gap: 12px;
}}
.funnel-step .lbl {{
  width: 140px;
  font-size: 13px;
  color: var(--text-muted);
}}
.funnel-bar-bg {{
  flex: 1;
  height: 10px;
  background: var(--bg-subtle);
  border-radius: 5px;
  overflow: hidden;
}}
.funnel-bar-fill {{
  height: 100%;
  border-radius: 5px;
  transition: width 0.3s ease;
}}
.funnel-step .val {{
  width: 40px;
  text-align: right;
  font-size: 13px;
  font-weight: 700;
}}

.controls-row {{
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}}
.controls-row input, .controls-row select {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-main);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
}}
.controls-row input {{ flex: 1; min-width: 200px; }}

table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}}
th, td {{
  padding: 12px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}}
th {{
  background: var(--bg-card);
  color: var(--text-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}
tr:hover td {{
  background: rgba(255, 255, 255, 0.02);
}}

.badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}}
.sector-tag {{
  color: var(--text-muted);
  font-size: 12px;
}}
.notes-cell {{
  max-width: 240px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-muted);
  font-size: 13px;
}}
.date-cell {{
  color: var(--text-muted);
  font-size: 13px;
}}
.link-portal {{
  color: var(--accent);
  text-decoration: none;
  font-weight: 500;
}}
.link-portal:hover {{ text-decoration: underline; }}
.empty {{ text-align: center; color: var(--text-muted); padding: 40px !important; }}

footer {{
  margin-top: 32px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}}
</style>
</head>
<body>
<div class="dashboard-container">
  <header>
    <h1>🚀 Career OS <span>&bull; Job Intelligence</span></h1>
    <div class="meta">Generated: {now_str} &bull; Offline & Zero-Dependency</div>
  </header>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="val">{len(rows)}</div>
      <div class="lbl">Total Tracked</div>
    </div>
    <div class="stat-card active">
      <div class="val">{bucket_counts['Active']}</div>
      <div class="lbl">Active Applications</div>
    </div>
    <div class="stat-card interview">
      <div class="val">{bucket_counts['Interview']}</div>
      <div class="lbl">Interview Stage</div>
    </div>
    <div class="stat-card offer">
      <div class="val">{bucket_counts['Offer']}</div>
      <div class="lbl">Active Offers</div>
    </div>
    <div class="stat-card drafted">
      <div class="val">{bucket_counts['Drafted']}</div>
      <div class="lbl">Pending Drafts</div>
    </div>
    <div class="stat-card rejected">
      <div class="val">{interview_rate:.0f}%</div>
      <div class="lbl">Screen Pass Rate</div>
    </div>
  </div>

  <div class="charts-row">
    <div class="card chart-center">
      <h2>Pipeline Distribution</h2>
      {donut_svg}
    </div>
    <div class="card">
      <h2>Conversion Funnel</h2>
      <div class="funnel-list">
        <div class="funnel-step">
          <div class="lbl">1. Submitted</div>
          <div class="funnel-bar-bg"><div class="funnel-bar-fill" style="width: 100%; background: var(--active);"></div></div>
          <div class="val">{total_submitted}</div>
        </div>
        <div class="funnel-step">
          <div class="lbl">2. Screen / Interview</div>
          <div class="funnel-bar-bg"><div class="funnel-bar-fill" style="width: {min(100.0, (interview_count / max(1, total_submitted)) * 100):.1f}%; background: var(--interview);"></div></div>
          <div class="val">{interview_count}</div>
        </div>
        <div class="funnel-step">
          <div class="lbl">3. Final / Offer</div>
          <div class="funnel-bar-bg"><div class="funnel-bar-fill" style="width: {min(100.0, (bucket_counts['Offer'] / max(1, total_submitted)) * 100):.1f}%; background: var(--offer);"></div></div>
          <div class="val">{bucket_counts['Offer']}</div>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Applications Table</h2>
    <div class="controls-row">
      <input type="text" id="searchInput" placeholder="Search by company, role, or notes..." oninput="filterTable()">
      <select id="statusFilter" onchange="filterTable()">
        <option value="">All Statuses</option>
        <option value="Drafted">Drafted</option>
        <option value="Active">Active</option>
        <option value="Interview">Interview</option>
        <option value="Offer">Offer</option>
        <option value="Hired">Hired</option>
        <option value="Rejected/Closed">Rejected/Closed</option>
      </select>
    </div>
    <div style="overflow-x: auto;">
      <table id="appsTable">
        <thead>
          <tr>
            <th>Company</th>
            <th>Role</th>
            <th>Sector</th>
            <th>Status</th>
            <th>Fit</th>
            <th>Date</th>
            <th>Notes</th>
            <th>Portal</th>
          </tr>
        </thead>
        <tbody>
          {table_body}
        </tbody>
      </table>
    </div>
  </div>

  <footer>
    Career OS &bull; "AI proposes, deterministic code validates and gates" &bull; Local-First Architecture
  </footer>
</div>

<script>
function filterTable() {{
  const query = document.getElementById('searchInput').value.toLowerCase();
  const statusFilter = document.getElementById('statusFilter').value;
  const rows = document.querySelectorAll('#appsTable tbody tr');

  rows.forEach(row => {{
    const text = row.innerText.toLowerCase();
    const rowStatus = row.getAttribute('data-status') || '';
    const matchesQuery = !query || text.includes(query);
    const matchesStatus = !statusFilter || rowStatus === statusFilter;

    if (matchesQuery && matchesStatus) {{
      row.style.display = '';
    }} else {{
      row.style.display = 'none';
    }}
  }});
}}
</script>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Career OS HTML Application Dashboard Generator")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_HTML, help="Output HTML file path")
    parser.add_argument("--open", action="store_true", help="Open generated dashboard in default web browser")
    parser.add_argument("--tracker", type=Path, default=TRACKER_CSV, help="Path to job_search_tracker.csv")
    args = parser.parse_args()

    out_file = generate_html_dashboard(tracker_path=args.tracker, output_path=args.out)
    print(f"✓ Dashboard generated: {out_file.resolve()}")

    if args.open:
        webbrowser.open(f"file://{out_file.resolve()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
