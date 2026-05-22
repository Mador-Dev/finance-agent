from __future__ import annotations

import asyncio
from typing import Any

from deepagents import create_deep_agent

from agents.analysis_agent.prompts import (
    ACTION_INSTRUCTIONS,
    BEAR_PROMPT,
    BULL_PROMPT,
    COORDINATOR_PROMPT,
    CRITIC_PROMPT,
    FUNDAMENTALS_PROMPT,
    PLANNER_PROMPT,
    RISK_PROMPT,
    SENTIMENT_PROMPT,
)
from agents.analysis_agent.state import AnalysisResearchInput
from agents.analysis_agent.tools import make_context_tool
from agents.app.config import Settings
from agents.app.schemas import PositionGuidanceInput, TickerStrategyDraft, utc_now


def build_research_input(
    action: str,
    ticker: str,
    position_context: dict[str, Any],
    guidance: PositionGuidanceInput | dict[str, Any] | None,
    current_strategy: dict[str, Any] | None,
    recent_reports: list[dict[str, Any]],
) -> AnalysisResearchInput:
    guidance_payload = guidance.model_dump() if hasattr(guidance, "model_dump") else guidance
    return {
        "action": action,
        "ticker": ticker,
        "position": position_context,
        "guidance": guidance_payload,
        "current_strategy": current_strategy,
        "recent_reports": recent_reports,
        "generated_at": utc_now(),
    }


def _subagent(name: str, description: str, system_prompt: str, tools: list[Any]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "system_prompt": system_prompt,
        "tools": tools,
    }


def build_strategy_agent(settings: Settings, packet: AnalysisResearchInput) -> Any:
    tools = [make_context_tool(packet)]
    subagents = [
        _subagent("planner", "Plan the minimum useful research path.", PLANNER_PROMPT, tools),
        _subagent("analyst_fundamentals", "Analyze fundamentals.", FUNDAMENTALS_PROMPT, tools),
        _subagent("analyst_sentiment", "Analyze sentiment and catalysts.", SENTIMENT_PROMPT, tools),
        _subagent("analyst_risk", "Analyze risks and invalidation conditions.", RISK_PROMPT, tools),
        _subagent("critic", "Critique the draft strategy.", CRITIC_PROMPT, tools),
        _subagent("bull_case", "Argue the bull case.", BULL_PROMPT, tools),
        _subagent("bear_case", "Argue the bear case.", BEAR_PROMPT, tools),
    ]
    return create_deep_agent(
        model=settings.deep_agent_model,
        system_prompt=COORDINATOR_PROMPT,
        tools=tools,
        subagents=subagents,
        response_format=TickerStrategyDraft,
    )


def _strategy_from_result(result: Any, *, ticker: str) -> TickerStrategyDraft:
    if not isinstance(result, dict):
        raise ValueError(f"No structured strategy returned for {ticker}")
    structured = result.get("structured_response")
    if isinstance(structured, TickerStrategyDraft):
        return structured
    if isinstance(structured, dict):
        return TickerStrategyDraft.model_validate(structured)
    raise ValueError(f"No structured strategy returned for {ticker}")


def _invoke_analysis_agent_sync(agent: Any, packet: AnalysisResearchInput) -> TickerStrategyDraft:
    action = packet["action"]
    instruction = ACTION_INSTRUCTIONS.get(action, "Refresh the ticker strategy.")
    prompt = (
        f"{instruction}\n\n"
        f"Ticker: {packet['ticker']}\n"
        f"Context packet:\n{packet}\n\n"
        "Use the subagents when useful, challenge weak assumptions, and return a structured strategy."
    )
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    return _strategy_from_result(result, ticker=packet["ticker"])


async def invoke_analysis_agent(
    settings: Settings,
    *,
    action: str,
    ticker: str,
    position_context: dict[str, Any],
    guidance: PositionGuidanceInput | dict[str, Any] | None,
    current_strategy: dict[str, Any] | None,
    recent_reports: list[dict[str, Any]],
) -> TickerStrategyDraft:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")
    packet = build_research_input(
        action, ticker, position_context, guidance, current_strategy, recent_reports
    )
    agent = build_strategy_agent(settings, packet)
    return await asyncio.to_thread(_invoke_analysis_agent_sync, agent, packet)
