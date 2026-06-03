"""Brand-audit config loader.

Loads `.brand-seo.yml` into a pydantic-validated `BrandSeoConfig`.
Unknown keys cause errors so typos are caught at load time.
"""
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field


class HostMap(BaseModel):
    model_config = ConfigDict(extra="forbid")
    staging: Optional[str] = None
    production: Optional[str] = None


class CanonicalMap(BaseModel):
    model_config = ConfigDict(extra="forbid")
    marketing: str


class RedirectEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    from_: str = Field(alias="from")
    to: str
    code: int = 301


class ExpectedEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    reason: str


class BrandSeoConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    brand: str
    display_name: str
    country: str = "AU"
    legal_entity: Optional[str] = None
    canonical: CanonicalMap
    hosts: dict[str, HostMap]
    redirects: list[RedirectEntry] = []
    out_of_scope: list[str] = []
    expected: dict[str, list[ExpectedEntry]] = {}


def load_config(path: Path) -> BrandSeoConfig:
    """Load and validate a brand-seo config YAML file."""
    data = yaml.safe_load(Path(path).read_text())
    return BrandSeoConfig(**data)
