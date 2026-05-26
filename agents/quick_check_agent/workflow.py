"""Quick-check workflow — coordinator-only, no specialist fan-out.

Graph:
    START → quick_check → synth → END

The `quick_check` node runs a fast web-search turn (price + breaking news).
The `synth` node projects the QuickCheckReport into a TickerStrategyDraft.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.app.schemas import (
    CatalystExpiryCheck,
    QuickCheckReport,
    ResearchEvidence,
    TickerStrategyDraft,
)
from agents.quick_check_agent.prompts import QUICK_CHECK_SYSTEM, quick_check_user
from agents.shared.research import research_safe
from agents.shared.state import AnalysisState


async def _quick_check_node(state: AnalysisState) -> dict:
    report = await research_safe(
        system=QUICK_CHECK_SYSTEM,
        user=quick_check_user(
            state["ticker"], state["position"],
            state.get("guidance"), state.get("current_strategy"),
        ),
        schema=QuickCheckReport,
        fallback=QuickCheckReport(
            score=50, decision="watch",
            advisorSummary="Quick check unavailable.",
            catalystExpiryCheck=CatalystExpiryCheck(),
        ),
    )
    return {"quick_check": report.model_dump()}


async def _synth_node(state: AnalysisState) -> dict:
    qc = state.get("quick_check", {})
    score = int(qc.get("score") or 50)
    decision = qc.get("decision") or "watch"
    verdict = "REDUCE" if decision == "escalate" else "HOLD"
    confidence = "high" if score >= 80 else "medium" if score >= 50 else "low"
    draft = TickerStrategyDraft(
        ticker=state["ticker"].upper(),
        thesis=(qc.get("advisorSummary") or "Thesis check.")[:280],
        verdict=verdict,
        confidence=confidence,
        timeframe="months",
        reasoning=(qc.get("advisorSummary") or "")[:800],
        key_risks=list(qc.get("thesisHealth") or [])[:5],
        evidence_summary=ResearchEvidence(
            supporting=list(qc.get("advisorReasons") or [])[:5]
        ),
        analyst_reports={"quick_check": qc},
    )
    return {"strategy": draft}


def _build_graph() -> Any:
    g = StateGraph(AnalysisState)
    g.add_node("quick_check", _quick_check_node)
    g.add_node("synth", _synth_node)
    g.add_edge(START, "quick_check")
    g.add_edge("quick_check", "synth")
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
        "action": "quick_check",
        "ticker": ticker.upper(),
        "position": position,
        "guidance": guidance,
        "current_strategy": current_strategy,
    }
    final = await GRAPH.ainvoke(state)
    return final["strategy"]
