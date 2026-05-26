"""All Postgres data access for the agents service."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import timezone
from typing import Any

logger = logging.getLogger(__name__)

from agents.app.db import execute, fetch_all, fetch_one
from agents.app.schemas import (
    BootstrapJobState,
    BootstrapStartRequest,
    BootstrapTickerState,
    ChatMemoryEntry,
    ConversationHistory,
    JobProgress,
    JobRecord,
    JobsResponse,
    SavedConversation,
    TickerStrategyDraft,
    utc_now,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


_MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "sept": "09", "oct": "10",
    "nov": "11", "dec": "12",
}


def _to_iso_date(value: Any) -> str | None:
    """Coerce a loose date string into ISO `YYYY-MM-DD` or None.

    LLM-emitted dates often come as "February 2024", "Q1 2025", "8/14/2025",
    etc. We accept the common shapes and drop anything else so the DB never
    sees a malformed DATE.
    """
    import re

    if not isinstance(value, str):
        return None
    s = value.strip().replace(",", "")
    if not s:
        return None

    # ISO already (YYYY-MM-DD)
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})\b", s)
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        return f"{y}-{mo}-{d}"

    # ISO month-only (YYYY-MM) → first of month
    m = re.match(r"^(\d{4})-(\d{1,2})$", s)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-01"

    # US-style M/D/YYYY or D/M/YYYY (ambiguous — assume M/D/YYYY)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        mo, d, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        return f"{y}-{mo}-{d}"

    # "Month YYYY" or "Month DD YYYY"
    parts = s.lower().split()
    if parts and parts[0] in _MONTHS:
        mo = _MONTHS[parts[0]]
        if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 4:
            return f"{parts[1]}-{mo}-01"
        if len(parts) >= 3 and parts[1].isdigit() and parts[-1].isdigit() and len(parts[-1]) == 4:
            try:
                return f"{parts[-1]}-{mo}-{int(parts[1]):02d}"
            except ValueError:
                pass

    return None


def _normalise_catalyst(c: dict) -> dict:
    """Coerce free-form dates and back-fill windowEnd from legacy expiresAt."""
    window_start = _to_iso_date(c.get("windowStart"))
    window_end = _to_iso_date(c.get("windowEnd") or c.get("expiresAt"))
    return {
        "description": str(c.get("description", ""))[:300],
        "category": c.get("category") or "other",
        "windowStart": window_start,
        "windowEnd": window_end,
        "importance": c.get("importance") or "medium",
        # Keep `expiresAt` mirrored so older readers keep working.
        "expiresAt": window_end,
        "triggered": bool(c.get("triggered", False)),
    }


def _ts(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "strftime"):
        if hasattr(value, "tzinfo") and value.tzinfo is not None:
            return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value)


def _normalize_lifecycle(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    onboarding = raw.get("onboarding")
    if not isinstance(onboarding, dict):
        onboarding = {}
    return {
        "lastFullReportAt": raw.get("lastFullReportAt"),
        "lastDailyAt": raw.get("lastDailyAt"),
        "pendingDeepDives": list(raw.get("pendingDeepDives") or []),
        "bootstrapProgress": raw.get("bootstrapProgress"),
        "onboarding": {
            "portfolioSubmittedAt": onboarding.get("portfolioSubmittedAt"),
            "positionGuidanceStatus": onboarding.get("positionGuidanceStatus") or "not_started",
            "positionGuidance": onboarding.get("positionGuidance") if isinstance(onboarding.get("positionGuidance"), dict) else {},
        },
    }

# ── User / bootstrap ──────────────────────────────────────────────────────────


def upsert_user(user_id: str, display_name: str, schedule: dict, guidance: dict | None = None) -> None:
    current = fetch_one("SELECT lifecycle FROM users WHERE user_id = %s", (user_id,))
    lifecycle = _normalize_lifecycle(current.get("lifecycle") if current else None)
    onboarding = lifecycle["onboarding"]
    onboarding["portfolioSubmittedAt"] = onboarding.get("portfolioSubmittedAt") or utc_now()
    if guidance is not None:
        onboarding["positionGuidance"] = guidance
        onboarding["positionGuidanceStatus"] = "completed" if guidance else "skipped"
    execute(
        """
        INSERT INTO users (user_id, display_name, password_hash, schedule, lifecycle, state)
        VALUES (%s, %s, '', %s::jsonb, %s::jsonb, 'BOOTSTRAPPING')
        ON CONFLICT (user_id) DO UPDATE SET
          display_name = EXCLUDED.display_name,
          schedule = EXCLUDED.schedule,
          lifecycle = EXCLUDED.lifecycle,
          state = 'BOOTSTRAPPING',
          updated_at = NOW()
        """,
        (user_id, display_name, json.dumps(schedule), json.dumps(lifecycle)),
    )


def save_bootstrap_progress(user_id: str, total_tickers: int, completed_tickers: list[str]) -> None:
    row = fetch_one("SELECT lifecycle FROM users WHERE user_id = %s", (user_id,))
    lifecycle = _normalize_lifecycle(row.get("lifecycle") if row else None)
    lifecycle["bootstrapProgress"] = {
        "total": total_tickers,
        "completed": len(completed_tickers),
        "completedTickers": completed_tickers,
    }
    onboarding = lifecycle["onboarding"]
    if onboarding.get("positionGuidanceStatus") == "not_started":
        onboarding["positionGuidanceStatus"] = "completed" if onboarding.get("positionGuidance") else "skipped"
    execute(
        """
        UPDATE users
        SET state = 'BOOTSTRAPPING', lifecycle = %s::jsonb, updated_at = NOW()
        WHERE user_id = %s
        """,
        (json.dumps(lifecycle), user_id),
    )


def finish_bootstrap(user_id: str, completed_tickers: list[str], failed_tickers: list[str]) -> None:
    row = fetch_one("SELECT lifecycle FROM users WHERE user_id = %s", (user_id,))
    lifecycle = _normalize_lifecycle(row.get("lifecycle") if row else None)
    pending = set(lifecycle["pendingDeepDives"])
    pending.update(failed_tickers)
    lifecycle["pendingDeepDives"] = sorted(pending)
    lifecycle["bootstrapProgress"] = None
    onboarding = lifecycle["onboarding"]
    if onboarding.get("positionGuidanceStatus") == "not_started":
        onboarding["positionGuidanceStatus"] = "completed" if onboarding.get("positionGuidance") else "skipped"
    next_state = "ACTIVE" if completed_tickers else "INCOMPLETE"
    execute(
        """
        UPDATE users
        SET state = %s, lifecycle = %s::jsonb, updated_at = NOW()
        WHERE user_id = %s
        """,
        (next_state, json.dumps(lifecycle), user_id),
    )


def upsert_portfolio(user_id: str, body: dict) -> None:
    execute(
        """
        INSERT INTO user_portfolios (user_id, body, updated_at)
        VALUES (%s, %s::jsonb, NOW())
        ON CONFLICT (user_id) DO UPDATE SET body = EXCLUDED.body, updated_at = NOW()
        """,
        (user_id, json.dumps(body)),
    )


def load_portfolio(user_id: str) -> dict[str, list[dict]]:
    row = fetch_one("SELECT body FROM user_portfolios WHERE user_id = %s", (user_id,))
    if not row:
        return {}
    body = row["body"]
    accounts = body.get("accounts") if isinstance(body, dict) else {}
    return accounts if isinstance(accounts, dict) else {}


def load_position_lookup(user_id: str) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for account_name, positions in load_portfolio(user_id).items():
        if not isinstance(positions, list):
            continue
        for raw in positions:
            if not isinstance(raw, dict):
                continue
            ticker = str(raw.get("ticker", "")).strip().upper()
            if ticker and ticker not in lookup:
                lookup[ticker] = {**raw, "ticker": ticker, "account": account_name}
    return lookup


def load_guidance(user_id: str) -> dict[str, dict]:
    row = fetch_one("SELECT lifecycle FROM users WHERE user_id = %s", (user_id,))
    if not row or not row.get("lifecycle"):
        return {}
    lifecycle = row["lifecycle"]
    if not isinstance(lifecycle, dict):
        return {}
    onboarding = lifecycle.get("onboarding")
    if not isinstance(onboarding, dict):
        return {}
    guidance = onboarding.get("positionGuidance")
    return guidance if isinstance(guidance, dict) else {}


# ── Strategies ────────────────────────────────────────────────────────────────


def upsert_strategy(
    user_id: str,
    ticker: str,
    draft: TickerStrategyDraft,
    *,
    guidance_applied: bool,
    run_id: str | None = None,
    action: str | None = None,
) -> None:
    """Write the strategy row from a draft. Persists the new entity fields:
    thesis, key_risks (separate from avoid_conditions), evidence_summary,
    next_review_at, next_earnings_date, and per-kind staleness timestamps.
    """
    now = utc_now()
    catalysts = [_normalise_catalyst(c.model_dump()) for c in draft.catalysts]
    entry_conditions = list(draft.entry_conditions or [])[:5]
    exit_conditions = list(draft.invalidation_conditions or [])[:5]
    key_risks = list(draft.key_risks or [])[:8]
    avoid_conditions: list[str] = []  # reserved for explicit "don't add if X"
    evidence_summary = draft.evidence_summary.model_dump() if draft.evidence_summary else {}
    metadata = {
        "source": action or "analysis",
        "status": "provisional",
        "generatedAt": now,
        "userGuidanceApplied": guidance_applied,
    }
    # Pull nextEarningsDate from the fundamentals report when present.
    fundamentals = draft.analyst_reports.get("fundamentals") or {}
    next_earnings_raw = fundamentals.get("nextEarningsDate") if isinstance(fundamentals, dict) else None
    next_earnings_date = _to_iso_date(next_earnings_raw)
    # next_review_at is also LLM-emitted; sanitise it the same way.
    next_review_at = _to_iso_date(draft.next_review_at) if draft.next_review_at else None

    # Per-action staleness timestamps.
    last_deep_dive_at = now if action == "deep_dive" else None
    last_full_report_at = now if action in {"full_report", "deep_dive", "bootstrap"} else None
    last_quick_check_at = now if action == "quick_check" else None
    last_daily_brief_at = now if action == "daily_brief" else None

    execute(
        """
        INSERT INTO strategies (
          user_id, ticker, asset_scope, verdict, confidence, reasoning, timeframe,
          position_size_ils, position_weight_pct,
          entry_conditions, exit_conditions, catalysts,
          bull_case, bear_case, last_deep_dive_at, metadata,
          action_catalysts, avoid_conditions, asset_class, derived_from_run_id,
          thesis, key_risks, evidence_summary,
          last_full_report_at, last_quick_check_at, last_daily_brief_at,
          next_earnings_date, next_review_at
        ) VALUES (
          %s, %s, 'portfolio', %s, %s, %s, %s, 0, 0,
          %s::jsonb, %s::jsonb, %s::jsonb,
          %s, %s, %s, %s::jsonb,
          '[]'::jsonb, %s::jsonb, 'equity', %s,
          %s, %s::jsonb, %s::jsonb,
          %s, %s, %s,
          %s, %s
        )
        ON CONFLICT (user_id, ticker) DO UPDATE SET
          asset_scope = EXCLUDED.asset_scope,
          verdict = EXCLUDED.verdict,
          confidence = EXCLUDED.confidence,
          reasoning = EXCLUDED.reasoning,
          timeframe = EXCLUDED.timeframe,
          entry_conditions = EXCLUDED.entry_conditions,
          exit_conditions = EXCLUDED.exit_conditions,
          bull_case = EXCLUDED.bull_case,
          bear_case = EXCLUDED.bear_case,
          catalysts = EXCLUDED.catalysts,
          metadata = EXCLUDED.metadata,
          action_catalysts = EXCLUDED.action_catalysts,
          avoid_conditions = EXCLUDED.avoid_conditions,
          derived_from_run_id = EXCLUDED.derived_from_run_id,
          thesis = EXCLUDED.thesis,
          key_risks = EXCLUDED.key_risks,
          evidence_summary = EXCLUDED.evidence_summary,
          last_deep_dive_at = COALESCE(EXCLUDED.last_deep_dive_at, strategies.last_deep_dive_at),
          last_full_report_at = COALESCE(EXCLUDED.last_full_report_at, strategies.last_full_report_at),
          last_quick_check_at = COALESCE(EXCLUDED.last_quick_check_at, strategies.last_quick_check_at),
          last_daily_brief_at = COALESCE(EXCLUDED.last_daily_brief_at, strategies.last_daily_brief_at),
          next_earnings_date = COALESCE(EXCLUDED.next_earnings_date, strategies.next_earnings_date),
          next_review_at = COALESCE(EXCLUDED.next_review_at, strategies.next_review_at),
          version = strategies.version + 1,
          updated_at = NOW()
        """,
        (
            user_id, ticker.upper(),
            draft.verdict, draft.confidence, draft.reasoning, draft.timeframe,
            json.dumps(entry_conditions),
            json.dumps(exit_conditions),
            json.dumps(catalysts),
            draft.bull_case,
            draft.bear_case,
            last_deep_dive_at,
            json.dumps(metadata),
            json.dumps(avoid_conditions),
            run_id,
            draft.thesis,
            json.dumps(key_risks),
            json.dumps(evidence_summary),
            last_full_report_at,
            last_quick_check_at,
            last_daily_brief_at,
            next_earnings_date,
            next_review_at,
        ),
    )


def upsert_report_artifact(user_id: str, ticker: str, artifact_key: str, payload: dict) -> None:
    execute(
        """
        INSERT INTO report_artifacts (user_id, ticker, artifact_key, payload, updated_at)
        VALUES (%s, %s, %s, %s::jsonb, NOW())
        ON CONFLICT (user_id, ticker, artifact_key) DO UPDATE SET
          payload = EXCLUDED.payload, updated_at = NOW()
        """,
        (user_id, ticker.upper(), artifact_key, json.dumps(payload)),
    )


def list_strategies(user_id: str) -> list[dict]:
    rows = fetch_all(
        """
        SELECT ticker, verdict, confidence, reasoning, timeframe,
               bull_case, bear_case, catalysts, updated_at
        FROM strategies WHERE user_id = %s ORDER BY updated_at DESC
        """,
        (user_id,),
    )
    return [
        {
            "ticker": r["ticker"],
            "verdict": r["verdict"],
            "confidence": r["confidence"],
            "reasoning": r["reasoning"],
            "timeframe": r["timeframe"],
            "bullCase": r.get("bull_case"),
            "bearCase": r.get("bear_case"),
            "catalysts": r.get("catalysts") or [],
            "updatedAt": _ts(r.get("updated_at")),
        }
        for r in rows
    ]


def load_strategy(user_id: str, ticker: str) -> dict | None:
    s = fetch_one(
        """
        SELECT ticker, verdict, confidence, reasoning, timeframe,
               bull_case, bear_case, catalysts, exit_conditions, updated_at
        FROM strategies WHERE user_id = %s AND ticker = %s
        """,
        (user_id, ticker.upper()),
    )
    if not s:
        return None
    return {
        "ticker": s["ticker"],
        "verdict": s["verdict"],
        "confidence": s["confidence"],
        "reasoning": s["reasoning"],
        "timeframe": s["timeframe"],
        "bullCase": s.get("bull_case"),
        "bearCase": s.get("bear_case"),
        "catalysts": s.get("catalysts") or [],
        "exitConditions": s.get("exit_conditions") or [],
        "updatedAt": _ts(s.get("updated_at")),
    }


def load_active_user_schedules() -> list[tuple[str, dict]]:
    rows = fetch_all("SELECT user_id, schedule FROM users WHERE state = 'ACTIVE'")
    return [(r["user_id"], r["schedule"] or {}) for r in rows]


def was_daily_brief_run_today(user_id: str) -> bool:
    """True if a daily_brief is already pending/running/done within the last 23 hours."""
    row = fetch_one(
        """
        SELECT 1 FROM jobs
        WHERE user_id = %s
          AND action = 'daily_brief'
          AND status IN ('pending', 'running', 'completed', 'partial_completed')
          AND triggered_at > NOW() - INTERVAL '23 hours'
        LIMIT 1
        """,
        (user_id,),
    )
    return row is not None


def list_report_summaries(user_id: str, limit: int = 5) -> list[dict]:
    """Returns recent strategy rows as context for the next analysis run."""
    rows = fetch_all(
        """
        SELECT ticker, verdict, confidence, reasoning, timeframe,
               bull_case, bear_case, catalysts, updated_at
        FROM strategies
        WHERE user_id = %s
        ORDER BY updated_at DESC LIMIT %s
        """,
        (user_id, limit),
    )
    return [
        {
            "ticker": r["ticker"],
            "verdict": r["verdict"],
            "confidence": r["confidence"],
            "reasoning": r["reasoning"],
            "timeframe": r["timeframe"],
            "bullCase": r.get("bull_case"),
            "bearCase": r.get("bear_case"),
            "catalysts": r.get("catalysts") or [],
            "updatedAt": _ts(r.get("updated_at")),
        }
        for r in rows
    ]


# ── Analysis runs ─────────────────────────────────────────────────────────────


def create_analysis_run(job_id: str, user_id: str, ticker: str, run_type: str) -> str:
    row = fetch_one(
        """
        INSERT INTO analysis_runs (job_id, user_id, ticker, run_type, status, started_at)
        VALUES (%s, %s, %s, %s, 'running', NOW())
        RETURNING id
        """,
        (job_id, user_id, ticker.upper(), run_type),
    )
    if not row:
        raise RuntimeError(f"Failed to create analysis_run for {ticker}")
    return str(row["id"])


def complete_analysis_run(run_id: str, status: str) -> None:
    execute(
        "UPDATE analysis_runs SET status = %s, completed_at = NOW() WHERE id = %s",
        (status, run_id),
    )


# ── Analyst reports ───────────────────────────────────────────────────────────


def write_analyst_reports(
    user_id: str,
    ticker: str,
    run_id: str,
    action: str,
    strategy: TickerStrategyDraft,
) -> None:
    """Write analyst_report rows from a completed strategy draft.

    The "strategy" overview row is no longer written — the strategies table is
    the single source of truth for the strategy overview. Each row written here
    is one structured specialist payload per analyst_type.

      quick_check  → "quick_check"
      daily_brief  → "daily"
      full_report  → "fundamentals", "technical", "sentiment", "macro", "risk"
      deep_dive    → full_report + "bull_case", "bear_case", "debate"
    """
    ar = strategy.analyst_reports

    if action == "quick_check":
        qc = ar.get("quick_check")
        if isinstance(qc, dict) and qc:
            _insert_analyst_report(run_id, user_id, ticker, "quick_check", qc)
        return

    if action == "daily_brief":
        daily = ar.get("daily")
        if isinstance(daily, dict) and daily:
            _insert_analyst_report(run_id, user_id, ticker, "daily", daily)
        return

    if action in {"full_report", "deep_dive", "bootstrap"}:
        for analyst_type in ("fundamentals", "technical", "sentiment", "macro", "risk"):
            payload = ar.get(analyst_type)
            if isinstance(payload, dict) and payload:
                _insert_analyst_report(run_id, user_id, ticker, analyst_type, payload)

        if action == "deep_dive":
            for analyst_type in ("bull_case", "bear_case", "debate"):
                payload = ar.get(analyst_type)
                if isinstance(payload, dict) and payload:
                    _insert_analyst_report(run_id, user_id, ticker, analyst_type, payload)


def _derive_health_score(strategy: TickerStrategyDraft) -> int:
    """Compute a 0-100 health score from top-level strategy fields as a fallback."""
    score = 80
    if strategy.verdict in {"SELL", "CLOSE"}:
        score -= 40
    elif strategy.verdict == "REDUCE":
        score -= 20
    elif strategy.verdict in {"BUY", "ADD"}:
        score += 10
    if strategy.confidence == "low":
        score -= 15
    elif strategy.confidence == "high":
        score += 5
    if len(strategy.key_risks) >= 3:
        score -= 5
    return max(0, min(100, score))


def _insert_analyst_report(
    run_id: str, user_id: str, ticker: str, analyst_type: str, payload: dict
) -> None:
    execute(
        """
        INSERT INTO analyst_reports (analysis_run_id, user_id, ticker, analyst_type, payload, generated_at)
        VALUES (%s, %s, %s, %s, %s::jsonb, NOW())
        """,
        (run_id, user_id, ticker.upper(), analyst_type, json.dumps(payload)),
    )


# ── Feed items ────────────────────────────────────────────────────────────────


def insert_feed_item(
    job: JobRecord,
    strategies: list[TickerStrategyDraft],
    completed: list[str],
) -> None:
    """Write a feed_items row when a job completes so the feed can read it directly.

    Each action kind produces a different entry shape:
      quick_check → compact: score, decision, key_alerts, day_change_pct
      daily_brief → compact: move_reason, day_change_pct, needs_escalation, deep_dive_queued
      full_report → full: analystTypes list (no bull/bear), hasBullCase=False
      deep_dive   → full: analystTypes + hasBullCase/hasBearCase from structured reports
    """
    if not completed:
        return

    action = job.action
    tickers = [s.ticker.strip().upper() for s in strategies]

    entries: dict[str, Any] = {}
    for strategy in strategies:
        ticker = strategy.ticker.strip().upper()
        ar = strategy.analyst_reports

        # Base fields — present for all report kinds
        entry: dict[str, Any] = {
            "ticker": ticker,
            "mode": action,
            "verdict": strategy.verdict,
            "confidence": strategy.confidence,
            "reasoning": strategy.reasoning,
            "timeframe": strategy.timeframe,
            "analystTypes": [],
            "hasBullCase": False,
            "hasBearCase": False,
        }

        if action == "quick_check":
            # New camelCase keys from the LangGraph QuickCheckReport schema.
            qc = ar.get("quick_check") or {}
            entry["analystTypes"] = ["quick_check"]
            entry["healthScore"] = qc.get("score") or _derive_health_score(strategy)
            entry["decision"] = qc.get("decision") or (
                "escalate" if strategy.verdict in {"REDUCE", "SELL", "CLOSE"} else "safe"
            )
            entry["keyAlerts"] = qc.get("thesisHealth") or qc.get("strategy_health") or []
            entry["dayChangePct"] = qc.get("dayChangePct") or qc.get("day_change_pct")
            entry["newsHeadline"] = qc.get("newsHeadline") or qc.get("news_headline")

        elif action == "daily_brief":
            # New camelCase keys from the LangGraph DailyReport schema.
            daily = ar.get("daily") or {}
            entry["analystTypes"] = ["daily"]
            entry["moveReason"] = (
                daily.get("moveReason") or daily.get("move_reason") or strategy.reasoning[:200]
            )
            entry["dayChangePct"] = daily.get("dayChangePct") or daily.get("day_change_pct")
            entry["sectorChangePct"] = daily.get("sectorChangePct")
            entry["relativeStrength"] = daily.get("relativeStrength")
            entry["newsHeadline"] = daily.get("newsHeadline") or daily.get("news_headline")
            entry["newsUrl"] = daily.get("newsUrl") or daily.get("news_url")
            entry["volumeFlag"] = daily.get("volumeFlag", daily.get("volume_flag", "normal"))
            entry["needsEscalation"] = bool(
                daily.get("escalationSignal")
                or daily.get("escalation_signal")
                or strategy.verdict in {"REDUCE", "SELL", "CLOSE"}
            )
            entry["escalationReason"] = (
                strategy.key_risks[0] if entry["needsEscalation"] and strategy.key_risks else None
            )
            entry["deepDiveQueued"] = bool(entry["needsEscalation"])

        elif action == "full_report":
            # Five analyst tabs; no bull/bear
            entry["analystTypes"] = [
                k for k in ("fundamentals", "technical", "sentiment", "macro", "risk")
                if isinstance(ar.get(k), dict) and ar[k]
            ]
            entry["hasBullCase"] = False
            entry["hasBearCase"] = False

        elif action == "deep_dive":
            # Full analysis + structured bull/bear debate
            entry["analystTypes"] = [
                k for k in ("fundamentals", "technical", "sentiment", "macro", "risk")
                if isinstance(ar.get(k), dict) and ar[k]
            ]
            has_bull = isinstance(ar.get("bull_case"), dict) and bool(ar["bull_case"])
            has_bear = isinstance(ar.get("bear_case"), dict) and bool(ar["bear_case"])
            # Fall back to string-level bull/bear
            if not has_bull and strategy.bull_case:
                has_bull = True
            if not has_bear and strategy.bear_case:
                has_bear = True
            entry["hasBullCase"] = has_bull
            entry["hasBearCase"] = has_bear
            # Include debate resolution if available — new camelCase keys.
            debate = ar.get("debate")
            if isinstance(debate, dict):
                entry["debateResolution"] = debate.get("resolution")
                entry["keySwingFactor"] = debate.get("keySwingFactor") or debate.get("key_swing_factor")

        entries[ticker] = entry

    highlights = [
        f"{s.ticker.upper()} {s.verdict} ({s.confidence})"
        for s in strategies[:3]
    ]

    title, summary, kind, tone = _feed_item_meta(action, tickers, strategies, completed)

    # Build dailyBrief batch-level metadata from aggregated strategy data
    daily_brief: dict[str, Any] | None = None
    if action == "daily_brief":
        escalated_count = sum(1 for e in entries.values() if e.get("needsEscalation"))
        movers = [
            f"{e['ticker']} {'+' if (e.get('dayChangePct') or 0) > 0 else ''}{(e.get('dayChangePct') or 0):.1f}%"
            for e in entries.values()
            if e.get("dayChangePct") is not None
        ][:4]
        # Collect macro views from strategies (first one with macro data)
        macro_view: str | None = None
        tomorrow_watch: str | None = None
        for s in strategies:
            macro = s.analyst_reports.get("macro") or {}
            if isinstance(macro, dict) and macro.get("macroView"):
                macro_view = str(macro["macroView"])[:200]
                break
        # "tomorrow" — upcoming catalysts from strategies
        upcoming = []
        for s in strategies:
            for cat in s.catalysts[:1]:
                upcoming.append(f"{s.ticker}: {cat.description[:60]}")
        if upcoming:
            tomorrow_watch = "; ".join(upcoming[:3])

        daily_brief = {
            "headline": summary,
            "today": "; ".join(movers) if movers else "; ".join(highlights[:3]),
            "tomorrow": tomorrow_watch,
            "marketView": macro_view,
            "securityNote": f"{escalated_count} position{'s' if escalated_count != 1 else ''} flagged for attention." if escalated_count else None,
            "dashboardPath": "/reports",
        }

    payload = {
        "mode": action,
        "entries": entries,
        "dailyBrief": daily_brief,
    }

    item_id = job.id
    execute(
        """
        INSERT INTO feed_items (id, user_id, job_id, kind, title, summary, tone, tickers, highlights, payload)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
        ON CONFLICT (id) DO UPDATE SET
          summary = EXCLUDED.summary, payload = EXCLUDED.payload, tone = EXCLUDED.tone
        """,
        (
            item_id, job.user_id, job.id, kind, title, summary, tone,
            tickers,
            json.dumps(highlights),
            json.dumps(payload),
        ),
    )


def _feed_item_meta(
    action: str,
    tickers: list[str],
    strategies: list[TickerStrategyDraft],
    completed: list[str],
) -> tuple[str, str, str, str]:
    """Returns (title, summary, kind, tone) for a feed item."""
    count = len(completed)
    primary = tickers[0] if tickers else "position"

    has_negative = any(s.verdict in {"REDUCE", "SELL", "CLOSE"} for s in strategies)
    has_positive = any(s.verdict in {"BUY", "ADD"} for s in strategies)

    if action == "daily_brief":
        title = "Daily brief"
        escalated = sum(1 for s in strategies if s.verdict in {"REDUCE", "SELL", "CLOSE"})
        summary = (
            f"{escalated} position{'s' if escalated != 1 else ''} flagged — closer look recommended."
            if escalated else
            f"Portfolio steady across {count} position{'s' if count != 1 else ''}."
        )
        kind = "daily_brief"
        tone = "rose" if has_negative else "sky"

    elif action == "quick_check":
        title = f"{primary} · Quick check"
        qc = strategies[0].analyst_reports.get("quick_check") if strategies else {}
        decision = (qc or {}).get("decision", "safe") if isinstance(qc, dict) else "safe"
        summary = (
            strategies[0].reasoning[:160]
            if strategies else f"Quick check completed for {primary}."
        )
        kind = "quick_check"
        tone = "rose" if decision == "escalate" else ("amber" if decision == "watch" else "emerald")

    elif action == "deep_dive":
        title = f"{primary} · Deep dive"
        summary = (
            strategies[0].thesis[:180]
            if strategies and strategies[0].thesis else
            strategies[0].reasoning[:180] if strategies else f"Deep dive completed for {primary}."
        )
        kind = "deep_dive"
        tone = "rose" if has_negative else ("emerald" if has_positive else "amber")

    elif action == "full_report":
        title = "Full report"
        summary = (
            f"{count} position{'s' if count != 1 else ''} refreshed — "
            f"{sum(1 for s in strategies if s.verdict in {'BUY','ADD'})} positive, "
            f"{sum(1 for s in strategies if s.verdict in {'REDUCE','SELL','CLOSE'})} flagged."
        )
        kind = "report"
        tone = "rose" if has_negative else ("emerald" if has_positive else "amber")

    else:
        title = action.replace("_", " ").title()
        summary = f"Analysis completed across {count} ticker{'s' if count != 1 else ''}."
        kind = "report"
        tone = "rose" if has_negative else ("emerald" if has_positive else "amber")

    return title, summary, kind, tone


# ── Bootstrap jobs ────────────────────────────────────────────────────────────


def create_bootstrap_job(user_id: str, payload: BootstrapStartRequest) -> BootstrapJobState:
    tickers = sorted({
        position.ticker
        for positions in payload.accounts.values()
        for position in positions
    })
    now = utc_now()
    job_id = f"job_py_bootstrap_{user_id}_{now.replace(':', '').replace('-', '')}"
    job = BootstrapJobState(
        jobId=job_id, userId=user_id, status="pending", createdAt=now,
        totalTickers=len(tickers),
        tickers=[BootstrapTickerState(ticker=t) for t in tickers],
    )
    execute(
        """
        INSERT INTO jobs (id, user_id, action, status, source, model_tier, triggered_at, result)
        VALUES (%s, %s, 'full_report', 'pending', 'bootstrap', 'balanced', NOW(), %s::jsonb)
        ON CONFLICT (id) DO NOTHING
        """,
        (job_id, user_id, json.dumps(job.model_dump())),
    )
    return job


def save_bootstrap_job(job: BootstrapJobState) -> None:
    execute(
        """
        UPDATE jobs SET status = %s, started_at = %s, completed_at = %s,
          failure_reason = %s, result = %s::jsonb
        WHERE id = %s
        """,
        (
            job.status, job.startedAt, job.completedAt, job.error,
            json.dumps(job.model_dump()), job.jobId,
        ),
    )


def load_bootstrap_job(user_id: str, job_id: str) -> BootstrapJobState:
    row = fetch_one("SELECT result FROM jobs WHERE id = %s AND user_id = %s", (job_id, user_id))
    if not row or not row.get("result"):
        raise FileNotFoundError(f"Bootstrap job not found: {job_id}")
    payload = row["result"]
    if not isinstance(payload, dict):
        raise FileNotFoundError(f"Bootstrap job not found: {job_id}")

    raw_tickers = payload.get("tickers")
    normalized_tickers: list[dict[str, Any]] = []
    if isinstance(raw_tickers, list):
        for item in raw_tickers:
            if isinstance(item, dict):
                ticker_value = item.get("ticker")
                if isinstance(ticker_value, str) and ticker_value.strip():
                    normalized_tickers.append({**item, "ticker": ticker_value.strip().upper()})
            elif isinstance(item, str):
                ticker = item.strip().upper()
                if ticker:
                    normalized_tickers.append({"ticker": ticker, "status": "pending"})
    payload["tickers"] = normalized_tickers

    for key in ("completedTickers", "failedTickers"):
        raw_values = payload.get(key)
        normalized_values: list[str] = []
        if isinstance(raw_values, list):
          for item in raw_values:
              if isinstance(item, str):
                  ticker = item.strip().upper()
                  if ticker:
                      normalized_values.append(ticker)
              elif isinstance(item, dict):
                  ticker_value = item.get("ticker")
                  if isinstance(ticker_value, str):
                      ticker = ticker_value.strip().upper()
                      if ticker:
                          normalized_values.append(ticker)
        payload[key] = normalized_values

    current_ticker = payload.get("currentTicker")
    if isinstance(current_ticker, str):
        payload["currentTicker"] = current_ticker.strip().upper() or None

    return BootstrapJobState.model_validate(payload)


def find_active_bootstrap_job(user_id: str) -> BootstrapJobState | None:
    row = fetch_one(
        """
        SELECT result
        FROM jobs
        WHERE user_id = %s
          AND source = 'bootstrap'
          AND action = 'full_report'
          AND status IN ('pending', 'running')
        ORDER BY triggered_at DESC
        LIMIT 1
        """,
        (user_id,),
    )
    if not row or not row.get("result"):
        return None
    payload = row["result"]
    if not isinstance(payload, dict):
        return None

    raw_tickers = payload.get("tickers")
    normalized_tickers: list[dict[str, Any]] = []
    if isinstance(raw_tickers, list):
        for item in raw_tickers:
            if isinstance(item, dict):
                ticker_value = item.get("ticker")
                if isinstance(ticker_value, str) and ticker_value.strip():
                    normalized_tickers.append({**item, "ticker": ticker_value.strip().upper()})
            elif isinstance(item, str):
                ticker = item.strip().upper()
                if ticker:
                    normalized_tickers.append({"ticker": ticker, "status": "pending"})
    payload["tickers"] = normalized_tickers

    for key in ("completedTickers", "failedTickers"):
        raw_values = payload.get(key)
        normalized_values: list[str] = []
        if isinstance(raw_values, list):
            for item in raw_values:
                if isinstance(item, str):
                    ticker = item.strip().upper()
                    if ticker:
                        normalized_values.append(ticker)
                elif isinstance(item, dict):
                    ticker_value = item.get("ticker")
                    if isinstance(ticker_value, str):
                        ticker = ticker_value.strip().upper()
                        if ticker:
                            normalized_values.append(ticker)
        payload[key] = normalized_values

    current_ticker = payload.get("currentTicker")
    if isinstance(current_ticker, str):
        payload["currentTicker"] = current_ticker.strip().upper() or None

    return BootstrapJobState.model_validate(payload)


# ── Analysis jobs ─────────────────────────────────────────────────────────────


def create_job_from_record(job: JobRecord) -> None:
    """Persist a pre-built JobRecord to the database (called from background task)."""
    extra = {
        "ticker": job.ticker,
        "tickers": job.tickers,
        "progress": job.progress.model_dump() if job.progress else None,
    }
    execute(
        """
        INSERT INTO jobs (id, user_id, action, status, source, model_tier, triggered_at, result)
        VALUES (%s, %s, %s, %s, 'dashboard_action', 'balanced', NOW(), %s::jsonb)
        ON CONFLICT (id) DO UPDATE SET
          status = EXCLUDED.status, result = EXCLUDED.result
        """,
        (job.id, job.user_id, job.action, job.status, json.dumps(extra)),
    )


def create_job(user_id: str, action: str, ticker: str | None, tickers: list[str]) -> JobRecord:
    job_id = f"job_py_{uuid.uuid4().hex[:12]}"
    progress = JobProgress(
        pct=0, currentTicker=ticker, currentStep="queued",
        completedTickers=[], remainingTickers=tickers.copy(),
        totalTickers=len(tickers), completedSteps=0, totalSteps=len(tickers),
    )
    job = JobRecord(
        id=job_id, action=action, ticker=ticker, status="pending",
        triggered_at=utc_now(), user_id=user_id, tickers=tickers, progress=progress,
    )
    extra = {"ticker": ticker, "tickers": tickers, "progress": progress.model_dump()}
    execute(
        """
        INSERT INTO jobs (id, user_id, action, status, source, model_tier, triggered_at, result)
        VALUES (%s, %s, %s, 'pending', 'dashboard_action', 'balanced', NOW(), %s::jsonb)
        ON CONFLICT (id) DO UPDATE SET
          status = EXCLUDED.status, result = EXCLUDED.result
        """,
        (job_id, user_id, action, json.dumps(extra)),
    )
    return job


def write_job(job: JobRecord) -> None:
    extra = {
        "ticker": job.ticker,
        "tickers": job.tickers,
        "progress": job.progress.model_dump() if job.progress else None,
        "result": job.result,
    }
    execute(
        """
        UPDATE jobs SET status = %s, started_at = %s, completed_at = %s,
          failure_reason = %s, result = %s::jsonb
        WHERE id = %s
        """,
        (job.status, job.started_at, job.completed_at, job.error, json.dumps(extra), job.id),
    )


def read_job(user_id: str, job_id: str) -> JobRecord:
    row = fetch_one(
        "SELECT id, user_id, action, status, triggered_at, started_at, completed_at, failure_reason, result, source FROM jobs WHERE id = %s AND user_id = %s",
        (job_id, user_id),
    )
    if not row:
        raise FileNotFoundError(f"Job not found: {job_id}")
    return _row_to_job(row)


def list_jobs(user_id: str, limit: int = 50) -> JobsResponse:
    rows = fetch_all(
        "SELECT id, user_id, action, status, triggered_at, started_at, completed_at, failure_reason, result, source FROM jobs WHERE user_id = %s ORDER BY triggered_at DESC LIMIT %s",
        (user_id, limit),
    )
    jobs = []
    for r in rows:
        try:
            jobs.append(_row_to_job(r))
        except Exception:
            logger.exception("Failed to deserialize job row id=%s; skipping", r.get("id"))
    return JobsResponse(jobs=jobs)


def _row_to_job(row: dict) -> JobRecord:
    extra = row.get("result") or {}
    if not isinstance(extra, dict):
        extra = {}
    progress_raw = extra.get("progress")
    progress = JobProgress.model_validate(progress_raw) if progress_raw else None
    tickers: list[str] = []
    raw_tickers = extra.get("tickers")
    if isinstance(raw_tickers, list):
        for item in raw_tickers:
            if isinstance(item, str):
                ticker = item.strip().upper()
                if ticker:
                    tickers.append(ticker)
            elif isinstance(item, dict):
                ticker_value = item.get("ticker")
                if isinstance(ticker_value, str):
                    ticker = ticker_value.strip().upper()
                    if ticker:
                        tickers.append(ticker)
    return JobRecord(
        id=row["id"],
        action=row["action"],
        ticker=extra.get("ticker"),
        status=row["status"],
        triggered_at=_ts(row["triggered_at"]) or utc_now(),
        started_at=_ts(row.get("started_at")),
        completed_at=_ts(row.get("completed_at")),
        result=extra.get("result"),
        error=row.get("failure_reason"),
        progress=progress,
        source=row.get("source"),
        user_id=row["user_id"],
        tickers=tickers,
    )


# ── Conversations ─────────────────────────────────────────────────────────────


def create_conversation(user_id: str, title: str | None) -> SavedConversation:
    conv_id = str(uuid.uuid4())
    execute(
        "INSERT INTO conversations (id, user_id, title) VALUES (%s, %s, %s)",
        (conv_id, user_id, title),
    )
    return SavedConversation(id=conv_id, userId=user_id, title=title, createdAt=utc_now())


def list_conversations(user_id: str, limit: int, offset: int) -> list[SavedConversation]:
    rows = fetch_all(
        "SELECT id, user_id, title, created_at FROM conversations WHERE user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
        (user_id, limit, offset),
    )
    return [_row_to_conversation(r) for r in rows]


def load_conversation(user_id: str, conv_id: str) -> ConversationHistory:
    row = fetch_one(
        "SELECT id, user_id, title, created_at FROM conversations WHERE id = %s AND user_id = %s",
        (conv_id, user_id),
    )
    if not row:
        raise FileNotFoundError(f"Conversation not found: {conv_id}")
    memory_rows = fetch_all(
        "SELECT id, conversation_id, sequence_number, role, content FROM chat_memory WHERE conversation_id = %s ORDER BY sequence_number",
        (conv_id,),
    )
    return ConversationHistory(
        conversation=_row_to_conversation(row),
        turns=[_row_to_memory(r) for r in memory_rows],
    )


def append_message(conv_id: str, role: str, content: str) -> ChatMemoryEntry:
    entry_id = str(uuid.uuid4())
    row = fetch_one(
        "INSERT INTO chat_memory (id, conversation_id, role, content) VALUES (%s, %s, %s, %s) RETURNING id, conversation_id, sequence_number, role, content",
        (entry_id, conv_id, role, content),
    )
    if not row:
        raise RuntimeError("Failed to insert chat memory entry")
    return _row_to_memory(row)


def rename_conversation(user_id: str, conv_id: str, title: str) -> SavedConversation:
    execute(
        "UPDATE conversations SET title = %s WHERE id = %s AND user_id = %s",
        (title, conv_id, user_id),
    )
    row = fetch_one(
        "SELECT id, user_id, title, created_at FROM conversations WHERE id = %s AND user_id = %s",
        (conv_id, user_id),
    )
    if not row:
        raise FileNotFoundError(f"Conversation not found: {conv_id}")
    return _row_to_conversation(row)


def archive_conversation(user_id: str, conv_id: str) -> SavedConversation:
    row = fetch_one(
        "SELECT id, user_id, title, created_at FROM conversations WHERE id = %s AND user_id = %s",
        (conv_id, user_id),
    )
    if not row:
        raise FileNotFoundError(f"Conversation not found: {conv_id}")
    execute("DELETE FROM conversations WHERE id = %s AND user_id = %s", (conv_id, user_id))
    return _row_to_conversation(row)


def _row_to_conversation(row: dict) -> SavedConversation:
    return SavedConversation(
        id=str(row["id"]),
        userId=row["user_id"],
        title=row.get("title"),
        createdAt=_ts(row.get("created_at")) or utc_now(),
    )


def _row_to_memory(row: dict) -> ChatMemoryEntry:
    return ChatMemoryEntry(
        id=str(row["id"]),
        conversationId=str(row["conversation_id"]),
        sequenceNumber=row["sequence_number"],
        role=row["role"],
        content=row["content"],
    )
