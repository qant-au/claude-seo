"""Apply env-aware suppression: matching FAIL findings become EXPECTED."""
from __future__ import annotations

from dataclasses import replace

from qant.config import BrandSeoConfig
from qant.findings import Finding, Status
from qant.registry import resolve


def apply_suppression(
    findings: list[Finding],
    config: BrandSeoConfig,
    env: str,
) -> list[Finding]:
    """Return a new list with matching FAILs flipped to EXPECTED.

    A finding matches if its (alias-resolved) ID equals an expected entry's
    (alias-resolved) ID for the given env. Non-FAIL statuses are never altered.
    """
    expected_entries = config.expected.get(env, [])
    # Build the resolved-ID → reason map once.
    expected_map = {resolve(e.id): e.reason for e in expected_entries}

    out: list[Finding] = []
    for f in findings:
        if f.status != Status.FAIL:
            out.append(f)
            continue
        reason = expected_map.get(resolve(f.id))
        if reason is None:
            out.append(f)
            continue
        out.append(replace(f, status=Status.EXPECTED, expected_reason=reason))
    return out
