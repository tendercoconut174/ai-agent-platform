---
name: architectural-skill
description: Generate services, agents, workflows, queues, and orchestration logic. Use when designing services, architecture, or when the user mentions gateway, supervisor, planner, worker, or orchestration.
---

# Architecture Skill – AI Agent Platform

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

The system follows an **event-driven distributed architecture**.

**Full flow:**

```
User
  ↓
Gateway
  ↓
Supervisor (Orchestrator)
  ↓
Planner
  ↓
Task Graph Engine
  ↓
Queue
  ↓
Workers
  ↓
Tools
  ↓
Delivery Service
  ↓
User
```

---

# Architecture Rules

1. Services must remain loosely coupled.
2. Communication between services must occur through queues.
3. Workers execute tasks from queues only.
4. Agents must not access databases directly.
5. Agents interact with external systems only through MCP tools.
6. API services must remain thin and stateless.
7. Long-running tasks must run in workers.

---

# System Layers

## 1. Gateway (`services/gateway/`)

- FastAPI endpoints
- Request validation
- Authentication
- Forwards requests to Supervisor
- Must not contain business logic

## 2. Supervisor / Orchestrator (`services/orchestrator/`)

- **Supervises all agents** — monitors execution, handles agent issues
- **Agent-to-user communication** — agents talk to user **only through Supervisor**; agents never contact user directly
- Coordinates the full workflow
- Receives user intent from Gateway
- Invokes Planner Agent to create execution plan
- Manages workflow state and user interaction
- Control plane of the system
- When agents face issues or need to talk back to user, they communicate through Supervisor

## 3. Planner Agent

- **OpenAI agent** that plans the action
- Converts user goals into executable task graphs
- Outputs DAG of tasks (e.g. collect_data → summarize → generate_report)
- Implemented with LangGraph + OpenAI
- Must be deterministic

## 4. Task Graph Engine

- Executes the task graph from Planner Agent
- **Calls different specialized agents** based on task type
- Schedules nodes based on dependencies
- Pushes individual tasks to Queue
- Routes each task to the appropriate specialized agent
- Handles retries and failed steps

## 5. Queue (`platform_queue/`)

- Redis-based task queue
- Workers consume tasks
- FIFO or priority ordering

## 6. Workers (`services/workers/`)

- Consume tasks from Queue
- Execute **specialized OpenAI agents** (research, coding, summarization, etc.)
- Invoke Tools for external capabilities
- Return results to Delivery Service
- Agents communicate with user via Supervisor when needed

## 7. Tools

- MCP-compatible tool interfaces
- Web search, code execution, document generation, etc.
- Stateless and independent
- Agents call tools, not external APIs directly

## 8. Delivery Service

- Receives results from Workers (via Supervisor)
- Delivers final output to User
- May push to WebSocket, webhook, or return via Gateway

---

# Agent Communication Rules

- **Agents never talk to user directly.** All agent-to-user communication goes through Supervisor.
- When an agent faces issues or needs to ask the user something, it sends a message to Supervisor.
- Supervisor relays to user and routes user response back to the agent.

---

# Project Structure

```
main.py                     # Entry point
platform_queue/             # Redis task queue
services/
  gateway/                  # FastAPI API
  orchestrator/             # Supervisor, Planner, Task Graph Engine
    supervisor/             # Orchestration logic
  workers/                  # Worker + agents + execution
  delivery/                 # Result delivery to user
shared/
  tools/                    # MCP tools
```

---

# Technology Constraints

- Python ≥ 3.12
- **OpenAI** for all agents (Planner, specialized agents)
- Pydantic for schemas
- LangGraph for agent workflows
- MCP for tool interfaces
- Redis for queues
- Docker for service runtime
