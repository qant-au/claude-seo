"""Canonical JSON writer for the brand-audit report.

Writes <brand>/audit/<env>/<timestamp>.json and <brand>/audit/<env>/latest.json.
The `latest.json` file is committed (small, diff-friendly); the timestamped
files are gitignored (large, ephemeral).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from qant.findings import Finding
from qant.scoring import Score


SCHEMA_VERSION = "1.0"


@dataclass
class AuditReport:
    brand: str
    host: str
    environment: str
    audited_at: str       # ISO 8601 UTC
    audit_run_id: str
    score: Score
    findings: list[Finding] = field(default_factory=list)


@dataclass(frozen=True)
class WrittenPaths:
    timestamped: Path
    latest: Path


def _to_dict(report: AuditReport) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "brand": report.brand,
        "host": report.host,
        "environment": report.environment,
        "audited_at": report.audited_at,
        "audit_run_id": report.audit_run_id,
        "score": {
            "overall": report.score.overall,
            "max": report.score.max,
            "categories": dict(report.score.categories),
        },
        "findings": [f.to_dict() for f in report.findings],
    }


def write_json(report: AuditReport, brand_dir: Path) -> WrittenPaths:
    """Write the JSON report. Returns paths written."""
    out_dir = Path(brand_dir) / "audit" / report.environment
    out_dir.mkdir(parents=True, exist_ok=True)

    # audit_run_id is shaped like "rbc-stg-20260603-114200"; pull the timestamp suffix.
    ts = report.audit_run_id.rsplit("-", 2)[-2] + "-" + report.audit_run_id.rsplit("-", 2)[-1]
    timestamped = out_dir / f"{ts}.json"
    latest = out_dir / "latest.json"

    payload = _to_dict(report)
    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    timestamped.write_text(text)
    latest.write_text(text)

    return WrittenPaths(timestamped=timestamped, latest=latest)
