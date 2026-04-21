"""Tests for HandoffBroker."""

import pytest
import os
import tempfile
from agent_handoff_protocol import HandoffPacket, Priority, HandoffBroker


class TestHandoffBrokerBasic:
    """Test basic HandoffBroker functionality."""
    
    def test_broker_in_memory(self):
        """Test broker with in-memory database."""
        broker = HandoffBroker()
        
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        packet_id = broker.send(packet, "AgentA", "AgentB")
        
        assert packet_id > 0
        
        broker.close()
    
    def test_broker_with_file(self):
        """Test broker with file-based database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            broker = HandoffBroker(db_path=db_path)
            
            packet = HandoffPacket(
                task_id="task_001",
                original_goal="Test goal"
            )
            
            broker.send(packet, "AgentA", "AgentB")
            broker.close()
            
            # Verify file exists and has content
            assert os.path.exists(db_path)
            assert os.path.getsize(db_path) > 0
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_context_manager(self):
        """Test broker as context manager."""
        with HandoffBroker() as broker:
            packet = HandoffPacket(
                task_id="task_001",
                original_goal="Test goal"
            )
            broker.send(packet, "AgentA", "AgentB")


class TestSendReceive:
    """Test send and receive operations."""
    
    def test_send_and_receive(self):
        """Test sending and receiving a packet."""
        broker = HandoffBroker()
        
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        broker.send(packet, "AgentA", "AgentB")
        
        received_packet = broker.receive("AgentB")
        
        assert received_packet is not None
        assert received_packet.task_id == "task_001"
        # Check routing metadata is stored in working_memory
        assert "_routing" in received_packet.working_memory
        assert received_packet.working_memory["_routing"]["from_agent"] == "AgentA"
        assert received_packet.working_memory["_routing"]["to_agent"] == "AgentB"
        
        broker.close()
    
    def test_receive_no_packet(self):
        """Test receiving when no packet exists."""
        broker = HandoffBroker()
        
        received = broker.receive("NonExistentAgent")
        
        assert received is None
        
        broker.close()
    
    def test_receive_multiple(self):
        """Test receiving multiple packets."""
        broker = HandoffBroker()
        
        packet1 = HandoffPacket(task_id="task_001", original_goal="Goal 1")
        packet2 = HandoffPacket(task_id="task_002", original_goal="Goal 2")
        
        broker.send(packet1, "AgentA", "AgentB")
        broker.send(packet2, "AgentA", "AgentB")
        
        # Should receive latest
        received = broker.receive("AgentB")
        assert received is not None
        assert received.task_id == "task_002"
        
        broker.close()
    
    def test_receive_all(self):
        """Test receiving all packets for an agent."""
        broker = HandoffBroker()
        
        packet1 = HandoffPacket(task_id="task_001", original_goal="Goal 1")
        packet2 = HandoffPacket(task_id="task_002", original_goal="Goal 2")
        
        broker.send(packet1, "AgentA", "AgentB")
        broker.send(packet2, "AgentA", "AgentB")
        
        all_packets = broker.receive_all("AgentB")
        
        assert len(all_packets) == 2
        
        broker.close()
    
    def test_receive_unread_only(self):
        """Test receiving only unread packets."""
        broker = HandoffBroker()
        
        packet1 = HandoffPacket(task_id="task_001", original_goal="Goal 1")
        packet2 = HandoffPacket(task_id="task_002", original_goal="Goal 2")
        
        broker.send(packet1, "AgentA", "AgentB")
        broker.send(packet2, "AgentA", "AgentB")
        
        # Receive one
        broker.receive("AgentB")
        
        # Get only unread
        unread = broker.receive_all("AgentB", unread_only=True)
        
        assert len(unread) == 1
        
        broker.close()


class TestPacketHistory:
    """Test packet history functionality."""
    
    def test_get_packet_history(self):
        """Test getting history for a task."""
        broker = HandoffBroker()
        
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        broker.send(packet, "AgentA", "AgentB")
        broker.send(packet, "AgentB", "AgentC")
        
        history = broker.get_packet_history("task_001")
        
        assert len(history) == 2
        
        broker.close()
    
    def test_get_packet_history_exclude_received(self):
        """Test getting history excluding received packets."""
        broker = HandoffBroker()
        
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        broker.send(packet, "AgentA", "AgentB")
        broker.receive("AgentB")  # Mark as received
        broker.send(packet, "AgentB", "AgentC")
        
        history = broker.get_packet_history("task_001", include_received=False)
        
        assert len(history) == 1
        
        broker.close()


class TestBrokerStats:
    """Test broker statistics."""
    
    def test_get_stats(self):
        """Test getting broker statistics."""
        broker = HandoffBroker()
        
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        broker.send(packet, "AgentA", "AgentB")
        broker.send(packet, "AgentB", "AgentC")
        broker.receive("AgentB")
        
        stats = broker.get_stats()
        
        assert stats["total_packets"] == 2
        assert stats["received_packets"] == 1
        assert stats["pending_packets"] == 1
        assert stats["unique_from_agents"] == 2
        assert stats["unique_to_agents"] == 2
        assert stats["unique_tasks"] == 1
        
        broker.close()
    
    def test_get_stats_empty(self):
        """Test stats with empty broker."""
        broker = HandoffBroker()
        
        stats = broker.get_stats()
        
        assert stats["total_packets"] == 0
        assert stats["received_packets"] == 0
        
        broker.close()


class TestRoutingMetadata:
    """Test routing metadata functionality."""
    
    def test_send_with_metadata(self):
        """Test sending with routing metadata."""
        broker = HandoffBroker()
        
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        metadata = {"priority": "high", "source": "api"}
        broker.send(packet, "AgentA", "AgentB", metadata=metadata)
        
        received_packet = broker.receive("AgentB")
        
        assert received_packet is not None
        # Check routing metadata is in working_memory['_routing']
        assert "_routing" in received_packet.working_memory
        assert received_packet.working_memory["_routing"]["metadata"] == metadata
        
        broker.close()


class TestReceiveWithMetadata:
    """Test receive_with_metadata method."""
    
    def test_receive_with_metadata_returns_tuple(self):
        """Test receive_with_metadata returns tuple with routing info."""
        broker = HandoffBroker()
        
        packet = HandoffPacket(
            task_id="task_001",
            original_goal="Test goal"
        )
        
        broker.send(packet, "AgentA", "AgentB")
        
        result = broker.receive_with_metadata("AgentB")
        
        assert result is not None
        received_packet, routing_info = result
        
        assert received_packet.task_id == "task_001"
        assert routing_info["from_agent"] == "AgentA"
        assert routing_info["to_agent"] == "AgentB"
        # Routing info should also be in working_memory
        assert "_routing" in received_packet.working_memory
        
        broker.close()
    
    def test_receive_with_metadata_no_packet(self):
        """Test receive_with_metadata when no packet exists."""
        broker = HandoffBroker()
        
        result = broker.receive_with_metadata("NonExistentAgent")
        
        assert result is None
        
        broker.close()


class TestPacketPreservation:
    """Test that packet data is preserved correctly."""
    
    def test_complex_packet_preserved(self):
        """Test that complex packet data is preserved."""
        broker = HandoffBroker()
        
        original = HandoffPacket(
            task_id="task_001",
            original_goal="Complex task",
            priority=Priority.HIGH,
            confidence_score=0.85,
            context_summary="Summary text",
            handoff_reason="Reason text",
            remaining_steps=["step1", "step2"],
            working_memory={"key1": "value1", "key2": [1, 2, 3]},
            tool_results_cache={"tool1": {"result": "data"}}
        )
        original.add_completed_step("Step1", "Output1", "Agent1")
        original.add_completed_step("Step2", "Output2", "Agent2")
        
        broker.send(original, "AgentA", "AgentB")
        
        received = broker.receive("AgentB")
        assert received is not None
        packet = received
        
        assert packet.task_id == original.task_id
        assert packet.priority == original.priority
        assert packet.confidence_score == original.confidence_score
        assert packet.context_summary == original.context_summary
        assert packet.handoff_reason == original.handoff_reason
        assert packet.remaining_steps == original.remaining_steps
        # working_memory should contain original data plus _routing
        assert packet.working_memory["key1"] == "value1"
        assert packet.working_memory["key2"] == [1, 2, 3]
        assert "_routing" in packet.working_memory
        assert packet.tool_results_cache == original.tool_results_cache
        assert len(packet.completed_steps) == len(original.completed_steps)
        
        broker.close()
