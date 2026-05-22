from __future__ import annotations

from collections.abc import Callable
from typing import Any


def make_research_packet_tool(research_packet: dict[str, Any]) -> Callable[[], dict[str, Any]]:
    def get_research_packet() -> dict[str, Any]:
        """Return the normalized research packet for the current ticker."""
        return research_packet

    return get_research_packet


def make_guidance_tool(guidance: dict[str, Any] | None) -> Callable[[], dict[str, Any]]:
    def get_guidance() -> dict[str, Any]:
        """Return the user-supplied guidance for this ticker."""
        return guidance or {}

    return get_guidance
