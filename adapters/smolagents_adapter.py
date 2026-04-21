"""Smolagents adapter for HandoffPacket."""

from typing import Any, Dict, List, Optional

from agent_handoff_protocol import HandoffPacket, Priority


class SmolagentsAdapter:
    """
    Adapter for converting HandoffPacket to/from smolagents task input format.
    
    Smolagents uses task inputs with specific structure for tool calling agents.
    This adapter maps HandoffPacket fields to smolagents-compatible task inputs.
    """
    
    # Default keys for smolagents task input
    DEFAULT_TASK_KEY = "handoff_packet"
    
    def __init__(self, task_key: str = DEFAULT_TASK_KEY):
        """
        Initialize the smolagents adapter.
        
        Args:
            task_key: The key to use in smolagents task input for the packet
        """
        self.task_key = task_key
    
    def to_smolagents_task(
        self,
        packet: HandoffPacket,
        additional_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert a HandoffPacket to smolagents task input format.
        
        Args:
            packet: The HandoffPacket to convert
            additional_input: Additional input to merge
            
        Returns:
            Smolagents-compatible task input dictionary
        """
        # Build task input in smolagents-compatible format
        task_input: Dict[str, Any] = {
            self.task_key: packet.model_dump(),
            # Smolagents-specific fields
            "task": packet.original_goal,
            "context": {
                "task_id": packet.task_id,
                "priority": packet.priority.value,
                "confidence": packet.confidence_score,
                "handoff_reason": packet.handoff_reason,
                "summary": packet.context_summary,
            },
            "previous_actions": [
                {
                    "tool": step.step_name,
                    "result": step.output,
                    "agent": step.agent_name,
                    "time": step.timestamp,
                }
                for step in packet.completed_steps
            ],
            "next_steps": packet.remaining_steps,
            "memory": packet.working_memory,
            "tool_cache": packet.tool_results_cache,
        }
        
        # Merge additional input if provided
        if additional_input:
            task_input.update(additional_input)
        
        return task_input
    
    def from_smolagents_task(
        self,
        task_input: Dict[str, Any],
        strict: bool = False
    ) -> HandoffPacket:
        """
        Extract a HandoffPacket from smolagents task input.
        
        Args:
            task_input: Smolagents task input dictionary
            strict: If True, raises error if packet not found
            
        Returns:
            HandoffPacket instance
        """
        # Try to get packet from task key
        packet_data = task_input.get(self.task_key)
        
        if packet_data is not None:
            if isinstance(packet_data, HandoffPacket):
                return packet_data
            elif isinstance(packet_data, dict):
                return HandoffPacket.model_validate(packet_data)
        
        # Try to reconstruct from smolagents-specific fields
        context = task_input.get("context", {})
        task = task_input.get("task", "")
        
        if task or context.get("task_id"):
            packet_dict: Dict[str, Any] = {
                "task_id": context.get("task_id", "unknown"),
                "original_goal": task or context.get("original_goal", ""),
                "priority": context.get("priority", "MEDIUM"),
                "confidence_score": context.get("confidence") or context.get("confidence_score", 1.0),
                "handoff_reason": context.get("handoff_reason", ""),
                "context_summary": context.get("summary") or context.get("context_summary", ""),
                "completed_steps": [],
                "remaining_steps": task_input.get("next_steps") or task_input.get("remaining_steps", []),
                "working_memory": task_input.get("memory") or task_input.get("working_memory", {}),
                "tool_results_cache": task_input.get("tool_cache") or task_input.get("tool_results_cache", {}),
            }
            
            # Parse previous_actions into completed_steps
            previous_actions = task_input.get("previous_actions") or task_input.get("completed_steps", [])
            if previous_actions:
                for action in previous_actions:
                    if isinstance(action, dict):
                        packet_dict["completed_steps"].append({
                            "step_name": action.get("tool") or action.get("step_name", "unknown"),
                            "output": action.get("result") or action.get("output", ""),
                            "agent_name": action.get("agent") or action.get("agent_name", "unknown"),
                            "timestamp": action.get("time") or action.get("timestamp", ""),
                        })
            
            return HandoffPacket.model_validate(packet_dict)
        
        if strict:
            raise ValueError(
                f"No HandoffPacket found in smolagents task input under key '{self.task_key}' "
                "and smolagents fields not present"
            )
        
        # Return minimal packet with defaults
        return HandoffPacket(
            task_id=context.get("task_id", "unknown"),
            original_goal=task or "unknown",
        )
    
    def to_framework(
        self,
        packet: HandoffPacket,
        additional_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert HandoffPacket to framework format (alias for to_smolagents_task).
        
        Args:
            packet: The HandoffPacket to convert
            additional_input: Additional input to merge
            
        Returns:
            Smolagents-compatible task input dictionary
        """
        return self.to_smolagents_task(packet, additional_input)
    
    def from_framework(
        self,
        task_input: Dict[str, Any],
        strict: bool = False
    ) -> HandoffPacket:
        """
        Convert framework format to HandoffPacket (alias for from_smolagents_task).
        
        Args:
            task_input: Smolagents task input dictionary
            strict: If True, raises error if packet not found
            
        Returns:
            HandoffPacket instance
        """
        return self.from_smolagents_task(task_input, strict)
    
    def create_agent_prompt(
        self,
        packet: HandoffPacket,
        agent_name: str = "Agent"
    ) -> str:
        """
        Create a prompt for smolagents from a HandoffPacket.
        
        Args:
            packet: The HandoffPacket to convert
            agent_name: Name of the agent
            
        Returns:
            Prompt string for smolagents
        """
        lines = [
            f"You are {agent_name}.",
            "",
            f"## Task: {packet.original_goal}",
            f"**Task ID:** {packet.task_id}",
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
                "## Previous Actions",
                "",
            ])
            for i, step in enumerate(packet.completed_steps, 1):
                lines.append(f"{i}. **{step.step_name}** (by {step.agent_name})")
                lines.append(f"   Result: {step.output}")
            lines.append("")
        
        if packet.remaining_steps:
            lines.extend([
                "## Next Steps",
                "Complete the following steps:",
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
        
        if packet.tool_results_cache:
            lines.extend([
                "## Cached Tool Results",
                "",
            ])
            for tool_id, result in packet.tool_results_cache.items():
                lines.append(f"- **{tool_id}:** {result}")
            lines.append("")
        
        lines.extend([
            "## Instructions",
            f"Continue with the task. Confidence from previous agent: {packet.confidence_score:.0%}",
            "Use the available tools to complete the remaining steps.",
        ])
        
        return "\n".join(lines)
    
    def update_task_input(
        self,
        task_input: Dict[str, Any],
        packet: HandoffPacket
    ) -> Dict[str, Any]:
        """
        Update an existing smolagents task input with a new HandoffPacket.
        
        Args:
            task_input: Existing smolagents task input
            packet: New HandoffPacket to update with
            
        Returns:
            Updated task input dictionary
        """
        # Update the packet in task input
        task_input[self.task_key] = packet.model_dump()
        
        # Update smolagents-specific fields
        if "context" not in task_input:
            task_input["context"] = {}
        
        task_input["context"]["task_id"] = packet.task_id
        task_input["context"]["priority"] = packet.priority.value
        task_input["context"]["confidence"] = packet.confidence_score
        task_input["context"]["handoff_reason"] = packet.handoff_reason
        task_input["context"]["summary"] = packet.context_summary
        
        task_input["task"] = packet.original_goal
        task_input["next_steps"] = packet.remaining_steps
        task_input["memory"] = packet.working_memory
        task_input["tool_cache"] = packet.tool_results_cache
        
        # Update previous actions
        task_input["previous_actions"] = [
            {
                "tool": step.step_name,
                "result": step.output,
                "agent": step.agent_name,
                "time": step.timestamp,
            }
            for step in packet.completed_steps
        ]
        
        return task_input
    
    def get_packet_from_task(
        self,
        task_input: Dict[str, Any]
    ) -> Optional[HandoffPacket]:
        """
        Get HandoffPacket from smolagents task input without raising errors.
        
        Args:
            task_input: Smolagents task input dictionary
            
        Returns:
            HandoffPacket or None if not found
        """
        try:
            return self.from_smolagents_task(task_input, strict=False)
        except Exception:
            return None
