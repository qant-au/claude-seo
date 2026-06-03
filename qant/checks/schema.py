"""JSON-LD presence and shape checks."""
from __future__ import annotations

import json

from bs4 import BeautifulSoup

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


def _extract_types(blocks: list[dict | list]) -> set[str]:
    types: set[str] = set()
    for block in blocks:
        items = block if isinstance(block, list) else [block]
        for item in items:
            if not isinstance(item, dict):
                continue
            if "@graph" in item and isinstance(item["@graph"], list):
                for g in item["@graph"]:
                    if isinstance(g, dict):
                        t = g.get("@type")
                        if isinstance(t, str):
                            types.add(t)
                        elif isinstance(t, list):
                            types.update(x for x in t if isinstance(x, str))
            t = item.get("@type")
            if isinstance(t, str):
                types.add(t)
            elif isinstance(t, list):
                types.update(x for x in t if isinstance(x, str))
    return types


def check(page_url: str) -> list[Finding]:
    page = fetch(page_url)
    soup = BeautifulSoup(page.html, "html.parser")
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

    parsed: list[dict | list] = []
    parse_errors: list[str] = []
    for s in scripts:
        raw = (s.string or s.get_text() or "").strip()
        if not raw:
            continue
        try:
            parsed.append(json.loads(raw))
        except json.JSONDecodeError as e:
            parse_errors.append(f"{type(e).__name__}: {e}")

    types = _extract_types(parsed)

    return [
        _make(
            "schema.invalid-jsonld-syntax",
            Status.FAIL if parse_errors else Status.PASS,
            page_url,
            "; ".join(parse_errors) if parse_errors else "All JSON-LD blocks parsed.",
            evidence={"errors": parse_errors} if parse_errors else {},
        ),
        _make(
            "schema.missing-organization",
            Status.PASS if "Organization" in types else Status.FAIL,
            page_url,
            f"Organization JSON-LD: {'present' if 'Organization' in types else 'absent'}.",
            evidence={"types_found": sorted(types)},
        ),
        _make(
            "schema.missing-website",
            Status.PASS if "WebSite" in types else Status.FAIL,
            page_url,
            f"WebSite JSON-LD: {'present' if 'WebSite' in types else 'absent'}.",
            evidence={"types_found": sorted(types)},
        ),
    ]
