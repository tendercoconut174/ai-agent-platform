# Architecture

## System Overview

The AI Agent Platform is a goal-oriented, multi-agent system that accepts user tasks, decomposes them into executable plans, dispatches specialized agents, evaluates results, and delivers output in the requested format.

The system is split into two FastAPI services (Gateway and Orchestrator), a shared agent pool, an MCP tool layer, and supporting infrastructure (PostgreSQL).

## High-Level Flow

```
                                 ┌─────────────────────────────┐
                                 │         User / Adapter       │
                                 │  (REST, WhatsApp, Slack...)  │
                                 └─────────────┬───────────────┘
                                               │
                                               ▼
                          ┌──────────────────────────────────────────┐
                          │              Gateway (port 8000)          │
                          │                                          │
                          │  ┌──────────────┐  ┌──────────────────┐  │
                          │  │Input Processor│  │ Session Manager  │  │
                          │  │(audio, image, │  │ (PostgreSQL /    │  │
                          │  │ files → text) │  │  in-memory)      │  │
                          │  └──────────────┘  └──────────────────┘  │
                          └────────────────────┬─────────────────────┘
                                               │ HTTP POST /orchestrate
                                               ▼
                          ┌──────────────────────────────────────────┐
                          │          Orchestrator (port 8001)         │
                          │                                          │
                          │  ┌────────────────────────────────────┐  │
                          │  │     Supervisor (LangGraph)          │  │
                          │  │                                    │  │
                          │  │  classify ──► plan ──► execute     │  │
                          │  │     │              ▲       │       │  │
                          │  │     │casual        │       ▼       │  │
                          │  │     ▼          replan   evaluate   │  │
                          │  │  chat_respond              │       │  │
                          │  │     │                      ▼       │  │
                          │  │     │needs_clarification   done    │  │
                          │  │     ▼                      │       │  │
                          │  │  ask_user ──► END          │       │  │
                          │  │     └──────► deliver ◄─────┘       │  │
                          │  └────────────────────────────────────┘  │
                          └────────────────────┬─────────────────────┘
                                               │
                              ┌────────────────┼────────────────┐
                              ▼                ▼                ▼
                       ┌──────────┐    ┌──────────┐    ┌──────────┐
                       │ research │    │ analysis │    │generator │  ...
                       │  agent   │    │  agent   │    │  agent   │
                       └────┬─────┘    └────┬─────┘    └────┬─────┘
                            │               │               │
                            ▼               ▼               ▼
                       ┌──────────────────────────────────────────┐
                       │            MCP Tool Layer                 │
                       │  web_search, scrape_url, code_executor,  │
                       │  file_io, media_processor                │
                       └──────────────────────────────────────────┘
                                               │
                                               ▼
                          ┌──────────────────────────────────────────┐
                          │          Delivery Service                 │
                          │   JSON / PDF / Excel / Audio (TTS)       │
                          └──────────────────────────────────────────┘
```

## Components

### Gateway (`services/gateway/`)

The user-facing API layer. Responsibilities:

- **API endpoints**: `POST /message` (JSON), `POST /message/stream` (SSE), and `POST /message/upload` (multipart)
- **Input processing**: Converts multi-modal input (audio, images, files) into text using Whisper, GPT-4V, and text extraction
- **Format inference**: Detects output format hints in messages ("give me pdf", "as excel") and strips them before forwarding
- **Session management**: Creates/retrieves sessions and stores message history in PostgreSQL (with in-memory fallback)
- **File delivery**: Returns binary file downloads (PDF, Excel, audio) with proper content types

The Gateway communicates with the Orchestrator via HTTP (`httpx`).

### Orchestrator (`services/orchestrator/`)

The brain of the system. Contains the LangGraph supervisor that orchestrates the entire workflow.

#### Supervisor Graph (`services/orchestrator/supervisor/`)

A compiled LangGraph `StateGraph` with the following nodes:

| Node | Purpose |
|------|---------|
| **classify** | Determines user intent: `casual`, `simple`, `complex`, `monitor`, or `needs_clarification` |
| **chat_respond** | Direct LLM response for casual messages (no planning) |
| **ask_user** | Human-in-the-loop: generates a clarifying question when the goal is vague or ambiguous |
| **plan** | LLM generates a DAG of `PlanStep`s with agent types, messages, and dependencies |
| **execute** | Dispatches steps to agents, respecting dependencies; parallelizes independent steps |
| **evaluate** | LLM evaluates whether the result satisfies the user's goal |
| **deliver** | Formats the final result text |

#### Follow-up Context

When the user sends a follow-up (e.g. "can you write one with python" after asking about a calculator app), the planner and agents receive conversation history so they can resolve references like "one", "it", "that". The plan node includes the last 6 messages in the planner prompt; the execute node prepends conversation context to each agent's task message.

#### Routing Logic

- After **classify**: casual → `chat_respond`; needs_clarification → `ask_user` (→ END); otherwise → `plan`
- After **evaluate**: goal achieved → `deliver`; not achieved → `plan` (replan loop, max 5 iterations)

#### Workflow State

```python
class WorkflowState(TypedDict, total=False):
    goal: str                          # User's original message
    output_format: str                 # json, pdf, xl, audio
    session_id: Optional[str]
    workflow_id: Optional[str]
    intent: str                        # casual, simple, complex, monitor
    plan: Optional[ExecutionPlan]      # DAG of PlanSteps
    step_results: list[StepResult]     # Results from executed steps
    iteration_count: int               # Current replan iteration
    max_iterations: int                # Max replan attempts (default 5)
    goal_achieved: bool
    final_result: Optional[str]
    error: Optional[str]
    needs_clarification: bool       # Human-in-the-loop: workflow paused for user input
    clarification_question: Optional[str]
```

### Agent Pool (`services/agents/`)

Seven specialized agents, all built with the same factory (`create_react_agent`):

| Agent | Tools | Purpose |
|-------|-------|---------|
| **research** | web_search, scrape_url | Web search, data gathering, fact-finding |
| **analysis** | web_search, execute_python, read_file | Summarization, comparison, pattern extraction |
| **generator** | web_search, write_file, read_file, execute_python | Report/document creation |
| **code** | execute_python, read_file, write_file, list_files | Calculations, data processing |
| **monitor** | web_search, scrape_url | Long-running observation tasks |
| **chat** | (none) | Casual conversation |
| **plan_execute** | web_search, execute_python, read_file | Complex tasks; planner creates steps, executor runs each |

Each agent is a LangChain ReAct agent (`langchain.agents.create_agent`) with access to a subset of MCP tools determined by the agent type.

### MCP Tool Layer (`shared/mcp/`)

Tools follow Model Context Protocol principles: structured input, structured output, stateless, single responsibility.

| Tool | Module | Description |
|------|--------|-------------|
| `tool_web_search` | `web_search.py` | DuckDuckGo search with multi-backend fallback (Google, DuckDuckGo, Brave, Yahoo) |
| `tool_scrape_url` | `url_scraper.py` | Extracts readable text from web pages (httpx + BeautifulSoup) |
| `tool_execute_python` | `code_executor.py` | Sandboxed Python code execution (safe stdlib modules only) |
| `tool_read_file` | `file_io.py` | Read files from agent workspace |
| `tool_write_file` | `file_io.py` | Write files to agent workspace |
| `tool_list_files` | `file_io.py` | List files in agent workspace |
| `tool_transcribe_audio` | `media_processor.py` | Audio → text via OpenAI Whisper |
| `tool_text_to_speech` | `media_processor.py` | Text → audio via OpenAI TTS |
| `tool_describe_image` | `media_processor.py` | Image → description via GPT-4V |

The `TOOL_REGISTRY` in `server.py` maps agent types to their allowed tool subsets.

### Delivery Service (`services/delivery/`)

Converts the text result into the requested output format:

- **JSON**: Pass-through as `MessageResponse`
- **PDF**: `fpdf2` with text wrapping and auto page breaks
- **Excel**: `openpyxl` parsing markdown tables into cells with bold headers
- **Audio**: OpenAI TTS to MP3, base64-encoded

### Human-in-the-Loop (Clarification)

When the classifier detects a vague or ambiguous request (`needs_clarification` intent), the supervisor routes to the **ask_user** node. This node uses the LLM to generate a clarifying question and pauses the workflow. The response includes `needs_clarification: true`, `question`, and `workflow_id`. The gateway persists this state in `pending_clarifications` (PostgreSQL or in-memory). The user can resume by sending a follow-up message with the same `session_id` and `workflow_id`, including their clarification. The gateway merges the original goal with the clarification and runs a fresh workflow.

**Flow:**
1. User: `{"message": "research companies"}` → Response: `{"needs_clarification": true, "question": "Which industry?", "workflow_id": "..."}`
2. User: `{"message": "tech sector", "workflow_id": "..."}` → Gateway merges goal, runs workflow, returns result

### Human-in-the-Loop (Code Approval)

When `require_code_approval` is true and a code/analysis/generator agent proposes Python code, the `execute_python` tool raises `CodeApprovalRequired` instead of running the code. The execute node saves the pending approval in `pending_code_approvals` (PostgreSQL or in-memory) and returns `needs_code_approval: true` with `code_approval_id` and `code`. The user reviews the code and resumes by sending a follow-up with `code_approval_id`. The gateway loads the pending approval, runs the code via `execute_python`, and forwards the output to the orchestrator. The agent receives the output and continues (e.g. analyzes and delivers the final answer).

**Flow:**
1. User: `{"message": "calculate fibonacci(10)", "require_code_approval": true}` → Agent proposes code → Response: `{"needs_code_approval": true, "code_approval_id": "...", "code": "def fib(n): ..."}`
2. User: `{"message": "approved", "code_approval_id": "..."}` → Gateway runs code, forwards output to orchestrator → Agent analyzes output → Returns final result

### Session Manager (`services/gateway/session_manager.py`)

Provides conversation continuity:

- Uses PostgreSQL (`sessions` and `message_history` tables) when available
- Gracefully falls back to in-memory storage when PostgreSQL is unreachable
- Database availability is checked once at startup and cached

### Database (`database/`)

- **Engine**: SQLAlchemy with `psycopg2` (sync) driver
- **Migrations**: Alembic with autogenerate support
- **Tables**: `sessions`, `message_history`, `workflows`, `workflow_steps`, `pending_clarifications`, `pending_code_approvals`

## Data Flow: Complex Task Example

1. User sends: `{"message": "research top 5 tech companies and create an excel report"}`
2. **Gateway** infers `output_format=xl`, strips "excel report" from message, creates/retrieves session
3. **Gateway** calls `POST /orchestrate` on the Orchestrator
4. **Supervisor.classify**: LLM classifies intent as `complex`
5. **Supervisor.plan**: LLM creates a 3-step DAG:
   - `step_1` (research): "Find top 5 tech companies by revenue"
   - `step_2` (analysis): "Summarize and compare" (depends on step_1)
   - `step_3` (generator): "Format as markdown table" (depends on step_2)
6. **Supervisor.execute**: Runs step_1 first, then step_2 with step_1's output as context, then step_3
7. **Supervisor.evaluate**: LLM confirms the result contains a proper table → goal achieved
8. **Supervisor.deliver**: Returns final text to Orchestrator
9. **Delivery Service**: Parses markdown table into Excel cells, base64-encodes the XLSX
10. **Gateway**: Decodes base64, returns binary XLSX with `Content-Disposition: attachment`

## Data Flow: Human-in-the-Loop (Clarification) Example

1. User sends: `{"message": "research companies"}`
2. **Gateway** creates session, forwards to Orchestrator
3. **Supervisor.classify**: LLM detects `needs_clarification` (too vague)
4. **Supervisor.ask_user**: LLM generates: "Which industry or sector are you interested in?"
5. **Orchestrator** returns `{needs_clarification: true, question: "...", workflow_id: "..."}` without calling deliver
6. **Gateway** saves pending clarification (original_goal, question, output_format) and returns to user
7. User sends: `{"message": "tech sector", "workflow_id": "..."}`
8. **Gateway** loads pending clarification, merges: "research companies\n\n[User clarification] tech sector"
9. **Gateway** forwards merged goal to Orchestrator (normal flow)
10. **Supervisor** runs classify → plan → execute → evaluate → deliver
11. **Gateway** returns final result

## Data Flow: Code Approval Example

1. User sends: `{"message": "calculate 2+2 in Python", "require_code_approval": true}`
2. **Gateway** creates session, forwards to Orchestrator with `require_code_approval: true`
3. **Supervisor** runs classify → plan → execute
4. **Execute node**: Code agent proposes `print(2+2)`; `execute_python` tool raises `CodeApprovalRequired` (approval mode)
5. **Execute node**: Saves pending approval (code, original_goal, output_format) via `save_pending_code_approval`, returns `needs_code_approval: true`, `code_approval_id`, `code`
6. **Gateway**: Returns response with `needs_code_approval`, `code_approval_id`, `code`
7. User reviews code, sends: `{"message": "approved", "code_approval_id": "..."}`
8. **Gateway**: Loads pending approval, runs `execute_python(pending.code)`, gets output `4`
9. **Gateway**: Forwards merged message `[Code approved and executed]\n\nOutput:\n4\n\nOriginal request: ...` to Orchestrator
10. **Supervisor**: Runs fresh workflow; agent receives output, analyzes, delivers final answer
11. **Gateway**: Returns result to user

## Data Flow: Casual Chat Example

1. User sends: `{"message": "hi how are you"}`
2. **Gateway** creates session, forwards to Orchestrator
3. **Supervisor.classify**: Heuristic/LLM detects `casual` intent
4. **Supervisor.chat_respond**: LLM generates conversational reply directly
5. **Supervisor.deliver**: Returns text
6. **Gateway**: Returns JSON response with `session_id`

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python >= 3.14 |
| Web framework | FastAPI + Uvicorn |
| Agent framework | LangChain + LangGraph |
| LLM | OpenAI (gpt-4o-mini default) |
| Database | PostgreSQL 15 + SQLAlchemy + Alembic |
| HTTP client | httpx |
| PDF generation | fpdf2 |
| Excel generation | openpyxl |
| Web scraping | httpx + BeautifulSoup4 |
| Web search | ddgs (DuckDuckGo) |
| Audio processing | OpenAI Whisper + TTS |
| Containerization | Docker Compose |
