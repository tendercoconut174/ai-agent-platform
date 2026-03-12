---
name: memory-skill
description: Generate session memory, vector memory, RAG patterns, and conversation history. Use when implementing memory, embeddings, vector stores, or when the user mentions session_memory, vector_memory, or retrieval.
---

# Memory Skill – AI Agent Platform

## When this skill applies

Use this skill when generating:

- session memory (conversation history)
- vector memory (embeddings, semantic search)
- RAG (retrieval-augmented generation)
- memory scoping and lifecycle

---

# Memory Types

## Session Memory (`shared/memory/session_memory.py`)

- Stores conversation history per session/user.
- Must be scoped by session_id or user_id.
- Use for short-term context within a workflow.
- Prefer Redis or in-memory for ephemeral sessions.

## Vector Memory (`shared/memory/vector_memory.py`)

- Stores embeddings for semantic search.
- Use for long-term knowledge, document retrieval.
- Integrate with vector DB (e.g. pgvector, Chroma).
- Must support add, search, and delete operations.

---

# Design Rules

1. Memory must be **stateless** at the service level (state in Redis/DB).
2. Define clear TTL and eviction for session memory.
3. Use Pydantic models for memory payloads.
4. Agents access memory through tools or injected context.
5. Never store secrets or PII in vector embeddings without encryption.

---

# RAG Pattern

When implementing RAG:

1. Chunk documents with overlap.
2. Embed chunks; store in vector store.
3. Retrieve top-k by similarity at query time.
4. Inject retrieved context into agent prompt.
5. Cite sources in agent output.
