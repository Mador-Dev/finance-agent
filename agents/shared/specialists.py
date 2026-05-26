"""Specialist LangGraph nodes shared by every analysis flow.

Each node is a small async function that takes the graph state, runs one
research turn for its specialist (via `research_safe`), and writes the
resulting dict back into the shared state.

All nodes follow the same shape:
    1. Build the fallback report (so the graph survives a failed call).
    2. Call `research_safe` with the specialist's system + user prompts.
    3. Return `{<state_key>: report.model_dump()}`.

These nodes are pure functions of `AnalysisState`, so any agent flow can
wire them in via `add_node` without further glue.
"""
from __future__ import annotations

from agents.app.schemas import (
    BearCaseReport,
    BullCaseReport,
    FundamentalsReport,
    MacroReport,
    RiskReport,
    SentimentReport,
    TechnicalReport,
)
from agents.shared import prompts as P
from agents.shared.research import research_safe
from agents.shared.state import AnalysisState


async def fundamentals_node(state: AnalysisState) -> dict:
    report = await research_safe(
        system=P.FUNDAMENTALS_SYSTEM,
        user=P.fundamentals_user(
            state["action"], state["ticker"], state["position"],
            state.get("guidance"), state.get("current_strategy"),
        ),
        schema=FundamentalsReport,
        fallback=FundamentalsReport(fundamentalView="Research unavailable."),
    )
    return {"fundamentals": report.model_dump()}


async def technical_node(state: AnalysisState) -> dict:
    report = await research_safe(
        system=P.TECHNICAL_SYSTEM,
        user=P.technical_user(
            state["action"], state["ticker"], state["position"],
            state.get("guidance"), state.get("current_strategy"),
        ),
        schema=TechnicalReport,
        fallback=TechnicalReport(technicalView="Research unavailable."),
    )
    return {"technical": report.model_dump()}


async def sentiment_node(state: AnalysisState) -> dict:
    report = await research_safe(
        system=P.SENTIMENT_SYSTEM,
        user=P.sentiment_user(
            state["action"], state["ticker"], state["position"],
            state.get("guidance"), state.get("current_strategy"),
        ),
        schema=SentimentReport,
        fallback=SentimentReport(sentimentView="Research unavailable."),
    )
    return {"sentiment": report.model_dump()}


async def macro_node(state: AnalysisState) -> dict:
    report = await research_safe(
        system=P.MACRO_SYSTEM,
        user=P.macro_user(
            state["action"], state["ticker"], state["position"],
            state.get("guidance"), state.get("current_strategy"),
        ),
        schema=MacroReport,
        fallback=MacroReport(macroView="Research unavailable."),
    )
    return {"macro": report.model_dump()}


async def risk_node(state: AnalysisState) -> dict:
    report = await research_safe(
        system=P.RISK_SYSTEM,
        user=P.risk_user(
            state["action"], state["ticker"], state["position"],
            state.get("guidance"), state.get("current_strategy"),
        ),
        schema=RiskReport,
        fallback=RiskReport(riskFacts="Risk analysis unavailable."),
    )
    return {"risk": report.model_dump()}


async def bull_node(state: AnalysisState) -> dict:
    report = await research_safe(
        system=P.BULL_SYSTEM,
        user=P.bull_user(
            state["action"], state["ticker"], state["position"],
            state.get("guidance"), state.get("current_strategy"),
        ),
        schema=BullCaseReport,
        fallback=BullCaseReport(coreThesis="Bull case unavailable."),
    )
    return {"bull_case": report.model_dump()}


async def bear_node(state: AnalysisState) -> dict:
    report = await research_safe(
        system=P.BEAR_SYSTEM,
        user=P.bear_user(
            state["action"], state["ticker"], state["position"],
            state.get("guidance"), state.get("current_strategy"),
        ),
        schema=BearCaseReport,
        fallback=BearCaseReport(coreConcern="Bear case unavailable."),
    )
    return {"bear_case": report.model_dump()}


# ── Coordinator helper used by full_report and deep_dive ────────────────────


def gather_specialist_reports(state: AnalysisState) -> dict:
    """Collect the specialist reports present in state for the coordinator."""
    keys = (
        "fundamentals", "technical", "sentiment", "macro", "risk",
        "bull_case", "bear_case", "debate",
    )
    return {k: state[k] for k in keys if state.get(k)}
