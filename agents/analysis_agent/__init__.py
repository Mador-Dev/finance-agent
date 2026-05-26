"""Analysis-agent dispatcher.

Maps an action name to the corresponding agent module's `invoke()` function.
Each agent flow lives in its own package:

    quick_check_agent / daily_brief_agent / full_report_agent / deep_dive_agent

Bootstrap lives in `bootstrap_agent` and is invoked separately by app.service
(it doesn't go through this dispatcher).
"""
from __future__ import annotations

from typing import Any

from agents.app.config import Settings
from agents.app.schemas import PositionGuidanceInput, TickerStrategyDraft
from agents.daily_brief_agent import invoke as invoke_daily_brief
from agents.deep_dive_agent import invoke as invoke_deep_dive
from agents.full_report_agent import invoke as invoke_full_report
from agents.quick_check_agent import invoke as invoke_quick_check

__all__ = ["invoke_analysis_agent"]


_DISPATCH = {
    "quick_check": invoke_quick_check,
    "daily_brief": invoke_daily_brief,
    "full_report": invoke_full_report,
    "deep_dive": invoke_deep_dive,
}


async def invoke_analysis_agent(
    settings: Settings,
    *,
    action: str,
    ticker: str,
    position_context: dict[str, Any],
    guidance: PositionGuidanceInput | dict[str, Any] | None = None,
    current_strategy: dict[str, Any] | None = None,
    recent_reports: list[dict[str, Any]] | None = None,  # noqa: ARG001
) -> TickerStrategyDraft:
    """Route an analysis action to the correct agent workflow."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")

    invoke = _DISPATCH.get(action, invoke_full_report)
    guidance_payload = guidance.model_dump() if hasattr(guidance, "model_dump") else guidance

    return await invoke(
        ticker=ticker,
        position=position_context,
        guidance=guidance_payload,
        current_strategy=current_strategy,
    )
