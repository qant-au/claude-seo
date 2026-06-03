"""Tests for qant.checks.redirects."""
from unittest.mock import patch
import sys
import os

from qant.checks import redirects
from qant.config import RedirectEntry
from qant.fetcher import FetchResult, RedirectStep
from qant.findings import Status

# Import URLSafetyError from the same path as redirects.py
_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
try:
    from url_safety import URLSafetyError  # type: ignore
except ImportError:
    URLSafetyError = Exception  # type: ignore[misc,assignment]


def _redirected(from_: str, to: str, code: int = 301) -> FetchResult:
    return FetchResult(
        url=from_, final_url=to, status=200, headers={}, html="",
        redirect_chain=(RedirectStep(from_url=from_, to_url=to, status=code),),
    )


def _no_redirect(url: str) -> FetchResult:
    return FetchResult(
        url=url, final_url=url, status=200, headers={}, html="", redirect_chain=(),
    )


@patch("qant.checks.redirects.fetch")
def test_passes_when_redirect_chain_matches(mock_fetch):
    mock_fetch.return_value = _redirected(
        "https://example.com", "https://example.com.au", 301,
    )
    entries = [RedirectEntry(**{"from": "https://example.com", "to": "https://example.com.au", "code": 301})]
    findings = redirects.check(entries)
    assert findings[0].status == Status.PASS


@patch("qant.checks.redirects.fetch")
def test_fails_when_no_redirect_happens(mock_fetch):
    mock_fetch.return_value = _no_redirect("https://example.com")
    entries = [RedirectEntry(**{"from": "https://example.com", "to": "https://example.com.au", "code": 301})]
    findings = redirects.check(entries)
    assert findings[0].status == Status.FAIL
    assert "did not redirect" in findings[0].detail.lower()


@patch("qant.checks.redirects.fetch")
def test_fails_when_final_url_differs(mock_fetch):
    mock_fetch.return_value = _redirected(
        "https://example.com", "https://wrong.example", 301,
    )
    entries = [RedirectEntry(**{"from": "https://example.com", "to": "https://example.com.au", "code": 301})]
    findings = redirects.check(entries)
    assert findings[0].status == Status.FAIL
    assert "wrong.example" in findings[0].detail


@patch("qant.checks.redirects.fetch")
def test_fails_when_status_code_mismatches(mock_fetch):
    mock_fetch.return_value = _redirected(
        "https://example.com", "https://example.com.au", 302,
    )
    entries = [RedirectEntry(**{"from": "https://example.com", "to": "https://example.com.au", "code": 301})]
    findings = redirects.check(entries)
    assert findings[0].status == Status.FAIL
    assert "302" in findings[0].detail


@patch("qant.checks.redirects.fetch")
def test_classifies_redirect_kind_from_url_shape(mock_fetch):
    # Path-only redirect → legacy-path
    mock_fetch.return_value = _redirected("https://x.com.au/blog", "https://x.com.au/improve")
    findings = redirects.check([
        RedirectEntry(**{"from": "https://x.com.au/blog", "to": "https://x.com.au/improve", "code": 301}),
    ])
    assert findings[0].id == "redirects.legacy-path-redirect-broken"

    # Subdomain → subdomain
    mock_fetch.reset_mock()
    mock_fetch.return_value = _redirected("https://improve.x.com.au", "https://x.com.au/improve")
    findings = redirects.check([
        RedirectEntry(**{"from": "https://improve.x.com.au", "to": "https://x.com.au/improve", "code": 301}),
    ])
    assert findings[0].id == "redirects.subdomain-redirect-broken"

    # Apex domain → apex domain
    mock_fetch.reset_mock()
    mock_fetch.return_value = _redirected("https://x.com", "https://x.com.au")
    findings = redirects.check([
        RedirectEntry(**{"from": "https://x.com", "to": "https://x.com.au", "code": 301}),
    ])
    assert findings[0].id == "redirects.brand-protection-redirect-broken"


@patch("qant.checks.redirects.fetch")
def test_fails_with_url_safety_error_dns_failure(mock_fetch):
    """Verify URLSafetyError (DNS/safety failure) produces FAIL finding, not crash."""
    mock_fetch.side_effect = URLSafetyError("DNS resolution failed for scan.redbridgecyber.com.au")
    entries = [RedirectEntry(**{"from": "https://scan.redbridgecyber.com.au", "to": "https://example.com.au", "code": 301})]
    findings = redirects.check(entries)

    assert len(findings) == 1
    assert findings[0].status == Status.FAIL
    # Detail should mention unreachable/DNS/error
    assert "unreachable" in findings[0].detail.lower() or "dns" in findings[0].detail.lower()
    # Evidence should contain the error message
    assert "error" in findings[0].evidence
    assert "DNS resolution failed" in findings[0].evidence["error"]
