# AI Agent Platform

Event-driven distributed platform for AI agents.

## Architecture

```
User → Gateway → Supervisor (Orchestrator) → Planner → Task Graph Engine → Queue → Workers → Tools → Delivery Service → User
```

### Components

| Component | Purpose |
|-----------|---------|
| **Gateway** | FastAPI endpoints, forwards to Orchestrator |
| **Supervisor** | Coordinates workflow, invokes Planner |
| **Planner** | Converts user goals into task graphs (DAGs) |
| **Task Graph Engine** | Executes graph, pushes tasks to Queue |
| **Queue** | Redis-based task queue |
| **Workers** | Consume tasks, run agents, invoke tools |
| **Tools** | MCP-compatible capabilities |
| **Delivery Service** | Formats and returns results to user |

## Prerequisites

- Python ≥ 3.14
- Redis
- uv (package manager)

## Setup

```bash
uv sync
```

## Running Locally

**1. Start Redis**
```bash
docker compose up -d redis
```

**2. Start services (3 terminals)**

Terminal 1 – Worker:
```bash
uv run python main.py worker
```

Terminal 2 – Orchestrator:
```bash
uv run python main.py orchestrator
```

Terminal 3 – Gateway:
```bash
uv run python main.py gateway
```

**3. Test**
```bash
# Default (JSON, auto mode)
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "research climate change"}'

# Casual chat (direct response, no planning)
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "hello!", "mode": "chat"}'

# Output as PDF or Excel (returns file for download)
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "extract ICC T20 world cup winners", "output_format": "xl"}' \
  -o result.xlsx
```

## Running with Docker

```bash
docker compose up -d redis orchestrator worker gateway
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| REDIS_HOST | localhost | Redis host (use `redis` in Docker) |
| REDIS_PORT | 6379 | Redis port |
| ORCHESTRATOR_URL | http://localhost:8001 | Orchestrator URL (use `http://orchestrator:8001` in Docker) |
| OPENAI_API_KEY | — | OpenAI API key for agents (Planner, research_agent, general_agent). If unset, uses fallbacks. |
| OPENAI_MODEL | gpt-4o-mini | OpenAI model for agents |

**Web search:** General and research agents use ddgs (Bing/DuckDuckGo metasearch) for real web search (no API key needed).

### Request options

| Field | Default | Description |
|-------|---------|-------------|
| `output_format` | json | `json`, `pdf`, or `xl` (Excel). When pdf/xl, response includes `content_base64`, `content_type`, `filename`. |
| `mode` | auto | `auto` (classify), `chat` (direct chat, no planning), or `task` (full planning flow). |

## Project Structure

```
main.py                     # Entry point (gateway, worker, orchestrator)
platform_queue/             # Redis task queue
shared/                     # Pydantic models, tools
services/
  gateway/                  # FastAPI API
  orchestrator/             # Supervisor, Planner, Task Graph Engine
  workers/                  # Worker, agents, execution
  delivery/                 # Result delivery to user
tests/                      # pytest tests
```

## Testing

```bash
uv run pytest
```
