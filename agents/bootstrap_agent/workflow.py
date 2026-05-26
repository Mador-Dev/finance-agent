"""Bootstrap workflow — initial strategy seeding for a new ticker.

Conceptually bootstrap is a full_report run on a brand-new position: same
depth (5 specialists + coordinator), no `current_strategy` to compare
against, and `metadata.source = "bootstrap"`. We therefore reuse the
full_report graph directly and just relabel the action.
"""
from __future__ import annotations

from agents.app.schemas import TickerStrategyDraft
from agents.full_report_agent.workflow import GRAPH
from agents.shared.state import AnalysisState

__all__ = ["GRAPH", "invoke"]


async def invoke(
    *,
    ticker: str,
    position: dict,
    guidance: dict | None = None,
) -> TickerStrategyDraft:
    """Run the bootstrap flow for ONE ticker."""
    state: AnalysisState = {
        "action": "bootstrap",
        "ticker": ticker.upper(),
        "position": position,
        "guidance": guidance,
        # No `current_strategy` — this is the first analysis.
        "current_strategy": None,
    }
    final = await GRAPH.ainvoke(state)
    return final["strategy"]
