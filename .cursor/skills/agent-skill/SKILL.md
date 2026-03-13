---
name: agent-skill
description: Generate agents, agent configurations, system prompts, and agent registry entries. Use when creating agents, modifying agent behavior, or when the user mentions research agent, coding agent, chat agent, or multi-agent coordination.
---

# Agent Skill -- AI Agent Platform

## When this skill applies

Use this skill when generating:

- new agents or modifying existing agents
- system prompts for agents
- agent registry entries
- agent-to-tool bindings
- multi-agent coordination logic

---

# Agent Technology

All agents use **LangChain ReAct agents** (`langchain.agents.create_agent`) backed by **OpenAI models** (default `gpt-4o-mini`). Each agent is created via the shared factory in `services/agents/base_agent.py`.

---

# Agent Design Philosophy

Agents are **specialized** components -- each agent is expert in a particular domain (research, analysis, code, generation, monitoring, chat).

Agents must:

- solve a specific problem
- be modular and stateless
- produce string output
- access external systems only through MCP tools

Agents must never contain API logic, infrastructure code, or database access.

---

# Agent-to-User Communication

**Agents never talk to the user directly.** All agent-to-user communication goes through the Supervisor (LangGraph StateGraph).

- Agents return results to the Supervisor via the execute node
- The Supervisor evaluates results and decides whether to replan or deliver
- The Delivery Service formats the final output for the user

---

# Agent Implementation Standard

All agents follow this pattern:

```python
# services/agents/my_agent.py
from services.agents.base_agent import create_react_agent

SYSTEM_PROMPT = (
    "You are a specialist in ...\n\n"
    "Guidelines:\n"
    "- Use tool_name to ...\n"
    "- Produce structured output\n"
)

_agent = create_react_agent("my_agent", SYSTEM_PROMPT)

def run(message: str) -> str:
    return _agent(message)
```

After creating the agent file:

1. Register it in `services/agents/registry.py`
2. Assign tools in `shared/mcp/server.py` `TOOL_REGISTRY`

---

# Current Agent Pool

| Agent | File | Tools | Purpose |
|-------|------|-------|---------|
| research | `research_agent.py` | web_search, scrape_url | Web search and data gathering |
| analysis | `analysis_agent.py` | web_search, execute_python, read_file | Summarization, comparison |
| generator | `generator_agent.py` | web_search, write_file, read_file, execute_python | Report/document creation |
| code | `code_agent.py` | execute_python, read_file, write_file, list_files | Calculations, data processing |
| monitor | `monitor_agent.py` | web_search, scrape_url | Long-running observation |
| chat | `chat_agent.py` | (none) | Casual conversation |

---

# Agent State

The Supervisor manages workflow state via `WorkflowState` (TypedDict). Individual agents are stateless -- they receive a message string and return a result string.

```python
class WorkflowState(TypedDict, total=False):
    goal: str
    output_format: str
    intent: str              # casual | simple | complex | monitor
    plan: Optional[ExecutionPlan]
    step_results: list[StepResult]
    iteration_count: int
    goal_achieved: bool
    final_result: Optional[str]
```

---

# Key Files

- `services/agents/base_agent.py` -- ReAct agent factory
- `services/agents/registry.py` -- Agent type → runner mapping
- `services/agents/*.py` -- Individual agent definitions
- `shared/mcp/server.py` -- Tool registry (agent type → tools)
- `services/orchestrator/supervisor/nodes/execute.py` -- Agent execution with dependency resolution
