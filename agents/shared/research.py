"""Research helpers used by every specialist node.

LangChain best practice: separate the *research* turn (web search, free prose)
from the *structuring* turn (`with_structured_output(Schema)`). Each call has
one job, and the structuring step is a deterministic JSON-schema cast.

Public API:
- `research(system, user, schema)`         — two-step with web search.
- `synthesise(system, user, schema)`       — single structured-output call.
- `research_safe` / `synthesise_safe`      — never raise; return a fallback.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from agents.shared.model import get_research_model, get_structured_model

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# ── Public helpers ──────────────────────────────────────────────────────────


async def research(*, system: str, user: str, schema: type[T]) -> T:
    """Web-research a topic, then cast the answer into `schema`."""
    research_msg = await get_research_model().ainvoke(
        [SystemMessage(content=system), HumanMessage(content=user)],
    )
    prose = _coerce_text(research_msg.content)

    structurer = get_structured_model(schema)
    return await structurer.ainvoke(
        [
            SystemMessage(
                content=(
                    "Convert the research notes below into the requested schema. "
                    "Use ONLY facts that appear in the notes. If a field is unknown, "
                    "leave it null. Preserve URLs in `sources`."
                )
            ),
            HumanMessage(content=prose),
        ],
    )


async def synthesise(*, system: str, user: str, schema: type[T]) -> T:
    """Single structured-output call — no web search."""
    return await get_structured_model(schema).ainvoke(
        [SystemMessage(content=system), HumanMessage(content=user)],
    )


async def research_safe(*, system: str, user: str, schema: type[T], fallback: T, timeout: float = 180) -> T:
    try:
        return await asyncio.wait_for(
            research(system=system, user=user, schema=schema), timeout=timeout
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("research failed (%s) — using fallback", type(exc).__name__)
        return fallback


async def synthesise_safe(*, system: str, user: str, schema: type[T], fallback: T, timeout: float = 120) -> T:
    try:
        return await asyncio.wait_for(
            synthesise(system=system, user=user, schema=schema), timeout=timeout
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("synthesise failed (%s) — using fallback", type(exc).__name__)
        return fallback


# ── Helpers ─────────────────────────────────────────────────────────────────


def _coerce_text(content: Any) -> str:
    """Flatten message content into a single string.

    The Responses API may return content as either a string or a list of
    content blocks (`{"type": "text", "text": "..."}`, etc.).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") in {"text", "output_text"}:
                    parts.append(str(block.get("text", "")))
                elif "text" in block:
                    parts.append(str(block["text"]))
            else:
                parts.append(str(block))
        return "\n".join(p for p in parts if p)
    return str(content)
