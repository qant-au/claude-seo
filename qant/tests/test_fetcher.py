"""Tests for qant.fetcher.

Uses unittest.mock.patch on _fetch_uncached because url_safety.safe_requests_get
calls validate_url_strict (real DNS) before responses' HTTPAdapter patch fires.
Mocking _fetch_uncached covers the full cache + return-shape contract.
"""
from unittest.mock import patch

from qant.fetcher import FetchResult, RedirectStep, fetch, fetch_cache_clear


def setup_function(_):
    fetch_cache_clear()


def test_fetch_returns_status_headers_html():
    with patch("qant.fetcher._fetch_uncached") as m:
        m.return_value = FetchResult(
            url="https://example.com/",
            final_url="https://example.com/",
            status=200,
            headers={"content-type": "text/html; charset=utf-8"},
            html="<html><head><title>x</title></head><body>hi</body></html>",
            redirect_chain=(),
        )
        r = fetch("https://example.com/")
        assert isinstance(r, FetchResult)
        assert r.status == 200
        assert "<title>x</title>" in r.html
        assert r.headers["content-type"] == "text/html; charset=utf-8"
        assert r.final_url == "https://example.com/"
        assert r.redirect_chain == ()


def test_fetch_captures_redirect_chain():
    with patch("qant.fetcher._fetch_uncached") as m:
        m.return_value = FetchResult(
            url="https://example.com",
            final_url="https://example.com.au/",
            status=200,
            headers={"content-type": "text/html"},
            html="<html></html>",
            redirect_chain=(
                RedirectStep(
                    from_url="https://example.com/",
                    to_url="https://example.com.au/",
                    status=301,
                ),
            ),
        )
        r = fetch("https://example.com")
        assert r.status == 200
        assert r.final_url == "https://example.com.au/"
        assert len(r.redirect_chain) == 1
        assert r.redirect_chain[0].status == 301
        assert r.redirect_chain[0].from_url == "https://example.com/"
        assert r.redirect_chain[0].to_url == "https://example.com.au/"


def test_fetch_does_not_follow_when_disabled():
    with patch("qant.fetcher._fetch_uncached") as m:
        m.return_value = FetchResult(
            url="https://example.com/",
            final_url="https://example.com/",
            status=301,
            headers={"Location": "https://example.com.au/"},
            html="",
            redirect_chain=(),
        )
        r = fetch("https://example.com/", follow_redirects=False)
        assert r.status == 301
        assert r.headers["Location"] == "https://example.com.au/"
        assert r.redirect_chain == ()


def test_fetch_caches_repeated_calls():
    with patch("qant.fetcher._fetch_uncached") as m:
        m.return_value = FetchResult(
            url="https://example.com/",
            final_url="https://example.com/",
            status=200,
            headers={"content-type": "text/html"},
            html="<html></html>",
            redirect_chain=(),
        )
        fetch("https://example.com/")
        fetch("https://example.com/")
        fetch("https://example.com/")
        assert m.call_count == 1


def test_fetch_cache_clear_forces_refetch():
    with patch("qant.fetcher._fetch_uncached") as m:
        m.return_value = FetchResult(
            url="https://example.com/",
            final_url="https://example.com/",
            status=200,
            headers={"content-type": "text/html"},
            html="<html></html>",
            redirect_chain=(),
        )
        fetch("https://example.com/")
        fetch_cache_clear()
        fetch("https://example.com/")
        assert m.call_count == 2
