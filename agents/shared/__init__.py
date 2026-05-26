"""Shared utilities for all analysis agents.

This package holds the cross-cutting pieces used by every agent flow:
- model.py       — `init_chat_model` + `with_structured_output` factories
- research.py    — `research_safe` / `synthesise_safe` helpers
- state.py       — the `AnalysisState` TypedDict shared by all workflows
- specialists.py — the analyst node functions (fundamentals, technical, etc.)
- prompts.py     — shared specialist prompts

Each agent directory (quick_check_agent, full_report_agent, ...) composes
these into a small LangGraph workflow.
"""
