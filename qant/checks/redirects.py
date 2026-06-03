"""Verify configured redirect graph: each entry must 301 from→to."""
from __future__ import annotations

import sys
import os

from urllib.parse import urlparse

from qant.config import RedirectEntry
from qant.fetcher import fetch
from qant.findings import Finding, Severity, Status
from qant.registry import get

# Import URLSafetyError for DNS/safety failures so we emit a FAIL finding
# rather than crashing when a redirect source has no A record.
_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
try:
    from url_safety import URLSafetyError  # type: ignore
except ImportError:
    URLSafetyError = Exception  # type: ignore[misc,assignment]


def _classify(entry: RedirectEntry) -> str:
    """Pick the finding ID based on the shape of the redirect."""
    from_p = urlparse(entry.from_)
    to_p = urlparse(entry.to)

    # Same host, path differs → legacy-path
    if from_p.netloc == to_p.netloc and from_p.path != to_p.path:
        return "redirects.legacy-path-redirect-broken"

    # Subdomain of the target's apex → subdomain
    if from_p.netloc.endswith("." + to_p.netloc.lstrip("www.")):
        return "redirects.subdomain-redirect-broken"
    if from_p.netloc != to_p.netloc and len(from_p.netloc.split(".")) > len(to_p.netloc.split(".")):
        return "redirects.subdomain-redirect-broken"

    # Different apex domains → brand-protection
    return "redirects.brand-protection-redirect-broken"


def _normalize(url: str) -> str:
    # Treat https://x and https://x/ as equal for comparison.
    p = urlparse(url)
    path = p.path or "/"
    return f"{p.scheme}://{p.netloc}{path}"


def _make(id_: str, status: Status, url: str, detail: str, evidence: dict | None = None) -> Finding:
    d = get(id_)
    return Finding(
        id=id_, category=d.category, severity=Severity(d.default_severity),
        status=status, url=url, title=d.title, detail=detail,
        evidence=evidence or {},
    )


def check(entries: list[RedirectEntry]) -> list[Finding]:
    findings: list[Finding] = []
    for entry in entries:
        id_ = _classify(entry)
        try:
            result = fetch(entry.from_)
        except URLSafetyError as exc:
            findings.append(_make(
                id_, Status.FAIL, entry.from_,
                f"{entry.from_} is unreachable (DNS/safety error): {exc}",
                evidence={"error": str(exc)},
            ))
            continue
        expected_to = _normalize(entry.to)
        actual_to = _normalize(result.final_url)

        if not result.redirect_chain:
            findings.append(_make(
                id_, Status.FAIL, entry.from_,
                f"{entry.from_} did not redirect (status {result.status}).",
                evidence={"final_url": result.final_url, "expected_to": entry.to},
            ))
            continue

        last_step = result.redirect_chain[-1]
        if last_step.status != entry.code:
            findings.append(_make(
                id_, Status.FAIL, entry.from_,
                f"Expected {entry.code}, got {last_step.status}.",
                evidence={"chain": [(s.from_url, s.to_url, s.status) for s in result.redirect_chain]},
            ))
            continue

        if actual_to != expected_to:
            findings.append(_make(
                id_, Status.FAIL, entry.from_,
                f"Redirected to {result.final_url}, expected {entry.to}.",
                evidence={"final_url": result.final_url, "expected_to": entry.to},
            ))
            continue

        findings.append(_make(
            id_, Status.PASS, entry.from_,
            f"{entry.from_} -> {entry.to} ({entry.code}) OK",
        ))
    return findings
