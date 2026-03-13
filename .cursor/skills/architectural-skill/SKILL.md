---
name: architectural-skill
description: Generate services, agents, workflows, queues, and orchestration logic. Use when designing services, architecture, or when the user mentions gateway, supervisor, orchestrator, planner, or delivery.
---

# Architecture Skill -- AI Agent Platform

## When this skill applies

Use this skill when generating:

- services
- agents
- workflows
- queues
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
        classify → plan → execute → evaluate → [replan | deliver]
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
- Graph nodes: classify, chat_respond, plan, execute, evaluate, deliver
- Goal-oriented: replans if evaluation determines goal not achieved (max 5 iterations)
- Plans are DAGs of PlanSteps with agent types and dependencies

## 3. Agent Pool (`services/agents/`)

- Six specialized agents: research, analysis, generator, code, monitor, chat
- All built via `create_react_agent` factory (LangChain ReAct + OpenAI)
- Each agent has a system prompt and a subset of MCP tools
- Registered in `services/agents/registry.py`

## 4. MCP Tools (`shared/mcp/`)

- Tool server with LangChain `@tool` wrappers
- Raw implementations in `shared/mcp/tools/`
- Tools: web_search, scrape_url, code_executor, file_io, media_processor
- `TOOL_REGISTRY` maps agent types to allowed tool subsets

## 5. Task Queue (`platform_queue/`)

- Redis Streams for async task queuing
- Consumer groups for reliable delivery
- Pub/Sub for progress updates

## 6. Delivery Service (`services/delivery/`)

- Converts text results to PDF (fpdf2), Excel (openpyxl), Audio (OpenAI TTS)
- Returns base64-encoded content for binary formats
- Gateway decodes and returns as file download

## 7. Database (`database/`)

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
main.py                              # CLI: gateway, orchestrator, worker, migrate
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
    base_agent.py                    #   ReAct agent factory
    registry.py                      #   Agent type → runner
    research_agent.py, analysis_agent.py, generator_agent.py,
    code_agent.py, monitor_agent.py, chat_agent.py
  delivery/                          # Output formatting
    delivery_service.py              #   PDF, Excel, Audio, JSON
    formatters/audio.py              #   TTS conversion
  workers/                           # Background worker
shared/
  models/                            # SQLAlchemy ORM + Pydantic schemas
  mcp/                               # MCP tool server + client
    tools/                           #   web_search, scrape_url, code_executor, file_io, media_processor
platform_queue/                      # Redis Streams task queue
database/                            # SQLAlchemy connection + Alembic
```

---

# Technology Constraints

- Python >= 3.14
- OpenAI for all LLM calls (agents, planner, classifier, evaluator)
- Pydantic for schemas
- LangGraph for supervisor workflow
- LangChain for agent creation
- MCP for tool interfaces
- Redis for queues and pub/sub
- PostgreSQL for persistence
- Docker Compose for service runtime
