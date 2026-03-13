# Development Guide

## Prerequisites

| Requirement | Version | Notes |
|------------|---------|-------|
| Python | >= 3.14 | Managed via `.python-version` |
| uv | latest | [Install guide](https://docs.astral.sh/uv/) |
| Docker + Docker Compose | latest | For Redis and PostgreSQL |
| OpenAI API key | -- | Required for LLM features |

## Initial Setup

```bash
# Clone the repository
git clone <repo-url>
cd ai-agent-platform

# Install dependencies
uv sync

# Create .env file
cat > .env << 'EOF'
OPENAI_API_KEY=sk-your-key-here
EOF
```

## Running Locally

### Option A: Minimal (no PostgreSQL)

Sessions stored in-memory (lost on restart). Simplest setup for development.

```bash
# Start Redis only
docker compose up -d redis

# Terminal 1 -- Orchestrator
uv run python main.py orchestrator

# Terminal 2 -- Gateway
uv run python main.py gateway
```

### Option B: Full stack (with PostgreSQL)

Sessions persisted to database.

```bash
# Start Redis + PostgreSQL
docker compose up -d redis postgres

# Run database migrations
uv run python main.py migrate

# Terminal 1 -- Orchestrator
uv run python main.py orchestrator

# Terminal 2 -- Gateway
uv run python main.py gateway
```

### Option C: Docker Compose (all services)

```bash
docker compose up -d
```

This starts gateway (8000), orchestrator (8001), worker, redis (6379), and postgres (5432).

## CLI Commands

```bash
uv run python main.py gateway       # Start gateway on port 8000
uv run python main.py orchestrator   # Start orchestrator on port 8001
uv run python main.py worker         # Start background worker
uv run python main.py migrate        # Run Alembic migrations
```

Custom host/port:

```bash
uv run python main.py gateway --host 127.0.0.1 --port 9000
uv run python main.py orchestrator --host 127.0.0.1 --port 9001
```

## Environment Variables

Create a `.env` file in the project root. The application loads it automatically via `python-dotenv`.

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
OPENAI_MODEL=gpt-4o-mini
REDIS_HOST=localhost
REDIS_PORT=6379
DATABASE_URL=postgresql://dev:dev@localhost:5432/agent_platform
ORCHESTRATOR_URL=http://localhost:8001
FILE_WORKSPACE=/tmp/agent_workspace
```

## Database Migrations

The project uses Alembic for database schema migrations.

```bash
# Apply all pending migrations
uv run python main.py migrate

# Or directly with alembic
uv run alembic upgrade head

# Check current migration state
uv run alembic current

# Generate a new migration after model changes
uv run alembic revision --autogenerate -m "description of change"

# Downgrade one step
uv run alembic downgrade -1
```

The `alembic.ini` file has a default `sqlalchemy.url`. If `DATABASE_URL` is set in the environment, it takes precedence.

### Database Models

ORM models are in `shared/models/`:

| Model | Table | Description |
|-------|-------|-------------|
| `Session` | `sessions` | Conversation sessions |
| `MessageHistory` | `message_history` | Individual messages in a session |
| `Workflow` | `workflows` | Multi-step workflow records |
| `WorkflowStep` | `workflow_steps` | Individual steps in a workflow |

After modifying any model, generate a migration:

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

## Testing

```bash
# Run all tests
uv run pytest

# Verbose output
uv run pytest -v

# Specific test file
uv run pytest tests/test_models.py

# Short tracebacks
uv run pytest --tb=short

# With coverage (if pytest-cov installed)
uv run pytest --cov=services --cov=shared
```

### Test Structure

```
tests/
  test_api.py              # Gateway endpoint tests (mocked orchestrator)
  test_models.py           # Pydantic schema validation tests
  test_research_agent.py   # Research agent tests (mocked LLM)
  test_task_runner.py      # Task routing tests (mocked agents)
  test_web_search.py       # Web search tool integration tests
```

Tests use `unittest.mock.patch` to mock LLM calls and external services, so they run without an API key or running services.

## Quick Verification

After starting the services, verify everything works:

```bash
# Health check
curl http://localhost:8000/health
# {"status":"ok"}

# Casual chat
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "hello!"}'

# Complex task
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the top 3 latest world news headlines?"}'

# PDF output
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "give me a pdf summary of climate change"}' \
  --output result.pdf

# Excel output
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "give me excel of top 10 countries by population"}' \
  --output result.xlsx
```

## Code Style

The project uses:
- **ruff** for linting (`uv run ruff check .`)
- **black** for formatting (`uv run black .`)
- **mypy** for type checking (`uv run mypy .`)

## Project Layout

```
main.py                     # CLI entry point
.env                        # Environment variables (not committed)
pyproject.toml              # Dependencies and project metadata
docker-compose.yml          # Service definitions
alembic.ini                 # Alembic configuration
alembic/                    # Migration scripts
  env.py                    # Migration environment
  versions/                 # Auto-generated migration files
database/
  connection.py             # SQLAlchemy engine + session factory
services/
  gateway/                  # User-facing API (port 8000)
  orchestrator/             # Workflow orchestration (port 8001)
  agents/                   # Agent pool (6 specialized agents)
  delivery/                 # Output formatting (PDF, Excel, audio)
  workers/                  # Background worker process
shared/
  models/                   # ORM models + Pydantic schemas
  mcp/                      # MCP tool system
    tools/                  # Individual tool implementations
platform_queue/             # Redis Streams task queue
tests/                      # Test suite
docs/                       # Documentation
```

## Troubleshooting

### "Set OPENAI_API_KEY for full chat"

The `.env` file is missing or doesn't contain `OPENAI_API_KEY`. Create it:

```bash
echo 'OPENAI_API_KEY=sk-your-key' > .env
```

### "Connection refused" to orchestrator

The orchestrator service isn't running. Start it in a separate terminal:

```bash
uv run python main.py orchestrator
```

### "relation sessions does not exist"

Database migrations haven't been run:

```bash
uv run python main.py migrate
```

### PostgreSQL connection refused

If PostgreSQL isn't running, the session manager falls back to in-memory storage automatically. To start PostgreSQL:

```bash
docker compose up -d postgres
uv run python main.py migrate
```

### DNS resolution failure in Docker

Already configured -- `docker-compose.yml` sets `dns: [8.8.8.8, 8.8.4.4]` on all services.
