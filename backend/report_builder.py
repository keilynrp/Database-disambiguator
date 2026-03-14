"""
Report Builder — generates self-contained HTML reports per domain.
No external template dependencies; uses f-strings with inline CSS.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend import models
from backend.analyzers.topic_modeling import TopicAnalyzer
from backend.schema_registry import registry

# ── CSS (inline, print-friendly) ─────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       font-size: 14px; color: #111827; background: #fff; padding: 32px; }
.cover { text-align: center; padding: 60px 0 48px; border-bottom: 2px solid #e5e7eb; margin-bottom: 40px; }
.cover .logo { display: inline-flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.cover .logo-icon { width: 40px; height: 40px; background: #2563eb; border-radius: 10px;
                    display: flex; align-items: center; justify-content: center; }
.cover .logo-icon svg { width: 24px; height: 24px; color: #fff; stroke: #fff; }
.cover h1 { font-size: 28px; font-weight: 700; color: #111827; margin-bottom: 8px; }
.cover .meta { font-size: 13px; color: #6b7280; }
section { margin-bottom: 40px; }
section h2 { font-size: 17px; font-weight: 600; color: #1d4ed8; margin-bottom: 16px;
             padding-bottom: 8px; border-bottom: 1px solid #dbeafe; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 16px; margin-bottom: 16px; }
.stat-card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px; }
.stat-card .label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; color: #6b7280; }
.stat-card .value { font-size: 26px; font-weight: 700; color: #111827; margin-top: 4px; }
.stat-card .sub { font-size: 12px; color: #9ca3af; margin-top: 2px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px 12px; background: #f3f4f6;
     font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; color: #6b7280;
     border-bottom: 1px solid #e5e7eb; }
td { padding: 9px 12px; border-bottom: 1px solid #f3f4f6; color: #374151; }
tr:last-child td { border-bottom: none; }
.bar-wrap { display: flex; align-items: center; gap: 8px; }
.bar { height: 8px; background: #2563eb; border-radius: 4px; }
.bar-bg { flex: 1; background: #e5e7eb; border-radius: 4px; height: 8px; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; }
.badge-blue   { background: #dbeafe; color: #1d4ed8; }
.badge-green  { background: #d1fae5; color: #065f46; }
.badge-amber  { background: #fef3c7; color: #92400e; }
.badge-gray   { background: #f3f4f6; color: #6b7280; }
.badge-red    { background: #fee2e2; color: #991b1b; }
.chip { display: inline-block; margin: 2px; padding: 3px 10px; border-radius: 9999px;
        font-size: 12px; background: #eff6ff; color: #1d4ed8; }
footer { margin-top: 48px; padding-top: 16px; border-top: 1px solid #e5e7eb;
         font-size: 12px; color: #9ca3af; text-align: center; }
@media print {
  body { padding: 16px; }
  .cover { padding: 40px 0 32px; }
  section { page-break-inside: avoid; }
}
"""

# ── Section builders ──────────────────────────────────────────────────────────

def _section_entity_stats(db: Session) -> str:
    total = db.query(func.count(models.RawEntity.id)).scalar() or 0
    by_status = db.query(models.RawEntity.validation_status, func.count(models.RawEntity.id))\
        .group_by(models.RawEntity.validation_status).all()
    by_enrich = db.query(models.RawEntity.enrichment_status, func.count(models.RawEntity.id))\
        .group_by(models.RawEntity.enrichment_status).all()

    status_map = {r[0]: r[1] for r in by_status}
    enrich_map = {r[0]: r[1] for r in by_enrich}

    valid_pct = round(status_map.get("valid", 0) / total * 100) if total else 0
    enriched = enrich_map.get("completed", 0)
    enrich_pct = round(enriched / total * 100) if total else 0

    cards = [
        ("Total Entities", f"{total:,}", ""),
        ("Valid", f"{status_map.get('valid', 0):,}", f"{valid_pct}% of total"),
        ("Pending", f"{status_map.get('pending', 0):,}", "awaiting validation"),
        ("Enriched", f"{enriched:,}", f"{enrich_pct}% coverage"),
    ]
    cards_html = "".join(f"""
        <div class="stat-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            <div class="sub">{sub}</div>
        </div>""" for label, value, sub in cards)

    rows = "".join(f"""
        <tr><td>{s or "—"}</td>
            <td>{c:,}</td>
            <td><div class="bar-wrap">
                <div class="bar-bg"><div class="bar" style="width:{round(c/total*100) if total else 0}%"></div></div>
                <span>{round(c/total*100) if total else 0}%</span>
            </div></td></tr>""" for s, c in sorted(by_status, key=lambda x: -x[1]))

    return f"""<section>
    <h2>Entity Statistics</h2>
    <div class="grid">{cards_html}</div>
    <table>
        <thead><tr><th>Validation Status</th><th>Count</th><th>Distribution</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
</section>"""


def _section_enrichment_coverage(db: Session) -> str:
    total = db.query(func.count(models.RawEntity.id)).scalar() or 0
    completed = db.query(func.count(models.RawEntity.id))\
        .filter(models.RawEntity.enrichment_status == "completed").scalar() or 0
    avg_cit = db.query(func.avg(models.RawEntity.enrichment_citation_count))\
        .filter(models.RawEntity.enrichment_status == "completed").scalar() or 0
    top = db.query(models.RawEntity.primary_label, models.RawEntity.enrichment_citation_count,
                   models.RawEntity.enrichment_source)\
        .filter(models.RawEntity.enrichment_status == "completed")\
        .order_by(models.RawEntity.enrichment_citation_count.desc()).limit(8).all()

    pct = round(completed / total * 100) if total else 0
    rows = "".join(f"""
        <tr><td>{r[0] or '—'}</td>
            <td>{r[1] or 0:,}</td>
            <td><span class="badge badge-blue">{r[2] or '—'}</span></td></tr>""" for r in top)

    return f"""<section>
    <h2>Enrichment Coverage</h2>
    <div class="grid">
        <div class="stat-card"><div class="label">Coverage</div><div class="value">{pct}%</div><div class="sub">{completed:,} of {total:,} entities</div></div>
        <div class="stat-card"><div class="label">Avg Citations</div><div class="value">{round(avg_cit or 0):,}</div><div class="sub">enriched entities only</div></div>
    </div>
    <table>
        <thead><tr><th>Entity</th><th>Citations</th><th>Source</th></tr></thead>
        <tbody>{rows if rows else '<tr><td colspan="3" style="color:#9ca3af;text-align:center;padding:20px">No enriched entities yet</td></tr>'}</tbody>
    </table>
</section>"""


def _section_top_brands(db: Session) -> str:
    rows_q = db.query(models.RawEntity.secondary_label, func.count(models.RawEntity.id).label("n"))\
        .filter(models.RawEntity.secondary_label.isnot(None))\
        .group_by(models.RawEntity.secondary_label)\
        .order_by(func.count(models.RawEntity.id).desc()).limit(15).all()
    max_n = rows_q[0][1] if rows_q else 1
    rows = "".join(f"""
        <tr><td>{r[0]}</td>
            <td>{r[1]:,}</td>
            <td><div class="bar-wrap">
                <div class="bar-bg"><div class="bar" style="width:{round(r[1]/max_n*100)}%"></div></div>
            </div></td></tr>""" for r in rows_q)

    return f"""<section>
    <h2>Top Brands / Classifications</h2>
    <table>
        <thead><tr><th>Brand</th><th>Entities</th><th>Share</th></tr></thead>
        <tbody>{rows if rows else '<tr><td colspan="3" style="color:#9ca3af;text-align:center;padding:20px">No brand data</td></tr>'}</tbody>
    </table>
</section>"""


def _section_topic_clusters(db: Session) -> str:
    analyzer = TopicAnalyzer()
    try:
        topics = analyzer.top_topics(db, limit=15)
    except Exception:
        topics = []

    if not topics:
        return f"""<section><h2>Topic Clusters</h2>
        <p style="color:#9ca3af;padding:12px 0">No enriched concepts found — run enrichment first.</p>
        </section>"""

    max_c = topics[0]["count"] if topics else 1
    chips = "".join(f'<span class="chip">{t["concept"]} <b>({t["count"]})</b></span>' for t in topics[:20])
    rows = "".join(f"""
        <tr><td>{t["concept"]}</td>
            <td>{t["count"]:,}</td>
            <td><div class="bar-wrap">
                <div class="bar-bg"><div class="bar" style="width:{round(t['count']/max_c*100)}%"></div></div>
            </div></td></tr>""" for t in topics[:10])

    return f"""<section>
    <h2>Topic Clusters</h2>
    <div style="margin-bottom:16px">{chips}</div>
    <table>
        <thead><tr><th>Concept</th><th>Frequency</th><th>Relative weight</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
</section>"""


def _section_harmonization_log(db: Session) -> str:
    logs = db.query(models.HarmonizationLog)\
        .order_by(models.HarmonizationLog.executed_at.desc()).limit(10).all()

    if not logs:
        return f"""<section><h2>Harmonization Log</h2>
        <p style="color:#9ca3af;padding:12px 0">No harmonization steps executed yet.</p></section>"""

    def badge(reverted: bool) -> str:
        return '<span class="badge badge-red">Reverted</span>' if reverted else '<span class="badge badge-green">Applied</span>'

    rows = "".join(f"""
        <tr><td>{l.step_name or l.step_id}</td>
            <td>{l.records_updated:,}</td>
            <td>{badge(l.reverted)}</td>
            <td style="color:#9ca3af;font-size:12px">{l.executed_at.strftime('%Y-%m-%d %H:%M') if l.executed_at else '—'}</td></tr>"""
        for l in logs)

    return f"""<section>
    <h2>Harmonization Log</h2>
    <table>
        <thead><tr><th>Step</th><th>Records Updated</th><th>Status</th><th>Executed</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
</section>"""


# ── Public API ────────────────────────────────────────────────────────────────

SECTION_BUILDERS = {
    "entity_stats": _section_entity_stats,
    "enrichment_coverage": _section_enrichment_coverage,
    "top_brands": _section_top_brands,
    "topic_clusters": _section_topic_clusters,
    "harmonization_log": _section_harmonization_log,
}

SECTION_LABELS = {
    "entity_stats": "Entity Statistics",
    "enrichment_coverage": "Enrichment Coverage",
    "top_brands": "Top Brands / Classifications",
    "topic_clusters": "Topic Clusters",
    "harmonization_log": "Harmonization Log",
}


def build(db: Session, domain_id: str, sections: List[str], title: str | None = None) -> str:
    """Return a complete, self-contained HTML report string."""
    domain_name = domain_id
    try:
        d = registry.get_domain(domain_id)
        domain_name = d.name if d else domain_id
    except Exception:
        pass

    report_title = title or f"UKIP Report — {domain_name}"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    logo_svg = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"/>
    </svg>"""

    cover = f"""<div class="cover">
        <div class="logo">
            <div class="logo-icon">{logo_svg}</div>
            <span style="font-size:20px;font-weight:700;color:#111827">UKIP</span>
        </div>
        <h1>{report_title}</h1>
        <p class="meta">Domain: <b>{domain_name}</b> &nbsp;·&nbsp; Generated: <b>{generated_at}</b></p>
    </div>"""

    body_sections = []
    for sec in sections:
        builder = SECTION_BUILDERS.get(sec)
        if builder:
            try:
                body_sections.append(builder(db))
            except Exception as exc:
                body_sections.append(f'<section><h2>{SECTION_LABELS.get(sec, sec)}</h2>'
                                     f'<p style="color:#ef4444">Error building section: {exc}</p></section>')

    footer = f'<footer>Generated by UKIP &nbsp;·&nbsp; {generated_at}</footer>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{report_title}</title>
  <style>{_CSS}</style>
</head>
<body>
  {cover}
  {"".join(body_sections)}
  {footer}
</body>
</html>"""
