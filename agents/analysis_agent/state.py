from typing import Any, TypedDict


class AnalysisResearchInput(TypedDict):
    action: str
    ticker: str
    position: dict[str, Any]
    guidance: dict[str, Any] | None
    current_strategy: dict[str, Any] | None
    recent_reports: list[dict[str, Any]]
    generated_at: str
