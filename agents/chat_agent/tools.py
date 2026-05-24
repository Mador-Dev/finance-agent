from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from agents.app import store as _store


def _cfg(config: RunnableConfig) -> dict:
    """Return the configurable dict from a RunnableConfig, never raising."""
    return config.get("configurable") or {}


@tool
def get_portfolio(config: RunnableConfig) -> dict:
    """Return the current workspace portfolio."""
    user_id: str = _cfg(config)["user_id"]
    return _store.load_portfolio(user_id)


@tool
def get_strategies(config: RunnableConfig) -> list:
    """Return current per-ticker strategies."""
    user_id: str = _cfg(config)["user_id"]
    return _store.list_strategies(user_id)


@tool
def get_recent_reports(config: RunnableConfig) -> list:
    """Return recent report summaries."""
    user_id: str = _cfg(config)["user_id"]
    return _store.list_report_summaries(user_id, limit=6)


@tool
def trigger_quick_check(ticker: str, config: RunnableConfig) -> dict:
    """Trigger a quick check for one ticker."""
    cfg = _cfg(config)
    jobs = cfg["jobs_service"]
    return jobs.trigger_from_chat(cfg["user_id"], "quick_check", ticker.strip().upper())


@tool
def trigger_deep_dive(ticker: str, config: RunnableConfig) -> dict:
    """Trigger a deep dive for one ticker."""
    cfg = _cfg(config)
    jobs = cfg["jobs_service"]
    return jobs.trigger_from_chat(cfg["user_id"], "deep_dive", ticker.strip().upper())


@tool
def trigger_daily_brief(config: RunnableConfig) -> dict:
    """Trigger a daily brief for the current workspace."""
    cfg = _cfg(config)
    jobs = cfg["jobs_service"]
    return jobs.trigger_from_chat(cfg["user_id"], "daily_brief", None)


CHAT_TOOLS = [
    get_portfolio,
    get_strategies,
    get_recent_reports,
    trigger_quick_check,
    trigger_deep_dive,
    trigger_daily_brief,
]
