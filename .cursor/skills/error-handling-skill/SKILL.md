---
name: error-handling-skill
description: Generate retry logic, circuit breakers, dead-letter queues, and graceful degradation. Use when handling failures, implementing retries, or when the user mentions error handling, resilience, or fault tolerance.
---

# Error Handling Skill – AI Agent Platform

## When this skill applies

Use this skill when generating:

- retry logic with backoff
- circuit breakers
- dead-letter queues
- graceful degradation
- error recovery

---

# Retry Rules

1. Retry only **idempotent** operations.
2. Use exponential backoff with jitter.
3. Set max retries to avoid infinite loops.
4. Log each retry attempt with context.
5. Distinguish transient vs permanent failures.

---

# Retry Pattern

```python
from typing import Callable, TypeVar

T = TypeVar("T")

def retry(
    fn: Callable[[], T],
    max_attempts: int = 3,
    exceptions: tuple = (ConnectionError, TimeoutError),
) -> T:
    """Retry fn on transient failures."""
    ...
```

---

# Worker and Queue

- Failed tasks: retry up to N times, then move to dead-letter queue.
- Dead-letter queue: store failed tasks for manual inspection.
- Do NOT silently drop failed tasks.
- Return structured error to gateway on permanent failure.

---

# Circuit Breaker

When calling external APIs:

- Open circuit after N consecutive failures.
- Half-open state: allow one test request.
- Close circuit after success or timeout.
- Use libraries like `tenacity` or `circuitbreaker` when appropriate.

---

# Graceful Degradation

- Gateway: return 503 when workers unavailable.
- Worker: catch agent errors; return error result, do not crash.
- Log errors with full context for debugging.
- Provide fallback responses when possible (e.g. "Service temporarily unavailable").
