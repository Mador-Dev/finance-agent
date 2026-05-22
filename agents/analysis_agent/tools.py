from __future__ import annotations

from typing import Any


def make_context_tool(packet: dict[str, Any]) -> Any:
    def get_analysis_context() -> dict[str, Any]:
        """Return the ticker-specific research packet."""
        return packet

    return get_analysis_context
