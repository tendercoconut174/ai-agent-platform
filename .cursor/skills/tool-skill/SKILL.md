---
name: tool-skill
description: Generate tools, external API integrations, MCP-compatible tool interfaces, and capability modules for agents. Use when creating tools, integrating APIs, or when the user mentions web search, code execution, or agent capabilities.
---

# Tool Skill – AI Agent Platform

## When this skill applies

Use this skill when generating:

- tools
- integrations with external APIs
- utilities used by agents
- MCP-compatible tool interfaces
- capability modules used by agents

---

# Tool Philosophy

Tools provide **capabilities to agents**. Agents decide *what to do*. Tools implement *how to do it*.

Tools must remain **simple, deterministic, and reusable**.

---

# MCP Compliance

All tools must follow **Model Context Protocol (MCP)** principles:

- tools must expose a clear callable interface
- tools must accept structured input
- tools must return structured output
- tools must remain stateless

Agents must interact with tools through these interfaces. Agents must not call external APIs directly.

---

# Tool Design Rules

Each tool must:

1. perform a single responsibility
2. have clear inputs
3. produce structured outputs
4. be deterministic
5. avoid side effects when possible

Tools must not contain agent logic or orchestration.

---

# Tool Input Models

Tool inputs must be defined using **Pydantic models**.

```python
from pydantic import BaseModel

class SearchInput(BaseModel):
    query: str
    limit: int = 5

class SearchOutput(BaseModel):
    results: list[str]
    count: int
```
