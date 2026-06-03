"""Tests for qant.suppress."""
from qant.config import BrandSeoConfig, CanonicalMap, ExpectedEntry, HostMap
from qant.findings import Finding, Severity, Status
from qant.suppress import apply_suppression


def _cfg(expected_staging=None, expected_prod=None) -> BrandSeoConfig:
    return BrandSeoConfig(
        brand="x",
        display_name="X",
        canonical=CanonicalMap(marketing="https://x.com"),
        hosts={"marketing": HostMap(staging="x-stg.test", production="x.com")},
        expected={
            "staging": expected_staging or [],
            "production": expected_prod or [],
        },
    )


def _f(id_, status=Status.FAIL) -> Finding:
    return Finding(
        id=id_, category="indexability", severity=Severity.P1,
        status=status, url="https://x.com/", title="t", detail="d",
    )


def test_matching_id_flips_fail_to_expected():
    cfg = _cfg(expected_staging=[
        ExpectedEntry(id="indexability.allows-indexing", reason="staging suppressed"),
    ])
    findings = [_f("indexability.allows-indexing")]
    result = apply_suppression(findings, cfg, env="staging")
    assert len(result) == 1
    assert result[0].status == Status.EXPECTED
    assert result[0].expected_reason == "staging suppressed"


def test_non_matching_id_unchanged():
    cfg = _cfg(expected_staging=[
        ExpectedEntry(id="indexability.allows-indexing", reason="ok"),
    ])
    findings = [_f("schema.missing-organization")]
    result = apply_suppression(findings, cfg, env="staging")
    assert result[0].status == Status.FAIL
    assert result[0].expected_reason is None


def test_wrong_env_does_not_suppress():
    cfg = _cfg(expected_prod=[
        ExpectedEntry(id="indexability.allows-indexing", reason="prod ok"),
    ])
    findings = [_f("indexability.allows-indexing")]
    result = apply_suppression(findings, cfg, env="staging")
    assert result[0].status == Status.FAIL


def test_pass_finding_not_flipped_even_if_in_expected_list():
    # EXPECTED is only meaningful for FAILs that would otherwise show. A passing
    # check shouldn't be flagged as EXPECTED.
    cfg = _cfg(expected_staging=[
        ExpectedEntry(id="indexability.allows-indexing", reason="ok"),
    ])
    findings = [_f("indexability.allows-indexing", status=Status.PASS)]
    result = apply_suppression(findings, cfg, env="staging")
    assert result[0].status == Status.PASS


def test_alias_resolution_applies():
    from qant.registry import ALIASES
    ALIASES["old.id"] = "indexability.allows-indexing"
    try:
        cfg = _cfg(expected_staging=[
            ExpectedEntry(id="old.id", reason="alias works"),
        ])
        findings = [_f("indexability.allows-indexing")]
        result = apply_suppression(findings, cfg, env="staging")
        assert result[0].status == Status.EXPECTED
        assert result[0].expected_reason == "alias works"
    finally:
        ALIASES.pop("old.id", None)
