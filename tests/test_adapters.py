"""Tests for framework adapters."""

import pytest
from agent_handoff_protocol import HandoffPacket, Priority
from adapters import LangGraphAdapter, CrewAIAdapter, ADKAdapter, SmolagentsAdapter


class TestLangGraphAdapter:
    """Test LangGraphAdapter."""
    
    def test_to_langgraph_state(self):
        """Test conversion to LangGraph state."""
        adapter = LangGraphAdapter()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal",
            working_memory={"key": "value"}
        )
        
        state = adapter.to_langgraph_state(packet)
        
        assert "handoff_packet" in state
        assert state["task_id"] == "task_001"
        assert state["memory_key"] == "value"
    
    def test_from_langgraph_state(self):
        """Test conversion from LangGraph state."""
        adapter = LangGraphAdapter()
        state = {
            "handoff_packet": {
                "task_id": "task_001",
                "original_goal": "Test goal"
            }
        }
        
        packet = adapter.from_langgraph_state(state)
        
        assert packet.task_id == "task_001"
        assert packet.original_goal == "Test goal"
    
    def test_from_langgraph_state_flattened(self):
        """Test conversion from flattened LangGraph state."""
        adapter = LangGraphAdapter()
        state = {
            "task_id": "task_001",
            "original_goal": "Test goal",
            "memory_key": "value"
        }
        
        packet = adapter.from_langgraph_state(state)
        
        assert packet.task_id == "task_001"
        assert packet.working_memory.get("key") == "value"
    
    def test_from_langgraph_state_strict(self):
        """Test strict mode raises error."""
        adapter = LangGraphAdapter()
        state = {"other_key": "value"}
        
        with pytest.raises(ValueError):
            adapter.from_langgraph_state(state, strict=True)
    
    def test_to_from_framework(self):
        """Test to_framework and from_framework aliases."""
        adapter = LangGraphAdapter()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        state = adapter.to_framework(packet)
        restored = adapter.from_framework(state)
        
        assert restored.task_id == packet.task_id


class TestCrewAIAdapter:
    """Test CrewAIAdapter."""
    
    def test_to_crewai_context(self):
        """Test conversion to CrewAI context."""
        adapter = CrewAIAdapter()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal",
            working_memory={"key": "value"}
        )
        
        context = adapter.to_crewai_context(packet)
        
        assert "handoff_context" in context
        assert context["task_id"] == "task_001"
        assert context["memory_key"] == "value"
    
    def test_from_crewai_context(self):
        """Test conversion from CrewAI context."""
        adapter = CrewAIAdapter()
        context = {
            "handoff_context": {
                "task_id": "task_001",
                "original_goal": "Test goal"
            }
        }
        
        packet = adapter.from_crewai_context(context)
        
        assert packet.task_id == "task_001"
    
    def test_create_task_description(self):
        """Test task description creation."""
        adapter = CrewAIAdapter()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        packet.add_completed_step("Step1", "Output1", "Agent1")
        
        description = adapter.create_task_description(packet, agent_role="Writer")
        
        assert "Test goal" in description
        assert "Step1" in description
        assert "Writer" in description
    
    def test_to_from_framework(self):
        """Test to_framework and from_framework aliases."""
        adapter = CrewAIAdapter()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        context = adapter.to_framework(packet)
        restored = adapter.from_framework(context)
        
        assert restored.task_id == packet.task_id


class TestADKAdapter:
    """Test ADKAdapter."""
    
    def test_to_adk_session_state(self):
        """Test conversion to ADK session state."""
        adapter = ADKAdapter()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        packet.add_completed_step("Step1", "Output1", "Agent1")
        
        state = adapter.to_adk_session_state(packet)
        
        assert "handoff_packet" in state
        assert state["adk_task_id"] == "task_001"
        assert len(state["adk_agent_history"]) == 1
    
    def test_from_adk_session_state(self):
        """Test conversion from ADK session state."""
        adapter = ADKAdapter()
        state = {
            "handoff_packet": {
                "task_id": "task_001",
                "original_goal": "Test goal"
            }
        }
        
        packet = adapter.from_adk_session_state(state)
        
        assert packet.task_id == "task_001"
    
    def test_from_adk_adk_keys(self):
        """Test conversion from ADK-specific keys."""
        adapter = ADKAdapter()
        state = {
            "adk_task_id": "task_001",
            "adk_original_goal": "Test goal",
            "adk_priority": "HIGH"
        }
        
        packet = adapter.from_adk_session_state(state)
        
        assert packet.task_id == "task_001"
        assert packet.priority == Priority.HIGH
    
    def test_create_adk_event(self):
        """Test ADK event creation."""
        adapter = ADKAdapter()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        event = adapter.create_adk_event(packet, "AgentA", "AgentB")
        
        assert event["type"] == "handoff"
        assert event["handoff_event"]["from_agent"] == "AgentA"
        assert event["handoff_event"]["to_agent"] == "AgentB"
    
    def test_from_adk_event(self):
        """Test conversion from ADK event."""
        adapter = ADKAdapter()
        event = {
            "type": "handoff",
            "handoff_event": {
                "packet": {
                    "task_id": "task_001",
                    "original_goal": "Test goal"
                }
            }
        }
        
        packet = adapter.from_adk_event(event)
        
        assert packet.task_id == "task_001"
    
    def test_to_from_framework(self):
        """Test to_framework and from_framework aliases."""
        adapter = ADKAdapter()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        state = adapter.to_framework(packet)
        restored = adapter.from_framework(state)
        
        assert restored.task_id == packet.task_id


class TestSmolagentsAdapter:
    """Test SmolagentsAdapter."""
    
    def test_to_smolagents_task(self):
        """Test conversion to smolagents task."""
        adapter = SmolagentsAdapter()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        packet.add_completed_step("Step1", "Output1", "Agent1")
        
        task = adapter.to_smolagents_task(packet)
        
        assert "handoff_packet" in task
        assert task["task"] == "Test goal"
        assert len(task["previous_actions"]) == 1
    
    def test_from_smolagents_task(self):
        """Test conversion from smolagents task."""
        adapter = SmolagentsAdapter()
        task_input = {
            "handoff_packet": {
                "task_id": "task_001",
                "original_goal": "Test goal"
            }
        }
        
        packet = adapter.from_smolagents_task(task_input)
        
        assert packet.task_id == "task_001"
    
    def test_from_smolagents_fields(self):
        """Test conversion from smolagents-specific fields."""
        adapter = SmolagentsAdapter()
        task_input = {
            "task": "Test goal",
            "context": {
                "task_id": "task_001",
                "priority": "CRITICAL"
            }
        }
        
        packet = adapter.from_smolagents_task(task_input)
        
        assert packet.task_id == "task_001"
        assert packet.priority == Priority.CRITICAL
    
    def test_create_agent_prompt(self):
        """Test agent prompt creation."""
        adapter = SmolagentsAdapter()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        prompt = adapter.create_agent_prompt(packet, agent_name="Coder")
        
        assert "Coder" in prompt
        assert "Test goal" in prompt
    
    def test_to_from_framework(self):
        """Test to_framework and from_framework aliases."""
        adapter = SmolagentsAdapter()
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        task = adapter.to_framework(packet)
        restored = adapter.from_framework(task)
        
        assert restored.task_id == packet.task_id


class TestAdapterRoundTrips:
    """Test round-trip conversions for all adapters."""
    
    def test_langgraph_round_trip(self):
        """Test LangGraph round-trip preserves data."""
        adapter = LangGraphAdapter()
        original = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal",
            priority=Priority.HIGH,
            working_memory={"key": "value"}
        )
        original.add_completed_step("Step1", "Output1", "Agent1")
        
        state = adapter.to_langgraph_state(original)
        restored = adapter.from_langgraph_state(state)
        
        assert restored.task_id == original.task_id
        assert restored.priority == original.priority
        assert restored.working_memory == original.working_memory
        assert len(restored.completed_steps) == len(original.completed_steps)
    
    def test_crewai_round_trip(self):
        """Test CrewAI round-trip preserves data."""
        adapter = CrewAIAdapter()
        original = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal",
            priority=Priority.MEDIUM
        )
        
        context = adapter.to_crewai_context(original)
        restored = adapter.from_crewai_context(context)
        
        assert restored.task_id == original.task_id
        assert restored.priority == original.priority
    
    def test_adk_round_trip(self):
        """Test ADK round-trip preserves data."""
        adapter = ADKAdapter()
        original = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal",
            priority=Priority.LOW
        )
        
        state = adapter.to_adk_session_state(original)
        restored = adapter.from_adk_session_state(state)
        
        assert restored.task_id == original.task_id
        assert restored.priority == original.priority
    
    def test_smolagents_round_trip(self):
        """Test smolagents round-trip preserves data."""
        adapter = SmolagentsAdapter()
        original = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal",
            priority=Priority.CRITICAL
        )
        
        task = adapter.to_smolagents_task(original)
        restored = adapter.from_smolagents_task(task)
        
        assert restored.task_id == original.task_id
        assert restored.priority == original.priority
