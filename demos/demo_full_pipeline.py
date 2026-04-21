#!/usr/bin/env python
"""
Full Pipeline Demo: 3-Agent Handoff Simulation

This demo simulates a content creation pipeline with three agents:
1. Research Agent - Gathers information and creates initial context
2. Writer Agent - Creates a draft based on research
3. Editor Agent - Finalizes and polishes the content

All agents use the HandoffBroker to pass state between each other.
"""

import os
import sys
from datetime import datetime

# Allow running directly from a source checkout without `pip install -e .`
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO_ROOT, "src")
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from agent_handoff_protocol import HandoffPacket, Priority, HandoffBroker, PacketSerializer


def print_section(title: str, char: str = "="):
    """Print a section header."""
    print(f"\n{char * 60}")
    print(f"  {title}")
    print(f"{char * 60}\n")


def simulate_research_agent(broker: HandoffBroker, task_id: str) -> HandoffPacket:
    """
    Simulate the Research Agent.
    
    This agent:
    - Receives the initial task
    - Performs research (simulated)
    - Creates a HandoffPacket with research results
    - Hands off to the Writer Agent
    """
    print_section("STEP 1: Research Agent", "=")
    print("Research Agent is gathering information...")
    
    # Create initial packet with research results
    packet = HandoffPacket(
        task_id=task_id,
        original_goal="Write a comprehensive blog post about multi-agent AI systems",
        priority=Priority.HIGH,
        context_summary=(
            "The task is to write a blog post about multi-agent AI systems. "
            "Research has been conducted on current frameworks including LangGraph, "
            "CrewAI, Google ADK, and smolagents. Key findings include the importance "
            "of state management, agent communication protocols, and handoff mechanisms "
            "for building effective multi-agent systems."
        ),
        handoff_reason="Research phase complete. Handing off to Writer Agent to create the draft.",
        confidence_score=0.95,
        remaining_steps=[
            "Create blog post draft based on research",
            "Edit and polish the final content",
            "Add formatting and publish"
        ]
    )
    
    # Add research as completed steps
    packet.add_completed_step(
        step_name="Framework Research",
        output="Analyzed LangGraph, CrewAI, ADK, and smolagents. Key insight: state management is critical.",
        agent_name="ResearchAgent"
    )
    
    packet.add_completed_step(
        step_name="Topic Analysis",
        output="Identified 5 key themes: coordination, communication, state passing, error handling, and scalability.",
        agent_name="ResearchAgent"
    )
    
    # Add working memory with key research findings
    packet.update_working_memory("frameworks", ["LangGraph", "CrewAI", "ADK", "smolagents"])
    packet.update_working_memory("key_themes", ["coordination", "communication", "state passing", "error handling", "scalability"])
    packet.update_working_memory("target_audience", "AI developers and architects")
    packet.update_working_memory("tone", "technical but accessible")
    
    # Cache some tool results (simulated)
    packet.cache_tool_result("web_search_001", {
        "query": "multi-agent AI systems 2024",
        "results": 150,
        "top_sources": ["arxiv.org", "openai.com", "langchain.ai"]
    })
    
    # Send to Writer Agent via broker
    broker.send(packet, from_agent="ResearchAgent", to_agent="WriterAgent")
    print(f"✓ Research complete. Packet sent to WriterAgent (ID: {packet.task_id})")
    
    return packet


def simulate_writer_agent(broker: HandoffBroker) -> HandoffPacket:
    """
    Simulate the Writer Agent.
    
    This agent:
    - Receives the packet from Research Agent
    - Creates a blog post draft
    - Updates the packet with the draft
    - Hands off to the Editor Agent
    """
    print_section("STEP 2: Writer Agent", "=")
    print("Writer Agent is receiving handoff from Research Agent...")
    
    # Receive packet from broker using receive_with_metadata to get routing info
    result = broker.receive_with_metadata("WriterAgent")
    if not result:
        raise RuntimeError("No packet received for WriterAgent")
    
    packet, routing_info = result
    print(f"✓ Received packet from {routing_info['from_agent']}")
    print(f"  Task: {packet.original_goal}")
    print(f"  Confidence: {packet.confidence_score:.0%}")
    
    # Print what the Writer Agent sees
    print("\n--- What Writer Agent Receives (Prompt Format) ---")
    print(PacketSerializer.to_prompt_format(packet))
    print("--- End of Prompt ---\n")
    
    # Simulate writing
    print("Writer Agent is creating the draft...")
    
    # Add writing step
    packet.add_completed_step(
        step_name="Draft Creation",
        output="Created comprehensive 800-word draft covering all 5 key themes with code examples.",
        agent_name="WriterAgent"
    )
    
    # Update context and handoff reason
    packet.context_summary = (
        f"{packet.context_summary} The Writer Agent has created a comprehensive draft "
        "incorporating all research findings. The draft includes an introduction, "
        "sections on each framework, comparison analysis, and best practices."
    )
    packet.handoff_reason = "Draft complete. Handing off to Editor Agent for final polish."
    packet.confidence_score = 0.88
    
    # Update remaining steps
    packet.remaining_steps = [
        "Edit and polish the final content",
        "Add formatting and publish"
    ]
    
    # Add draft to working memory
    packet.update_working_memory("draft_word_count", 800)
    packet.update_working_memory("sections_written", ["Introduction", "Framework Overview", "Comparison", "Best Practices", "Conclusion"])
    packet.update_working_memory("draft_status", "ready_for_editing")
    
    # Send to Editor Agent via broker
    broker.send(packet, from_agent="WriterAgent", to_agent="EditorAgent")
    print(f"✓ Draft complete. Packet sent to EditorAgent")
    
    return packet


def simulate_editor_agent(broker: HandoffBroker) -> HandoffPacket:
    """
    Simulate the Editor Agent.
    
    This agent:
    - Receives the packet from Writer Agent
    - Edits and polishes the content
    - Finalizes the task
    """
    print_section("STEP 3: Editor Agent", "=")
    print("Editor Agent is receiving handoff from Writer Agent...")
    
    # Receive packet from broker using receive_with_metadata to get routing info
    result = broker.receive_with_metadata("EditorAgent")
    if not result:
        raise RuntimeError("No packet received for EditorAgent")
    
    packet, routing_info = result
    print(f"✓ Received packet from {routing_info['from_agent']}")
    print(f"  Draft sections: {packet.working_memory.get('sections_written', [])}")
    
    # Print what the Editor Agent sees
    print("\n--- What Editor Agent Receives (Prompt Format) ---")
    print(PacketSerializer.to_prompt_format(packet))
    print("--- End of Prompt ---\n")
    
    # Simulate editing
    print("Editor Agent is polishing the content...")
    
    # Add editing step
    packet.add_completed_step(
        step_name="Content Editing",
        output="Improved clarity, fixed grammar, enhanced code examples, added formatting.",
        agent_name="EditorAgent"
    )
    
    packet.add_completed_step(
        step_name="Final Review",
        output="Final content approved. Ready for publication.",
        agent_name="EditorAgent"
    )
    
    # Update context and finalize
    packet.context_summary = (
        f"{packet.context_summary} The Editor Agent has polished the content, "
        "improving clarity and formatting. The blog post is now complete and ready for publication."
    )
    packet.handoff_reason = "Task complete. Content finalized and ready for publication."
    packet.confidence_score = 0.98
    
    # Clear remaining steps
    packet.remaining_steps = []
    
    # Update working memory
    packet.update_working_memory("final_word_count", 850)
    packet.update_working_memory("edits_made", ["grammar fixes", "clarity improvements", "code formatting", "added conclusion"])
    packet.update_working_memory("status", "published")
    
    # Send completion notification (optional - could send to a Publisher Agent)
    broker.send(packet, from_agent="EditorAgent", to_agent="PublisherAgent")
    print(f"✓ Editing complete. Final content ready for publication!")
    
    return packet


def simulate_publisher_agent(broker: HandoffBroker) -> HandoffPacket:
    """
    Simulate the Publisher Agent.

    Receives the finalized packet from the Editor Agent and publishes it.
    """
    print_section("STEP 4: Publisher Agent", "=")
    print("Publisher Agent is receiving handoff from Editor Agent...")

    result = broker.receive_with_metadata("PublisherAgent")
    if not result:
        raise RuntimeError("No packet received for PublisherAgent")

    packet, routing_info = result
    print(f"Received packet from {routing_info['from_agent']}")
    print(f"  Word count: {packet.working_memory.get('final_word_count')}")
    print(f"  Status: {packet.working_memory.get('status')}")

    packet.add_completed_step(
        step_name="Publication",
        output="Content published to production. URL: https://example.com/posts/multi-agent-systems",
        agent_name="PublisherAgent",
    )
    packet.handoff_reason = "Task complete. Content published."
    packet.confidence_score = 1.0
    packet.update_working_memory("published_url", "https://example.com/posts/multi-agent-systems")
    print("Publication complete.")
    return packet


def print_final_summary(broker: HandoffBroker, task_id: str):
    """Print a summary of the entire pipeline."""
    print_section("Pipeline Summary", "=")
    
    # Get stats from broker
    stats = broker.get_stats()
    print(f"Total handoffs: {stats['total_packets']}")
    print(f"Unique agents involved: {stats['unique_from_agents'] + stats['unique_to_agents']}")
    
    # Get full history for this task
    history = broker.get_packet_history(task_id)
    print(f"\nHandoff History for Task '{task_id}':")
    print("-" * 50)
    
    for i, (packet, routing) in enumerate(history, 1):
        print(f"\n{i}. {routing['from_agent']} → {routing['to_agent']}")
        print(f"   Timestamp: {routing['sent_timestamp']}")
        print(f"   Completed steps so far: {len(packet.completed_steps)}")
        print(f"   Remaining steps: {len(packet.remaining_steps)}")
        print(f"   Confidence: {packet.confidence_score:.0%}")
    
    print("\n" + "=" * 60)
    print("Demo complete! The 4-agent pipeline executed successfully.")
    print("=" * 60)


def main():
    """Run the full pipeline demo."""
    print("=" * 60)
    print("  Agent Handoff Protocol - Full Pipeline Demo")
    print("=" * 60)
    print("\nThis demo simulates a 4-agent content creation pipeline:")
    print("  1. Research Agent -> 2. Writer Agent -> 3. Editor Agent -> 4. Publisher Agent")
    print()
    
    # Initialize broker with in-memory database
    broker = HandoffBroker()
    
    # Generate unique task ID
    task_id = f"blog_post_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Run the pipeline
        simulate_research_agent(broker, task_id)
        simulate_writer_agent(broker)
        simulate_editor_agent(broker)
        simulate_publisher_agent(broker)
        
        # Print summary
        print_final_summary(broker, task_id)
        
        # Show compact format of final packet
        print("\n--- Final Packet (Compact Format) ---")
        final_history = broker.get_packet_history(task_id)
        if final_history:
            final_packet = final_history[-1][0]
            print(PacketSerializer.to_compact_string(final_packet))
        
    finally:
        # Clean up
        broker.close()


if __name__ == "__main__":
    main()
