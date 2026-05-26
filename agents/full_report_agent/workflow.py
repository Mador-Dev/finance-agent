"""Full-report workflow — 5 specialists in parallel, then coordinator.

Graph:
    START → [fundamentals, technical, sentiment, macro, risk] (parallel)
          → coordinator → END
"""
from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.app.schemas import CoordinatorDraft, ResearchEvidence, TickerStrategyDraft, utc_now
from agents.full_report_agent.prompts import COORDINATOR_SYSTEM, coordinator_user
from agents.shared.research import synthesise_safe
from agents.shared.specialists import (
    fundamentals_node,
    gather_specialist_reports,
    macro_node,
    risk_node,
    sentiment_node,
    technical_node,
)
from agents.shared.state import AnalysisState

logger = logging.getLogger(__name__)

_SPECIALIST_KEYS = ("fundamentals", "technical", "sentiment", "macro", "risk")


async def _coordinator_node(state: AnalysisState) -> dict:
    reports = gather_specialist_reports(state)
    coordinator = await synthesise_safe(
        system=COORDINATOR_SYSTEM,
        user=coordinator_user(
            state["action"], state["ticker"], state["position"],
            state.get("guidance"), state.get("current_strategy"), reports,
        ),
        schema=CoordinatorDraft,
        fallback=CoordinatorDraft(
            ticker=state["ticker"].upper(),
            thesis="Synthesis unavailable; defaulting to HOLD.",
            verdict="HOLD",
            confidence="low",
            timeframe="months",
            reasoning=f"Coordinator synthesis failed at {utc_now()}.",
            evidence_summary=ResearchEvidence(),
        ),
    )
    draft = TickerStrategyDraft.from_coordinator(coordinator, reports)
    return {"strategy": draft}


def _build_graph() -> Any:
    g = StateGraph(AnalysisState)
    g.add_node("fundamentals", fundamentals_node)
    g.add_node("technical", technical_node)
    g.add_node("sentiment", sentiment_node)
    g.add_node("macro", macro_node)
    g.add_node("risk", risk_node)
    g.add_node("coordinator", _coordinator_node)
    for spec in _SPECIALIST_KEYS:
        g.add_edge(START, spec)
        g.add_edge(spec, "coordinator")
    g.add_edge("coordinator", END)
    return g.compile()


GRAPH = _build_graph()


async def invoke(
    *,
    ticker: str,
    position: dict,
    guidance: dict | None = None,
    current_strategy: dict | None = None,
    action: str = "full_report",
) -> TickerStrategyDraft:
    state: AnalysisState = {
        "action": action,
        "ticker": ticker.upper(),
        "position": position,
        "guidance": guidance,
        "current_strategy": current_strategy,
    }
    final = await GRAPH.ainvoke(state)
    return final["strategy"]
