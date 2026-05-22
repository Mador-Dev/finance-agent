from __future__ import annotations

import asyncio
from typing import Any

from agents.app.config import get_settings
from agents.app.schemas import (
    BootstrapJobResult,
    BootstrapJobState,
    BootstrapStartRequest,
    TickerStrategyDraft,
    utc_now,
)
from agents.app.storage import WorkspaceStore
from agents.bootstrap_agent import invoke_bootstrap_agent


class BootstrapService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.store = WorkspaceStore()
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def start_bootstrap(self, payload: BootstrapStartRequest) -> BootstrapJobState:
        ws = self.store.ensure_workspace(payload)
        job = self.store.create_job(payload)
        self.store.save_job_state(ws, job)
        self._tasks[job.jobId] = asyncio.create_task(self._run_job(payload, job))
        return job

    def get_job(self, user_id: str, job_id: str) -> BootstrapJobState:
        return self.store.load_job(user_id, job_id)

    def get_result(self, user_id: str, job_id: str) -> BootstrapJobResult:
        job = self.store.load_job(user_id, job_id)
        return self.store.build_result(job)

    async def _run_job(self, payload: BootstrapStartRequest, job: BootstrapJobState) -> None:
        ws = self.store.workspace(payload.userId)
        job.status = "running"
        job.startedAt = utc_now()
        self.store.save_job_state(ws, job)

        ticker_states = {item.ticker: item for item in job.tickers}
        position_lookup = self._position_lookup(payload.accounts)
        semaphore = asyncio.Semaphore(max(1, self.settings.bootstrap_max_concurrency))

        async def run_ticker(ticker: str) -> tuple[str, TickerStrategyDraft | None, str | None]:
            async with semaphore:
                ticker_state = ticker_states[ticker]
                ticker_state.status = "running"
                ticker_state.currentStep = "planner"
                job.currentTicker = ticker
                job.currentStep = "planner"
                self._refresh_job_progress(job)
                self.store.save_job_state(ws, job)
                try:
                    strategy = await invoke_bootstrap_agent(
                        self.settings,
                        ticker=ticker,
                        position_context=position_lookup[ticker],
                        guidance=payload.guidance.get(ticker),
                    )
                    ticker_state.currentStep = "synthesis"
                    self.store.save_job_state(ws, job)
                    return ticker, strategy, None
                except Exception as exc:  # pragma: no cover - runtime failure branch
                    return ticker, None, str(exc)

        results = await asyncio.gather(*(run_ticker(item.ticker) for item in job.tickers))

        strategies: list[TickerStrategyDraft] = []
        for ticker, strategy, error in results:
            state = ticker_states[ticker]
            if strategy is not None:
                state.status = "completed"
                state.currentStep = None
                state.strategy = strategy
                job.completedTickers.append(ticker)
                self.store.persist_ticker_strategy(ws, strategy)
                strategies.append(strategy)
            else:
                state.status = "failed"
                state.currentStep = None
                state.failureReason = error
                job.failedTickers.append(ticker)

            self._refresh_job_progress(job)
            self.store.save_job_state(ws, job)

        if job.failedTickers and job.completedTickers:
            job.status = "partial_completed"
        elif job.failedTickers:
            job.status = "failed"
            job.error = "All tickers failed during bootstrap." if len(job.failedTickers) == job.totalTickers else None
        else:
            job.status = "completed"

        job.currentTicker = None
        job.currentStep = None
        job.completedAt = utc_now()
        self._refresh_job_progress(job)
        self.store.save_job_state(ws, job)
        if strategies:
            self.store.persist_feed_index(ws, job, strategies)

    @staticmethod
    def _position_lookup(accounts: dict[str, list[Any]]) -> dict[str, dict[str, Any]]:
        lookup: dict[str, dict[str, Any]] = {}
        for account_name, positions in accounts.items():
            for position in positions:
                if position.ticker not in lookup:
                    payload = position.model_dump() if hasattr(position, "model_dump") else dict(position)
                    payload["account"] = account_name
                    lookup[position.ticker] = payload
        return lookup

    @staticmethod
    def _refresh_job_progress(job: BootstrapJobState) -> None:
        total_done = len(job.completedTickers) + len(job.failedTickers)
        job.progressPct = 0 if job.totalTickers == 0 else min(100, round((total_done / job.totalTickers) * 100))
