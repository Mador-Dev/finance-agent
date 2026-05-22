"""Postgres-backed persistence for the agents service (no users/ workspace)."""

from __future__ import annotations

import json
from typing import Any

from agents.app.config import get_settings


def _connection():
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for agents Postgres store")
    import psycopg

    return psycopg.connect(settings.database_url)


def upsert_portfolio(user_id: str, body: dict[str, Any]) -> None:
    with _connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_portfolios (user_id, body, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                  body = EXCLUDED.body,
                  updated_at = NOW()
                """,
                (user_id, json.dumps(body)),
            )
        conn.commit()


def upsert_report_artifact(
    user_id: str, ticker: str, artifact_key: str, payload: dict[str, Any]
) -> None:
    with _connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO report_artifacts (user_id, ticker, artifact_key, payload, updated_at)
                VALUES (%s, %s, %s, %s::jsonb, NOW())
                ON CONFLICT (user_id, ticker, artifact_key) DO UPDATE SET
                  payload = EXCLUDED.payload,
                  updated_at = NOW()
                """,
                (user_id, ticker.upper(), artifact_key, json.dumps(payload)),
            )
        conn.commit()


def upsert_persona(user_id: str, persona_md: str) -> None:
    with _connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (user_id, display_name, password_hash, persona_md)
                VALUES (%s, %s, '', %s)
                ON CONFLICT (user_id) DO UPDATE SET
                  persona_md = EXCLUDED.persona_md,
                  updated_at = NOW()
                """,
                (user_id, user_id, persona_md),
            )
        conn.commit()


def upsert_bootstrap_lifecycle(user_id: str, display_name: str, schedule: dict[str, Any]) -> None:
    lifecycle = {
        "lastFullReportAt": None,
        "lastDailyAt": None,
        "pendingDeepDives": [],
        "bootstrapProgress": None,
        "onboarding": {"portfolioSubmittedAt": None, "positionGuidanceStatus": "not_started", "positionGuidance": {}},
    }
    with _connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
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
        conn.commit()


def upsert_strategy_row(user_id: str, ticker: str, draft: dict[str, Any]) -> None:
    """Minimal strategy upsert from bootstrap draft — full shape filled by backend later."""
    with _connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO strategies (
                  user_id, ticker, verdict, confidence, reasoning, timeframe,
                  position_size_ils, position_weight_pct
                ) VALUES (%s, %s, %s, %s, %s, %s, 0, 0)
                ON CONFLICT (user_id, ticker) DO UPDATE SET
                  verdict = EXCLUDED.verdict,
                  confidence = EXCLUDED.confidence,
                  reasoning = EXCLUDED.reasoning,
                  timeframe = EXCLUDED.timeframe,
                  updated_at = NOW()
                """,
                (
                    user_id,
                    ticker.upper(),
                    draft.get("verdict", "HOLD"),
                    draft.get("confidence", "low"),
                    draft.get("reasoning", "Bootstrap draft"),
                    draft.get("timeframe", "undefined"),
                ),
            )
        conn.commit()
