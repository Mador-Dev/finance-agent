"""Minimal Postgres helpers — shared connection pool, no ORM."""

from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from agents.app.config import get_settings


def _url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("APP_DATABASE_URL is required")
    return url


_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(_url(), min_size=2, max_size=10, open=True)
    return _pool


def execute(sql: str, params: tuple = ()) -> None:
    with _get_pool().connection() as conn:
        conn.execute(sql, params)
        conn.commit()


def fetch_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    with _get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def fetch_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with _get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
