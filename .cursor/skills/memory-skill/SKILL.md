---
name: memory-skill
description: Generate session memory, conversation history, vector memory, and RAG patterns. Use when implementing memory, sessions, embeddings, vector stores, or when the user mentions session management, conversation history, or retrieval.
---

# Memory Skill -- AI Agent Platform

## When this skill applies

Use this skill when generating:

- session memory (conversation history)
- vector memory (embeddings, semantic search)
- RAG (retrieval-augmented generation)
- memory scoping and lifecycle

---

# Session Management

Session management is implemented in `services/gateway/session_manager.py`.

## Current Implementation

- **Primary storage**: PostgreSQL (`sessions` and `message_history` tables)
- **Fallback**: In-memory dicts when PostgreSQL is unavailable
- **DB availability**: Checked once at startup and cached

### Key Functions

```python
get_or_create_session(session_id: Optional[str]) -> tuple[str, bool]
add_message(session_id: str, role: str, content: str, content_type: str = "text")
get_history(session_id: str, limit: int = 20) -> list[dict[str, str]]
```

### ORM Models

```python
# shared/models/session.py
class Session(TimestampMixin, Base):
    __tablename__ = "sessions"
    id: Mapped[str]
    user_id: Mapped[Optional[str]]
    metadata_: Mapped[Optional[dict]]
    is_active: Mapped[bool]
    messages: Mapped[list["MessageHistory"]]

class MessageHistory(TimestampMixin, Base):
    __tablename__ = "message_history"
    id: Mapped[str]
    session_id: Mapped[str]
    role: Mapped[str]           # user, assistant, system
    content: Mapped[str]
    content_type: Mapped[str]   # text, audio, image, file
```

---

# Vector Memory (Future)

Not yet implemented. Planned approach:

- Store embeddings for semantic search
- Use pgvector or a dedicated vector DB
- Integrate with agent context for RAG
- Module path: `shared/models/embeddings.py` (placeholder exists)

---

# Design Rules

1. Memory must be **stateless** at the service level (state in PostgreSQL/Redis).
2. Session manager must gracefully fall back to in-memory when DB is unavailable.
3. Use Pydantic models for API schemas; SQLAlchemy for persistence.
4. Agents access conversation context through injected messages, not by querying DB directly.
5. Never store secrets or PII in vector embeddings without encryption.
6. Content is truncated to 50,000 characters before storage.

---

# RAG Pattern (Future)

When implementing RAG:

1. Chunk documents with overlap.
2. Embed chunks; store in vector store.
3. Retrieve top-k by similarity at query time.
4. Inject retrieved context into agent prompt.
5. Cite sources in agent output.
