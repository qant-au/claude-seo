"""Tests for qant.registry."""
import pytest

from qant.registry import REGISTRY, get, resolve


def test_registry_contains_seed_ids_for_first_three_checks():
    expected_ids = {
        "indexability.allows-indexing",
        "indexability.no-x-robots-tag-noindex",
        "indexability.robots-txt-missing",
        "indexability.sitemap-not-referenced-in-robots",
        "redirects.brand-protection-redirect-broken",
        "redirects.legacy-path-redirect-broken",
        "redirects.subdomain-redirect-broken",
        "schema.missing-organization",
        "schema.missing-website",
        "schema.invalid-jsonld-syntax",
    }
    assert expected_ids.issubset(set(REGISTRY.keys()))


def test_get_returns_definition_for_known_id():
    d = get("schema.missing-organization")
    assert d.id == "schema.missing-organization"
    assert d.category == "schema"
    assert d.default_severity == "P2"


def test_get_raises_keyerror_for_unknown_id():
    with pytest.raises(KeyError, match="Unknown finding id"):
        get("nonsense.does-not-exist")


def test_resolve_returns_canonical_id_for_known_id():
    assert resolve("schema.missing-organization") == "schema.missing-organization"


def test_resolve_passes_unknown_id_through_unchanged():
    # resolve does not validate — only get() does. This lets configs reference
    # IDs from registry expansions without breaking on rename ordering.
    assert resolve("nonsense.does-not-exist") == "nonsense.does-not-exist"


def test_aliases_dict_exists_and_is_a_mapping():
    from qant.registry import ALIASES
    assert isinstance(ALIASES, dict)
