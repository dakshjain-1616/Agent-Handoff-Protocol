"""Agent Handoff Protocol - A standard for passing state between agents in multi-agent systems."""

from .packet import HandoffPacket, Priority
from .validator import HandoffValidator, ValidationResult
from .serializer import PacketSerializer
from .broker import HandoffBroker

__version__ = "0.1.0"
__all__ = [
    "HandoffPacket",
    "Priority",
    "HandoffValidator",
    "ValidationResult",
    "PacketSerializer",
    "HandoffBroker",
]
