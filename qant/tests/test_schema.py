"""Tests for qant.checks.schema."""
from unittest.mock import patch

from qant.checks import schema
from qant.fetcher import FetchResult
from qant.findings import Status


def _page(html: str) -> FetchResult:
    return FetchResult(
        url="https://x.test/", final_url="https://x.test/",
        status=200, headers={"content-type": "text/html"},
        html=html, redirect_chain=(),
    )


ORG_BLOCK = """<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"X","url":"https://x.test"}
</script>"""

WEBSITE_BLOCK = """<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebSite","name":"X","url":"https://x.test"}
</script>"""


@patch("qant.checks.schema.fetch")
def test_passes_when_organization_present(mock_fetch):
    mock_fetch.return_value = _page(f"<html><head>{ORG_BLOCK}</head></html>")
    findings = schema.check("https://x.test/")
    by_id = {f.id: f for f in findings}
    assert by_id["schema.missing-organization"].status == Status.PASS


@patch("qant.checks.schema.fetch")
def test_fails_when_organization_missing(mock_fetch):
    mock_fetch.return_value = _page("<html><head></head></html>")
    findings = schema.check("https://x.test/")
    by_id = {f.id: f for f in findings}
    assert by_id["schema.missing-organization"].status == Status.FAIL


@patch("qant.checks.schema.fetch")
def test_passes_when_website_present(mock_fetch):
    mock_fetch.return_value = _page(f"<html><head>{WEBSITE_BLOCK}</head></html>")
    findings = schema.check("https://x.test/")
    by_id = {f.id: f for f in findings}
    assert by_id["schema.missing-website"].status == Status.PASS


@patch("qant.checks.schema.fetch")
def test_fails_when_invalid_json(mock_fetch):
    bad = '<script type="application/ld+json">{ this is not json }</script>'
    mock_fetch.return_value = _page(f"<html><head>{bad}</head></html>")
    findings = schema.check("https://x.test/")
    by_id = {f.id: f for f in findings}
    assert by_id["schema.invalid-jsonld-syntax"].status == Status.FAIL


@patch("qant.checks.schema.fetch")
def test_passes_invalid_json_when_all_blocks_parse(mock_fetch):
    mock_fetch.return_value = _page(f"<html><head>{ORG_BLOCK}{WEBSITE_BLOCK}</head></html>")
    findings = schema.check("https://x.test/")
    by_id = {f.id: f for f in findings}
    assert by_id["schema.invalid-jsonld-syntax"].status == Status.PASS


@patch("qant.checks.schema.fetch")
def test_handles_graph_wrapped_jsonld(mock_fetch):
    graph = """<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
  {"@type":"Organization","name":"X","url":"https://x.test"},
  {"@type":"WebSite","name":"X","url":"https://x.test"}
]}
</script>"""
    mock_fetch.return_value = _page(f"<html><head>{graph}</head></html>")
    findings = schema.check("https://x.test/")
    by_id = {f.id: f for f in findings}
    assert by_id["schema.missing-organization"].status == Status.PASS
    assert by_id["schema.missing-website"].status == Status.PASS
