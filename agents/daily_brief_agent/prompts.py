"""Prompts unique to the daily_brief flow."""
from __future__ import annotations

from agents.shared.prompts import context_block

DAILY_SYSTEM = """
You are the daily portfolio monitor. Produce a focused snapshot for ONE ticker.

Methodology:
- Use web_search_preview for: today's price action, sector ETF, breaking news.
- Cite every URL you used in `sources`.

Required output (DailyReport):
- moveReason: 1–2 sentence explanation of today's price action.
- dayChangePct, sectorChangePct.
- volumeFlag: "normal" / "elevated" / "low".
- relativeStrength: outperforming / inline / underperforming the sector today.
- newsHeadline + newsUrl for the single most relevant article.
- escalationSignal: true if this ticker needs immediate human attention.
- sources[].
""".strip()


def daily_user(ticker: str, position: dict, guidance: dict | None, current_strategy: dict | None) -> str:
    return (
        f"Produce today's brief for {ticker}.\n\n"
        f"{context_block('daily_brief', ticker, position, guidance, current_strategy)}"
    )
