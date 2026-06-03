"""Tests for qant.config."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from qant.config import load_config


def test_load_config_parses_sample(fixture_dir: Path):
    cfg = load_config(fixture_dir / "sample_brand_seo.yml")
    assert cfg.brand == "redbridgecyber"
    assert cfg.display_name == "Red Bridge Cyber"
    assert cfg.country == "AU"
    assert cfg.canonical.marketing == "https://redbridgecyber.com.au"
    assert cfg.hosts["marketing"].staging == "redbridgecyber-stg.qant.co"
    assert cfg.hosts["marketing"].production == "redbridgecyber.com.au"


def test_load_config_parses_redirects(fixture_dir: Path):
    cfg = load_config(fixture_dir / "sample_brand_seo.yml")
    assert len(cfg.redirects) == 3
    first = cfg.redirects[0]
    assert first.from_ == "https://redbridgecyber.com"
    assert first.to == "https://redbridgecyber.com.au"
    assert first.code == 301


def test_load_config_parses_expected(fixture_dir: Path):
    cfg = load_config(fixture_dir / "sample_brand_seo.yml")
    assert len(cfg.expected["staging"]) == 2
    assert cfg.expected["staging"][0].id == "indexability.allows-indexing"
    assert cfg.expected["staging"][0].reason == "staging suppressed via edge header"
    assert cfg.expected["production"] == []


def test_load_config_parses_out_of_scope(fixture_dir: Path):
    cfg = load_config(fixture_dir / "sample_brand_seo.yml")
    assert cfg.out_of_scope == ["report.redbridgecyber.com.au"]


def test_load_config_rejects_unknown_top_level_key(tmp_path: Path):
    bad = tmp_path / "bad.yml"
    bad.write_text(
        "brand: x\n"
        "display_name: X\n"
        "canonical:\n  marketing: https://x.com\n"
        "hosts:\n  marketing:\n    production: x.com\n"
        "garbage_key: oops\n"
    )
    with pytest.raises(ValidationError):
        load_config(bad)


def test_load_config_requires_brand(tmp_path: Path):
    bad = tmp_path / "bad.yml"
    bad.write_text(
        "display_name: X\n"
        "canonical:\n  marketing: https://x.com\n"
        "hosts:\n  marketing:\n    production: x.com\n"
    )
    with pytest.raises(ValidationError):
        load_config(bad)


def test_load_config_defaults_country_to_au(tmp_path: Path):
    minimal = tmp_path / "min.yml"
    minimal.write_text(
        "brand: x\n"
        "display_name: X\n"
        "canonical:\n  marketing: https://x.com\n"
        "hosts:\n  marketing:\n    production: x.com\n"
    )
    cfg = load_config(minimal)
    assert cfg.country == "AU"
