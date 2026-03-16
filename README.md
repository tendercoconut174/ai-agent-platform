# AI Agent Platform

A fully async, goal-oriented, multi-agent AI system built with LangGraph orchestration, MCP tools, multi-modal I/O, and persistent session management. Provider-agnostic LLM support (OpenAI, Anthropic, Google, Ollama, Groq). Accepts complex tasks via REST API, breaks them into executable plans, dispatches specialized agents, evaluates results, and delivers output in the requested format.

## Architecture

```
User / Adapter (REST, WhatsApp, Slack...)
  │
  ▼
Gateway (FastAPI)
  ├── Input Processor (text, voice/Whisper, image/GPT-4V, file extraction)
  ├── Session Manager (PostgreSQL with in-memory fallback)
  │
  ▼
Orchestrator (FastAPI)
  └── Supervisor (LangGraph StateGraph)
        ├── classify  ─── casual? ──► chat_respond ──► deliver ──► END
        │                    │
        │                    └── task? ──► plan ──► execute ──► evaluate ──┐
        │                                   ▲                              │
        │                                   └── goal not achieved ─────────┘
        │                                          goal achieved ──► deliver ──► END
        │
        └── Agent Pool (research, analysis, generator, code, monitor, chat)
              └── MCP Tools (web_search, scrape_url, code_executor, file_io, media_processor)
  │
  ▼
Delivery Service (JSON, PDF, Excel, Audio/TTS)
  │
  ▼
User
```

## Key Features

- **Fully async** -- end-to-end async from HTTP endpoints through LangGraph to LLM calls (`ainvoke`)
- **Provider-agnostic LLM** -- swap between OpenAI, Anthropic, Google Gemini, Ollama, Groq via env vars
- **Goal-oriented execution** -- plans, executes, evaluates, and replans until the goal is achieved
- **Intent classification** -- casual chat bypasses planning; complex tasks get full DAG execution
- **Async parallel execution** -- independent plan steps run concurrently via `asyncio.gather()`
- **Multi-modal input** -- text, voice (Whisper transcription), images (GPT-4V), file attachments (PDF, Excel, CSV, TXT)
- **Multi-format output** -- JSON, PDF (fpdf2), Excel (openpyxl), Audio (TTS)
- **Session continuity** -- PostgreSQL-backed conversation history with in-memory fallback
- **MCP tools** -- agents use structured, discoverable tools rather than calling APIs directly
- **Format-aware planning** -- the planner injects output format instructions so agents produce data suitable for the requested format
- **Human-in-the-loop** -- when a request is vague or ambiguous, the supervisor asks for clarification; user can resume with `workflow_id`
- **Code approval** -- when enabled (`require_code_approval: true`), agents pause for user approval before running Python code; user reviews and approves via UI or API

## Prerequisites

- Python >= 3.14
- PostgreSQL (optional; falls back to in-memory)
- [uv](https://docs.astral.sh/uv/) package manager

## Quick Start

```bash
# Install dependencies
uv sync

# Optional: Start PostgreSQL for persistent sessions
docker compose up -d postgres
uv run python main.py migrate

# Terminal 1 -- Orchestrator (port 8001)
uv run python main.py orchestrator

# Terminal 2 -- Gateway (port 8000)
uv run python main.py gateway
```

PostgreSQL is optional. Without it, sessions are stored in-memory (lost on restart).

## Test UI

A web UI for testing the API is available at `http://localhost:8000/ui/` (or `http://localhost:8000/` which redirects there). It provides:

- **Chat interface** — Send messages and view responses
- **Streaming** — Live workflow steps and results as they run (toggle via "Stream" checkbox)
- **Steps panel** — See workflow steps (classify, plan, execute) as they complete
- **Session management** — Session ID persisted in localStorage; "New session" to reset
- **Workflow ID** — Displayed for clarification resume flow
- **Code approval** — When enabled, shows a banner with proposed code; user clicks "Approve & run" to execute
- **Clarification banner** — Separate area for replying when the system asks for clarification
- **Clear chat** — Reset messages and steps
- **Stop** — Cancel in-flight requests
- **Output format** — JSON, PDF, Excel, Audio selector
- **API URL** — Configurable (default `http://localhost:8000`)

Start the gateway and open `http://localhost:8000` in your browser.

## API Usage

### POST /message -- Synchronous JSON

```bash
# Casual chat
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "hello!"}'

# Complex task with PDF output
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "research ICC T20 world cup winners"}' \
  --output result.pdf

# Excel output (auto-detected from message)
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "give me excel of top 10 tech companies by revenue"}'  \
  --output result.xlsx

# Session continuity
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "tell me more", "session_id": "<session_id_from_previous>"}'
```

### POST /message/upload -- Multipart (voice, image, files)

```bash
# Voice input
curl -X POST http://localhost:8000/message/upload \
  -F audio=@recording.wav

# Image + text
curl -X POST http://localhost:8000/message/upload \
  -F message="analyze this image" \
  -F image=@photo.png

# File attachment
curl -X POST http://localhost:8000/message/upload \
  -F message="summarize this data" \
  -F files=@data.csv
```

### Request Fields

| Field | Default | Description |
|-------|---------|-------------|
| `message` | required | User message or task description |
| `output_format` | `json` | `json`, `pdf`, `xl`, `audio` |
| `mode` | `auto` | `auto`, `chat`, `task` |
| `session_id` | auto-generated | Session ID for conversation continuity |
| `callback_url` | null | Webhook URL for async result delivery |
| `workflow_id` | null | When resuming after clarification: the `workflow_id` from the `needs_clarification` response |
| `require_code_approval` | `false` | When true, pause for user approval before running Python code |
| `code_approval_id` | null | When resuming after code approval: the `code_approval_id` from the `needs_code_approval` response |

### Response Format

```json
{
  "result": "...",
  "workflow_id": "uuid",
  "output_format": "json",
  "content_base64": null,
  "content_type": null,
  "filename": null,
  "session_id": "uuid",
  "needs_clarification": false,
  "question": null
}
```

When the request is vague (`needs_clarification: true`), the response includes a `question` to ask the user. Resume by sending a follow-up with `workflow_id` and your clarification as `message`.

When code approval is enabled and an agent proposes Python code (`needs_code_approval: true`), the response includes `code_approval_id` and `code`. Resume by sending a follow-up with `code_approval_id`; the gateway runs the approved code and forwards the output to the orchestrator.

For file formats (`pdf`, `xl`, `audio`), the gateway returns a binary file download with appropriate `Content-Type` and `Content-Disposition` headers.

### POST /message/stream -- Server-Sent Events

Stream workflow progress in real time. Same request body as `POST /message`. Returns SSE events with step updates and final delivery. Use when you want live steps and streaming results.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | -- | API key for OpenAI (default provider) |
| `LLM_PROVIDER` | `openai` | Global LLM provider: `openai`, `anthropic`, `google`, `ollama`, `groq` |
| `LLM_MODEL` | provider default | Global model name (e.g. `gpt-4o-mini`, `claude-sonnet-4-20250514`, `gemini-2.0-flash`) |
| `LLM_PROVIDER__<CMP>` | inherits global | Per-component override (CMP: `AGENTS`, `CLASSIFY`, `PLANNER`, `EVALUATOR`, `CHAT`) |
| `LLM_MODEL__<CMP>` | inherits global | Per-component model override |
| `ANTHROPIC_API_KEY` | -- | API key for Anthropic (when using Claude) |
| `GOOGLE_API_KEY` | -- | API key for Google (when using Gemini) |
| `GROQ_API_KEY` | -- | API key for Groq |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL (for local models) |
| `DATABASE_URL` | `postgresql://dev:dev@localhost:5432/agent_platform` | PostgreSQL connection URL |
| `ORCHESTRATOR_URL` | `http://localhost:8001` | Orchestrator service URL (used by gateway) |
| `AGENT_TIMEOUT_SECONDS` | `180` | Max seconds per agent step (increase for complex analysis) |
| `FILE_WORKSPACE` | `/tmp/agent_workspace` | Workspace directory for file_io tool |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server for email sending |
| `SMTP_PORT` | `587` | SMTP port (587 for TLS) |
| `SMTP_USER` | -- | SMTP username (usually your email) |
| `SMTP_PASSWORD` | -- | SMTP password (for Gmail, use an [App Password](https://support.google.com/accounts/answer/185833)) |
| `SMTP_FROM` | same as SMTP_USER | Sender email address |

### LLM Provider Examples

```bash
# All OpenAI (default, no changes needed)
OPENAI_API_KEY=sk-...

# All Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...

# Mix: cheap classifier + powerful agents
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_PROVIDER__AGENTS=anthropic
LLM_MODEL__AGENTS=claude-sonnet-4-20250514
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Local Ollama (no API key needed)
LLM_PROVIDER=ollama
LLM_MODEL=llama3
```

Install only the provider packages you need:

```bash
uv pip install "ai-agent-platform[anthropic]"  # Claude
uv pip install "ai-agent-platform[google]"     # Gemini
uv pip install "ai-agent-platform[ollama]"     # Ollama
uv pip install "ai-agent-platform[groq]"       # Groq
uv pip install "ai-agent-platform[all-llm]"    # All providers
```

## Project Structure

```
main.py                              # CLI entry point: gateway, orchestrator, migrate
services/
  gateway/                           # Async FastAPI gateway service (port 8000)
    api/routes.py                    #   Async /message and /message/upload endpoints
    api/orchestrator_client.py       #   Async HTTP client for orchestrator (httpx.AsyncClient)
    input_processor.py               #   Multi-modal input handling (audio, image, files)
    session_manager.py               #   Session and message history (PostgreSQL + fallback)
  orchestrator/                      # Async FastAPI orchestrator service (port 8001)
    api/routes.py                    #   Async /orchestrate endpoint
    supervisor/                      #   Async LangGraph supervisor graph
      graph.py                       #     StateGraph with ainvoke: classify → plan → execute → evaluate → deliver
      state.py                       #     WorkflowState, PlanStep, ExecutionPlan, StepResult
      nodes/
        classify.py                  #     Structured LLM intent classification (casual/simple/complex/monitor)
        plan.py                      #     Structured LLM DAG planning with format hints
        execute.py                   #     Async step execution with asyncio.gather for parallelism
        evaluate.py                  #     Structured LLM goal evaluation with replan loop
        deliver.py                   #     Async final result formatting
  agents/                            # Async agent pool
    base_agent.py                    #   Async ReAct agent factory (create_agent + ainvoke + MCP tools)
    registry.py                      #   Agent type → async runner mapping
    research_agent.py                #   Web search and data gathering
    analysis_agent.py                #   Summarization and pattern extraction
    generator_agent.py               #   Report and document generation
    code_agent.py                    #   Code execution and data processing
    monitor_agent.py                 #   Long-running observation tasks
    chat_agent.py                    #   Casual conversation
  delivery/                          # Output formatting
    delivery_service.py              #   PDF, Excel, Audio, JSON formatting
    formatters/audio.py              #   OpenAI TTS conversion
shared/
  llm.py                             # Centralized LLM factory (provider-agnostic get_llm)
  models/                            # Data models
    base.py                          #   SQLAlchemy DeclarativeBase + TimestampMixin
    schemas.py                       #   Pydantic API schemas
    session.py                       #   Session and MessageHistory ORM models
    workflow.py                      #   Workflow and WorkflowStep ORM models
  mcp/                               # MCP tool system
    server.py                        #   Tool registry + LangChain tool wrappers
    client.py                        #   Tool discovery client
    tools/
      web_search.py                  #   DuckDuckGo multi-backend search
      url_scraper.py                 #   Web page text extraction (httpx + BeautifulSoup)
      code_executor.py               #   Sandboxed Python execution
      file_io.py                     #   File read/write/list in workspace
      media_processor.py             #   Audio transcription, TTS, image description
database/                            # Database layer
  connection.py                      #   SQLAlchemy engine + session factory
alembic/                             # Database migrations
  env.py                             #   Migration environment
  versions/                          #   Migration scripts
tests/                               # Test suite
docker-compose.yml                   # PostgreSQL + gateway + orchestrator
```

## Testing

```bash
uv run pytest           # run all tests
uv run pytest -v        # verbose output
uv run pytest --tb=short  # short tracebacks
```

## Docker

```bash
# Full stack (gateway, orchestrator, postgres)
docker compose up -d

# PostgreSQL only (for local dev)
docker compose up -d postgres
```

## Supervisor Flow Detail

All nodes are async and invoked via `await graph.ainvoke()`:

1. **Classify** -- Determines intent using `await llm.ainvoke()` or heuristics: `casual`, `simple`, `complex`, or `monitor`
2. **Chat Respond** -- For casual intent, responds directly without planning via async LLM chat
3. **Plan** -- LLM generates a DAG of `PlanStep`s with agent types, messages, and dependencies
4. **Execute** -- Dispatches steps to async agents; independent steps run concurrently via `asyncio.gather()`
5. **Evaluate** -- LLM evaluates whether the result achieves the user's goal
6. **Replan** -- If the goal is not achieved and max iterations not reached, loops back to Plan
7. **Deliver** -- Formats the final result; file conversion (PDF/Excel/Audio) handled by the Delivery Service

## License

MIT
