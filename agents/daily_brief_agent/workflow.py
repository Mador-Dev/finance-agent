"""Daily-brief workflow — single research turn, no specialists.

Graph:
    START → daily → synth → END
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.app.schemas import (
    DailyReport,
    ResearchEvidence,
    StrategyCatalyst,
    TickerStrategyDraft,
)
from agents.daily_brief_agent.prompts import DAILY_SYSTEM, daily_user
from agents.shared.research import research_safe
from agents.shared.state import AnalysisState


async def _daily_node(state: AnalysisState) -> dict:
    report = await research_safe(
        system=DAILY_SYSTEM,
        user=daily_user(
            state["ticker"], state["position"],
            state.get("guidance"), state.get("current_strategy"),
        ),
        schema=DailyReport,
        fallback=DailyReport(moveReason="Daily brief unavailable."),
    )
    return {"daily": report.model_dump()}


async def _synth_node(state: AnalysisState) -> dict:
    d = state.get("daily", {})
    escalated = bool(d.get("escalationSignal"))
    verdict = "REDUCE" if escalated else "HOLD"
    catalysts: list[StrategyCatalyst] = []
    if d.get("newsHeadline"):
        catalysts.append(StrategyCatalyst(description=d["newsHeadline"][:300]))
    draft = TickerStrategyDraft(
        ticker=state["ticker"].upper(),
        thesis=(d.get("moveReason") or "Daily monitoring.")[:280],
        verdict=verdict,
        confidence="medium",
        timeframe="months",
        reasoning=(d.get("moveReason") or "")[:800],
        catalysts=catalysts,
        evidence_summary=ResearchEvidence(),
        analyst_reports={"daily": d},
    )
    return {"strategy": draft}


def _build_graph() -> Any:
    g = StateGraph(AnalysisState)
    g.add_node("daily", _daily_node)
    g.add_node("synth", _synth_node)
    g.add_edge(START, "daily")
    g.add_edge("daily", "synth")
    g.add_edge("synth", END)
    return g.compile()


GRAPH = _build_graph()


async def invoke(
    *,
    ticker: str,
    position: dict,
    guidance: dict | None = None,
    current_strategy: dict | None = None,
) -> TickerStrategyDraft:
    state: AnalysisState = {
        "action": "daily_brief",
        "ticker": ticker.upper(),
        "position": position,
        "guidance": guidance,
        "current_strategy": current_strategy,
    }
    final = await GRAPH.ainvoke(state)
    return final["strategy"]
