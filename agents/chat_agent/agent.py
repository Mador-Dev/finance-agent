from __future__ import annotations

import asyncio
from typing import Any

from langchain.agents import create_agent

from agents.app.config import Settings
from agents.chat_agent.prompts import CHAT_SYSTEM_PROMPT
from agents.chat_agent.tools import build_chat_tools


def build_chat_agent(
    settings: Settings,
    *,
    load_portfolio: Any,
    load_strategies: Any,
    load_reports: Any,
    trigger_job: Any,
) -> Any:
    tools = build_chat_tools(
        load_portfolio=load_portfolio,
        load_strategies=load_strategies,
        load_reports=load_reports,
        trigger_job=trigger_job,
    )
    return create_agent(
        model=settings.deep_agent_model,
        system_prompt=CHAT_SYSTEM_PROMPT,
        tools=tools,
    )


def _invoke_chat_agent_sync(
    agent: Any,
    messages: list[dict[str, str]],
) -> str:
    result = agent.invoke({"messages": messages})
    text = result["messages"][-1].text.strip()
    if not text:
        raise ValueError("Chat agent returned an empty response")
    return text


async def invoke_chat_agent(
    settings: Settings,
    *,
    messages: list[dict[str, str]],
    load_portfolio: Any,
    load_strategies: Any,
    load_reports: Any,
    trigger_job: Any,
) -> str:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")
    agent = build_chat_agent(
        settings,
        load_portfolio=load_portfolio,
        load_strategies=load_strategies,
        load_reports=load_reports,
        trigger_job=trigger_job,
    )
    return await asyncio.to_thread(_invoke_chat_agent_sync, agent, messages)
