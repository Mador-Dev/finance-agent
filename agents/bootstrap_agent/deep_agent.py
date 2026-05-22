from __future__ import annotations

import asyncio
from typing import Any

from deepagents import create_deep_agent

from agents.app.config import Settings
from agents.app.schemas import PositionGuidanceInput, TickerStrategyDraft, utc_now
from agents.bootstrap_agent.prompts import (
    BEAR_SUBAGENT_PROMPT,
    BULL_SUBAGENT_PROMPT,
    COORDINATOR_PROMPT,
    CRITIC_SUBAGENT_PROMPT,
    FUNDAMENTALS_SUBAGENT_PROMPT,
    RISK_SUBAGENT_PROMPT,
    SENTIMENT_SUBAGENT_PROMPT,
)
from agents.bootstrap_agent.state import BootstrapResearchInput
from agents.bootstrap_agent.tools import make_guidance_tool, make_research_packet_tool

BASE_LIMITATIONS = [
    "Bootstrap v1 uses shared workspace state and lightweight built-in context.",
    "For stronger research, connect deterministic market/news/fundamental data sources here.",
]

BASE_SUBAGENTS = [
    (
        "analyst_fundamentals",
        "Analyze business quality, growth durability, and thesis-critical fundamentals.",
        FUNDAMENTALS_SUBAGENT_PROMPT,
    ),
    (
        "analyst_sentiment",
        "Analyze narrative shifts, recent perception changes, and concrete catalysts.",
        SENTIMENT_SUBAGENT_PROMPT,
    ),
    (
        "analyst_risk",
        "Analyze downside drivers, key risks, and invalidation conditions.",
        RISK_SUBAGENT_PROMPT,
    ),
    (
        "critic",
        "Find flaws, unsupported claims, and missing evidence in the draft strategy.",
        CRITIC_SUBAGENT_PROMPT,
    ),
]

BULL_BEAR_SUBAGENTS = [
    (
        "bull_case",
        "Argue the strongest case for owning or adding the ticker.",
        BULL_SUBAGENT_PROMPT,
    ),
    (
        "bear_case",
        "Argue the strongest case against owning or adding the ticker.",
        BEAR_SUBAGENT_PROMPT,
    ),
]


def build_bootstrap_research_input(
    ticker: str,
    position_context: dict[str, Any],
    guidance: PositionGuidanceInput | None,
) -> BootstrapResearchInput:
    return BootstrapResearchInput(
        ticker=ticker,
        position=position_context,
        guidance=guidance.model_dump() if guidance else None,
        generatedAt=utc_now(),
        limitations=BASE_LIMITATIONS,
    )


def _subagent(name: str, description: str, system_prompt: str, tools: list[Any]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "system_prompt": system_prompt,
        "tools": tools,
    }


def build_bootstrap_subagents(research_packet: BootstrapResearchInput, include_bull_bear: bool) -> list[dict[str, Any]]:
    tools = [
        make_research_packet_tool(research_packet),
        make_guidance_tool(research_packet["guidance"]),
    ]
    specs = BASE_SUBAGENTS + (BULL_BEAR_SUBAGENTS if include_bull_bear else [])
    return [_subagent(name, description, prompt, tools) for name, description, prompt in specs]


def build_bootstrap_deep_agent(settings: Settings, *, research_packet: BootstrapResearchInput) -> Any:
    tools = [
        make_research_packet_tool(research_packet),
        make_guidance_tool(research_packet["guidance"]),
    ]
    return create_deep_agent(
        model=settings.deep_agent_model,
        system_prompt=COORDINATOR_PROMPT,
        tools=tools,
        subagents=build_bootstrap_subagents(research_packet, settings.bootstrap_include_bull_bear),
        response_format=TickerStrategyDraft,
    )


class BootstrapStrategyRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def build_strategy(
        self,
        *,
        ticker: str,
        position_context: dict[str, Any],
        guidance: PositionGuidanceInput | None,
    ) -> TickerStrategyDraft:
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")

        research_packet = build_bootstrap_research_input(ticker, position_context, guidance)
        agent = build_bootstrap_deep_agent(self.settings, research_packet=research_packet)
        return await asyncio.to_thread(self._invoke, agent, ticker, research_packet)

    @staticmethod
    def _invoke(agent: Any, ticker: str, research_packet: BootstrapResearchInput) -> TickerStrategyDraft:
        prompt = (
            f"Build the initial portfolio strategy for ticker {ticker}.\n\n"
            f"Research packet:\n{research_packet}\n\n"
            "Run the relevant specialist subagents, challenge weak assumptions, "
            "and synthesize a final ticker strategy."
        )
        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        structured = BootstrapStrategyRunner._extract_structured_response(result)
        if not structured:
            raise ValueError(f"Deep agent returned no structured strategy for {ticker}")
        return TickerStrategyDraft.model_validate(structured)

    @staticmethod
    def _extract_structured_response(result: Any) -> dict[str, Any] | None:
        if isinstance(result, dict):
            for key in ("structured_response", "output", "final_output", "response"):
                candidate = result.get(key)
                if isinstance(candidate, dict):
                    return candidate
            messages = result.get("messages")
            if isinstance(messages, list):
                for message in reversed(messages):
                    if isinstance(message, dict):
                        content = message.get("content")
                        if isinstance(content, dict):
                            return content
        return result if isinstance(result, dict) else None
