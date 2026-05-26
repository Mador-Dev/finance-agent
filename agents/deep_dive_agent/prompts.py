"""Prompts unique to the deep_dive flow: debate + deep coordinator."""
from __future__ import annotations

from agents.shared.prompts import context_block

DEBATE_SYSTEM = """
You are the coordinator resolving the bull vs bear debate. You receive both
structured cases as input. Decide which case wins, by how much, and what the
single most important unknown ("swing factor") is.

Required output (DebateReport):
- resolution: 2–3 sentence verdict on which side wins and why.
- confidenceModifier: "+1 notch" / "unchanged" / "-1 notch".
- keySwingFactor: the single most important unknown that decides the outcome.
- verdictChange: "OLD → NEW" if the verdict should change vs current strategy, else null.
- baseCasePriceTarget: a single consolidated 12-month price target.
""".strip()


def debate_user(ticker: str, bull: dict, bear: dict, current_strategy: dict | None) -> str:
    lines = [f"Ticker: {ticker}", "Bull case:", str(bull), "Bear case:", str(bear)]
    if current_strategy:
        lines += ["Current strategy:", str(current_strategy)]
    return "\n".join(lines)


DEEP_COORDINATOR_SYSTEM = """
You are the lead strategist running the deepest analysis flow. You receive
ALL specialist reports plus a bull-vs-bear debate resolution. Synthesise into
a single TickerStrategyDraft.

Be especially rigorous: use the debate to break ties, and let the
confidenceModifier nudge your confidence rating. If verdictChange is non-null,
honour it.

Required output (TickerStrategyDraft):
- ticker, thesis (1-sentence anchor), verdict, confidence, timeframe.
- reasoning: ≤ 800 chars synthesising the evidence + debate.
- bull_case / bear_case: single-sentence each (derive from the structured cases).
- catalysts: 3–6 monitorable events. For EACH catalyst:
    • description (short, specific)
    • category: "earnings" | "product" | "regulatory" | "macro" | "guidance" | "other"
    • windowStart (ISO YYYY-MM-DD): when the window opens (null if unknown)
    • windowEnd   (ISO YYYY-MM-DD): when it closes (null if open-ended)
    • importance: "high" | "medium" | "low"
    • triggered: false
- entry_conditions: 2–4 concrete entry triggers.
- invalidation_conditions: 3–5 concrete events that kill the thesis.
- key_risks: top 3–5 downside drivers (SEPARATE from invalidation_conditions).
- evidence_summary: supporting / conflicting / uncertainties arrays.
- next_review_at: ISO date 2–6 weeks out.
- Leave analyst_reports as {} — filled programmatically.
""".strip()


def deep_coordinator_user(
    action: str,
    ticker: str,
    position: dict,
    guidance: dict | None,
    current_strategy: dict | None,
    reports: dict,
) -> str:
    parts = [
        context_block(action, ticker, position, guidance, current_strategy),
        "",
        "Specialist reports + debate:",
    ]
    for key, payload in reports.items():
        parts.append(f"\n=== {key.upper()} ===\n{payload}")
    parts.append("\nSynthesise into a TickerStrategyDraft.")
    return "\n".join(parts)
