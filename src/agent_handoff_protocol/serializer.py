"""PacketSerializer for converting HandoffPacket to/from various formats."""

import json
from typing import Any, Dict

from .packet import HandoffPacket


class PacketSerializer:
    """
    Serializes and deserializes HandoffPacket instances.
    
    Supports conversion to/from:
    - JSON strings
    - Python dictionaries
    - Compact string format for LLM prompts
    """
    
    @staticmethod
    def to_json(packet: HandoffPacket, indent: int = 2) -> str:
        """
        Convert a HandoffPacket to a JSON string.
        
        Args:
            packet: The HandoffPacket to serialize
            indent: JSON indentation level (default: 2)
            
        Returns:
            JSON string representation of the packet
        """
        return packet.model_dump_json(indent=indent)
    
    @staticmethod
    def from_json(json_str: str) -> HandoffPacket:
        """
        Parse a JSON string into a HandoffPacket.
        
        Args:
            json_str: JSON string to parse
            
        Returns:
            HandoffPacket instance
            
        Raises:
            ValueError: If JSON is invalid or missing required fields
        """
        try:
            data = json.loads(json_str)
            return HandoffPacket.model_validate(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse HandoffPacket: {e}")
    
    @staticmethod
    def to_dict(packet: HandoffPacket) -> Dict[str, Any]:
        """
        Convert a HandoffPacket to a dictionary.
        
        Args:
            packet: The HandoffPacket to convert
            
        Returns:
            Dictionary representation of the packet
        """
        return packet.model_dump()
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> HandoffPacket:
        """
        Create a HandoffPacket from a dictionary.
        
        Args:
            data: Dictionary containing packet data
            
        Returns:
            HandoffPacket instance
            
        Raises:
            ValueError: If data is invalid or missing required fields
        """
        try:
            return HandoffPacket.model_validate(data)
        except Exception as e:
            raise ValueError(f"Failed to create HandoffPacket from dict: {e}")
    
    @staticmethod
    def to_prompt_format(packet: HandoffPacket, include_metadata: bool = False) -> str:
        """
        Convert a HandoffPacket to a clean markdown format suitable for LLM prompts.
        
        This format is designed to be easily readable by LLMs and provides
        all necessary context for the receiving agent to continue the task.
        
        Args:
            packet: The HandoffPacket to format
            include_metadata: Whether to include technical metadata (timestamps, IDs)
            
        Returns:
            Markdown formatted string for LLM consumption
        """
        lines = [
            "# Agent Handoff Context",
            "",
            "## Task Information",
            f"**Task ID:** {packet.task_id}",
            f"**Original Goal:** {packet.original_goal}",
            f"**Priority:** {packet.priority.value}",
            "",
        ]
        
        # Context Summary
        if packet.context_summary:
            lines.extend([
                "## Context Summary",
                packet.context_summary,
                "",
            ])
        
        # Handoff Reason
        if packet.handoff_reason:
            lines.extend([
                "## Handoff Reason",
                packet.handoff_reason,
                "",
            ])
        
        # Confidence Score
        lines.extend([
            "## Confidence Score",
            f"The previous agent has a confidence score of **{packet.confidence_score:.2f}** in their outputs.",
            "",
        ])
        
        # Completed Steps
        if packet.completed_steps:
            lines.extend([
                "## Completed Steps",
                "",
            ])
            for i, step in enumerate(packet.completed_steps, 1):
                lines.extend([
                    f"### Step {i}: {step.step_name}",
                    f"**Agent:** {step.agent_name}",
                    f"**Output:** {step.output}",
                    "",
                ])
        
        # Remaining Steps
        if packet.remaining_steps:
            lines.extend([
                "## Remaining Steps",
                "The following steps still need to be completed:",
                "",
            ])
            for i, step in enumerate(packet.remaining_steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")
        
        # Working Memory
        if packet.working_memory:
            lines.extend([
                "## Working Memory",
                "Key information for the next agent:",
                "",
            ])
            for key, value in packet.working_memory.items():
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, indent=2)
                    lines.append(f"- **{key}:**")
                    lines.append(f"```json\n{value_str}\n```")
                else:
                    lines.append(f"- **{key}:** {value}")
            lines.append("")
        
        # Tool Results Cache
        if packet.tool_results_cache:
            lines.extend([
                "## Cached Tool Results",
                "Results from previously executed tools:",
                "",
            ])
            for tool_call_id, result in packet.tool_results_cache.items():
                if isinstance(result, (dict, list)):
                    result_str = json.dumps(result, indent=2)
                    lines.append(f"- **{tool_call_id}:**")
                    lines.append(f"```json\n{result_str}\n```")
                else:
                    lines.append(f"- **{tool_call_id}:** {result}")
            lines.append("")
        
        # Metadata (optional)
        if include_metadata:
            lines.extend([
                "## Metadata",
                f"- **Created:** {packet.created_at}",
            ])
            if packet.updated_at:
                lines.append(f"- **Last Updated:** {packet.updated_at}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("You are now taking over this task. Please review the context above and continue with the remaining steps.")
        
        return "\n".join(lines)
    
    @staticmethod
    def to_compact_string(packet: HandoffPacket) -> str:
        """
        Convert a HandoffPacket to a compact string format.
        
        This format is optimized for size while maintaining readability.
        Useful for logging or when space is constrained.
        
        Args:
            packet: The HandoffPacket to format
            
        Returns:
            Compact string representation
        """
        parts = [
            f"[Handoff: {packet.task_id}]",
            f"Goal: {packet.original_goal[:50]}{'...' if len(packet.original_goal) > 50 else ''}",
            f"Priority: {packet.priority.value}",
            f"Confidence: {packet.confidence_score:.2f}",
        ]
        
        if packet.completed_steps:
            parts.append(f"Completed: {len(packet.completed_steps)} steps")
        
        if packet.remaining_steps:
            parts.append(f"Remaining: {', '.join(packet.remaining_steps[:3])}{'...' if len(packet.remaining_steps) > 3 else ''}")
        
        if packet.context_summary:
            summary = packet.context_summary[:100].replace('\n', ' ')
            parts.append(f"Summary: {summary}{'...' if len(packet.context_summary) > 100 else ''}")
        
        return " | ".join(parts)
    
    @classmethod
    def serialize(cls, packet: HandoffPacket, format: str = "json") -> str:
        """
        Serialize a packet to the specified format.
        
        Args:
            packet: The HandoffPacket to serialize
            format: One of "json", "dict", "prompt", "compact"
            
        Returns:
            Serialized representation
            
        Raises:
            ValueError: If format is not recognized
        """
        if format == "json":
            return cls.to_json(packet)
        elif format == "dict":
            return str(cls.to_dict(packet))
        elif format == "prompt":
            return cls.to_prompt_format(packet)
        elif format == "compact":
            return cls.to_compact_string(packet)
        else:
            raise ValueError(f"Unknown format: {format}. Use 'json', 'dict', 'prompt', or 'compact'")
    
    @classmethod
    def deserialize(cls, data: str, format: str = "json") -> HandoffPacket:
        """
        Deserialize data to a HandoffPacket.
        
        Args:
            data: The data to deserialize
            format: One of "json" or "dict"
            
        Returns:
            HandoffPacket instance
            
        Raises:
            ValueError: If format is not recognized or data is invalid
        """
        if format == "json":
            return cls.from_json(data)
        elif format == "dict":
            import ast
            try:
                dict_data = ast.literal_eval(data)
                return cls.from_dict(dict_data)
            except (ValueError, SyntaxError) as e:
                raise ValueError(f"Failed to parse dict string: {e}")
        else:
            raise ValueError(f"Unknown format for deserialization: {format}. Use 'json' or 'dict'")
