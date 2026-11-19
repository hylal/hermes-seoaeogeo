"""Core data models and validation for SEO/AEO/GEO audit results."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditResult(BaseModel):
    """Structured result of a website SEO / AEO / GEO audit."""

    url: str
    mode: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    overall_score: int = Field(default=0, ge=0, le=100)
    technical: dict[str, Any] = Field(default_factory=dict)
    aeo: dict[str, Any] = Field(default_factory=dict)
    geo: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        """Return a compact summary for Rich display."""
        return {
            "url": self.url,
            "mode": self.mode,
            "score": self.overall_score,
            "tech_items": len(self.technical),
            "aeo_items": len(self.aeo),
            "geo_items": len(self.geo),
            "errors": len(self.errors),
        }
