from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from agents.app.config import get_settings
from agents.app.schemas import (
    ConversationHistory,
    ConversationTurn,
    JobProgress,
    JobRecord,
    JobsResponse,
    SavedConversation,
    utc_now,
)
from agents.app.workspace import WorkspacePaths, build_workspace


class RuntimeStore:
    def __init__(self) -> None:
        self.users_dir = get_settings().resolved_users_dir

    def workspace(self, user_id: str) -> WorkspacePaths:
        return build_workspace(self.users_dir, user_id)

    def ensure_runtime_dirs(self, user_id: str) -> WorkspacePaths:
        ws = self.workspace(user_id)
        for directory in [ws.root, ws.data_dir, ws.jobs_dir, ws.reports_dir, ws.report_index_dir, ws.tickers_dir, ws.chat_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        return ws

    def require_workspace(self, user_id: str) -> WorkspacePaths:
        ws = self.workspace(user_id)
        if not ws.root.exists():
            raise FileNotFoundError(f"Workspace not found for user: {user_id}")
        self.ensure_runtime_dirs(user_id)
        return ws

    def load_portfolio_accounts(self, user_id: str) -> dict[str, list[dict[str, Any]]]:
        ws = self.require_workspace(user_id)
        payload = self.read_json(ws.portfolio_file, default={})
        accounts = payload.get("accounts")
        return accounts if isinstance(accounts, dict) else {}

    def load_position_lookup(self, user_id: str) -> dict[str, dict[str, Any]]:
        lookup: dict[str, dict[str, Any]] = {}
        for account_name, positions in self.load_portfolio_accounts(user_id).items():
            if not isinstance(positions, list):
                continue
            for raw in positions:
                if not isinstance(raw, dict):
                    continue
                ticker = str(raw.get("ticker", "")).strip().upper()
                if ticker and ticker not in lookup:
                    lookup[ticker] = {**raw, "ticker": ticker, "account": account_name}
        return lookup

    def load_guidance(self, user_id: str) -> dict[str, dict[str, Any]]:
        ws = self.require_workspace(user_id)
        payload = self.read_json(ws.state_file, default={})
        onboarding = payload.get("onboarding")
        if not isinstance(onboarding, dict):
            return {}
        guidance = onboarding.get("positionGuidance")
        return guidance if isinstance(guidance, dict) else {}

    def load_strategy_snapshot(self, user_id: str, ticker: str) -> dict[str, Any] | None:
        ws = self.require_workspace(user_id)
        payload = self.read_json(ws.strategy_file(ticker), default=None)
        return payload if isinstance(payload, dict) else None

    def list_report_summaries(self, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        ws = self.require_workspace(user_id)
        items: list[dict[str, Any]] = []
        for report_path in sorted(ws.reports_dir.glob("*/*.json"), reverse=True):
            if report_path.name in {"strategy.json", "synthesis.json"}:
                payload = self.read_json(report_path, default=None)
                if isinstance(payload, dict):
                    items.append(payload)
            if len(items) >= limit:
                break
        return items

    def create_job(self, user_id: str, action: str, ticker: str | None, tickers: list[str]) -> JobRecord:
        ws = self.require_workspace(user_id)
        job = JobRecord(
            id=f"job_py_{uuid.uuid4().hex[:12]}",
            action=action,
            ticker=ticker,
            status="pending",
            triggered_at=utc_now(),
            user_id=user_id,
            tickers=tickers,
            progress=JobProgress(
                pct=0,
                currentTicker=ticker,
                currentStep="queued",
                completedTickers=[],
                remainingTickers=tickers.copy(),
                totalTickers=len(tickers),
                completedSteps=0,
                totalSteps=len(tickers),
            ),
        )
        self.write_job(ws, job)
        return job

    def write_job(self, ws: WorkspacePaths, job: JobRecord) -> None:
        payload = job.model_dump()
        self._write_json(ws.job_file(job.id), payload)

    def read_job(self, user_id: str, job_id: str) -> JobRecord:
        ws = self.require_workspace(user_id)
        payload = self.read_json(ws.job_file(job_id), default=None)
        if not payload:
            raise FileNotFoundError(f"Job not found: {job_id}")
        return JobRecord.model_validate(payload)

    def list_jobs(self, user_id: str, limit: int = 50) -> JobsResponse:
        ws = self.require_workspace(user_id)
        items: list[JobRecord] = []
        for job_path in sorted(ws.jobs_dir.glob("*.json"), reverse=True):
            payload = self.read_json(job_path, default=None)
            if not isinstance(payload, dict):
                continue
            try:
                items.append(JobRecord.model_validate(payload))
            except Exception:
                continue
        items.sort(key=lambda item: item.triggered_at, reverse=True)
        return JobsResponse(jobs=items[:limit])

    def create_conversation(self, user_id: str, title: str | None = None) -> SavedConversation:
        ws = self.require_workspace(user_id)
        now = utc_now()
        conversation = SavedConversation(
            id=f"conv_{uuid.uuid4().hex[:12]}",
            userId=user_id,
            title=title,
            startedAt=now,
            updatedAt=now,
            lastActivityAt=now,
        )
        self._write_json(self._conversation_path(ws, conversation.id), {"conversation": conversation.model_dump(), "turns": []})
        return conversation

    def list_conversations(self, user_id: str, limit: int, offset: int) -> list[SavedConversation]:
        ws = self.require_workspace(user_id)
        items: list[SavedConversation] = []
        for path in sorted(self._conversations_dir(ws).glob("*.json"), reverse=True):
            payload = self.read_json(path, default=None)
            if not isinstance(payload, dict):
                continue
            try:
                conversation = SavedConversation.model_validate(payload.get("conversation"))
            except Exception:
                continue
            if not conversation.isArchived:
                items.append(conversation)
        items.sort(key=lambda item: item.updatedAt, reverse=True)
        return items[offset:offset + limit]

    def load_conversation(self, user_id: str, conversation_id: str) -> ConversationHistory:
        ws = self.require_workspace(user_id)
        payload = self.read_json(self._conversation_path(ws, conversation_id), default=None)
        if not isinstance(payload, dict):
            raise FileNotFoundError(f"Conversation not found: {conversation_id}")
        return ConversationHistory.model_validate(payload)

    def save_conversation(self, user_id: str, history: ConversationHistory) -> None:
        ws = self.require_workspace(user_id)
        self._write_json(self._conversation_path(ws, history.conversation.id), history.model_dump())

    def archive_conversation(self, user_id: str, conversation_id: str) -> SavedConversation:
        history = self.load_conversation(user_id, conversation_id)
        history.conversation.archivedAt = utc_now()
        history.conversation.accessState = "archived"
        history.conversation.isArchived = True
        history.conversation.updatedAt = history.conversation.archivedAt
        self.save_conversation(user_id, history)
        return history.conversation

    def rename_conversation(self, user_id: str, conversation_id: str, title: str) -> SavedConversation:
        history = self.load_conversation(user_id, conversation_id)
        history.conversation.title = title
        history.conversation.updatedAt = utc_now()
        history.conversation.lastActivityAt = history.conversation.updatedAt
        self.save_conversation(user_id, history)
        return history.conversation

    def append_turns(self, user_id: str, conversation_id: str, turns: list[ConversationTurn], *, model: str | None, cost_usd: float, tool_call_count: int) -> ConversationHistory:
        history = self.load_conversation(user_id, conversation_id)
        history.turns.extend(turns)
        conversation = history.conversation
        conversation.turnCount = len([turn for turn in history.turns if turn.role in {"user", "assistant"}])
        conversation.updatedAt = utc_now()
        conversation.lastActivityAt = conversation.updatedAt
        conversation.totalCostUsd = round(conversation.totalCostUsd + cost_usd, 6)
        conversation.toolCallCount += tool_call_count
        conversation.model = model
        self.save_conversation(user_id, history)
        return history

    def list_strategies(self, user_id: str) -> list[dict[str, Any]]:
        ws = self.require_workspace(user_id)
        strategies: list[dict[str, Any]] = []
        for path in sorted(ws.tickers_dir.glob("*/strategy.json")):
            payload = self.read_json(path, default=None)
            if isinstance(payload, dict):
                strategies.append(payload)
        return strategies

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
    def _conversations_dir(ws: WorkspacePaths) -> Path:
        return ws.chat_dir / "conversations"

    def _conversation_path(self, ws: WorkspacePaths, conversation_id: str) -> Path:
        return self._conversations_dir(ws) / f"{conversation_id}.json"
