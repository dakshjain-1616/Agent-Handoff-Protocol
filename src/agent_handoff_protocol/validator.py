"""HandoffValidator for validating HandoffPacket instances."""

from dataclasses import dataclass
from typing import Any, Dict, List

from .packet import HandoffPacket, CompletedStep


@dataclass
class ValidationResult:
    """Result of validating a HandoffPacket."""
    is_valid: bool
    errors: List[str]
    
    def __bool__(self) -> bool:
        """Allow using ValidationResult in boolean contexts."""
        return self.is_valid


class HandoffValidator:
    """
    Validates HandoffPacket instances before they are sent.
    
    Performs comprehensive checks on packet fields to ensure data integrity
    and consistency before handoff between agents.
    """
    
    def __init__(self, strict: bool = False):
        """
        Initialize the validator.
        
        Args:
            strict: If True, warnings are treated as errors
        """
        self.strict = strict
    
    def validate(self, packet: HandoffPacket) -> ValidationResult:
        """
        Validate a HandoffPacket.
        
        Args:
            packet: The HandoffPacket to validate
            
        Returns:
            ValidationResult with is_valid flag and list of error messages
        """
        errors: List[str] = []
        
        # Validate required fields
        errors.extend(self._validate_required_fields(packet))
        
        # Validate confidence_score
        errors.extend(self._validate_confidence_score(packet))
        
        # Validate completed_steps
        errors.extend(self._validate_completed_steps(packet))
        
        # Validate working_memory
        errors.extend(self._validate_working_memory(packet))
        
        # Validate context_summary
        errors.extend(self._validate_context_summary(packet))
        
        # Validate tool_results_cache
        errors.extend(self._validate_tool_results_cache(packet))
        
        # Validate remaining_steps
        errors.extend(self._validate_remaining_steps(packet))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
    
    def _validate_required_fields(self, packet: HandoffPacket) -> List[str]:
        """Validate that required fields are present and non-empty."""
        errors = []
        
        if not packet.task_id or not isinstance(packet.task_id, str):
            errors.append("task_id is required and must be a non-empty string")
        
        if not packet.original_goal or not isinstance(packet.original_goal, str):
            errors.append("original_goal is required and must be a non-empty string")
        
        return errors
    
    def _validate_confidence_score(self, packet: HandoffPacket) -> List[str]:
        """Validate that confidence_score is between 0 and 1."""
        errors = []
        
        if not isinstance(packet.confidence_score, (int, float)):
            errors.append("confidence_score must be a number")
        elif packet.confidence_score < 0.0 or packet.confidence_score > 1.0:
            errors.append(f"confidence_score must be between 0 and 1, got {packet.confidence_score}")
        
        return errors
    
    def _validate_completed_steps(self, packet: HandoffPacket) -> List[str]:
        """Validate that all completed_steps have required fields."""
        errors = []
        
        if not isinstance(packet.completed_steps, list):
            errors.append("completed_steps must be a list")
            return errors
        
        required_fields = ['step_name', 'output', 'agent_name']
        
        for i, step in enumerate(packet.completed_steps):
            if not isinstance(step, (CompletedStep, dict)):
                errors.append(f"completed_steps[{i}] must be a CompletedStep or dict")
                continue
            
            # Convert to dict for uniform checking
            step_dict = step if isinstance(step, dict) else step.model_dump()
            
            for field in required_fields:
                if field not in step_dict or not step_dict[field]:
                    errors.append(f"completed_steps[{i}].{field} is required and must be non-empty")
            
            # Validate timestamp format if present
            if 'timestamp' in step_dict and step_dict['timestamp']:
                if not isinstance(step_dict['timestamp'], str):
                    errors.append(f"completed_steps[{i}].timestamp must be a string")
        
        return errors
    
    def _validate_working_memory(self, packet: HandoffPacket) -> List[str]:
        """Validate that working_memory keys are strings."""
        errors = []
        
        if not isinstance(packet.working_memory, dict):
            errors.append("working_memory must be a dictionary")
            return errors
        
        for key in packet.working_memory.keys():
            if not isinstance(key, str):
                errors.append(f"working_memory key '{key}' must be a string, got {type(key).__name__}")
        
        return errors
    
    def _validate_context_summary(self, packet: HandoffPacket) -> List[str]:
        """Validate that context_summary is not empty (if provided)."""
        errors = []
        
        # Only validate if context_summary is provided (it's optional with default)
        if packet.context_summary is not None:
            if not isinstance(packet.context_summary, str):
                errors.append("context_summary must be a string")
            elif self.strict and not packet.context_summary.strip():
                errors.append("context_summary cannot be empty in strict mode")
        
        return errors
    
    def _validate_tool_results_cache(self, packet: HandoffPacket) -> List[str]:
        """Validate tool_results_cache structure."""
        errors = []
        
        if not isinstance(packet.tool_results_cache, dict):
            errors.append("tool_results_cache must be a dictionary")
            return errors
        
        for key in packet.tool_results_cache.keys():
            if not isinstance(key, str):
                errors.append(f"tool_results_cache key '{key}' must be a string")
        
        return errors
    
    def _validate_remaining_steps(self, packet: HandoffPacket) -> List[str]:
        """Validate remaining_steps structure."""
        errors = []
        
        if not isinstance(packet.remaining_steps, list):
            errors.append("remaining_steps must be a list")
            return errors
        
        for i, step in enumerate(packet.remaining_steps):
            if not isinstance(step, str):
                errors.append(f"remaining_steps[{i}] must be a string, got {type(step).__name__}")
        
        return errors
    
    def validate_quick(self, packet: HandoffPacket) -> bool:
        """
        Quick validation that returns only a boolean result.
        
        Args:
            packet: The HandoffPacket to validate
            
        Returns:
            True if valid, False otherwise
        """
        result = self.validate(packet)
        return result.is_valid
