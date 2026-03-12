---
name: agent-skill
description: Generate OpenAI agents, LangGraph workflows, agent state models, and tool interactions. Use when creating agents, implementing LangGraph nodes, or when the user mentions research agent, coding agent, or multi-agent coordination.
---

# Agent Skill – AI Agent Platform

## When this skill applies

Use this skill when generating:

- agents
- LangGraph workflows
- agent state models
- tool interactions
- multi-agent coordination

---

# Agent Technology

**All agents are OpenAI agents.** Use OpenAI models (GPT-4, etc.) for agent reasoning and execution.

---

# Agent Design Philosophy

Agents are **specialized** components — each agent is expert in a particular domain (research, coding, summarization, etc.).

Agents must:

- solve a specific problem
- be modular
- be stateless
- produce structured outputs

Agents must never contain API logic or infrastructure code.

---

# Agent-to-User Communication

**Agents never talk to user directly.** All agent-to-user communication goes through the Supervisor.

- When an agent faces issues, it reports to Supervisor
- When an agent needs to ask the user something, it sends a message to Supervisor
- Supervisor relays to user and routes user response back to the agent
- Agents must use the Supervisor interface for any user interaction

---

# Agent Implementation Standard

All agents must be implemented using **LangGraph + OpenAI**. Each agent must define:

1. State schema
2. Graph nodes
3. Graph builder
4. Execution entrypoint

---

# Agent State

Agent state must use **Pydantic models**.

```python
from typing import Optional
from pydantic import BaseModel

class AgentState(BaseModel):
    task: str
    result: Optional[str] = None
```
