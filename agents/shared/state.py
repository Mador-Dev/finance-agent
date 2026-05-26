"""Shared LangGraph state used by every agent workflow."""
from __future__ import annotations

from typing import TypedDict

from agents.app.schemas import TickerStrategyDraft


class AnalysisState(TypedDict, total=False):
    # ── Inputs (set by `invoke`) ─────────────────────────────────────────────
    action: str
    ticker: str
    position: dict
    guidance: dict | None
    current_strategy: dict | None

    # ── Specialist outputs (one key per specialist node) ─────────────────────
    fundamentals: dict
    technical: dict
    sentiment: dict
    macro: dict
    risk: dict
    bull_case: dict
    bear_case: dict
    debate: dict
    quick_check: dict
    daily: dict

    # ── Final synthesis ─────────────────────────────────────────────────────
    strategy: TickerStrategyDraft
