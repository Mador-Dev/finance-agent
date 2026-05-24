"""Bootstrap agent — coordinator with specialist subagents."""
from __future__ import annotations

import logging
from functools import cache
from typing import Any

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

from agents.app.config import Settings
from agents.app.schemas import PositionGuidanceInput, TickerStrategyDraft, utc_now
from agents.bootstrap_agent.prompts import (
    BEAR_SUBAGENT_PROMPT, BULL_SUBAGENT_PROMPT, COORDINATOR_PROMPT,
    CRITIC_SUBAGENT_PROMPT, FUNDAMENTALS_SUBAGENT_PROMPT,
    RISK_SUBAGENT_PROMPT, SENTIMENT_SUBAGENT_PROMPT,
)
from agents.bootstrap_agent.state import BootstrapResearchInput
from agents.bootstrap_agent.tools import get_guidance, get_research_packet

logger = logging.getLogger(__name__)

BASE_LIMITATIONS = [
    "Bootstrap v1 uses lightweight built-in context without live market data.",
    "For stronger research, connect deterministic market/news/fundamental data sources.",
]

_TOOLS = [get_research_packet, get_guidance]


@cache
def _build_agent(model: str, include_bull_bear: bool) -> Any:
    """Compile and cache the bootstrap graph. Built once per (model, include_bull_bear) pair."""
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
            "name": "fundamentals",
            "description": "Analyses business quality, growth durability, and key valuation drivers.",
            "system_prompt": FUNDAMENTALS_SUBAGENT_PROMPT,
            "tools": _TOOLS,
        },
        {
            "name": "sentiment",
            "description": "Analyses market narrative and near-term catalysts to monitor.",
            "system_prompt": SENTIMENT_SUBAGENT_PROMPT,
            "tools": _TOOLS,
        },
        {
            "name": "risk",
            "description": "Analyses thesis failure modes and invalidation conditions.",
            "system_prompt": RISK_SUBAGENT_PROMPT,
            "tools": _TOOLS,
        },
        {
            "name": "critic",
            "description": "Stress-tests the emerging strategy before it becomes the user's foundation.",
            "system_prompt": CRITIC_SUBAGENT_PROMPT,
            "tools": _TOOLS,
        },
    ]

    if include_bull_bear:
        subagents += [
            {
                "name": "bull_case",
                "description": "Argues the strongest evidence-based case for holding the position.",
                "system_prompt": BULL_SUBAGENT_PROMPT,
                "tools": _TOOLS,
            },
            {
                "name": "bear_case",
                "description": "Argues the strongest evidence-based case against holding the position.",
                "system_prompt": BEAR_SUBAGENT_PROMPT,
                "tools": _TOOLS,
            },
        ]

    return create_deep_agent(
        model=resolved_model,
        system_prompt=COORDINATOR_PROMPT,
        tools=_TOOLS,
        subagents=subagents,
        response_format=TickerStrategyDraft,
    )


async def invoke_bootstrap_agent(
    settings: Settings,
    *,
    ticker: str,
    position_context: dict[str, Any],
    guidance: PositionGuidanceInput | None = None,
) -> TickerStrategyDraft:
    """Run the bootstrap agent for one ticker and return a TickerStrategyDraft."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")

    research_packet = BootstrapResearchInput(
        ticker=ticker,
        position=position_context,
        guidance=guidance.model_dump() if guidance else None,
        generatedAt=utc_now(),
        limitations=BASE_LIMITATIONS,
    )

    result = await _build_agent(settings.deep_agent_model, settings.bootstrap_include_bull_bear).ainvoke(
        {
            "messages": [{
                "role": "user",
                "content": (
                    f"Bootstrap the initial investment strategy for {ticker}.\n\n"
                    "Call get_research_packet for position data and "
                    "get_guidance for user preferences."
                ),
            }],
        },
        config={
            "configurable": {
                "research_packet": dict(research_packet),
                "guidance": research_packet.get("guidance") or {},
            },
        },
    )

    # ainvoke returns the graph state dict; structured output lives in "structured_response".
    strategy = result.get("structured_response")
    if not isinstance(strategy, TickerStrategyDraft):
        raise ValueError(
            f"Bootstrap agent did not produce a valid strategy for {ticker}. "
            f"Got: {type(strategy).__name__}"
        )
    return strategy
