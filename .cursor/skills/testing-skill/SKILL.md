---
name: testing-skill
description: Generate unit tests, integration tests, workflow tests, agent tests, tool tests, and API endpoint tests. Use when writing tests, adding test coverage, or when the user mentions pytest, testing, or test cases.
---

# Testing Skill – AI Agent Platform

## When this skill applies

Use this skill when generating:

- unit tests
- integration tests
- workflow tests
- agent tests
- tool tests
- API endpoint tests

All generated tests must follow the standards defined here.

---

# Testing Philosophy

Tests must:

- verify correctness
- isolate dependencies
- remain deterministic
- run quickly

Tests must never depend on external services. External APIs must always be mocked.

---

# Testing Framework

The project uses **pytest**. Additional tools may include pytest-asyncio, httpx (for API testing), pytest-mock.

---

# Test Types

## Unit Tests

Test individual components in isolation (agent node logic, tools, utility functions, models). Must not interact with external systems.

## Integration Tests

Test interaction between system components (API → queue, worker → agent, agent → tool). May use mocked dependencies.

## Workflow Tests

Test full multi-step workflows end-to-end with mocked external services.

---

# Test Location

Place tests in `tests/` directory mirroring the source structure. Use `test_` prefix for test files and functions.
