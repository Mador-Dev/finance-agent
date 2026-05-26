"""LangChain chat-model factories used by every agent.

Two separate model paths, each with one job:

- `get_research_model()` — OpenAI Responses API + `web_search_preview` tool.
  Used for the research turn (web search + free prose + citations).

- `get_structured_model(Schema)` — OpenAI Chat Completions API +
  `with_structured_output(Schema, method="json_schema")`. Used for the
  structuring/synthesis turn that emits a typed Pydantic instance.

Why two backends?
  Both LangChain and openai-python wrap Responses API output in a
  `ParsedResponse` envelope whose discriminated-union types Pydantic warns
  about when LangGraph serialises intermediate state. Chat Completions
  returns a plain message that round-trips through Pydantic without
  warnings. Web search isn't needed on the structuring turn anyway, so the
  split is also semantically cleaner.
"""
from __future__ import annotations

from functools import lru_cache
from typing import TypeVar

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from agents.app.config import get_settings

T = TypeVar("T", bound=BaseModel)


@lru_cache(maxsize=4)
def _research_base(temperature: float) -> BaseChatModel:
    """Responses-API model (needed for `web_search_preview`)."""
    return init_chat_model(
        get_settings().deep_agent_model,
        temperature=temperature,
        use_responses_api=True,
    )


@lru_cache(maxsize=4)
def _structured_base(temperature: float) -> BaseChatModel:
    """Chat-Completions model (clean structured output, no Pydantic warnings)."""
    return init_chat_model(
        get_settings().deep_agent_model,
        temperature=temperature,
    )


def get_research_model(temperature: float = 0.2) -> Runnable:
    """For research turns: Responses API with `web_search_preview` bound."""
    return _research_base(temperature).bind_tools([{"type": "web_search_preview"}])


def get_structured_model(schema: type[T], temperature: float = 0.0) -> Runnable:
    """For structuring / synthesis turns: typed Pydantic output via Chat Completions."""
    return _structured_base(temperature).with_structured_output(
        schema, method="json_schema"
    )
