from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.app.config import get_settings
from agents.app.schemas import (
    BootstrapJobResult,
    BootstrapJobState,
    BootstrapStartRequest,
    BootstrapTickerState,
    TickerStrategyDraft,
    utc_now,
)
from agents.app.workspace import WorkspacePaths, build_workspace


class WorkspaceStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.users_dir = self.settings.resolved_users_dir

    def workspace(self, user_id: str) -> WorkspacePaths:
        return build_workspace(self.users_dir, user_id)

    def ensure_workspace(self, payload: BootstrapStartRequest) -> WorkspacePaths:
        ws = self.workspace(payload.userId)
        portfolio_body = {
            "meta": {
                "currency": payload.currency,
                "transactionFeeILS": payload.transactionFeeILS,
                "note": payload.note,
            },
            "accounts": {
                account: [position.model_dump() for position in positions]
                for account, positions in payload.accounts.items()
            },
        }
        if self.settings.database_url:
            from agents.app.pg_store import (
                upsert_bootstrap_lifecycle,
                upsert_persona,
                upsert_portfolio,
            )

            upsert_portfolio(payload.userId, portfolio_body)
            upsert_bootstrap_lifecycle(
                payload.userId,
                payload.displayName or payload.userId,
                payload.schedule.model_dump(),
            )
            upsert_persona(
                payload.userId,
                (
                    f"# Investor Profile\n\n"
                    f"Display name: {payload.displayName or payload.userId}\n\n"
                    "## Bootstrap guidance\n"
                    "Managed by the Python bootstrap agents service.\n"
                ),
            )
            return ws

        for directory in [
            ws.root,
            ws.data_dir,
            ws.jobs_dir,
            ws.reports_dir,
            ws.report_index_dir,
            ws.tickers_dir,
            ws.chat_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

        self._write_json(
            ws.config_file,
            {
                "modelProfile": "python-bootstrap",
                "plan": "pro",
            },
        )
        self._write_json(
            ws.profile_file,
            {
                "userId": payload.userId,
                "displayName": payload.displayName or payload.userId,
                "telegramChatId": None,
                "schedule": payload.schedule.model_dump(),
                "createdAt": utc_now(),
            },
        )
        self._write_json(ws.portfolio_file, portfolio_body)
        self._write_json(
            ws.state_file,
            {
                "userId": payload.userId,
                "state": "INCOMPLETE",
                "lastFullReportAt": None,
                "lastDailyAt": None,
                "pendingDeepDives": [],
                "bootstrapProgress": None,
                "onboarding": {
                    "portfolioSubmittedAt": utc_now(),
                    "positionGuidanceStatus": "completed" if payload.guidance else "skipped",
                    "positionGuidance": {
                        ticker: guidance.model_dump() for ticker, guidance in payload.guidance.items()
                    },
                },
            },
        )
        if not ws.user_md_file.exists():
            ws.user_md_file.write_text(
                (
                    f"# Investor Profile\n"
                    f"# Generated: {utc_now()}\n\n"
                    f"Display name: {payload.displayName or payload.userId}\n\n"
                    "## Bootstrap guidance\n"
                    "This workspace is managed by the Python bootstrap agents service.\n"
                ),
                encoding="utf-8",
            )
        return ws

    def create_job(self, payload: BootstrapStartRequest) -> BootstrapJobState:
        tickers = sorted(
            {
                position.ticker
                for positions in payload.accounts.values()
                for position in positions
            }
        )
        job_id = f"job_py_bootstrap_{payload.userId}_{utc_now().replace(':', '').replace('-', '')}"
        job = BootstrapJobState(
            jobId=job_id,
            userId=payload.userId,
            status="pending",
            createdAt=utc_now(),
            totalTickers=len(tickers),
            tickers=[BootstrapTickerState(ticker=ticker) for ticker in tickers],
        )
        ws = self.workspace(payload.userId)
        self._write_json(
            ws.state_file,
            {
                **self.read_json(ws.state_file, default={}),
                "state": "BOOTSTRAPPING",
                "bootstrapProgress": {
                    "total": len(tickers),
                    "completed": 0,
                    "completedTickers": [],
                },
            },
        )
        self._write_json(
            ws.reports_dir / "full_report_state.json",
            self._build_full_report_state(job),
        )
        self._write_json(
            ws.job_file(job_id),
            {
                "id": job.jobId,
                "action": "full_report",
                "ticker": None,
                "source": "dashboard_action",
                "budget_admitted_at": utc_now(),
                "status": "pending",
                "triggered_at": job.createdAt,
                "started_at": None,
                "completed_at": None,
                "result": {},
                "error": None,
            },
        )
        return job

    def load_job(self, user_id: str, job_id: str) -> BootstrapJobState:
        ws = self.workspace(user_id)
        raw = self.read_json(ws.reports_dir / "bootstrap_job_state.json", default=None)
        if raw and raw.get("jobId") == job_id:
            return BootstrapJobState.model_validate(raw)

        legacy = self.read_json(ws.jobs_dir / f"{job_id}.state.json", default=None)
        if legacy:
            return BootstrapJobState.model_validate(legacy)

        full_report_state = self.read_json(ws.reports_dir / "full_report_state.json", default=None)
        if full_report_state and full_report_state.get("jobId") == job_id:
            tickers = [
                BootstrapTickerState(
                    ticker=item["ticker"],
                    status=item["status"],
                    currentStep=item.get("currentStep"),
                    failureReason=item.get("failureReason"),
                )
                for item in full_report_state.get("tickers", [])
            ]
            return BootstrapJobState(
                jobId=job_id,
                userId=user_id,
                status=full_report_state["status"],
                createdAt=full_report_state["triggeredAt"],
                startedAt=full_report_state.get("startedAt"),
                completedAt=full_report_state.get("completedAt"),
                progressPct=self._calc_pct(
                    len(full_report_state.get("completedTickers", []))
                    + len(full_report_state.get("failedTickers", [])),
                    full_report_state.get("totalTickers", len(tickers)),
                ),
                totalTickers=full_report_state.get("totalTickers", len(tickers)),
                completedTickers=full_report_state.get("completedTickers", []),
                failedTickers=full_report_state.get("failedTickers", []),
                currentTicker=full_report_state.get("currentTicker"),
                currentStep=full_report_state.get("currentStep"),
                tickers=tickers,
                error=full_report_state.get("failureReason"),
            )
        raise FileNotFoundError(f"Bootstrap job not found: {job_id}")

    def save_job_state(self, ws: WorkspacePaths, job: BootstrapJobState) -> None:
        self._write_json(ws.reports_dir / "bootstrap_job_state.json", job.model_dump())
        self._write_json(ws.jobs_dir / f"{job.jobId}.state.json", job.model_dump())
        self._write_json(ws.reports_dir / "full_report_state.json", self._build_full_report_state(job))
        self._write_json(
            ws.state_file,
            {
                **self.read_json(ws.state_file, default={}),
                "state": "ACTIVE" if job.status in {"completed", "partial_completed"} else "BOOTSTRAPPING",
                "lastFullReportAt": job.completedAt if job.status in {"completed", "partial_completed"} else None,
                "bootstrapProgress": {
                    "total": job.totalTickers,
                    "completed": len(job.completedTickers),
                    "completedTickers": job.completedTickers,
                },
            },
        )
        self._write_json(
            ws.job_file(job.jobId),
            {
                "id": job.jobId,
                "action": "full_report",
                "ticker": None,
                "source": "dashboard_action",
                "budget_admitted_at": job.startedAt or job.createdAt,
                "status": "running" if job.status == "running" else job.status,
                "triggered_at": job.createdAt,
                "started_at": job.startedAt,
                "completed_at": job.completedAt,
                "result": {
                    "totalTickers": job.totalTickers,
                    "completedTickers": job.completedTickers,
                    "failedTickers": job.failedTickers,
                },
                "error": job.error,
            },
        )
        self._write_json(
            ws.reports_dir / "progress.json",
            {
                "startedAt": job.startedAt or job.createdAt,
                "totalTickers": job.totalTickers,
                "completed": job.completedTickers,
                "failed": job.failedTickers,
                "remaining": [
                    item.ticker
                    for item in job.tickers
                    if item.status not in {"completed", "failed"}
                ],
            },
        )

    def persist_ticker_strategy(self, ws: WorkspacePaths, strategy: TickerStrategyDraft) -> None:
        if self.settings.database_url:
            from agents.app.pg_store import upsert_report_artifact, upsert_strategy_row

            upsert_strategy_row(ws.user_id, strategy.ticker, strategy.model_dump())
            for name in ("fundamentals", "sentiment", "risk", "debate", "bull_case", "bear_case"):
                payload = strategy.analyst_reports.get(name)
                if payload:
                    upsert_report_artifact(ws.user_id, strategy.ticker, name, payload)
            upsert_report_artifact(
                ws.user_id,
                strategy.ticker,
                "strategy",
                {
                    "ticker": strategy.ticker,
                    "thesis": strategy.thesis,
                    "verdict": strategy.verdict,
                    "confidence": strategy.confidence,
                    "reasoning": strategy.reasoning,
                },
            )
            return

        ticker_dir = ws.tickers_dir / strategy.ticker
        report_dir = ws.reports_dir / strategy.ticker
        ticker_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)

        strategy_payload = {
            "ticker": strategy.ticker,
            "updatedAt": utc_now(),
            "version": 1,
            "verdict": strategy.verdict,
            "confidence": strategy.confidence,
            "reasoning": strategy.reasoning,
            "timeframe": strategy.timeframe,
            "positionSizeILS": 0,
            "positionWeightPct": 0,
            "entryConditions": [],
            "exitConditions": strategy.invalidation_conditions[:5],
            "catalysts": [item.model_dump() for item in strategy.catalysts],
            "bullCase": strategy.bull_case,
            "bearCase": strategy.bear_case,
            "lastDeepDiveAt": utc_now(),
            "deepDiveTriggeredBy": "full_report",
            "metadata": {
                "source": "full_report",
                "status": "validated",
                "generatedAt": utc_now(),
                "userGuidanceApplied": True,
            },
            "actionCatalysts": [item.model_dump() for item in strategy.catalysts],
            "avoidConditions": strategy.key_risks[:8],
            "nextReviewAt": None,
        }
        self._write_json(ws.strategy_file(strategy.ticker), strategy_payload)
        self._write_json(
            ws.report_file(strategy.ticker, "strategy"),
            {
                "ticker": strategy.ticker,
                "thesis": strategy.thesis,
                "verdict": strategy.verdict,
                "confidence": strategy.confidence,
                "catalysts": [item.model_dump() for item in strategy.catalysts],
                "timeframe": strategy.timeframe,
                "reasoning": strategy.reasoning,
                "key_risks": strategy.key_risks,
                "invalidation_conditions": strategy.invalidation_conditions,
                "bull_case": strategy.bull_case,
                "bear_case": strategy.bear_case,
                "evidence_summary": strategy.evidence_summary.model_dump(),
            },
        )
        self._write_json(
            ws.report_file(strategy.ticker, "synthesis"),
            {
                "ticker": strategy.ticker,
                "thesis": strategy.thesis,
                "verdict": strategy.verdict,
                "confidence": strategy.confidence,
                "catalysts": [item.model_dump() for item in strategy.catalysts],
                "reasoning": strategy.reasoning,
            },
        )

        analyst_reports = strategy.analyst_reports
        for name in ("fundamentals", "sentiment", "risk", "debate", "bull_case", "bear_case"):
            payload = analyst_reports.get(name)
            if payload:
                file_name = name
                self._write_json(ws.report_file(strategy.ticker, file_name), payload)

    def persist_feed_index(self, ws: WorkspacePaths, job: BootstrapJobState, strategies: list[TickerStrategyDraft]) -> None:
        entries = {}
        for strategy in strategies:
            entries[strategy.ticker] = {
                "ticker": strategy.ticker,
                "mode": "full_report",
                "verdict": strategy.verdict,
                "confidence": strategy.confidence,
                "reasoning": strategy.reasoning,
                "timeframe": strategy.timeframe,
                "analystTypes": ["fundamentals", "sentiment", "risk"],
                "hasBullCase": bool(strategy.bull_case),
                "hasBearCase": bool(strategy.bear_case),
                "actionCatalysts": [item.model_dump() for item in strategy.catalysts],
                "avoidConditions": strategy.key_risks,
            }

        batch_id = f"batch_{job.jobId}_full_report"
        meta = {
            "totalBatches": 1,
            "totalPages": 1,
            "lastUpdated": job.completedAt,
            "newestBatchId": batch_id,
            "pageSize": 10,
        }
        page = {
            "page": 1,
            "totalPages": 1,
            "batches": [
                {
                    "batchId": batch_id,
                    "triggeredAt": job.completedAt or job.createdAt,
                    "date": (job.completedAt or job.createdAt)[:10],
                    "mode": "full_report",
                    "tickers": [item.ticker for item in strategies],
                    "tickerCount": len(strategies),
                    "jobId": job.jobId,
                    "entries": entries,
                }
            ],
        }
        self._write_json(ws.report_index_dir / "meta.json", meta)
        self._write_json(ws.report_index_dir / "page-001.json", page)

    def build_result(self, job: BootstrapJobState) -> BootstrapJobResult:
        strategies = [item.strategy for item in job.tickers if item.strategy is not None]
        return BootstrapJobResult(
            jobId=job.jobId,
            userId=job.userId,
            status=job.status,
            strategies=strategies,
            completedAt=job.completedAt,
        )

    @staticmethod
    def read_json(path: Path, default: Any = None) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return default

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _calc_pct(completed: int, total: int) -> int:
        if total <= 0:
            return 0
        return min(100, round((completed / total) * 100))

    def _build_full_report_state(self, job: BootstrapJobState) -> dict[str, Any]:
        report_status = "completed" if job.status == "partial_completed" else ("running" if job.status == "pending" else job.status)
        return {
            "version": 1,
            "jobId": job.jobId,
            "status": report_status,
            "triggeredAt": job.createdAt,
            "startedAt": job.startedAt,
            "updatedAt": utc_now(),
            "completedAt": job.completedAt,
            "totalTickers": job.totalTickers,
            "completedTickers": job.completedTickers,
            "failedTickers": job.failedTickers,
            "remainingTickers": [
                item.ticker
                for item in job.tickers
                if item.status not in {"completed", "failed"}
            ],
            "currentTicker": job.currentTicker,
            "currentStep": job.currentStep,
            "completedSteps": len(job.completedTickers),
            "totalSteps": job.totalTickers,
            "failureReason": job.error,
            "tickers": [
                {
                    "ticker": item.ticker,
                    "status": item.status,
                    "completedSteps": 1 if item.status == "completed" else 0,
                    "totalSteps": 1,
                    "currentStep": item.currentStep,
                    "strategyReady": item.strategy is not None,
                    "baselineTrust": "validated" if item.status == "completed" else "provisional",
                    "failureReason": item.failureReason,
                }
                for item in job.tickers
            ],
        }
