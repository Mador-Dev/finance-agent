from __future__ import annotations

from typing import Any, TypedDict


class BootstrapResearchInput(TypedDict):
    ticker: str
    position: dict[str, Any]
    guidance: dict[str, Any] | None
    generatedAt: str
    limitations: list[str]
