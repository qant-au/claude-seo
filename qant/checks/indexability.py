"""Indexability check: robots.txt, X-Robots-Tag, sitemap reference."""
from __future__ import annotations

from qant.fetcher import fetch
from qant.findings import Finding, Severity, Status
from qant.registry import get


def _make(id_: str, status: Status, url: str, detail: str, evidence: dict | None = None) -> Finding:
    d = get(id_)
    return Finding(
        id=id_, category=d.category, severity=Severity(d.default_severity),
        status=status, url=url, title=d.title, detail=detail,
        evidence=evidence or {},
    )


def _xrobots_blocks_indexing(headers: dict[str, str]) -> bool:
    for k, v in headers.items():
        if k.lower() == "x-robots-tag":
            return "noindex" in v.lower()
    return False


def _robots_disallows_root(robots_body: str) -> bool:
    in_star = False
    for raw in robots_body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("user-agent:"):
            ua = line.split(":", 1)[1].strip()
            in_star = ua == "*"
            continue
        if in_star and line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path == "/":
                return True
    return False


def _robots_sitemap_line(robots_body: str) -> str | None:
    for raw in robots_body.splitlines():
        line = raw.strip()
        if line.lower().startswith("sitemap:"):
            return line.split(":", 1)[1].strip()
    return None


def check(page_url: str, *, host: str) -> list[Finding]:
    """Run indexability checks against the given page URL."""
    findings: list[Finding] = []
    page = fetch(page_url)
    robots_url = f"https://{host}/robots.txt"
    robots = fetch(robots_url)

    # 1. allows-indexing (P1)
    blocks_via_header = _xrobots_blocks_indexing(page.headers)
    blocks_via_robots = robots.status == 200 and _robots_disallows_root(robots.html)
    allows = not (blocks_via_header or blocks_via_robots)
    findings.append(_make(
        "indexability.allows-indexing",
        Status.FAIL if allows else Status.PASS,
        page_url,
        f"X-Robots-Tag noindex: {'yes' if blocks_via_header else 'no'}; "
        f"robots.txt disallows /: {'yes' if blocks_via_robots else 'no'}.",
        evidence={
            "x_robots_tag": page.headers.get("X-Robots-Tag") or page.headers.get("x-robots-tag"),
            "robots_status": robots.status,
        },
    ))

    # 2. no-x-robots-tag-noindex (P2)
    findings.append(_make(
        "indexability.no-x-robots-tag-noindex",
        Status.PASS if blocks_via_header else Status.FAIL,
        page_url,
        "X-Robots-Tag: noindex header present." if blocks_via_header
        else "No X-Robots-Tag: noindex header on response.",
    ))

    # 3. robots-txt-missing (P2)
    findings.append(_make(
        "indexability.robots-txt-missing",
        Status.PASS if robots.status == 200 else Status.FAIL,
        robots_url,
        f"GET /robots.txt returned {robots.status}.",
    ))

    # 4. sitemap-not-referenced-in-robots (P3)
    if robots.status == 200:
        sitemap_line = _robots_sitemap_line(robots.html)
        findings.append(_make(
            "indexability.sitemap-not-referenced-in-robots",
            Status.PASS if sitemap_line else Status.FAIL,
            robots_url,
            f"Sitemap: line present → {sitemap_line}" if sitemap_line
            else "robots.txt does not contain a Sitemap: directive.",
        ))
    else:
        findings.append(_make(
            "indexability.sitemap-not-referenced-in-robots",
            Status.NOT_APPLICABLE,
            robots_url,
            "robots.txt missing — cannot evaluate Sitemap: directive.",
        ))

    return findings
