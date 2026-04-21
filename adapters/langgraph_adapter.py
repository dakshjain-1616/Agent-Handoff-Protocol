"""LangGraph adapter for HandoffPacket."""

from typing import Any, Dict, Optional

from agent_handoff_protocol import HandoffPacket, Priority


class LangGraphAdapter:
    """
    Adapter for converting HandoffPacket to/from LangGraph state format.
    
    LangGraph uses a state dictionary that flows through the graph.
    This adapter maps HandoffPacket fields to LangGraph state keys.
    """
    
    # Default state keys used in LangGraph
    DEFAULT_STATE_KEY = "handoff_packet"
    
    def __init__(self, state_key: str = DEFAULT_STATE_KEY):
        """
        Initialize the LangGraph adapter.
        
        Args:
            state_key: The key to use in LangGraph state for the packet
        """
        self.state_key = state_key
    
    def to_langgraph_state(
        self,
        packet: HandoffPacket,
        additional_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert a HandoffPacket to LangGraph state format.
        
        Args:
            packet: The HandoffPacket to convert
            additional_state: Additional state to merge into the LangGraph state
            
        Returns:
            LangGraph state dictionary
        """
        state: Dict[str, Any] = {
            self.state_key: packet.model_dump(),
            "task_id": packet.task_id,
            "original_goal": packet.original_goal,
            "priority": packet.priority.value,
            "confidence_score": packet.confidence_score,
            "handoff_reason": packet.handoff_reason,
            "context_summary": packet.context_summary,
            "completed_steps_count": len(packet.completed_steps),
            "remaining_steps_count": len(packet.remaining_steps),
        }
        
        # Add working memory as flattened state keys for easy access
        for key, value in packet.working_memory.items():
            state[f"memory_{key}"] = value
        
        # Merge additional state if provided
        if additional_state:
            state.update(additional_state)
        
        return state
    
    def from_langgraph_state(
        self,
        state: Dict[str, Any],
        strict: bool = False
    ) -> HandoffPacket:
        """
        Extract a HandoffPacket from LangGraph state.
        
        Args:
            state: LangGraph state dictionary
            strict: If True, raises error if packet not found; otherwise returns minimal packet
            
        Returns:
            HandoffPacket instance
            
        Raises:
            ValueError: If strict=True and packet not found in state
        """
        # Try to get packet from state key
        packet_data = state.get(self.state_key)
        
        if packet_data is not None:
            if isinstance(packet_data, HandoffPacket):
                return packet_data
            elif isinstance(packet_data, dict):
                return HandoffPacket.model_validate(packet_data)
        
        # Try to reconstruct from flattened state
        if "task_id" in state and "original_goal" in state:
            packet_dict: Dict[str, Any] = {
                "task_id": state.get("task_id", ""),
                "original_goal": state.get("original_goal", ""),
                "priority": state.get("priority", "MEDIUM"),
                "confidence_score": state.get("confidence_score", 1.0),
                "handoff_reason": state.get("handoff_reason", ""),
                "context_summary": state.get("context_summary", ""),
                "completed_steps": state.get("completed_steps", []),
                "remaining_steps": state.get("remaining_steps", []),
                "working_memory": {},
                "tool_results_cache": state.get("tool_results_cache", {}),
            }
            
            # Extract working memory from flattened keys
            for key, value in state.items():
                if key.startswith("memory_"):
                    memory_key = key[7:]  # Remove 'memory_' prefix
                    packet_dict["working_memory"][memory_key] = value
            
            return HandoffPacket.model_validate(packet_dict)
        
        if strict:
            raise ValueError(
                f"No HandoffPacket found in state under key '{self.state_key}' "
                "and required fields (task_id, original_goal) not present"
            )
        
        # Return minimal packet with defaults
        return HandoffPacket(
            task_id=state.get("task_id", "unknown"),
            original_goal=state.get("original_goal", "unknown"),
        )
    
    def to_framework(
        self,
        packet: HandoffPacket,
        additional_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert HandoffPacket to framework format (alias for to_langgraph_state).
        
        Args:
            packet: The HandoffPacket to convert
            additional_state: Additional state to merge
            
        Returns:
            LangGraph state dictionary
        """
        return self.to_langgraph_state(packet, additional_state)
    
    def from_framework(
        self,
        state: Dict[str, Any],
        strict: bool = False
    ) -> HandoffPacket:
        """
        Convert framework format to HandoffPacket (alias for from_langgraph_state).
        
        Args:
            state: LangGraph state dictionary
            strict: If True, raises error if packet not found
            
        Returns:
            HandoffPacket instance
        """
        return self.from_langgraph_state(state, strict)
    
    def update_state_with_packet(
        self,
        state: Dict[str, Any],
        packet: HandoffPacket
    ) -> Dict[str, Any]:
        """
        Update an existing LangGraph state with a new HandoffPacket.
        
        Args:
            state: Existing LangGraph state
            packet: New HandoffPacket to update with
            
        Returns:
            Updated state dictionary
        """
        # Update the packet in state
        state[self.state_key] = packet.model_dump()
        
        # Update derived fields
        state["task_id"] = packet.task_id
        state["original_goal"] = packet.original_goal
        state["priority"] = packet.priority.value
        state["confidence_score"] = packet.confidence_score
        state["handoff_reason"] = packet.handoff_reason
        state["context_summary"] = packet.context_summary
        state["completed_steps_count"] = len(packet.completed_steps)
        state["remaining_steps_count"] = len(packet.remaining_steps)
        
        # Update working memory
        for key, value in packet.working_memory.items():
            state[f"memory_{key}"] = value
        
        return state
    
    def get_packet_from_state(
        self,
        state: Dict[str, Any]
    ) -> Optional[HandoffPacket]:
        """
        Get HandoffPacket from state without raising errors.
        
        Args:
            state: LangGraph state dictionary
            
        Returns:
            HandoffPacket or None if not found
        """
        try:
            return self.from_langgraph_state(state, strict=False)
        except Exception:
            return None
