"""Analysis agent — coordinator with specialist subagents."""
from __future__ import annotations

import logging
from functools import cache
from typing import Any

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

from agents.analysis_agent.prompts import (
    ACTION_INSTRUCTIONS,
    BEAR_PROMPT, BULL_PROMPT, COORDINATOR_PROMPT, CRITIC_PROMPT,
    FUNDAMENTALS_PROMPT, PLANNER_PROMPT, RISK_PROMPT, SENTIMENT_PROMPT,
)
from agents.analysis_agent.state import AnalysisResearchInput
from agents.analysis_agent.tools import get_analysis_context
from agents.app.config import Settings
from agents.app.schemas import PositionGuidanceInput, TickerStrategyDraft, utc_now

logger = logging.getLogger(__name__)

# full_report and deep_dive use the complete 7-specialist crew.
_FULL_ACTIONS = {"deep_dive", "full_report"}


@cache
def _build_agent(model: str, full: bool) -> Any:
    """Compile and cache the analysis graph. Built once per (model, full) pair."""
    # deepagents defaults to the OpenAI Responses API for `openai:` models, which
    # conflicts with tool-based structured output (response_format). Use Chat
    # Completions instead for reliable structured output.
    resolved_model = (
        init_chat_model(model, use_responses_api=False)
        if model.startswith("openai:")
        else model
    )

    subagents = [
        {
            "name": "planner",
            "description": "Plans the minimum useful research path for this ticker and action.",
            "system_prompt": PLANNER_PROMPT,
            "tools": [get_analysis_context],
        },
        {
            "name": "fundamentals",
            "description": "Analyses business quality, growth durability, and valuation drivers.",
            "system_prompt": FUNDAMENTALS_PROMPT,
            "tools": [get_analysis_context],
        },
        {
            "name": "sentiment",
            "description": "Analyses narrative shifts and near-term catalysts.",
            "system_prompt": SENTIMENT_PROMPT,
            "tools": [get_analysis_context],
        },
        {
            "name": "risk",
            "description": "Analyses downside scenarios and invalidation conditions.",
            "system_prompt": RISK_PROMPT,
            "tools": [get_analysis_context],
        },
    ]

    if full:
        subagents += [
            {
                "name": "critic",
                "description": "Critiques the strategy for logical gaps and unsupported claims.",
                "system_prompt": CRITIC_PROMPT,
                "tools": [get_analysis_context],
            },
            {
                "name": "bull_case",
                "description": "Argues the strongest evidence-based case for owning the ticker.",
                "system_prompt": BULL_PROMPT,
                "tools": [get_analysis_context],
            },
            {
                "name": "bear_case",
                "description": "Argues the strongest evidence-based case against owning the ticker.",
                "system_prompt": BEAR_PROMPT,
                "tools": [get_analysis_context],
            },
        ]

    return create_deep_agent(
        model=resolved_model,
        system_prompt=COORDINATOR_PROMPT,
        tools=[get_analysis_context],
        subagents=subagents,
        response_format=TickerStrategyDraft,
    )


async def invoke_analysis_agent(
    settings: Settings,
    *,
    action: str,
    ticker: str,
    position_context: dict[str, Any],
    guidance: PositionGuidanceInput | dict[str, Any] | None = None,
    current_strategy: dict[str, Any] | None = None,
    recent_reports: list[dict[str, Any]] | None = None,
) -> TickerStrategyDraft:
    """Run the analysis agent for one ticker and return a TickerStrategyDraft."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")

    guidance_payload = guidance.model_dump() if hasattr(guidance, "model_dump") else guidance
    packet: AnalysisResearchInput = {
        "action": action,
        "ticker": ticker,
        "position": position_context,
        "guidance": guidance_payload,
        "current_strategy": current_strategy,
        "recent_reports": recent_reports or [],
        "generated_at": utc_now(),
    }
    instruction = ACTION_INSTRUCTIONS.get(action, "Refresh the investment strategy.")

    result = await _build_agent(settings.deep_agent_model, action in _FULL_ACTIONS).ainvoke(
        {
            "messages": [{
                "role": "user",
                "content": (
                    f"{instruction}\n\n"
                    f"Ticker: {ticker}\n\n"
                    "Call get_analysis_context to load the full research packet."
                ),
            }],
        },
        config={"configurable": {"packet": packet}},
    )

    # ainvoke returns the graph state dict; structured output lives in "structured_response".
    strategy = result.get("structured_response")
    if not isinstance(strategy, TickerStrategyDraft):
        raise ValueError(
            f"Agent did not produce a valid strategy for {ticker}. "
            f"Got: {type(strategy).__name__}"
        )
    return strategy
