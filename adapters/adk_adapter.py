"""Google ADK (Agent Development Kit) adapter for HandoffPacket."""

from typing import Any, Dict, List, Optional

from agent_handoff_protocol import HandoffPacket, Priority


class ADKAdapter:
    """
    Adapter for converting HandoffPacket to/from Google ADK agent context format.
    
    Google ADK uses session state and event-based context. This adapter maps
    HandoffPacket fields to ADK-compatible session state and event data.
    """
    
    # Default keys for ADK session state
    DEFAULT_SESSION_KEY = "handoff_packet"
    DEFAULT_EVENT_KEY = "handoff_event"
    
    def __init__(
        self,
        session_key: str = DEFAULT_SESSION_KEY,
        event_key: str = DEFAULT_EVENT_KEY
    ):
        """
        Initialize the ADK adapter.
        
        Args:
            session_key: The key to use in ADK session state for the packet
            event_key: The key to use in ADK events for handoff data
        """
        self.session_key = session_key
        self.event_key = event_key
    
    def to_adk_session_state(
        self,
        packet: HandoffPacket,
        additional_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert a HandoffPacket to ADK session state format.
        
        Args:
            packet: The HandoffPacket to convert
            additional_state: Additional state to merge
            
        Returns:
            ADK-compatible session state dictionary
        """
        state: Dict[str, Any] = {
            self.session_key: packet.model_dump(),
            # ADK-specific metadata
            "adk_task_id": packet.task_id,
            "adk_original_goal": packet.original_goal,
            "adk_priority": packet.priority.value,
            "adk_confidence": packet.confidence_score,
            "adk_handoff_reason": packet.handoff_reason,
            "adk_context_summary": packet.context_summary,
            "adk_agent_history": [
                {
                    "agent": step.agent_name,
                    "step": step.step_name,
                    "output": step.output,
                    "timestamp": step.timestamp,
                }
                for step in packet.completed_steps
            ],
            "adk_remaining_tasks": packet.remaining_steps,
            "adk_working_memory": packet.working_memory,
            "adk_tool_cache": packet.tool_results_cache,
        }
        
        # Merge additional state if provided
        if additional_state:
            state.update(additional_state)
        
        return state
    
    def from_adk_session_state(
        self,
        state: Dict[str, Any],
        strict: bool = False
    ) -> HandoffPacket:
        """
        Extract a HandoffPacket from ADK session state.
        
        Args:
            state: ADK session state dictionary
            strict: If True, raises error if packet not found
            
        Returns:
            HandoffPacket instance
        """
        # Try to get packet from session key
        packet_data = state.get(self.session_key)
        
        if packet_data is not None:
            if isinstance(packet_data, HandoffPacket):
                return packet_data
            elif isinstance(packet_data, dict):
                return HandoffPacket.model_validate(packet_data)
        
        # Try to reconstruct from ADK-specific keys
        if "adk_task_id" in state or "task_id" in state:
            packet_dict: Dict[str, Any] = {
                "task_id": state.get("adk_task_id") or state.get("task_id", ""),
                "original_goal": state.get("adk_original_goal") or state.get("original_goal", ""),
                "priority": state.get("adk_priority") or state.get("priority", "MEDIUM"),
                "confidence_score": state.get("adk_confidence") or state.get("confidence_score", 1.0),
                "handoff_reason": state.get("adk_handoff_reason") or state.get("handoff_reason", ""),
                "context_summary": state.get("adk_context_summary") or state.get("context_summary", ""),
                "completed_steps": [],
                "remaining_steps": state.get("adk_remaining_tasks") or state.get("remaining_steps", []),
                "working_memory": state.get("adk_working_memory") or state.get("working_memory", {}),
                "tool_results_cache": state.get("adk_tool_cache") or state.get("tool_results_cache", {}),
            }
            
            # Parse agent history into completed_steps
            agent_history = state.get("adk_agent_history") or state.get("completed_steps", [])
            if agent_history:
                for entry in agent_history:
                    if isinstance(entry, dict):
                        packet_dict["completed_steps"].append({
                            "step_name": entry.get("step", entry.get("step_name", "unknown")),
                            "output": entry.get("output", ""),
                            "agent_name": entry.get("agent", entry.get("agent_name", "unknown")),
                            "timestamp": entry.get("timestamp", ""),
                        })
            
            return HandoffPacket.model_validate(packet_dict)
        
        if strict:
            raise ValueError(
                f"No HandoffPacket found in ADK state under key '{self.session_key}' "
                "and ADK fields not present"
            )
        
        # Return minimal packet with defaults
        return HandoffPacket(
            task_id=state.get("adk_task_id") or state.get("task_id", "unknown"),
            original_goal=state.get("adk_original_goal") or state.get("original_goal", "unknown"),
        )
    
    def create_adk_event(
        self,
        packet: HandoffPacket,
        from_agent: str,
        to_agent: str,
        event_type: str = "handoff"
    ) -> Dict[str, Any]:
        """
        Create an ADK event for a handoff.
        
        Args:
            packet: The HandoffPacket being handed off
            from_agent: Name of the sending agent
            to_agent: Name of the receiving agent
            event_type: Type of event (default: "handoff")
            
        Returns:
            ADK event dictionary
        """
        return {
            "type": event_type,
            self.event_key: {
                "packet": packet.model_dump(),
                "from_agent": from_agent,
                "to_agent": to_agent,
                "timestamp": packet.updated_at or packet.created_at,
            },
            "metadata": {
                "task_id": packet.task_id,
                "priority": packet.priority.value,
                "confidence": packet.confidence_score,
            }
        }
    
    def from_adk_event(
        self,
        event: Dict[str, Any],
        strict: bool = False
    ) -> HandoffPacket:
        """
        Extract a HandoffPacket from an ADK event.
        
        Args:
            event: ADK event dictionary
            strict: If True, raises error if packet not found
            
        Returns:
            HandoffPacket instance
        """
        # Try to get packet from event key
        handoff_event = event.get(self.event_key)
        
        if handoff_event and isinstance(handoff_event, dict):
            packet_data = handoff_event.get("packet")
            if packet_data:
                if isinstance(packet_data, HandoffPacket):
                    return packet_data
                elif isinstance(packet_data, dict):
                    return HandoffPacket.model_validate(packet_data)
        
        # Try metadata as fallback
        metadata = event.get("metadata", {})
        if metadata and "task_id" in metadata:
            return HandoffPacket(
                task_id=metadata.get("task_id", "unknown"),
                original_goal=metadata.get("original_goal", "unknown"),
                priority=metadata.get("priority", "MEDIUM"),
                confidence_score=metadata.get("confidence", 1.0),
            )
        
        if strict:
            raise ValueError(
                f"No HandoffPacket found in ADK event under key '{self.event_key}'"
            )
        
        return HandoffPacket(
            task_id="unknown",
            original_goal="unknown",
        )
    
    def to_framework(
        self,
        packet: HandoffPacket,
        additional_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert HandoffPacket to framework format (alias for to_adk_session_state).
        
        Args:
            packet: The HandoffPacket to convert
            additional_state: Additional state to merge
            
        Returns:
            ADK-compatible session state dictionary
        """
        return self.to_adk_session_state(packet, additional_state)
    
    def from_framework(
        self,
        state: Dict[str, Any],
        strict: bool = False
    ) -> HandoffPacket:
        """
        Convert framework format to HandoffPacket (alias for from_adk_session_state).
        
        Args:
            state: ADK session state dictionary
            strict: If True, raises error if packet not found
            
        Returns:
            HandoffPacket instance
        """
        return self.from_adk_session_state(state, strict)
    
    def update_session_state(
        self,
        state: Dict[str, Any],
        packet: HandoffPacket
    ) -> Dict[str, Any]:
        """
        Update an existing ADK session state with a new HandoffPacket.
        
        Args:
            state: Existing ADK session state
            packet: New HandoffPacket to update with
            
        Returns:
            Updated session state dictionary
        """
        # Update the packet in state
        state[self.session_key] = packet.model_dump()
        
        # Update ADK-specific fields
        state["adk_task_id"] = packet.task_id
        state["adk_original_goal"] = packet.original_goal
        state["adk_priority"] = packet.priority.value
        state["adk_confidence"] = packet.confidence_score
        state["adk_handoff_reason"] = packet.handoff_reason
        state["adk_context_summary"] = packet.context_summary
        state["adk_remaining_tasks"] = packet.remaining_steps
        state["adk_working_memory"] = packet.working_memory
        state["adk_tool_cache"] = packet.tool_results_cache
        
        # Update agent history
        state["adk_agent_history"] = [
            {
                "agent": step.agent_name,
                "step": step.step_name,
                "output": step.output,
                "timestamp": step.timestamp,
            }
            for step in packet.completed_steps
        ]
        
        return state
    
    def get_packet_from_session(
        self,
        state: Dict[str, Any]
    ) -> Optional[HandoffPacket]:
        """
        Get HandoffPacket from ADK session state without raising errors.
        
        Args:
            state: ADK session state dictionary
            
        Returns:
            HandoffPacket or None if not found
        """
        try:
            return self.from_adk_session_state(state, strict=False)
        except Exception:
            return None
