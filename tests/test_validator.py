"""Tests for HandoffValidator."""

import pytest
from agent_handoff_protocol import HandoffPacket, Priority, HandoffValidator, ValidationResult


class TestValidationResult:
    """Test ValidationResult dataclass."""
    
    def test_valid_result(self):
        """Test a valid validation result."""
        result = ValidationResult(is_valid=True, errors=[])
        assert result.is_valid is True
        assert result.errors == []
        assert bool(result) is True
    
    def test_invalid_result(self):
        """Test an invalid validation result."""
        result = ValidationResult(is_valid=False, errors=["Error 1", "Error 2"])
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert bool(result) is False


class TestHandoffValidatorBasic:
    """Test basic HandoffValidator functionality."""
    
    def test_valid_packet(self):
        """Test validating a valid packet."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        result = validator.validate(packet)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert bool(result) is True
    
    def test_empty_task_id(self):
        """Test validation fails with empty task_id."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="",
            original_goal="Test goal"
        )
        
        result = validator.validate(packet)
        
        assert result.is_valid is False
        assert any("task_id" in error for error in result.errors)
    
    def test_empty_original_goal(self):
        """Test validation fails with empty original_goal."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal=""
        )
        
        result = validator.validate(packet)
        
        assert result.is_valid is False
        assert any("original_goal" in error for error in result.errors)


class TestConfidenceScoreValidation:
    """Test confidence score validation."""
    
    def test_valid_confidence_scores(self):
        """Test valid confidence scores pass."""
        validator = HandoffValidator()
        
        for score in [0.0, 0.5, 1.0]:
            packet = HandoffPacket(
                task_id="task_001",
                original_goal="Test",
                confidence_score=score
            )
            result = validator.validate(packet)
            assert result.is_valid, f"Score {score} should be valid"
    
    def test_invalid_confidence_scores(self):
        """Test invalid confidence scores fail."""
        validator = HandoffValidator()
        
        # Note: Pydantic validates bounds, so these should raise during creation
        # But we test the validator's own check for non-numeric values
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test"
        )
        # Manually set invalid value to test validator
        packet.confidence_score = "invalid"  # type: ignore
        
        result = validator.validate(packet)
        assert result.is_valid is False
        assert any("confidence_score" in error for error in result.errors)


class TestCompletedStepsValidation:
    """Test completed_steps validation."""
    
    def test_valid_completed_steps(self):
        """Test valid completed steps."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test"
        )
        packet.add_completed_step("Step1", "Output1", "Agent1")
        
        result = validator.validate(packet)
        assert result.is_valid is True
    
    def test_completed_step_missing_fields(self):
        """Test validation catches missing fields in completed steps."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test"
        )
        # Manually add invalid step
        packet.completed_steps.append({"step_name": "OnlyName"})  # type: ignore
        
        result = validator.validate(packet)
        assert result.is_valid is False
        assert any("completed_steps" in error for error in result.errors)


class TestWorkingMemoryValidation:
    """Test working_memory validation."""
    
    def test_valid_working_memory(self):
        """Test valid working memory with string keys."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test",
            working_memory={"key1": "value1", "key2": 123}
        )
        
        result = validator.validate(packet)
        assert result.is_valid is True
    
    def test_non_string_keys(self):
        """Test validation catches non-string keys in working_memory."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test"
        )
        # Manually add invalid key
        packet.working_memory[123] = "value"  # type: ignore
        
        result = validator.validate(packet)
        assert result.is_valid is False
        assert any("working_memory" in error for error in result.errors)


class TestContextSummaryValidation:
    """Test context_summary validation."""
    
    def test_valid_context_summary(self):
        """Test valid context summary."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test",
            context_summary="This is a valid summary."
        )
        
        result = validator.validate(packet)
        assert result.is_valid is True
    
    def test_empty_context_summary_strict_mode(self):
        """Test empty context summary fails in strict mode."""
        validator = HandoffValidator(strict=True)
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test",
            context_summary="   "  # Whitespace only
        )
        
        result = validator.validate(packet)
        assert result.is_valid is False
        assert any("context_summary" in error for error in result.errors)
    
    def test_empty_context_summary_non_strict(self):
        """Test empty context summary passes in non-strict mode."""
        validator = HandoffValidator(strict=False)
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test",
            context_summary="   "  # Whitespace only
        )
        
        result = validator.validate(packet)
        # Should be valid in non-strict mode
        assert result.is_valid is True


class TestToolResultsCacheValidation:
    """Test tool_results_cache validation."""
    
    def test_valid_tool_cache(self):
        """Test valid tool results cache."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test",
            tool_results_cache={"tool1": "result1", "tool2": {"data": "value"}}
        )
        
        result = validator.validate(packet)
        assert result.is_valid is True
    
    def test_non_string_keys_in_cache(self):
        """Test validation catches non-string keys in tool cache."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test"
        )
        # Manually add invalid key
        packet.tool_results_cache[456] = "value"  # type: ignore
        
        result = validator.validate(packet)
        assert result.is_valid is False
        assert any("tool_results_cache" in error for error in result.errors)


class TestRemainingStepsValidation:
    """Test remaining_steps validation."""
    
    def test_valid_remaining_steps(self):
        """Test valid remaining steps."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test",
            remaining_steps=["step1", "step2", "step3"]
        )
        
        result = validator.validate(packet)
        assert result.is_valid is True
    
    def test_non_string_remaining_steps(self):
        """Test validation catches non-string items in remaining_steps."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test"
        )
        # Manually add invalid step
        packet.remaining_steps.append(123)  # type: ignore
        
        result = validator.validate(packet)
        assert result.is_valid is False
        assert any("remaining_steps" in error for error in result.errors)


class TestValidateQuick:
    """Test validate_quick method."""
    
    def test_validate_quick_valid(self):
        """Test validate_quick returns True for valid packet."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test"
        )
        
        assert validator.validate_quick(packet) is True
    
    def test_validate_quick_invalid(self):
        """Test validate_quick returns False for invalid packet."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="",
            original_goal="Test"
        )
        
        assert validator.validate_quick(packet) is False


class TestMultipleErrors:
    """Test validation with multiple errors."""
    
    def test_multiple_validation_errors(self):
        """Test that all errors are collected."""
        validator = HandoffValidator()
        packet = HandoffPacket(
            task_id="",
            original_goal=""
        )
        packet.working_memory[123] = "value"  # type: ignore
        
        result = validator.validate(packet)
        
        assert result.is_valid is False
        assert len(result.errors) >= 3  # task_id, original_goal, working_memory
