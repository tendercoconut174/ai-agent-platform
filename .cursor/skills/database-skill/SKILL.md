---
name: database-skill
description: Generate database models, migrations, queries, and SQLAlchemy code. Use when working with PostgreSQL, schemas, migrations, or when the user mentions database, persistence, or data storage.
---

# Database Skill – AI Agent Platform

## When this skill applies

Use this skill when generating:

- SQLAlchemy models
- database migrations (Alembic)
- queries and repositories
- connection pooling
- session management

---

# Technology Stack

- **PostgreSQL** — primary database
- **SQLAlchemy 2.0** — ORM and migrations
- **Alembic** — schema migrations

---

# Model Rules

1. Use SQLAlchemy 2.0 declarative style.
2. Define models in `shared/models` or service-specific modules.
3. Use Pydantic for API schemas; SQLAlchemy for persistence.
4. All models must have explicit primary keys.
5. Use `typing` module for type hints on model attributes.

---

# Migration Rules

1. Generate migrations with `alembic revision --autogenerate`.
2. Review generated migrations before applying.
3. Never edit applied migrations.
4. Use descriptive migration messages.

---

# Connection and Sessions

- Use environment variables for connection strings.
- Prefer connection pooling for production.
- Use context managers for session lifecycle.
- Workers and agents must not hold long-lived DB connections.
