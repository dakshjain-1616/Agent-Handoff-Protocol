"""CrewAI adapter for HandoffPacket."""

from typing import Any, Dict, List, Optional

from agent_handoff_protocol import HandoffPacket, Priority


class CrewAIAdapter:
    """
    Adapter for converting HandoffPacket to/from CrewAI task context format.
    
    CrewAI uses tasks with context dictionaries. This adapter maps
    HandoffPacket fields to CrewAI-compatible context.
    """
    
    def __init__(self, context_key: str = "handoff_context"):
        """
        Initialize the CrewAI adapter.
        
        Args:
            context_key: The key to use in CrewAI context for the packet
        """
        self.context_key = context_key
    
    def to_crewai_context(
        self,
        packet: HandoffPacket,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert a HandoffPacket to CrewAI task context format.
        
        Args:
            packet: The HandoffPacket to convert
            additional_context: Additional context to merge
            
        Returns:
            CrewAI-compatible context dictionary
        """
        # Build context in CrewAI-compatible format
        context: Dict[str, Any] = {
            self.context_key: {
                "task_id": packet.task_id,
                "original_goal": packet.original_goal,
                "priority": packet.priority.value,
                "confidence_score": packet.confidence_score,
                "handoff_reason": packet.handoff_reason,
                "context_summary": packet.context_summary,
                "completed_steps": [
                    {
                        "step_name": step.step_name,
                        "output": step.output,
                        "agent_name": step.agent_name,
                        "timestamp": step.timestamp,
                    }
                    for step in packet.completed_steps
                ],
                "remaining_steps": packet.remaining_steps,
                "working_memory": packet.working_memory,
                "tool_results_cache": packet.tool_results_cache,
            },
            # Flattened keys for easy access in CrewAI task descriptions
            "task_id": packet.task_id,
            "original_goal": packet.original_goal,
            "priority": packet.priority.value,
            "confidence_score": packet.confidence_score,
            "handoff_reason": packet.handoff_reason,
            "context_summary": packet.context_summary,
        }
        
        # Add working memory as top-level context
        for key, value in packet.working_memory.items():
            context[f"memory_{key}"] = value
        
        # Merge additional context if provided
        if additional_context:
            context.update(additional_context)
        
        return context
    
    def from_crewai_context(
        self,
        context: Dict[str, Any],
        strict: bool = False
    ) -> HandoffPacket:
        """
        Extract a HandoffPacket from CrewAI task context.
        
        Args:
            context: CrewAI task context dictionary
            strict: If True, raises error if packet not found
            
        Returns:
            HandoffPacket instance
        """
        # Try to get packet from context key
        handoff_context = context.get(self.context_key)
        
        if handoff_context is not None and isinstance(handoff_context, dict):
            # Check if it's a full packet or nested context
            if "task_id" in handoff_context and "original_goal" in handoff_context:
                # It might be a nested context structure
                if "task_id" in handoff_context.get("task_id", {}):
                    # Unwrap one level
                    handoff_context = handoff_context
                return HandoffPacket.model_validate(handoff_context)
        
        # Try to reconstruct from flattened context
        if "task_id" in context and "original_goal" in context:
            packet_dict: Dict[str, Any] = {
                "task_id": context.get("task_id", ""),
                "original_goal": context.get("original_goal", ""),
                "priority": context.get("priority", "MEDIUM"),
                "confidence_score": context.get("confidence_score", 1.0),
                "handoff_reason": context.get("handoff_reason", ""),
                "context_summary": context.get("context_summary", ""),
                "completed_steps": context.get("completed_steps", []),
                "remaining_steps": context.get("remaining_steps", []),
                "working_memory": {},
                "tool_results_cache": context.get("tool_results_cache", {}),
            }
            
            # Extract working memory from flattened keys
            for key, value in context.items():
                if key.startswith("memory_"):
                    memory_key = key[7:]  # Remove 'memory_' prefix
                    packet_dict["working_memory"][memory_key] = value
            
            return HandoffPacket.model_validate(packet_dict)
        
        if strict:
            raise ValueError(
                f"No HandoffPacket found in context under key '{self.context_key}' "
                "and required fields (task_id, original_goal) not present"
            )
        
        # Return minimal packet with defaults
        return HandoffPacket(
            task_id=context.get("task_id", "unknown"),
            original_goal=context.get("original_goal", "unknown"),
        )
    
    def to_framework(
        self,
        packet: HandoffPacket,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert HandoffPacket to framework format (alias for to_crewai_context).
        
        Args:
            packet: The HandoffPacket to convert
            additional_context: Additional context to merge
            
        Returns:
            CrewAI-compatible context dictionary
        """
        return self.to_crewai_context(packet, additional_context)
    
    def from_framework(
        self,
        context: Dict[str, Any],
        strict: bool = False
    ) -> HandoffPacket:
        """
        Convert framework format to HandoffPacket (alias for from_crewai_context).
        
        Args:
            context: CrewAI task context dictionary
            strict: If True, raises error if packet not found
            
        Returns:
            HandoffPacket instance
        """
        return self.from_crewai_context(context, strict)
    
    def create_task_description(
        self,
        packet: HandoffPacket,
        agent_role: str = "Agent"
    ) -> str:
        """
        Create a CrewAI task description from a HandoffPacket.
        
        Args:
            packet: The HandoffPacket to convert
            agent_role: Description of the agent's role
            
        Returns:
            Task description string for CrewAI
        """
        lines = [
            f"# Task: {packet.task_id}",
            "",
            f"**Original Goal:** {packet.original_goal}",
            f"**Priority:** {packet.priority.value}",
            "",
        ]
        
        if packet.context_summary:
            lines.extend([
                "## Context Summary",
                packet.context_summary,
                "",
            ])
        
        if packet.handoff_reason:
            lines.extend([
                "## Handoff Reason",
                packet.handoff_reason,
                "",
            ])
        
        if packet.completed_steps:
            lines.extend([
                "## Completed Steps",
                "",
            ])
            for step in packet.completed_steps:
                lines.append(f"- **{step.step_name}** (by {step.agent_name})")
                lines.append(f"  Output: {step.output}")
            lines.append("")
        
        if packet.remaining_steps:
            lines.extend([
                "## Remaining Steps",
                "",
            ])
            for i, step in enumerate(packet.remaining_steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")
        
        if packet.working_memory:
            lines.extend([
                "## Working Memory",
                "",
            ])
            for key, value in packet.working_memory.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")
        
        lines.extend([
            "## Instructions",
            f"As the {agent_role}, review the context above and continue with the task.",
            f"Confidence level from previous agent: {packet.confidence_score:.0%}",
        ])
        
        return "\n".join(lines)
    
    def get_packet_from_context(
        self,
        context: Dict[str, Any]
    ) -> Optional[HandoffPacket]:
        """
        Get HandoffPacket from context without raising errors.
        
        Args:
            context: CrewAI task context dictionary
            
        Returns:
            HandoffPacket or None if not found
        """
        try:
            return self.from_crewai_context(context, strict=False)
        except Exception:
            return None
