"""Core HandoffPacket dataclass definition using Pydantic."""

from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Priority(str, Enum):
    """Priority levels for handoff packets."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CompletedStep(BaseModel):
    """Represents a completed step in the task pipeline."""
    step_name: str = Field(..., description="Name of the completed step")
    output: str = Field(..., description="Output or result of the step")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(), description="When the step was completed")
    agent_name: str = Field(..., description="Name of the agent that completed the step")


class HandoffPacket(BaseModel):
    """
    Standard packet for passing state between agents in multi-agent systems.
    
    This dataclass defines the contract for agent handoffs, ensuring that
    all necessary context, state, and metadata is preserved when control
    transfers from one agent to another.
    """
    
    # Required fields
    task_id: str = Field(..., description="Unique identifier for this task")
    original_goal: str = Field(..., description="The original goal or objective of the task")
    
    # Optional fields with defaults
    completed_steps: List[CompletedStep] = Field(
        default_factory=list,
        description="List of steps that have been completed so far"
    )
    remaining_steps: List[str] = Field(
        default_factory=list,
        description="List of steps that still need to be completed"
    )
    working_memory: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value pairs the next agent should know"
    )
    tool_results_cache: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cache of tool call results, mapping tool_call_id to result"
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1) of the handing-off agent in its outputs"
    )
    handoff_reason: str = Field(
        default="",
        description="Explanation of why control is being handed off"
    )
    context_summary: str = Field(
        default="",
        description="3-5 sentence summary of what has happened so far"
    )
    priority: Priority = Field(
        default=Priority.MEDIUM,
        description="Priority level of this task"
    )
    
    # Metadata (auto-populated)
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Timestamp when the packet was created"
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="Timestamp when the packet was last updated"
    )

    # TTL / expiry
    ttl_seconds: Optional[int] = Field(
        default=None,
        description="Time-to-live in seconds from creation. If set, expires_at is auto-filled."
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Absolute UTC expiry time. Auto-filled from ttl_seconds if provided."
    )

    @model_validator(mode='after')
    def _fill_expires_at(self) -> "HandoffPacket":
        """Auto-fill expires_at from ttl_seconds if set."""
        if self.ttl_seconds is not None and self.expires_at is None:
            try:
                base = datetime.fromisoformat(self.created_at)
                if base.tzinfo is None:
                    base = base.replace(tzinfo=UTC)
            except Exception:
                base = datetime.now(UTC)
            # Use object.__setattr__ to avoid re-triggering validation recursion
            object.__setattr__(self, 'expires_at', base + timedelta(seconds=self.ttl_seconds))
        # Ensure tz-aware
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            object.__setattr__(self, 'expires_at', self.expires_at.replace(tzinfo=UTC))
        return self

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        """Check whether this packet has expired."""
        if self.expires_at is None:
            return False
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        return current >= self.expires_at

    @field_validator('confidence_score')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('confidence_score must be between 0 and 1')
        return v
    
    def add_completed_step(
        self,
        step_name: str,
        output: str,
        agent_name: str,
        timestamp: Optional[str] = None
    ) -> "HandoffPacket":
        """Add a completed step to the packet and return self for chaining."""
        step = CompletedStep(
            step_name=step_name,
            output=output,
            agent_name=agent_name,
            timestamp=timestamp or datetime.now(UTC).isoformat()
        )
        self.completed_steps.append(step)
        self.updated_at = datetime.now(UTC).isoformat()
        return self
    
    def update_working_memory(self, key: str, value: Any) -> "HandoffPacket":
        """Update working memory with a key-value pair."""
        self.working_memory[key] = value
        self.updated_at = datetime.now(UTC).isoformat()
        return self
    
    def cache_tool_result(self, tool_call_id: str, result: Any) -> "HandoffPacket":
        """Cache a tool result for later retrieval."""
        self.tool_results_cache[tool_call_id] = result
        self.updated_at = datetime.now(UTC).isoformat()
        return self
    
    def get_tool_result(self, tool_call_id: str) -> Optional[Any]:
        """Retrieve a cached tool result."""
        return self.tool_results_cache.get(tool_call_id)
    
    def mark_step_complete(self, step_name: str) -> "HandoffPacket":
        """Move a step from remaining to completed (without output)."""
        if step_name in self.remaining_steps:
            self.remaining_steps.remove(step_name)
        self.updated_at = datetime.now(UTC).isoformat()
        return self
    
    def model_dump_json_safe(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return self.model_dump(mode='json')
