"""Single source of truth for finding IDs.

Each ID is a contract — once published, it doesn't change. Renames go through
the ALIASES map so existing brand configs keep working. The checklist (deferred
work) is generated from this registry, so every new check must register here.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class FindingDef:
    id: str
    category: str
    default_severity: str  # "P1" | "P2" | "P3" | "INFO"
    title: str
    description: str


def _d(id: str, category: str, sev: str, title: str, desc: str) -> FindingDef:
    return FindingDef(id=id, category=category, default_severity=sev, title=title, description=desc)


REGISTRY: dict[str, FindingDef] = {
    # ---- indexability ----
    "indexability.allows-indexing": _d(
        "indexability.allows-indexing", "indexability", "P1",
        "Site allows indexing",
        "robots.txt allows / and no X-Robots-Tag noindex header is present. "
        "Expected on production; in staging this should typically be EXPECTED.",
    ),
    "indexability.no-x-robots-tag-noindex": _d(
        "indexability.no-x-robots-tag-noindex", "indexability", "P2",
        "No X-Robots-Tag: noindex header",
        "The response does not carry an X-Robots-Tag: noindex header. "
        "In staging, edge-injected noindex is the safest barrier against accidental indexing.",
    ),
    "indexability.robots-txt-missing": _d(
        "indexability.robots-txt-missing", "indexability", "P2",
        "robots.txt is missing",
        "GET /robots.txt returned a non-2xx status. A robots.txt file should always exist.",
    ),
    "indexability.sitemap-not-referenced-in-robots": _d(
        "indexability.sitemap-not-referenced-in-robots", "indexability", "P3",
        "Sitemap not referenced in robots.txt",
        "robots.txt does not contain a Sitemap: directive pointing at the canonical sitemap.",
    ),

    # ---- redirects ----
    "redirects.brand-protection-redirect-broken": _d(
        "redirects.brand-protection-redirect-broken", "redirects", "P1",
        "Brand-protection domain redirect broken",
        "A configured brand-protection hostname did not 301 to the canonical hostname.",
    ),
    "redirects.legacy-path-redirect-broken": _d(
        "redirects.legacy-path-redirect-broken", "redirects", "P2",
        "Legacy path redirect broken",
        "A configured legacy path (e.g. /blog) did not 301 to its replacement.",
    ),
    "redirects.subdomain-redirect-broken": _d(
        "redirects.subdomain-redirect-broken", "redirects", "P2",
        "Retired subdomain redirect broken",
        "A retired subdomain did not 301 to its canonical replacement on the primary host.",
    ),

    # ---- schema ----
    "schema.missing-organization": _d(
        "schema.missing-organization", "schema", "P2",
        "Missing Organization JSON-LD",
        "No <script type=\"application/ld+json\"> Organization block was found on the page.",
    ),
    "schema.missing-website": _d(
        "schema.missing-website", "schema", "P3",
        "Missing WebSite JSON-LD",
        "No <script type=\"application/ld+json\"> WebSite block was found on the page.",
    ),
    "schema.invalid-jsonld-syntax": _d(
        "schema.invalid-jsonld-syntax", "schema", "P2",
        "Invalid JSON-LD syntax",
        "A <script type=\"application/ld+json\"> block could not be parsed as JSON.",
    ),
}


# Renames go here: {"old.id": "new.id"}. Once published, NEVER remove an entry —
# brand configs may still reference the old ID.
ALIASES: dict[str, str] = {}


def resolve(finding_id: str) -> str:
    """Map an ID through aliases. Unknown IDs pass through unchanged."""
    return ALIASES.get(finding_id, finding_id)


def get(finding_id: str) -> FindingDef:
    """Look up a finding definition. Raises KeyError on unknown ID."""
    canonical = resolve(finding_id)
    if canonical not in REGISTRY:
        raise KeyError(f"Unknown finding id: {finding_id}")
    return REGISTRY[canonical]
