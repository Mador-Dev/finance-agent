from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    user_id: str
    root: Path
    data_dir: Path
    portfolio_file: Path
    config_file: Path
    state_file: Path
    jobs_dir: Path
    reports_dir: Path
    report_index_dir: Path
    tickers_dir: Path
    chat_dir: Path
    user_md_file: Path
    profile_file: Path

    def strategy_file(self, ticker: str) -> Path:
        return self.tickers_dir / ticker / "strategy.json"

    def events_file(self, ticker: str) -> Path:
        return self.tickers_dir / ticker / "events.jsonl"

    def report_dir(self, ticker: str) -> Path:
        return self.reports_dir / ticker

    def report_file(self, ticker: str, name: str) -> Path:
        return self.report_dir(ticker) / f"{name}.json"

    def job_file(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.json"


def build_workspace(users_dir: Path, user_id: str) -> WorkspacePaths:
    root = users_dir / user_id
    data_dir = root / "data"
    return WorkspacePaths(
        user_id=user_id,
        root=root,
        data_dir=data_dir,
        portfolio_file=data_dir / "portfolio.json",
        config_file=data_dir / "config.json",
        state_file=data_dir / "state.json",
        jobs_dir=data_dir / "jobs",
        reports_dir=data_dir / "reports",
        report_index_dir=data_dir / "reports" / "index",
        tickers_dir=data_dir / "tickers",
        chat_dir=data_dir / "chat",
        user_md_file=root / "USER.md",
        profile_file=root / "profile.json",
    )
