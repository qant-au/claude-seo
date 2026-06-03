"""HTTP fetcher with redirect-chain capture and per-process caching.

Uses the fork's own DNS-pinned `url_safety.safe_requests_get` helper.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

# Make scripts/ importable so we can reuse url_safety.safe_requests_get.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS_DIR = os.path.join(_REPO_ROOT, "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)


@dataclass(frozen=True)
class RedirectStep:
    from_url: str
    to_url: str
    status: int


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    status: int
    headers: dict[str, str]
    html: str
    redirect_chain: tuple[RedirectStep, ...] = ()


def _fetch_uncached(url: str, follow_redirects: bool, timeout: int) -> FetchResult:
    # Import lazily so test-time path manipulation takes effect.
    from url_safety import safe_requests_get  # type: ignore

    resp = safe_requests_get(url, timeout=timeout, allow_redirects=follow_redirects)

    chain: list[RedirectStep] = []
    if follow_redirects:
        for h in resp.history:
            loc = h.headers.get("Location", "")
            chain.append(RedirectStep(from_url=h.url, to_url=loc or resp.url, status=h.status_code))

    # Ensure the last hop's to_url matches the final landed URL.
    if chain and chain[-1].to_url != resp.url:
        chain[-1] = RedirectStep(
            from_url=chain[-1].from_url, to_url=resp.url, status=chain[-1].status,
        )

    return FetchResult(
        url=url,
        final_url=resp.url,
        status=resp.status_code,
        headers=dict(resp.headers),
        html=resp.text if "text" in resp.headers.get("content-type", "").lower() else "",
        redirect_chain=tuple(chain),
    )


# Module-level cache so multiple checks against the same URL fetch once per run.
# Key is (url, follow_redirects) — different follow modes are independent fetches.
_CACHE: dict[tuple[str, bool], FetchResult] = {}


def fetch(url: str, *, follow_redirects: bool = True, timeout: int = 30) -> FetchResult:
    """Fetch a URL once per run. Returns cached FetchResult on repeat calls."""
    key = (url, follow_redirects)
    if key in _CACHE:
        return _CACHE[key]
    result = _fetch_uncached(url, follow_redirects, timeout)
    _CACHE[key] = result
    return result


def fetch_cache_clear() -> None:
    """Drop the per-process fetch cache. Tests rely on this."""
    _CACHE.clear()
