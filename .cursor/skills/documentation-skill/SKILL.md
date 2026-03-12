---
name: documentation-skill
description: Generate README files, architecture docs, API documentation, code docstrings, setup instructions, and developer guides. Use when documenting code, writing README, or when the user asks for documentation.
---

# Documentation Skill – AI Agent Platform

## When this skill applies

Use this skill whenever generating:

- README files
- architecture documentation
- module documentation
- API documentation
- code docstrings
- setup instructions
- developer guides

---

# Documentation Principles

Documentation must be: clear, structured, concise, technically accurate.

Documentation must help developers quickly understand: what the component does, how it works, how to use it, how it integrates with the system.

Avoid: unnecessary verbosity, vague descriptions, undocumented interfaces.

---

# Required Documentation Areas

Every major component must document:

1. **Purpose** — What the component does
2. **Inputs** — What it accepts
3. **Outputs** — What it returns
4. **Dependencies** — What it depends on
5. **Execution Flow** — How it runs

---

# Docstring Format

Use Google-style docstrings for Python code.

```python
def process_task(task: dict) -> dict:
    """Process a task and return the result.

    Args:
        task: Task payload with message and optional metadata.

    Returns:
        Structured result dict from the agent.
    """
```
