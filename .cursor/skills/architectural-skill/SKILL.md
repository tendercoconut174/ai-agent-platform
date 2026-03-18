---
name: architectural-skill
description: Generate services, agents, workflows, and orchestration logic. Use when designing services, architecture, or when the user mentions gateway, supervisor, orchestrator, planner, or delivery.
---

# Architecture Skill -- AI Agent Platform

## When this skill applies

Use this skill when generating:

- services
- agents
- workflows
- orchestration logic
- infrastructure code

---

# Target Architecture

The system is a **goal-oriented multi-agent platform** with two FastAPI services, a LangGraph supervisor, and an MCP tool layer.

**Full flow:**

```
User / Adapter (REST, WhatsApp, Slack...)
  │
  ▼
Gateway (FastAPI, port 8000)
  ├── Input Processor (text, voice, image, files → text)
  ├── Session Manager (PostgreSQL / in-memory fallback)
  │
  ▼
Orchestrator (FastAPI, port 8001)
  └── Supervisor (LangGraph StateGraph)
        classify → [chat_respond | ask_user | plan → execute → evaluate → [replan | deliver]]
        │
        └── Agent Pool → MCP Tools
  │
  ▼
Delivery Service (JSON / PDF / Excel / Audio)
  │
  ▼
User
```

---

# Architecture Rules

1. Services must remain loosely coupled.
2. Gateway communicates with Orchestrator via HTTP (httpx).
3. Agents are stateless -- they receive a message and return a string.
4. Agents must not access databases directly.
5. Agents interact with external systems only through MCP tools.
6. API services must remain thin.
7. The Supervisor (LangGraph graph) is the single orchestration point.
8. All output formatting is handled by the Delivery Service.

---

# System Layers

## 1. Gateway (`services/gateway/`)

- FastAPI endpoints: `POST /message`, `POST /message/upload`
- Input processing: multi-modal → text
- Session management: PostgreSQL with in-memory fallback
- Format inference: detects "give me pdf/excel" in messages
- File delivery: returns binary downloads for PDF/Excel/audio
- Must not contain business logic or orchestration

## 2. Orchestrator (`services/orchestrator/`)

- FastAPI endpoint: `POST /orchestrate`
- Contains the LangGraph Supervisor graph
- Graph nodes: classify, chat_respond, ask_user (human-in-the-loop), plan, execute, evaluate, deliver
- Goal-oriented: replans if evaluation determines goal not achieved (max 5 iterations)
- Plans are DAGs of PlanSteps with agent types and dependencies

## 3. Agent Pool (`services/agents/`)

- **CrewAI sub-agents** (research, analysis, generator, code, monitor): Implemented as CrewAI crews in `crewai_agents.py`. Each crew has one agent with role, goal, backstory. MCP tools (LangChain `@tool`) are converted via `Tool.from_langchain()` before passing to CrewAI.
- **Special agents**: chat (simple LLM), plan_execute (planner + CrewAI analysis executor), scheduler (scheduler-specific logic)
- Registered in `services/agents/registry.py`; registry maps agent types to async runners

## 4. MCP Tools (`shared/mcp/`)

- Tool server with LangChain `@tool` wrappers
- Raw implementations in `shared/mcp/tools/`
- Tools: web_search, scrape_url, code_executor, file_io, media_processor
- `TOOL_REGISTRY` maps agent types to allowed tool subsets

## 5. Delivery Service (`services/delivery/`)

- Converts text results to PDF (fpdf2), Excel (openpyxl), Audio (OpenAI TTS)
- Returns base64-encoded content for binary formats
- Gateway decodes and returns as file download

## 6. Database (`database/`)

- PostgreSQL + SQLAlchemy + Alembic
- Tables: sessions, message_history, workflows, workflow_steps
- Session manager gracefully falls back to in-memory when DB unavailable

---

# Agent Communication Rules

- Agents never talk to the user directly.
- The execute node dispatches agents and collects results.
- The evaluate node determines if the goal is achieved.
- If not achieved, the supervisor replans and re-executes.
- The deliver node passes the final result to the Delivery Service.

---

# Project Structure

```
main.py                              # CLI: gateway, orchestrator, migrate
services/
  gateway/                           # FastAPI API (port 8000)
    api/routes.py                    #   /message, /message/upload
    api/orchestrator_client.py       #   httpx client for orchestrator
    input_processor.py               #   Multi-modal input handling
    session_manager.py               #   Session + message history
  orchestrator/                      # FastAPI orchestrator (port 8001)
    api/routes.py                    #   /orchestrate
    supervisor/
      graph.py                       #   LangGraph StateGraph
      state.py                       #   WorkflowState, PlanStep, ExecutionPlan
      nodes/                         #   classify, plan, execute, evaluate, deliver
  agents/                            # Agent pool
    crewai_agents.py                 #   CrewAI crews (research, analysis, generator, code, monitor)
    registry.py                      #   Agent type → runner
    chat_agent.py, plan_execute_agent.py, scheduler_agent.py
  delivery/                          # Output formatting
    delivery_service.py              #   PDF, Excel, Audio, JSON
    formatters/audio.py              #   TTS conversion
shared/
  models/                            # SQLAlchemy ORM + Pydantic schemas
  mcp/                               # MCP tool server + client
    tools/                           #   web_search, scrape_url, code_executor, file_io, media_processor
database/                            # SQLAlchemy connection + Alembic
```

---

# Technology Constraints

- Python >= 3.14
- OpenAI for all LLM calls (agents, planner, classifier, evaluator)
- Pydantic for schemas
- LangGraph for supervisor workflow
- CrewAI for sub-agents (research, analysis, generator, code, monitor)
- LangChain for tool wrappers (MCP tools); converted to CrewAI via `Tool.from_langchain()`
- MCP for tool interfaces
- PostgreSQL for persistence
- Docker Compose for service runtime
