"""Tests for qant.checks.indexability."""
from unittest.mock import patch

from qant.checks import indexability
from qant.fetcher import FetchResult
from qant.findings import Status


def _fetched(url: str, html: str = "<html><head></head></html>", headers: dict | None = None) -> FetchResult:
    return FetchResult(
        url=url, final_url=url, status=200,
        headers=headers or {"content-type": "text/html"},
        html=html, redirect_chain=(),
    )


def _robots(allow: str = "*", path_disallow: str = "", sitemap: str | None = None) -> FetchResult:
    body = f"User-agent: {allow}\n"
    if path_disallow:
        body += f"Disallow: {path_disallow}\n"
    else:
        body += "Allow: /\n"
    if sitemap:
        body += f"Sitemap: {sitemap}\n"
    return FetchResult(
        url="x", final_url="x", status=200,
        headers={"content-type": "text/plain"},
        html=body, redirect_chain=(),
    )


@patch("qant.checks.indexability.fetch")
def test_flags_allows_indexing_when_robots_allows_and_no_xrobots(mock_fetch):
    mock_fetch.side_effect = [
        _fetched("https://x.test/"),  # main page
        _robots(),                    # /robots.txt
    ]
    findings = indexability.check("https://x.test/", host="x.test")
    ids = [f.id for f in findings if f.status == Status.FAIL]
    assert "indexability.allows-indexing" in ids


@patch("qant.checks.indexability.fetch")
def test_passes_allows_indexing_when_xrobots_noindex_present(mock_fetch):
    mock_fetch.side_effect = [
        _fetched("https://x.test/", headers={
            "content-type": "text/html",
            "X-Robots-Tag": "noindex, nofollow",
        }),
        _robots(),
    ]
    findings = indexability.check("https://x.test/", host="x.test")
    by_id = {f.id: f for f in findings}
    assert by_id["indexability.allows-indexing"].status == Status.PASS


@patch("qant.checks.indexability.fetch")
def test_passes_allows_indexing_when_robots_disallows_root(mock_fetch):
    mock_fetch.side_effect = [
        _fetched("https://x.test/"),
        _robots(path_disallow="/"),
    ]
    findings = indexability.check("https://x.test/", host="x.test")
    by_id = {f.id: f for f in findings}
    assert by_id["indexability.allows-indexing"].status == Status.PASS


@patch("qant.checks.indexability.fetch")
def test_flags_missing_robots_when_404(mock_fetch):
    mock_fetch.side_effect = [
        _fetched("https://x.test/"),
        FetchResult(url="x", final_url="x", status=404, headers={}, html="", redirect_chain=()),
    ]
    findings = indexability.check("https://x.test/", host="x.test")
    ids = [f.id for f in findings if f.status == Status.FAIL]
    assert "indexability.robots-txt-missing" in ids


@patch("qant.checks.indexability.fetch")
def test_flags_sitemap_not_referenced(mock_fetch):
    mock_fetch.side_effect = [
        _fetched("https://x.test/"),
        _robots(),  # no Sitemap: line
    ]
    findings = indexability.check("https://x.test/", host="x.test")
    by_id = {f.id: f for f in findings}
    assert by_id["indexability.sitemap-not-referenced-in-robots"].status == Status.FAIL


@patch("qant.checks.indexability.fetch")
def test_passes_sitemap_when_referenced(mock_fetch):
    mock_fetch.side_effect = [
        _fetched("https://x.test/"),
        _robots(sitemap="https://x.test/sitemap.xml"),
    ]
    findings = indexability.check("https://x.test/", host="x.test")
    by_id = {f.id: f for f in findings}
    assert by_id["indexability.sitemap-not-referenced-in-robots"].status == Status.PASS
