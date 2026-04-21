"""Tests for HandoffPacket."""

import json
import pytest
from datetime import datetime

from agent_handoff_protocol import HandoffPacket, Priority


class TestHandoffPacketCreation:
    """Test HandoffPacket creation with various field combinations."""
    
    def test_minimal_packet(self):
        """Test creating a packet with only required fields."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        assert packet.task_id == "task_001"
        assert packet.original_goal == "Test goal"
        # Check defaults
        assert packet.priority == Priority.MEDIUM
        assert packet.confidence_score == 1.0
        assert packet.completed_steps == []
        assert packet.remaining_steps == []
        assert packet.working_memory == {}
        assert packet.tool_results_cache == {}
        assert packet.handoff_reason == ""
        assert packet.context_summary == ""
    
    def test_full_packet(self):
        """Test creating a packet with all fields."""
        packet = HandoffPacket(
            task_id="task_002",
            original_goal="Complete task",
            priority=Priority.HIGH,
            confidence_score=0.85,
            handoff_reason="Need specialized processing",
            context_summary="Summary of work done so far.",
            remaining_steps=["step1", "step2"],
            working_memory={"key": "value"},
            tool_results_cache={"tool_1": "result"}
        )
        
        assert packet.task_id == "task_002"
        assert packet.original_goal == "Complete task"
        assert packet.priority == Priority.HIGH
        assert packet.confidence_score == 0.85
        assert packet.handoff_reason == "Need specialized processing"
        assert packet.context_summary == "Summary of work done so far."
        assert packet.remaining_steps == ["step1", "step2"]
        assert packet.working_memory == {"key": "value"}
        assert packet.tool_results_cache == {"tool_1": "result"}
    
    def test_all_priority_levels(self):
        """Test all priority enum values."""
        for priority in Priority:
            packet = HandoffPacket(
                task_id=f"task_{priority.value}",
                original_goal="Test",
                priority=priority
            )
            assert packet.priority == priority


class TestHandoffPacketMethods:
    """Test HandoffPacket helper methods."""
    
    def test_add_completed_step(self):
        """Test adding completed steps."""
        packet = HandoffPacket(
            task_id="task_003",
            original_goal="Test goal"
        )
        
        result = packet.add_completed_step(
            step_name="Research",
            output="Found 10 sources",
            agent_name="ResearchAgent"
        )
        
        # Should return self for chaining
        assert result is packet
        assert len(packet.completed_steps) == 1
        assert packet.completed_steps[0].step_name == "Research"
        assert packet.completed_steps[0].output == "Found 10 sources"
        assert packet.completed_steps[0].agent_name == "ResearchAgent"
        assert packet.updated_at is not None
    
    def test_update_working_memory(self):
        """Test updating working memory."""
        packet = HandoffPacket(
            task_id="task_004",
            original_goal="Test goal"
        )
        
        result = packet.update_working_memory("key1", "value1")
        assert result is packet
        assert packet.working_memory["key1"] == "value1"
        
        packet.update_working_memory("key2", {"nested": "dict"})
        assert packet.working_memory["key2"] == {"nested": "dict"}
    
    def test_cache_tool_result(self):
        """Test caching tool results."""
        packet = HandoffPacket(
            task_id="task_005",
            original_goal="Test goal"
        )
        
        result = packet.cache_tool_result("search_001", {"results": ["a", "b"]})
        assert result is packet
        assert packet.tool_results_cache["search_001"] == {"results": ["a", "b"]}
    
    def test_get_tool_result(self):
        """Test retrieving cached tool results."""
        packet = HandoffPacket(
            task_id="task_006",
            original_goal="Test goal"
        )
        
        packet.cache_tool_result("tool_1", "result_1")
        
        assert packet.get_tool_result("tool_1") == "result_1"
        assert packet.get_tool_result("nonexistent") is None
    
    def test_mark_step_complete(self):
        """Test marking steps complete."""
        packet = HandoffPacket(
            task_id="task_007",
            original_goal="Test goal",
            remaining_steps=["step1", "step2", "step3"]
        )
        
        result = packet.mark_step_complete("step2")
        assert result is packet
        assert "step2" not in packet.remaining_steps
        assert "step1" in packet.remaining_steps
        assert "step3" in packet.remaining_steps
    
    def test_chaining_methods(self):
        """Test method chaining."""
        packet = HandoffPacket(
            task_id="task_008",
            original_goal="Test goal"
        )
        
        packet \
            .add_completed_step("Step1", "Output1", "Agent1") \
            .update_working_memory("key", "value") \
            .cache_tool_result("tool1", "result1")
        
        assert len(packet.completed_steps) == 1
        assert packet.working_memory["key"] == "value"
        assert packet.tool_results_cache["tool1"] == "result1"


class TestHandoffPacketValidation:
    """Test Pydantic validation."""
    
    def test_confidence_score_bounds(self):
        """Test confidence score must be between 0 and 1."""
        # Valid values
        HandoffPacket(task_id="t1", original_goal="g", confidence_score=0.0)
        HandoffPacket(task_id="t1", original_goal="g", confidence_score=0.5)
        HandoffPacket(task_id="t1", original_goal="g", confidence_score=1.0)
        
        # Invalid values should raise error
        with pytest.raises(Exception):  # Pydantic validation error
            HandoffPacket(task_id="t1", original_goal="g", confidence_score=-0.1)
        
        with pytest.raises(Exception):
            HandoffPacket(task_id="t1", original_goal="g", confidence_score=1.1)
    
    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):
            HandoffPacket()  # Missing task_id and original_goal
        
        with pytest.raises(Exception):
            HandoffPacket(task_id="only_id")  # Missing original_goal
        
        with pytest.raises(Exception):
            HandoffPacket(original_goal="only_goal")  # Missing task_id


class TestHandoffPacketSerialization:
    """Test serialization methods."""
    
    def test_model_dump(self):
        """Test model_dump produces valid dict."""
        packet = HandoffPacket(
            task_id="task_009",
            original_goal="Test goal",
            priority=Priority.CRITICAL
        )
        
        data = packet.model_dump()
        assert isinstance(data, dict)
        assert data["task_id"] == "task_009"
        assert data["original_goal"] == "Test goal"
        assert data["priority"] == "CRITICAL"
    
    def test_model_dump_json(self):
        """Test model_dump_json produces valid JSON."""
        packet = HandoffPacket(
            task_id="task_010",
            original_goal="Test goal"
        )
        
        json_str = packet.model_dump_json()
        assert isinstance(json_str, str)
        
        # Should be parseable
        parsed = json.loads(json_str)
        assert parsed["task_id"] == "task_010"
    
    def test_model_dump_json_safe(self):
        """Test model_dump_json_safe method."""
        packet = HandoffPacket(
            task_id="task_011",
            original_goal="Test goal"
        )
        
        data = packet.model_dump_json_safe()
        assert isinstance(data, dict)
        assert data["task_id"] == "task_011"


class TestCompletedStep:
    """Test CompletedStep model."""
    
    def test_completed_step_creation(self):
        """Test creating a completed step."""
        from agent_handoff_protocol.packet import CompletedStep
        
        step = CompletedStep(
            step_name="Test Step",
            output="Test output",
            agent_name="TestAgent"
        )
        
        assert step.step_name == "Test Step"
        assert step.output == "Test output"
        assert step.agent_name == "TestAgent"
        assert step.timestamp is not None  # Auto-generated
    
    def test_completed_step_with_timestamp(self):
        """Test completed step with custom timestamp."""
        from agent_handoff_protocol.packet import CompletedStep
        
        custom_time = "2025-01-15T10:30:00"
        step = CompletedStep(
            step_name="Test Step",
            output="Test output",
            agent_name="TestAgent",
            timestamp=custom_time
        )
        
        assert step.timestamp == custom_time
