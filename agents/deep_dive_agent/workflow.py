"""Deep-dive workflow — 5 specialists + bull/bear in parallel, debate, coordinator.

Graph:
    START → [fundamentals, technical, sentiment, macro, risk, bull, bear] (parallel)
    bull, bear → debate
    [fundamentals, technical, sentiment, macro, risk, debate] → coordinator → END
"""
from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.app.schemas import (
    CoordinatorDraft,
    DebateReport,
    ResearchEvidence,
    TickerStrategyDraft,
    utc_now,
)
from agents.deep_dive_agent.prompts import (
    DEBATE_SYSTEM,
    DEEP_COORDINATOR_SYSTEM,
    debate_user,
    deep_coordinator_user,
)
from agents.shared.research import synthesise_safe
from agents.shared.specialists import (
    bear_node,
    bull_node,
    fundamentals_node,
    gather_specialist_reports,
    macro_node,
    risk_node,
    sentiment_node,
    technical_node,
)
from agents.shared.state import AnalysisState

logger = logging.getLogger(__name__)

_ANALYST_KEYS = ("fundamentals", "technical", "sentiment", "macro", "risk")


async def _debate_node(state: AnalysisState) -> dict:
    report = await synthesise_safe(
        system=DEBATE_SYSTEM,
        user=debate_user(
            state["ticker"], state.get("bull_case", {}), state.get("bear_case", {}),
            state.get("current_strategy"),
        ),
        schema=DebateReport,
        fallback=DebateReport(resolution="Debate inconclusive."),
    )
    return {"debate": report.model_dump()}


async def _coordinator_node(state: AnalysisState) -> dict:
    reports = gather_specialist_reports(state)
    coordinator = await synthesise_safe(
        system=DEEP_COORDINATOR_SYSTEM,
        user=deep_coordinator_user(
            state["action"], state["ticker"], state["position"],
            state.get("guidance"), state.get("current_strategy"), reports,
        ),
        schema=CoordinatorDraft,
        fallback=CoordinatorDraft(
            ticker=state["ticker"].upper(),
            thesis="Deep-dive synthesis unavailable.",
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
    # Five analyst specialists.
    for name, fn in (
        ("fundamentals", fundamentals_node),
        ("technical", technical_node),
        ("sentiment", sentiment_node),
        ("macro", macro_node),
        ("risk", risk_node),
        ("bull", bull_node),
        ("bear", bear_node),
        ("debate", _debate_node),
        ("coordinator", _coordinator_node),
    ):
        g.add_node(name, fn)

    # Parallel fan-out: all analysts + bull + bear from START.
    for spec in (*_ANALYST_KEYS, "bull", "bear"):
        g.add_edge(START, spec)
    # bull + bear converge at the debate.
    g.add_edge("bull", "debate")
    g.add_edge("bear", "debate")
    # Analysts and debate all feed the coordinator.
    for spec in (*_ANALYST_KEYS, "debate"):
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
) -> TickerStrategyDraft:
    state: AnalysisState = {
        "action": "deep_dive",
        "ticker": ticker.upper(),
        "position": position,
        "guidance": guidance,
        "current_strategy": current_strategy,
    }
    final = await GRAPH.ainvoke(state)
    return final["strategy"]
