"""Agent event types for async communication between agent and UI."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EventType(str, Enum):
    TOKEN = "TOKEN"
    TOOL_START = "TOOL_START"
    TOOL_END = "TOOL_END"
    TOOL_ERROR = "TOOL_ERROR"
    DONE = "DONE"
    ERROR = "ERROR"


@dataclass
class AgentEvent:
    type: EventType
    data: str = ""
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    duration_ms: float = 0.0
    error: str = ""
