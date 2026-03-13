---
name: coding-skill
description: Generate Python code, API services, agents, workflows, workers, tools, and data models for the AI Agent Platform. Use when writing code, implementing features, or when the user mentions Python, FastAPI, Pydantic, or LangGraph.
---

# Code Skill -- AI Agent Platform

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

- Python >= 3.14
- Current runtime: **Python 3.14**

## Frameworks

- **FastAPI** -- async API services
- **LangChain** -- agent creation (`langchain.agents.create_agent`)
- **LangGraph** -- supervisor orchestration (`StateGraph` with async `ainvoke`)
- **LLM providers** -- provider-agnostic via `shared/llm.py` factory (OpenAI, Anthropic, Google, Ollama, Groq)
- **Pydantic v2** -- schema validation and models
- **SQLAlchemy 2.0** -- ORM (declarative mapped columns)

## Infrastructure

- Redis -- task queues (Redis Streams) and pub/sub
- PostgreSQL -- persistent storage (sessions, workflows)
- Docker -- runtime environment

## Package Manager

- **uv**

### Rules

- Do NOT introduce alternative LLM frameworks (use LangChain's BaseChatModel interface).
- Do NOT replace LangGraph or LangChain.
- Do NOT hardcode `ChatOpenAI` -- always use `get_llm()` from `shared/llm.py`.
- Do NOT introduce unnecessary libraries.
- Prefer Python standard library where possible.
- **Always update README.md and relevant docs after changes** (see `change-docs-skill`).

---

# Python Coding Standards

All code must follow **modern Python 3.14 practices**.

## Required

- All functions must include **type hints**
- All public classes must define typed attributes
- All return types must be explicit
- Code must be compatible with **Python 3.14**

---

# Typing Standards

Use **built-in generics** (Python 3.10+ style) for type hints. Only import from `typing` for special types.

```python
from typing import Any, Optional

def process_tasks(tasks: list[str]) -> dict[str, int]:
    ...

def find_item(id: str) -> Optional[str]:
    ...

def handler(fn: callable) -> None:
    ...
```

Prefer built-in generics (`list`, `dict`, `set`, `tuple`) over `typing` equivalents (`List`, `Dict`, `Set`, `Tuple`).

---

# Logging Standards

**Every module must include structured, timestamped logging.** Logs are written to both console and `logs/platform.log` via the centralized config in `shared/logging_config.py`.

## Required

- Every Python module that does meaningful work must create a logger: `logger = logging.getLogger(__name__)`
- Every major function must log START (with key inputs) and DONE (with timing and key outputs)
- Use `time.perf_counter()` to measure elapsed time in seconds
- Use a bracketed prefix tag to identify the component: `[gateway]`, `[classify]`, `[plan]`, `[execute]`, etc.
- Log errors with full context: input values, elapsed time, and error message
- Never log secrets, API keys, or full user data -- truncate messages with `[:120]`

## Log format

Logs follow this format (configured automatically):

```
2026-03-13 22:01:46.906 | INFO    | module.name | [tag] message
```

## Logging pattern

```python
import logging
import time

logger = logging.getLogger(__name__)

def my_function(input: str) -> str:
    t0 = time.perf_counter()
    logger.info("[my_component] START | input=%s", input[:120])

    # ... do work ...

    logger.info("[my_component] DONE  | result_len=%d | %.2fs", len(result), time.perf_counter() - t0)
    return result
```

## Error logging

```python
try:
    result = do_something()
except Exception as e:
    logger.exception("[my_component] FAILED | input=%s | %.2fs: %s", input[:120], time.perf_counter() - t0, e)
    raise
```

## Rules

- Do NOT use `print()` for logging. Always use the `logging` module.
- Do NOT call `logging.basicConfig()` in any module. The centralized `setup_logging()` in `shared/logging_config.py` handles all configuration.
- Do NOT log at DEBUG level for normal operations. Use INFO for major steps, DEBUG for detailed internals.
- Log at WARNING for recoverable issues, ERROR for failures, and EXCEPTION (which includes traceback) for unexpected errors.

---

# Key Patterns

## LLM instantiation (provider-agnostic)

```python
from shared.llm import get_llm, is_llm_available

if is_llm_available("my_component"):
    llm = get_llm("my_component", temperature=0)
    response = await llm.ainvoke(prompt)
```

Never import `ChatOpenAI` directly. The `get_llm()` factory reads `LLM_PROVIDER` / `LLM_MODEL` env vars and supports per-component overrides like `LLM_PROVIDER__AGENTS`.

## Agent creation (async)

```python
from services.agents.base_agent import create_react_agent

SYSTEM_PROMPT = "You are a ..."
_agent = create_react_agent("agent_type", SYSTEM_PROMPT)

async def run(message: str) -> str:
    return await _agent(message)
```

## LangGraph nodes (async)

```python
import logging
import time
from services.orchestrator.supervisor.state import WorkflowState

logger = logging.getLogger(__name__)

async def my_node(state: WorkflowState) -> WorkflowState:
    t0 = time.perf_counter()
    logger.info("[my_node] START | goal=%s", state.get("goal", "")[:120])

    # ... process state (use await for LLM/IO calls) ...

    logger.info("[my_node] DONE  | %.2fs", time.perf_counter() - t0)
    return {**state, "field": new_value}
```

## MCP tools

```python
from langchain_core.tools import tool

@tool
def tool_my_tool(input: str) -> str:
    """Description for LLM tool selection."""
    return result
```

## Pydantic schemas

```python
from pydantic import BaseModel, Field

class MyRequest(BaseModel):
    message: str = Field(..., description="User message")
    option: str = Field(default="default", description="Optional setting")
```

## SQLAlchemy models

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from shared.models.base import Base, TimestampMixin, generate_uuid

class MyModel(TimestampMixin, Base):
    __tablename__ = "my_table"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
```
