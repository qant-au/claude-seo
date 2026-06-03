"""End-to-end test for run_brand_audit with mocked HTTP."""
import json
from pathlib import Path
from unittest.mock import patch

from qant.fetcher import FetchResult, RedirectStep, fetch_cache_clear
from qant.run_brand_audit import run


def _mk_fetch_responses() -> dict[str, FetchResult]:
    home = FetchResult(
        url="https://redbridgecyber-stg.qant.co/",
        final_url="https://redbridgecyber-stg.qant.co/",
        status=200,
        headers={"content-type": "text/html", "X-Robots-Tag": "noindex, nofollow"},
        html=(
            "<html><head>"
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Organization","name":"RBC"}'
            "</script>"
            "</head></html>"
        ),
        redirect_chain=(),
    )
    robots = FetchResult(
        url="https://redbridgecyber-stg.qant.co/robots.txt",
        final_url="https://redbridgecyber-stg.qant.co/robots.txt",
        status=200, headers={"content-type": "text/plain"},
        html="User-agent: *\nAllow: /\nSitemap: https://redbridgecyber-stg.qant.co/sitemap.xml\n",
        redirect_chain=(),
    )
    redirect_com_to_au = FetchResult(
        url="https://redbridgecyber.com",
        final_url="https://redbridgecyber.com.au/",
        status=200, headers={}, html="",
        redirect_chain=(RedirectStep(
            from_url="https://redbridgecyber.com",
            to_url="https://redbridgecyber.com.au/",
            status=301,
        ),),
    )
    return {
        "https://redbridgecyber-stg.qant.co/": home,
        "https://redbridgecyber-stg.qant.co/robots.txt": robots,
        "https://redbridgecyber.com": redirect_com_to_au,
    }


@patch("qant.fetcher._fetch_uncached")
def test_run_writes_json_and_md_for_staging(mock_uncached, tmp_path: Path):
    fetch_cache_clear()
    responses_map = _mk_fetch_responses()

    def _side_effect(url, follow_redirects, timeout):
        return responses_map.get(url) or FetchResult(
            url=url, final_url=url, status=404, headers={}, html="", redirect_chain=(),
        )

    mock_uncached.side_effect = _side_effect

    # Minimal config: only home + one redirect.
    config_yaml = (
        "brand: redbridgecyber\n"
        "display_name: Red Bridge Cyber\n"
        "canonical:\n  marketing: https://redbridgecyber.com.au\n"
        "hosts:\n  marketing:\n    staging: redbridgecyber-stg.qant.co\n"
        "    production: redbridgecyber.com.au\n"
        "redirects:\n"
        '  - { from: "https://redbridgecyber.com", to: "https://redbridgecyber.com.au/", code: 301 }\n'
        "expected:\n  staging:\n"
        "    - { id: indexability.allows-indexing, reason: staging suppressed }\n"
    )
    cfg_path = tmp_path / ".brand-seo.yml"
    cfg_path.write_text(config_yaml)

    paths = run(config_path=cfg_path, env="staging", brand_dir=tmp_path)

    assert paths.json_paths.latest.exists()
    assert paths.md_paths.latest.exists()

    data = json.loads(paths.json_paths.latest.read_text())
    assert data["brand"] == "redbridgecyber"
    assert data["environment"] == "staging"
    assert data["host"] == "redbridgecyber-stg.qant.co"
    # Indexability suppression should have flipped the allows-indexing fail to EXPECTED
    by_id = {f["id"]: f for f in data["findings"]}
    # X-Robots-Tag noindex is present in our mocked response, so allows-indexing is PASS,
    # not EXPECTED — and the suppression code only flips FAILs.
    assert by_id["indexability.allows-indexing"]["status"] == "PASS"
    # Schema Organization present
    assert by_id["schema.missing-organization"]["status"] == "PASS"
    # Schema WebSite absent
    assert by_id["schema.missing-website"]["status"] == "FAIL"
    # Redirect passed
    assert by_id["redirects.brand-protection-redirect-broken"]["status"] == "PASS"
