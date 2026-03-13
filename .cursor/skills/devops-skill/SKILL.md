---
name: devops-skill
description: Run the project locally or with Docker, manage Redis and PostgreSQL, build images, and deploy. Use when the user asks how to run, start, or test the application, or when working with Docker, docker-compose, or local development.
---

# DevOps Skill -- AI Agent Platform

## When this skill applies

Use this skill when:

- Running the project locally or with Docker
- Managing Redis, PostgreSQL, and other dependencies
- Building or deploying services
- Configuring environment variables
- Debugging connection issues
- Running database migrations

---

# Local Development

## Minimal (no PostgreSQL)

Sessions stored in-memory (lost on restart).

```bash
docker compose up -d redis

# Terminal 1
uv run python main.py orchestrator

# Terminal 2
uv run python main.py gateway
```

## Full stack (with PostgreSQL)

```bash
docker compose up -d redis postgres
uv run python main.py migrate

# Terminal 1
uv run python main.py orchestrator

# Terminal 2
uv run python main.py gateway
```

**Test:**

```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the latest news headlines?"}'
```

---

# Docker Compose

**Start all services:** `docker compose up -d`

| Service | Host | Port | Notes |
|---------|------|------|-------|
| gateway | gateway | 8000 | User-facing API |
| orchestrator | orchestrator | 8001 | Workflow orchestration |
| worker | worker | -- | Background task consumer |
| redis | redis | 6379 | Task queue and pub/sub |
| postgres | postgres | 5432 | Persistent storage |

All services use `dns: [8.8.8.8, 8.8.4.4]` for external DNS resolution.

---

# CLI Commands

```bash
uv run python main.py gateway                    # Start gateway (port 8000)
uv run python main.py gateway --port 9000        # Custom port
uv run python main.py orchestrator               # Start orchestrator (port 8001)
uv run python main.py orchestrator --port 9001   # Custom port
uv run python main.py worker                     # Start background worker
uv run python main.py migrate                    # Run Alembic migrations
```

---

# Environment Variables

Create a `.env` file in project root. Loaded automatically via `python-dotenv`.

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | -- | Required for LLM features |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for agents and planner |
| `REDIS_HOST` | `localhost` | Redis host (`redis` in Docker) |
| `REDIS_PORT` | `6379` | Redis port |
| `DATABASE_URL` | `postgresql://dev:dev@localhost:5432/agent_platform` | PostgreSQL URL |
| `ORCHESTRATOR_URL` | `http://localhost:8001` | Orchestrator URL (`http://orchestrator:8001` in Docker) |
| `FILE_WORKSPACE` | `/tmp/agent_workspace` | Workspace for file_io tool |

---

# Database Migrations

```bash
uv run python main.py migrate                                    # Apply all
uv run alembic current                                           # Check state
uv run alembic revision --autogenerate -m "description"          # Generate new
uv run alembic downgrade -1                                      # Rollback one step
```

---

# Package Manager

Use **uv** for all dependency management:

```bash
uv sync              # Install all dependencies
uv add <package>     # Add a new dependency
uv run <command>     # Run in the project's virtual environment
```
