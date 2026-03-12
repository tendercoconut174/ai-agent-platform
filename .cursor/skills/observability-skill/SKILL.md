---
name: observability-skill
description: Generate logging, metrics, tracing, and structured logs. Use when adding logging, debugging production issues, or when the user mentions metrics, tracing, or monitoring.
---

# Observability Skill – AI Agent Platform

## When this skill applies

Use this skill when generating:

- structured logging
- log levels and formatting
- metrics and counters
- distributed tracing
- error tracking

---

# Logging Rules

1. Use **structured logging** (JSON or key-value pairs).
2. Include `request_id`, `task_id`, `service` in log context.
3. Use appropriate levels: DEBUG, INFO, WARNING, ERROR.
4. Do NOT log secrets, tokens, or full PII.
5. Use `logging` standard library or structlog.

---

# Log Format

```python
import logging

logger = logging.getLogger(__name__)

logger.info(
    "Task completed",
    extra={
        "task_id": task_id,
        "duration_ms": duration,
        "agent": "research_agent",
    },
)
```

---

# Metrics

- Count tasks by status (success, failure, timeout).
- Track queue depth and processing latency.
- Use OpenTelemetry or Prometheus when adding metrics.
- Keep metric names consistent and namespaced.

---

# Tracing

- Propagate trace IDs across gateway → queue → worker.
- Use OpenTelemetry for distributed tracing when needed.
- Correlate logs with trace IDs for debugging.
