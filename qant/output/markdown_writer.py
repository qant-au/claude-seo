"""Human-readable markdown summary alongside the JSON report."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qant.findings import Finding, Status
from qant.output.json_writer import AuditReport


@dataclass(frozen=True)
class WrittenMdPaths:
    timestamped: Path
    latest: Path


def _render(report: AuditReport) -> str:
    lines: list[str] = []
    lines.append(f"# Audit — {report.host} ({report.environment})")
    lines.append("")
    lines.append(f"- **Brand:** {report.brand}")
    lines.append(f"- **Audited at:** {report.audited_at}")
    lines.append(f"- **Run ID:** {report.audit_run_id}")
    lines.append(f"- **Score:** {report.score.overall} / {report.score.max}")
    lines.append("")
    if report.score.categories:
        lines.append("| Category | Score |")
        lines.append("|---|---|")
        for cat, sc in report.score.categories.items():
            lines.append(f"| {cat} | {sc} |")
        lines.append("")

    expected = [f for f in report.findings if f.status == Status.EXPECTED]
    fails = [f for f in report.findings if f.status == Status.FAIL]
    passes = [f for f in report.findings if f.status == Status.PASS]
    na = [f for f in report.findings if f.status == Status.NOT_APPLICABLE]

    if expected:
        lines.append("## EXPECTED (env-suppressed)")
        lines.append("")
        for f in expected:
            lines.append(f"- ✓ `{f.id}` — {f.title} — _{f.expected_reason or ''}_")
        lines.append("")

    if fails:
        lines.append("## Failures")
        lines.append("")
        for f in fails:
            lines.append(f"### {f.severity.value} `{f.id}` — {f.title}")
            lines.append("")
            lines.append(f"- **URL:** {f.url}")
            lines.append(f"- **Detail:** {f.detail}")
            if f.fix:
                lines.append(f"- **Fix:** {f.fix}")
            lines.append("")

    if passes:
        lines.append(f"## Passing ({len(passes)})")
        lines.append("")
        for f in passes:
            lines.append(f"- ✓ `{f.id}` — {f.title}")
        lines.append("")

    if na:
        lines.append(f"## Not applicable ({len(na)})")
        lines.append("")
        for f in na:
            lines.append(f"- `{f.id}` — {f.title}")
        lines.append("")

    return "\n".join(lines) + "\n"


def write_markdown(report: AuditReport, brand_dir: Path) -> WrittenMdPaths:
    out_dir = Path(brand_dir) / "audit" / report.environment
    out_dir.mkdir(parents=True, exist_ok=True)

    parts = report.audit_run_id.rsplit("-", 2)
    ts = parts[-2] + "-" + parts[-1]
    timestamped = out_dir / f"{ts}.md"
    latest = out_dir / "latest.md"

    text = _render(report)
    timestamped.write_text(text)
    latest.write_text(text)

    return WrittenMdPaths(timestamped=timestamped, latest=latest)
