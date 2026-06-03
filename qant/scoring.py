"""Score findings by category and overall.

v1 model: each category scored as percent passing of applicable findings.
Overall = equally-weighted mean across present categories.
EXPECTED counts as PASS for scoring purposes (it's an intentional override).
NOT_APPLICABLE is excluded from the category total.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from qant.findings import Finding, Status


@dataclass
class Score:
    overall: int
    max: int = 100
    categories: dict[str, int] = field(default_factory=dict)


_APPLICABLE = {Status.PASS, Status.FAIL, Status.EXPECTED}
_PASSING = {Status.PASS, Status.EXPECTED}


def score(findings: list[Finding]) -> Score:
    if not findings:
        return Score(overall=100, max=100, categories={})

    per_cat_passing: dict[str, int] = defaultdict(int)
    per_cat_applicable: dict[str, int] = defaultdict(int)

    for f in findings:
        if f.status not in _APPLICABLE:
            continue
        per_cat_applicable[f.category] += 1
        if f.status in _PASSING:
            per_cat_passing[f.category] += 1

    categories: dict[str, int] = {}
    for cat, applicable in per_cat_applicable.items():
        if applicable == 0:
            continue
        categories[cat] = round(per_cat_passing[cat] * 100 / applicable)

    if not categories:
        return Score(overall=100, max=100, categories={})

    overall = round(sum(categories.values()) / len(categories))
    return Score(overall=overall, max=100, categories=categories)
