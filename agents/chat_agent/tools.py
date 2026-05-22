from __future__ import annotations

from typing import Any, Callable


def build_chat_tools(
    *,
    load_portfolio: Callable[[], dict[str, Any]],
    load_strategies: Callable[[], list[dict[str, Any]]],
    load_reports: Callable[[], list[dict[str, Any]]],
    trigger_job: Callable[[str, str | None], dict[str, Any]],
) -> list[Any]:
    def get_portfolio() -> dict[str, Any]:
        """Return the current workspace portfolio."""
        return load_portfolio()

    def get_strategies() -> list[dict[str, Any]]:
        """Return current per-ticker strategies."""
        return load_strategies()

    def get_recent_reports() -> list[dict[str, Any]]:
        """Return recent report summaries."""
        return load_reports()

    def trigger_quick_check(ticker: str) -> dict[str, Any]:
        """Trigger a quick check for one ticker."""
        return trigger_job("quick_check", ticker.strip().upper())

    def trigger_deep_dive(ticker: str) -> dict[str, Any]:
        """Trigger a deep dive for one ticker."""
        return trigger_job("deep_dive", ticker.strip().upper())

    def trigger_daily_brief() -> dict[str, Any]:
        """Trigger a daily brief for the current workspace."""
        return trigger_job("daily_brief", None)

    return [
        get_portfolio,
        get_strategies,
        get_recent_reports,
        trigger_quick_check,
        trigger_deep_dive,
        trigger_daily_brief,
    ]
