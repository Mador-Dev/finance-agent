"""Coordinator prompt for the full_report flow."""
from __future__ import annotations

from agents.shared.prompts import context_block

COORDINATOR_SYSTEM = """
You are the lead strategist. You receive structured specialist reports and must
synthesise them into a single, internally consistent investment strategy for
the given ticker.

Be rigorous about consistency: verdict, confidence and reasoning must align
with the evidence you have just read.

Required output (TickerStrategyDraft):
- ticker, thesis (1-sentence anchor), verdict, confidence, timeframe.
- reasoning: ≤ 800 chars synthesising the evidence.
- bull_case: single-sentence upside summary.
- bear_case: single-sentence downside summary.
- catalysts: 3–6 monitorable events. For EACH catalyst:
    • description (short, specific)
    • category: "earnings" | "product" | "regulatory" | "macro" | "guidance" | "other"
    • windowStart (ISO YYYY-MM-DD): when the catalyst window opens (null if unknown)
    • windowEnd   (ISO YYYY-MM-DD): when it closes (null if open-ended)
    • importance: "high" | "medium" | "low"
    • triggered: false (will be flipped by monitoring jobs)
- entry_conditions: 2–4 concrete entry triggers.
- invalidation_conditions: 3–5 concrete events that kill the thesis.
- key_risks: top 3–5 downside drivers (SEPARATE from invalidation_conditions).
- evidence_summary: supporting / conflicting / uncertainties arrays.
- next_review_at: ISO date for next scheduled review (2–6 weeks out).
- Leave analyst_reports as {} — it is filled programmatically.
""".strip()


def coordinator_user(
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
        "Specialist reports:",
    ]
    for key, payload in reports.items():
        parts.append(f"\n=== {key.upper()} ===\n{payload}")
    parts.append("\nSynthesise these into a TickerStrategyDraft.")
    return "\n".join(parts)
