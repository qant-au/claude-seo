"""Tests for qant.scoring."""
from qant.findings import Finding, Severity, Status
from qant.scoring import score


def _f(id_, category, status):
    return Finding(
        id=id_, category=category, severity=Severity.P2,
        status=status, url="https://x.com/", title="t", detail="d",
    )


def test_empty_findings_yields_perfect_score():
    s = score([])
    assert s.overall == 100
    assert s.max == 100
    assert s.categories == {}


def test_all_pass_yields_100():
    findings = [
        _f("a.x", "indexability", Status.PASS),
        _f("b.y", "schema", Status.PASS),
    ]
    s = score(findings)
    assert s.overall == 100
    assert s.categories["indexability"] == 100
    assert s.categories["schema"] == 100


def test_one_fail_in_one_category_lowers_only_that_category():
    findings = [
        _f("a.x", "indexability", Status.PASS),
        _f("a.y", "indexability", Status.FAIL),
        _f("b.z", "schema", Status.PASS),
    ]
    s = score(findings)
    assert s.categories["indexability"] == 50
    assert s.categories["schema"] == 100
    # Overall is the equally-weighted mean across present categories.
    assert s.overall == 75


def test_expected_counts_as_pass_for_score():
    findings = [
        _f("a.x", "indexability", Status.EXPECTED),
        _f("a.y", "indexability", Status.PASS),
    ]
    s = score(findings)
    assert s.categories["indexability"] == 100


def test_not_applicable_excluded_from_category_total():
    findings = [
        _f("a.x", "indexability", Status.NOT_APPLICABLE),
        _f("a.y", "indexability", Status.FAIL),
    ]
    s = score(findings)
    # Only one applicable finding, which failed → 0
    assert s.categories["indexability"] == 0


def test_category_with_only_not_applicable_omitted():
    findings = [
        _f("a.x", "indexability", Status.NOT_APPLICABLE),
        _f("b.y", "schema", Status.PASS),
    ]
    s = score(findings)
    assert "indexability" not in s.categories
    assert s.categories["schema"] == 100
    assert s.overall == 100
