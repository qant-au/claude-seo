"""Finding dataclass and enums — the wrapper's central data shape."""
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class Severity(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    INFO = "INFO"


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    EXPECTED = "EXPECTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class Finding:
    id: str
    category: str
    severity: Severity
    status: Status
    url: str
    title: str
    detail: str
    fix: Optional[str] = None
    evidence: dict[str, Any] = field(default_factory=dict)
    expected_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["status"] = self.status.value
        # Drop None-valued optional fields for a clean JSON shape.
        if d.get("fix") is None:
            d.pop("fix", None)
        if d.get("expected_reason") is None:
            d.pop("expected_reason", None)
        # Empty evidence stays as {} — it's a stable key downstream consumers expect.
        return d
