---
name: coding-skill
description: Generate Python code, API services, agents, workflows, workers, tools, and data models for the AI Agent Platform. Use when writing code, implementing features, or when the user mentions Python, FastAPI, Pydantic, or LangGraph.
---

# Code Skill – AI Agent Platform

## When this skill applies

Use this skill whenever generating:

- Python code
- API services
- agents
- workflows
- background workers
- tools
- data models
- infrastructure integration code

All generated code must follow the standards defined in this document.

---

# Core Technology Stack

## Language

- Python ≥ 3.11
- Current runtime: **Python 3.14**

## Frameworks

- **FastAPI** — API services
- **OpenAI** — all agents (Planner, specialized agents)
- **Pydantic v2** — schema validation and models
- **LangGraph** — agent orchestration
- **MCP (Model Context Protocol)** — tool interfaces

## Infrastructure

- Redis — task queues
- PostgreSQL — primary database
- Docker — runtime environment

## Package Manager

- **uv**

### Rules

- Do NOT introduce alternative frameworks.
- Do NOT replace LangGraph.
- Do NOT introduce unnecessary libraries.
- Prefer Python standard library where possible.

---

# Python Coding Standards

All code must follow **modern Python practices**.

## Required

- All functions must include **type hints**
- All public classes must define typed attributes
- All return types must be explicit
- Code must be compatible with **Python 3.14**

---

# Typing Standards

Use the **`typing`** module for all type hints.

Import from `typing`:

- `List`, `Dict`, `Set`, `Tuple` for collections
- `Optional` for nullable types
- `Union` for union types
- `Any` when type is dynamic
- `Callable` for function types

```python
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

def process_tasks(tasks: List[str]) -> Dict[str, int]:
    ...

def find_item(id: str) -> Optional[str]:
    ...

def handler(fn: Callable[[str], bool]) -> None:
    ...
```

Prefer `typing` types over built-in generics (`list`, `dict`) for consistency.
