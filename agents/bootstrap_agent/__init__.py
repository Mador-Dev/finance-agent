"""Bootstrap agent — thin wrapper around the full_report graph."""
from agents.app.config import Settings
from agents.app.schemas import PositionGuidanceInput, TickerStrategyDraft
from agents.bootstrap_agent.workflow import GRAPH, invoke

__all__ = ["GRAPH", "invoke", "invoke_bootstrap_agent"]


async def invoke_bootstrap_agent(
    settings: Settings,
    *,
    ticker: str,
    position_context: dict,
    guidance: PositionGuidanceInput | None = None,
) -> TickerStrategyDraft:
    """Adapter that matches the legacy signature used by app.service."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")
    guidance_payload = guidance.model_dump() if guidance else None
    return await invoke(
        ticker=ticker,
        position=position_context,
        guidance=guidance_payload,
    )
