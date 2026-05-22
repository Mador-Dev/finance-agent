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


class ChatAgentRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def reply(
        self,
        *,
        messages: list[dict[str, str]],
        load_portfolio: Any,
        load_strategies: Any,
        load_reports: Any,
        trigger_job: Any,
    ) -> tuple[str, int]:
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        agent = build_chat_agent(
            self.settings,
            load_portfolio=load_portfolio,
            load_strategies=load_strategies,
            load_reports=load_reports,
            trigger_job=trigger_job,
        )
        return await asyncio.to_thread(self._invoke, agent, messages)

    @staticmethod
    def _invoke(agent: Any, messages: list[dict[str, str]]) -> tuple[str, int]:
        result = agent.invoke({"messages": messages})
        text = ChatAgentRunner._extract_text(result)
        tool_calls = ChatAgentRunner._count_tool_calls(result)
        if not text:
            raise ValueError("Chat agent returned an empty response")
        return text, tool_calls

    @staticmethod
    def _extract_text(result: Any) -> str:
        if isinstance(result, dict):
            output = result.get("output")
            if isinstance(output, str) and output.strip():
                return output.strip()
            messages = result.get("messages")
            if isinstance(messages, list):
                for message in reversed(messages):
                    if not isinstance(message, dict):
                        continue
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()
                    if isinstance(content, list):
                        text = "".join(
                            part.get("text", "")
                            for part in content
                            if isinstance(part, dict) and isinstance(part.get("text"), str)
                        ).strip()
                        if text:
                            return text
        return str(result).strip()

    @staticmethod
    def _count_tool_calls(result: Any) -> int:
        if not isinstance(result, dict):
            return 0
        messages = result.get("messages")
        if not isinstance(messages, list):
            return 0
        count = 0
        for message in messages:
            if isinstance(message, dict) and message.get("tool_calls"):
                count += len(message["tool_calls"])
        return count
