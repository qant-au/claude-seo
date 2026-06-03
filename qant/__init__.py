"""QANT brand SEO audit wrapper.

Additive layer over the upstream claude-seo fork. Calls the fork's
scripts directly (no LLM interpretation), emits Firestore-shaped JSON
with stable finding IDs and env-aware suppression.

Run via: python -m qant.run_brand_audit --config .brand-seo.yml --env staging
"""

__version__ = "0.1.0"
