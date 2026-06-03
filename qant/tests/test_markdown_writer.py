"""Tests for qant.output.markdown_writer."""
from pathlib import Path

from qant.findings import Finding, Severity, Status
from qant.output.json_writer import AuditReport
from qant.output.markdown_writer import write_markdown
from qant.scoring import Score


def _report() -> AuditReport:
    return AuditReport(
        brand="rbc",
        host="rbc-stg.qant.co",
        environment="staging",
        audited_at="2026-06-03T11:42:00Z",
        audit_run_id="rbc-stg-20260603-114200",
        score=Score(overall=82, categories={"schema": 60, "indexability": 100}),
        findings=[
            Finding(
                id="schema.missing-organization", category="schema",
                severity=Severity.P2, status=Status.FAIL,
                url="https://rbc-stg.qant.co/",
                title="Missing Organization JSON-LD",
                detail="No Organization block found.",
                fix="Add <Organization /> to layout.tsx",
            ),
            Finding(
                id="indexability.allows-indexing", category="indexability",
                severity=Severity.P1, status=Status.EXPECTED,
                url="https://rbc-stg.qant.co/",
                title="Site allows indexing",
                detail="robots.txt allows /.",
                expected_reason="staging suppressed via edge header",
            ),
        ],
    )


def test_writes_files_alongside_json(tmp_path: Path):
    paths = write_markdown(_report(), tmp_path)
    assert paths.timestamped.exists()
    assert paths.latest.exists()
    assert paths.timestamped.name == "20260603-114200.md"
    assert paths.latest.name == "latest.md"


def test_markdown_contains_header_and_score(tmp_path: Path):
    paths = write_markdown(_report(), tmp_path)
    text = paths.latest.read_text()
    assert "rbc-stg.qant.co" in text
    assert "staging" in text
    assert "82" in text


def test_markdown_groups_expected_separately(tmp_path: Path):
    paths = write_markdown(_report(), tmp_path)
    text = paths.latest.read_text()
    # EXPECTED section appears before the FAIL section.
    expected_idx = text.find("EXPECTED")
    fail_idx = text.find("schema.missing-organization")
    assert expected_idx != -1
    assert fail_idx != -1
    assert expected_idx < fail_idx


def test_markdown_shows_fix_hint_when_present(tmp_path: Path):
    paths = write_markdown(_report(), tmp_path)
    text = paths.latest.read_text()
    assert "Add <Organization />" in text
