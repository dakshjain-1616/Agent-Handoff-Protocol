"""Tests for PacketSerializer."""

import json
import pytest
from agent_handoff_protocol import HandoffPacket, Priority, PacketSerializer


class TestToJson:
    """Test JSON serialization."""
    
    def test_to_json_basic(self):
        """Test basic JSON serialization."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        json_str = PacketSerializer.to_json(packet)
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["task_id"] == "task_001"
        assert parsed["original_goal"] == "Test goal"
    
    def test_to_json_with_indent(self):
        """Test JSON serialization with custom indent."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        json_str = PacketSerializer.to_json(packet, indent=4)
        
        # Should have indentation
        assert "    " in json_str
    
    def test_to_json_complex_packet(self):
        """Test JSON serialization with complex data."""
        packet = HandoffPacket(
            task_id="task_002",
            original_goal="Complex task",
            priority=Priority.HIGH,
            working_memory={"key": "value", "number": 42},
            remaining_steps=["step1", "step2"]
        )
        packet.add_completed_step("Step1", "Output1", "Agent1")
        
        json_str = PacketSerializer.to_json(packet)
        parsed = json.loads(json_str)
        
        assert parsed["priority"] == "HIGH"
        assert parsed["working_memory"]["key"] == "value"
        assert len(parsed["completed_steps"]) == 1


class TestFromJson:
    """Test JSON deserialization."""
    
    def test_from_json_basic(self):
        """Test basic JSON deserialization."""
        original = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        json_str = PacketSerializer.to_json(original)
        restored = PacketSerializer.from_json(json_str)
        
        assert restored.task_id == original.task_id
        assert restored.original_goal == original.original_goal
    
    def test_from_json_round_trip(self):
        """Test round-trip serialization."""
        original = HandoffPacket(
            task_id="task_002",
            original_goal="Complex task",
            priority=Priority.CRITICAL,
            confidence_score=0.85,
            working_memory={"data": [1, 2, 3]},
            remaining_steps=["a", "b", "c"]
        )
        original.add_completed_step("Step1", "Output", "Agent")
        
        json_str = PacketSerializer.to_json(original)
        restored = PacketSerializer.from_json(json_str)
        
        assert restored.task_id == original.task_id
        assert restored.priority == original.priority
        assert restored.confidence_score == original.confidence_score
        assert restored.working_memory == original.working_memory
        assert len(restored.completed_steps) == len(original.completed_steps)
    
    def test_from_json_invalid(self):
        """Test error on invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            PacketSerializer.from_json("not valid json")
    
    def test_from_json_missing_fields(self):
        """Test error on JSON missing required fields."""
        invalid_json = json.dumps({"task_id": "only_id"})
        
        with pytest.raises(ValueError):
            PacketSerializer.from_json(invalid_json)


class TestToDict:
    """Test dictionary conversion."""
    
    def test_to_dict_basic(self):
        """Test basic dict conversion."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        data = PacketSerializer.to_dict(packet)
        
        assert isinstance(data, dict)
        assert data["task_id"] == "task_001"
        assert data["original_goal"] == "Test goal"
    
    def test_to_dict_modification(self):
        """Test that dict can be modified without affecting original."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal",
            working_memory={"key": "value"}
        )
        
        data = PacketSerializer.to_dict(packet)
        data["working_memory"]["new_key"] = "new_value"
        
        # Original should be unchanged
        assert "new_key" not in packet.working_memory


class TestFromDict:
    """Test dictionary deserialization."""
    
    def test_from_dict_basic(self):
        """Test basic dict deserialization."""
        data = {
            "task_id": "task_001",
            "original_goal": "Test goal",
            "priority": "HIGH"
        }
        
        packet = PacketSerializer.from_dict(data)
        
        assert packet.task_id == "task_001"
        assert packet.original_goal == "Test goal"
        assert packet.priority == Priority.HIGH
    
    def test_from_dict_round_trip(self):
        """Test round-trip through dict."""
        original = HandoffPacket(
            task_id="task_002",
            original_goal="Complex task",
            priority=Priority.LOW
        )
        
        data = PacketSerializer.to_dict(original)
        restored = PacketSerializer.from_dict(data)
        
        assert restored.task_id == original.task_id
        assert restored.priority == original.priority
    
    def test_from_dict_invalid(self):
        """Test error on invalid dict."""
        with pytest.raises(ValueError):
            PacketSerializer.from_dict({"invalid": "data"})


class TestToPromptFormat:
    """Test prompt format generation."""
    
    def test_to_prompt_format_basic(self):
        """Test basic prompt format."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        prompt = PacketSerializer.to_prompt_format(packet)
        
        assert "# Agent Handoff Context" in prompt
        assert "task_001" in prompt
        assert "Test goal" in prompt
    
    def test_to_prompt_format_with_context(self):
        """Test prompt format with context summary."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal",
            context_summary="This is the context summary.",
            handoff_reason="Handing off for review."
        )
        
        prompt = PacketSerializer.to_prompt_format(packet)
        
        assert "## Context Summary" in prompt
        assert "This is the context summary." in prompt
        assert "## Handoff Reason" in prompt
        assert "Handing off for review." in prompt
    
    def test_to_prompt_format_with_steps(self):
        """Test prompt format with completed steps."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        packet.add_completed_step("Step1", "Output1", "Agent1")
        packet.add_completed_step("Step2", "Output2", "Agent2")
        
        prompt = PacketSerializer.to_prompt_format(packet)
        
        assert "## Completed Steps" in prompt
        assert "Step1" in prompt
        assert "Step2" in prompt
        assert "Agent1" in prompt
        assert "Agent2" in prompt
    
    def test_to_prompt_format_with_memory(self):
        """Test prompt format with working memory."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal",
            working_memory={"key1": "value1", "key2": "value2"}
        )
        
        prompt = PacketSerializer.to_prompt_format(packet)
        
        assert "## Working Memory" in prompt
        assert "key1" in prompt
        assert "value1" in prompt
    
    def test_to_prompt_format_with_metadata(self):
        """Test prompt format with metadata included."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        prompt = PacketSerializer.to_prompt_format(packet, include_metadata=True)
        
        assert "## Metadata" in prompt
        assert "Created:" in prompt


class TestToCompactString:
    """Test compact string format."""
    
    def test_to_compact_string_basic(self):
        """Test basic compact format."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        compact = PacketSerializer.to_compact_string(packet)
        
        assert "[Handoff: task_001]" in compact
        assert "Goal:" in compact
        assert "MEDIUM" in compact
    
    def test_to_compact_string_truncation(self):
        """Test that long goals are truncated."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="A" * 100  # Very long goal
        )
        
        compact = PacketSerializer.to_compact_string(packet)
        
        assert "..." in compact
        assert len(compact) < 200  # Should be truncated


class TestSerializeDeserialize:
    """Test generic serialize/deserialize methods."""
    
    def test_serialize_json(self):
        """Test serialize to JSON format."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        result = PacketSerializer.serialize(packet, format="json")
        
        assert isinstance(result, str)
        assert "task_001" in result
    
    def test_serialize_prompt(self):
        """Test serialize to prompt format."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        result = PacketSerializer.serialize(packet, format="prompt")
        
        assert "# Agent Handoff Context" in result
    
    def test_serialize_compact(self):
        """Test serialize to compact format."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        result = PacketSerializer.serialize(packet, format="compact")
        
        assert "[Handoff:" in result
    
    def test_serialize_invalid_format(self):
        """Test error on invalid format."""
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        with pytest.raises(ValueError, match="Unknown format"):
            PacketSerializer.serialize(packet, format="invalid")
    
    def test_deserialize_json(self):
        """Test deserialize from JSON format."""
        original = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        json_str = PacketSerializer.to_json(original)
        restored = PacketSerializer.deserialize(json_str, format="json")
        
        assert restored.task_id == original.task_id
    
    def test_deserialize_invalid_format(self):
        """Test error on invalid deserialize format."""
        with pytest.raises(ValueError, match="Unknown format"):
            PacketSerializer.deserialize("data", format="invalid")
