---
name: devops-skill
description: Run the project locally or with Docker, manage Redis, build images, and deploy. Use when the user asks how to run, start, or test the application, or when working with Docker, docker-compose, or local development.
---

# DevOps Skill – AI Agent Platform

## When this skill applies

Use this skill when:

- Running the project locally or with Docker
- Managing Redis and dependencies
- Building or deploying services
- Configuring environment variables
- Debugging connection issues

---

# Local Development (without Docker)

**Prerequisites:** Redis must be running (e.g. `docker compose up -d redis`).

**Terminal 1:** `uv run python main.py gateway`  
**Terminal 2:** `uv run python main.py worker`

**Test:** `curl -X POST http://localhost:8000/message -H "Content-Type: application/json" -d '{"message": "research climate change"}'`

---

# Docker

**Start all services:** `docker compose up -d redis gateway worker`

**Gateway:** `REDIS_HOST=redis`, port 8000  
**Worker:** `REDIS_HOST=redis`, `PYTHONUNBUFFERED=1`

---

# Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| REDIS_HOST | localhost | Redis host (use `redis` in Docker) |
| REDIS_PORT | 6379 | Redis port |

---

# Package Manager

Use **uv** for dependency management. Commands: `uv sync`, `uv run`, `uv add`.
