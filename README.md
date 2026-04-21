# Agent Handoff Protocol

> 🤖 **Autonomously built using [NEO](https://heyneo.com) — Your Autonomous AI Engineering Agent**
>
> [![VS Code Extension](https://img.shields.io/badge/VS%20Code-NEO%20Extension-007ACC?logo=visual-studio-code&logoColor=white)](https://marketplace.visualstudio.com/items?itemName=NeoResearchInc.heyneo) [![Cursor Extension](https://img.shields.io/badge/Cursor-NEO%20Extension-000000?logo=cursor&logoColor=white)](https://marketplace.cursorapi.com/items/?itemName=NeoResearchInc.heyneo)

<p align="center">
  <img src="assets/infographic.svg" alt="Agent Handoff Protocol Architecture" width="900" />
</p>

[![PyPI version](https://badge.fury.io/py/agent-handoff-protocol.svg)](https://badge.fury.io/py/agent-handoff-protocol)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A standardized protocol for passing state between agents in multi-agent AI systems. This library provides a structured way to hand off tasks, context, and intermediate results between different agents, with support for multiple popular AI frameworks.

## Problem Statement

Building multi-agent systems is becoming increasingly common, but there's no standard way for agents to communicate and pass state to each other. Each framework has its own conventions, making it difficult to:

- Build agents that can work across different frameworks
- Debug and trace the flow of work between agents
- Maintain context when handing off from one agent to another
- Cache and reuse tool results across agent boundaries

The Agent Handoff Protocol solves these problems by providing a standardized `HandoffPacket` structure that captures all the information needed for seamless agent-to-agent communication.

## Features

- 📦 **Standardized Packet Structure**: Pydantic-based `HandoffPacket` with all essential fields
- ✅ **Validation**: Built-in validation to ensure packets are well-formed
- 🔄 **Serialization**: JSON, dict, and LLM-friendly prompt formats
- 🔌 **Framework Adapters**: Native support for LangGraph, CrewAI, Google ADK, and smolagents
- 💾 **Persistence**: SQLite-based `HandoffBroker` for reliable handoff management
- 🧪 **Well Tested**: Comprehensive test suite with pytest

## ✨ New Features

### TTL & Expiry

Packets can carry a time-to-live. The broker skips expired packets and can purge them. Example stats output:

```
{'total': 1, 'pending': 1, 'expired': 0, 'delivered': 0}
```

### Audit Log

Every broker operation records an entry in the `audit_log` table. Query it programmatically or pretty-print recent events via the CLI (Rich table when installed, plain text otherwise):

```bash
handoff-cli audit --db handoffs.db --limit 20
handoff-cli audit --event expired
```

## Installation

```bash
pip install agent-handoff-protocol
```

### Optional Dependencies

For framework-specific adapters:

```bash
# For LangGraph support
pip install agent-handoff-protocol[langgraph]

# For CrewAI support
pip install agent-handoff-protocol[crewai]

# For Google ADK support
pip install agent-handoff-protocol[adk]

# For smolagents support
pip install agent-handoff-protocol[smolagents]

# Install all adapters
pip install agent-handoff-protocol[all]
```

## HandoffPacket Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | `str` | ✅ Yes | Unique identifier for the task |
| `original_goal` | `str` | ✅ Yes | The original goal/objective |
| `priority` | `Priority` | No | Task priority: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `confidence_score` | `float` | No | Confidence in outputs (0.0 - 1.0) |
| `context_summary` | `str` | No | 3-5 sentence summary of progress |
| `handoff_reason` | `str` | No | Why control is being handed off |
| `completed_steps` | `List[CompletedStep]` | No | Steps already completed |
| `remaining_steps` | `List[str]` | No | Steps still to do |
| `working_memory` | `Dict[str, Any]` | No | Key-value pairs for next agent |
| `tool_results_cache` | `Dict[str, Any]` | No | Cached tool call results |
| `created_at` | `datetime` | Auto | Creation timestamp |
| `updated_at` | `datetime` | Auto | Last update timestamp |

### CompletedStep Structure

```python
{
    "step_name": str,      # Name of the completed step
    "output": str,         # Output/result of the step
    "timestamp": str,      # ISO format timestamp
    "agent_name": str      # Agent that completed the step
}
```

## Framework Adapters

Native adapters are provided for LangGraph, CrewAI, Google ADK, and smolagents, each exposing conversions between `HandoffPacket` and the framework's native state/context/task representations.

## HandoffBroker API

The `HandoffBroker` provides persistent storage and routing for handoff packets, supporting in-memory or file-based SQLite stores, send/receive, packet history, statistics, and context-manager usage.

## 3-Agent Pipeline Example

```
┌─────────────────────────────────────────────────────────────────┐
│                    3-Agent Pipeline Flow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │   Research   │      │    Writer    │      │    Editor    │  │
│  │    Agent     │─────▶│    Agent     │─────▶│    Agent     │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│         │                     │                     │           │
│         │                     │                     │           │
│    [Research]            [Draft]              [Final]          │
│         │                     │                     │           │
│         ▼                     ▼                     ▼           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              HandoffBroker (SQLite)                      │   │
│  │  • Stores all handoffs                                  │   │
│  │  • Tracks routing metadata                              │   │
│  │  • Provides packet history                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

See `demos/demo_full_pipeline.py` for a complete working example.

## Validation

`HandoffValidator` supports both strict full validation (returning a result with `is_valid` and `errors`) and a quick boolean check.

## Serialization

`PacketSerializer` converts packets to/from JSON, dict, LLM-friendly prompt format, and compact strings.

## Development

```bash
# Clone the repository
git clone https://github.com/dakshjain-1616/agent-handoff-protocol.git
cd agent-handoff-protocol

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
black src/ tests/
ruff check src/ tests/
mypy src/

# Run demo
python demos/demo_full_pipeline.py
```

## Project Structure

```
agent-handoff-protocol/
├── src/agent_handoff_protocol/
│   ├── __init__.py          # Package exports
│   ├── packet.py            # HandoffPacket model
│   ├── validator.py         # HandoffValidator
│   ├── serializer.py        # PacketSerializer
│   └── broker.py            # HandoffBroker
├── adapters/
│   ├── __init__.py
│   ├── langgraph_adapter.py
│   ├── crewai_adapter.py
│   ├── adk_adapter.py
│   └── smolagents_adapter.py
├── tests/
│   ├── test_packet.py
│   ├── test_validator.py
│   ├── test_serializer.py
│   ├── test_adapters.py
│   └── test_broker.py
├── demos/
│   └── demo_full_pipeline.py
├── pyproject.toml
├── LICENSE
└── README.md
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the need for better inter-agent communication in multi-agent AI systems
- Built with [Pydantic](https://docs.pydantic.dev/) for robust data validation
- Framework adapters designed to work seamlessly with their respective ecosystems

## Support

- 📖 [Documentation](https://github.com/dakshjain-1616/agent-handoff-protocol/wiki)
- 🐛 [Issue Tracker](https://github.com/dakshjain-1616/agent-handoff-protocol/issues)
- 💬 [Discussions](https://github.com/dakshjain-1616/agent-handoff-protocol/discussions)

---

**Made with ❤️ for the multi-agent AI community**
