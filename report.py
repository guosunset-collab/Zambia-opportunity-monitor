from datetime import datetime
from html import escape
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def _group(items: Iterable[Dict], predicate) -> List[Dict]:
    return [item for item in items if predicate(item)]


def _item_markdown(item: Dict) -> str:
    source = item.get("original_link") or item.get("source_website") or "N/A"
    return "\n".join([
        f"### {item.get('title', 'Untitled')}",
        f"- Entity: {item.get('procuring_entity') or 'Unknown'}",
        f"- Deadline: {item.get('deadline') or 'Not stated'}",
        f"- Type: {item.get('procurement_type') or 'Unspecified'}",
        f"- Sector: {item.get('sector') or 'Unclassified'}",
        f"- Source: {source}",
        f"- Score: {item.get('relevance_score', 0)} ({item.get('priority', 'LOW')})",
        f"- Why relevant: {item.get('recommendation_reason') or 'Not assessed'}",
        f"- Summary: {item.get('raw_text_summary') or 'No summary available'}",
    ])


SOURCE_SECTIONS: Tuple[Tuple[str, str], ...] = (
    ("Government Procurement (ZPPA / eGP)", "Government Procurement"),
    ("Road & Transport (RDA / NRFA / RTSA)", "Road & Transport"),
    ("Airport / Aviation (ZACL / Ministry)", "Airport / Aviation"),
    ("PPP / Investment", "PPP / Investment"),
    ("Donor-funded", "Donor-funded"),
    ("Newspapers", "Newspapers"),
    ("Social Media", "Social Media"),
)


def generate_markdown(items: List[Dict], report_date: str, duplicate_count: int = 0) -> str:
    high = _group(items, lambda item: item.get("priority") == "HIGH")
    ppp = _group(items, lambda item: item.get("ppp_flag"))
    newspaper = _group(items, lambda item: item.get("newspaper_flag"))
    donor = _group(items, lambda item: item.get("donor_funded_flag"))
    manual_review = _group(items, lambda item: item.get("manual_review_flag") or item.get("social_signal_flag"))

    lines = [
        "# Zambia Infrastructure Opportunity Intelligence Report",
        f"Date: {report_date}",
        "",
        "## Executive Brief",
        f"- Total new opportunities: {len(items)}",
        f"- Duplicate historical records skipped: {duplicate_count}",
        f"- High priority items: {len(high)}",
        f"- PPP signals: {len(ppp)}",
        f"- Newspaper findings: {len(newspaper)}",
        f"- Donor-funded opportunities: {len(donor)}",
        f"- Alerts requiring manual review: {len(manual_review)}",
        "",
    ]

    for title, group_key in SOURCE_SECTIONS:
        section_items = _group(items, lambda item, expected=group_key: item.get("source_group") == expected)
        lines.append(f"## {title}")
        if not section_items:
            lines.append("No new matching items found.")
        else:
            seen = set()
            for item in section_items:
                key = item.get("dedupe_key") or item.get("original_link") or item.get("title")
                if key in seen:
                    continue
                seen.add(key)
                lines.append(_item_markdown(item))
                lines.append("")
        lines.append("")

    unknown_items = _group(items, lambda item: item.get("source_group") not in {key for _, key in SOURCE_SECTIONS})
    if unknown_items:
        lines.append("## Other Sources")
        for item in unknown_items:
            lines.append(_item_markdown(item))
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def markdown_to_html(markdown: str) -> str:
    html_lines = []
    in_list = False
    for line in markdown.splitlines():
        if line.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{escape(line[2:])}</li>")
        elif line.strip():
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{escape(line)}</p>")
    if in_list:
        html_lines.append("</ul>")

    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Zambia Infrastructure Opportunity Intelligence Report</title>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.5; max-width: 980px; margin: 32px auto; padding: 0 20px; color: #202124; }
    h1, h2, h3 { color: #12355b; }
    h2 { border-top: 1px solid #d8dee4; padding-top: 18px; }
    li { margin: 4px 0; }
  </style>
</head>
<body>
""" + "\n".join(html_lines) + "\n</body>\n</html>\n"


def write_reports(items: List[Dict], output_dir: str, duplicate_count: int = 0) -> Tuple[Path, Path]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report_date = datetime.utcnow().date().isoformat()
    markdown = generate_markdown(items, report_date, duplicate_count)
    html = markdown_to_html(markdown)

    md_path = Path(output_dir) / f"zambia_infrastructure_report_{report_date}.md"
    html_path = Path(output_dir) / f"zambia_infrastructure_report_{report_date}.html"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return md_path, html_path
