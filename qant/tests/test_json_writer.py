"""Tests for qant.output.json_writer."""
import json
from pathlib import Path

from qant.findings import Finding, Severity, Status
from qant.output.json_writer import AuditReport, write_json
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
                url="https://rbc-stg.qant.co/", title="t", detail="d",
            ),
        ],
    )


def test_writes_timestamped_and_latest(tmp_path: Path):
    report = _report()
    paths = write_json(report, tmp_path)

    assert paths.timestamped.exists()
    assert paths.latest.exists()
    assert paths.timestamped.name == "20260603-114200.json"
    assert paths.timestamped.parent.name == "staging"
    assert paths.latest.name == "latest.json"


def test_json_shape_matches_schema(tmp_path: Path):
    paths = write_json(_report(), tmp_path)
    data = json.loads(paths.latest.read_text())

    assert data["schema_version"] == "1.0"
    assert data["brand"] == "rbc"
    assert data["host"] == "rbc-stg.qant.co"
    assert data["environment"] == "staging"
    assert data["audited_at"] == "2026-06-03T11:42:00Z"
    assert data["audit_run_id"] == "rbc-stg-20260603-114200"
    assert data["score"]["overall"] == 82
    assert data["score"]["max"] == 100
    assert data["score"]["categories"]["schema"] == 60
    assert len(data["findings"]) == 1
    assert data["findings"][0]["id"] == "schema.missing-organization"
    assert data["findings"][0]["severity"] == "P2"
    assert data["findings"][0]["status"] == "FAIL"


def test_round_trip_equality(tmp_path: Path):
    paths = write_json(_report(), tmp_path)
    a = json.loads(paths.timestamped.read_text())
    b = json.loads(paths.latest.read_text())
    assert a == b


def test_idempotent_overwrites_latest(tmp_path: Path):
    write_json(_report(), tmp_path)
    paths = write_json(_report(), tmp_path)
    assert paths.latest.exists()
    # Two distinct timestamped files now exist.
    timestamped_files = list((tmp_path / "audit" / "staging").glob("*.json"))
    timestamped_only = [p for p in timestamped_files if p.name != "latest.json"]
    assert len(timestamped_only) == 1  # same audit_run_id → same filename → overwrite
