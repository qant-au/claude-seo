"""CLI entry point: orchestrates the brand-audit pipeline.

Usage:
    python -m qant.run_brand_audit --config .brand-seo.yml --env staging
    python -m qant.run_brand_audit --config .brand-seo.yml --env production
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from qant.checks import indexability, redirects, schema
from qant.config import BrandSeoConfig, load_config
from qant.fetcher import fetch_cache_clear
from qant.findings import Finding
from qant.output.json_writer import AuditReport, WrittenPaths, write_json
from qant.output.markdown_writer import WrittenMdPaths, write_markdown
from qant.scoring import score
from qant.suppress import apply_suppression


@dataclass(frozen=True)
class RunResult:
    json_paths: WrittenPaths
    md_paths: WrittenMdPaths
    report: AuditReport


def _build_run_id(brand: str, env: str, when: datetime) -> str:
    env_short = "stg" if env == "staging" else "prd"
    stamp = when.strftime("%Y%m%d-%H%M%S")
    return f"{brand}-{env_short}-{stamp}"


def _select_host(config: BrandSeoConfig, env: str) -> str:
    hostmap = config.hosts["marketing"]
    host = getattr(hostmap, env, None)
    if not host:
        raise SystemExit(f"No host configured for env={env} in hosts.marketing")
    return host


def _is_in_scope(url: str, out_of_scope: list[str]) -> bool:
    netloc = urlparse(url).netloc
    return netloc not in out_of_scope


def run(config_path: Path, env: str, brand_dir: Path) -> RunResult:
    fetch_cache_clear()
    config = load_config(config_path)
    host = _select_host(config, env)
    page_url = f"https://{host}/"

    findings: list[Finding] = []

    # ----- indexability -----
    if _is_in_scope(page_url, config.out_of_scope):
        findings.extend(indexability.check(page_url, host=host))

    # ----- redirects -----
    in_scope_redirects = [
        r for r in config.redirects if _is_in_scope(r.from_, config.out_of_scope)
    ]
    if in_scope_redirects:
        findings.extend(redirects.check(in_scope_redirects))

    # ----- schema -----
    if _is_in_scope(page_url, config.out_of_scope):
        findings.extend(schema.check(page_url))

    # ----- suppress, score, write -----
    findings = apply_suppression(findings, config, env=env)
    sc = score(findings)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    report = AuditReport(
        brand=config.brand,
        host=host,
        environment=env,
        audited_at=now.isoformat().replace("+00:00", "Z"),
        audit_run_id=_build_run_id(config.brand, env, now),
        score=sc,
        findings=findings,
    )

    json_paths = write_json(report, brand_dir)
    md_paths = write_markdown(report, brand_dir)
    return RunResult(json_paths=json_paths, md_paths=md_paths, report=report)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="QANT brand SEO audit")
    p.add_argument("--config", required=True, type=Path, help="Path to .brand-seo.yml")
    p.add_argument("--env", required=True, choices=("staging", "production"))
    p.add_argument(
        "--brand-dir", type=Path, default=Path.cwd(),
        help="Brand repo root (audit/ output goes here). Defaults to cwd.",
    )
    args = p.parse_args(argv)

    result = run(args.config, args.env, args.brand_dir)
    print(f"Audit complete: {result.json_paths.latest}")
    print(f"Score: {result.report.score.overall}/{result.report.score.max}")
    print(f"Findings: {len(result.report.findings)}")
    # Exit non-zero if any FAIL remains after suppression — useful for CI later.
    has_failures = any(f.status.value == "FAIL" for f in result.report.findings)
    return 1 if has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
