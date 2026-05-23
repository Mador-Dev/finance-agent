from __future__ import annotations

import uuid
from dataclasses import dataclass

from agents.app.db import execute, fetch_one


POINT_COSTS: dict[str, float] = {
    "chat_message": 25.0,
    "quick_check": 35.0,
    "deep_dive": 80.0,
    "daily_brief": 60.0,
    "full_report": 90.0,
    "bootstrap_per_ticker": 90.0,
}


class PointsBudgetExceededError(RuntimeError):
    pass


@dataclass(slots=True)
class BalanceSnapshot:
    daily_budget_points: float
    points_used: float
    points_remaining: float


def _round_points(value: float) -> float:
    return round(float(value), 3)


def _coerce_float(value: object, fallback: float = 0.0) -> float:
    try:
      parsed = float(value)
    except (TypeError, ValueError):
      return fallback
    return parsed


def get_effective_daily_budget(user_id: str) -> float:
    row = fetch_one(
        """
        SELECT
          u.daily_points_budget,
          (
            SELECT value
            FROM admin_defaults
            WHERE key = 'pointsBudget'
            LIMIT 1
          ) AS admin_points_budget
        FROM users u
        WHERE u.user_id = %s
        LIMIT 1
        """,
        (user_id,),
    )
    if row:
        user_budget = _coerce_float(row.get("daily_points_budget"), 0.0)
        if user_budget > 0:
            return _round_points(user_budget)
        admin_points_budget = row.get("admin_points_budget")
        if isinstance(admin_points_budget, dict):
            default_budget = _coerce_float(admin_points_budget.get("dailyBudgetPoints"), 500.0)
            if default_budget > 0:
                return _round_points(default_budget)
    return 500.0


def get_balance_snapshot(user_id: str) -> BalanceSnapshot:
    budget = get_effective_daily_budget(user_id)
    row = fetch_one(
        """
        SELECT
          COALESCE(SUM(CASE WHEN points_delta < 0 THEN -points_delta ELSE 0 END), 0) AS points_used,
          COALESCE(SUM(CASE WHEN points_delta > 0 THEN points_delta ELSE 0 END), 0) AS points_credits
        FROM user_points_ledger
        WHERE user_id = %s
          AND expires_at > NOW()
        """,
        (user_id,),
    ) or {}
    points_used = _round_points(_coerce_float(row.get("points_used"), 0.0))
    points_credits = _round_points(_coerce_float(row.get("points_credits"), 0.0))
    effective_budget = _round_points(budget + points_credits)
    points_remaining = _round_points(max(0.0, effective_budget - points_used))
    return BalanceSnapshot(
        daily_budget_points=effective_budget,
        points_used=points_used,
        points_remaining=points_remaining,
    )


def require_points(user_id: str, points: float, *, source: str, action: str, ref_id: str | None = None, note: str | None = None) -> None:
    required_points = _round_points(points)
    if required_points <= 0:
        return

    snapshot = get_balance_snapshot(user_id)
    if snapshot.points_remaining < required_points:
        raise PointsBudgetExceededError(
            f"Not enough points remaining for {action}: need {required_points:.3f}, have {snapshot.points_remaining:.3f}"
        )

    execute(
        """
        INSERT INTO user_points_ledger (
          id, user_id, points_delta, entry_type, source, action, ref_id, note, expires_at
        ) VALUES (
          %s, %s, %s, 'usage', %s, %s, %s, %s, NOW() + INTERVAL '24 hours'
        )
        """,
        (
            str(uuid.uuid4()),
            user_id,
            -required_points,
            source,
            action,
            ref_id,
            (note[:1000] if note else None),
        ),
    )
