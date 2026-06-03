"""Tests for qant.findings."""
import pytest

from qant.findings import Finding, Severity, Status


def test_finding_serialises_with_enum_values_as_strings():
    f = Finding(
        id="indexability.allows-indexing",
        category="indexability",
        severity=Severity.P1,
        status=Status.FAIL,
        url="https://example.com/",
        title="Site allows indexing",
        detail="robots.txt allows /.",
    )
    d = f.to_dict()
    assert d["severity"] == "P1"
    assert d["status"] == "FAIL"
    assert d["id"] == "indexability.allows-indexing"


def test_finding_omits_none_optional_fields():
    f = Finding(
        id="schema.missing-organization",
        category="schema",
        severity=Severity.P2,
        status=Status.FAIL,
        url="https://example.com/",
        title="t",
        detail="d",
    )
    d = f.to_dict()
    assert "fix" not in d
    assert "expected_reason" not in d


def test_finding_includes_evidence_and_fix_when_set():
    f = Finding(
        id="schema.missing-organization",
        category="schema",
        severity=Severity.P2,
        status=Status.FAIL,
        url="https://example.com/",
        title="t",
        detail="d",
        fix="Add <Organization /> to layout.tsx",
        evidence={"html_snippet": "<head>...</head>"},
    )
    d = f.to_dict()
    assert d["fix"] == "Add <Organization /> to layout.tsx"
    assert d["evidence"] == {"html_snippet": "<head>...</head>"}


def test_finding_includes_expected_reason_for_expected_status():
    f = Finding(
        id="indexability.allows-indexing",
        category="indexability",
        severity=Severity.P1,
        status=Status.EXPECTED,
        url="https://example.com/",
        title="t",
        detail="d",
        expected_reason="staging suppressed via edge header",
    )
    d = f.to_dict()
    assert d["status"] == "EXPECTED"
    assert d["expected_reason"] == "staging suppressed via edge header"


def test_severity_values():
    assert Severity.P1.value == "P1"
    assert Severity.P2.value == "P2"
    assert Severity.P3.value == "P3"
    assert Severity.INFO.value == "INFO"


def test_status_values():
    assert Status.PASS.value == "PASS"
    assert Status.FAIL.value == "FAIL"
    assert Status.EXPECTED.value == "EXPECTED"
    assert Status.NOT_APPLICABLE.value == "NOT_APPLICABLE"
