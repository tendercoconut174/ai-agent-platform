---
name: workflow-skill
description: Generate planners, task graphs, workflow execution engines, orchestration logic, and multi-agent pipelines. Use when creating workflows, task scheduling, or when the user mentions LangGraph, DAGs, or orchestration.
---

# Workflow Skill – AI Agent Platform

## When this skill applies

Use this skill when generating:

- planners
- task graphs
- workflow execution engines
- orchestration logic
- multi-agent pipelines
- task scheduling logic

---

# Workflow Philosophy

Workflows represent **structured execution plans** that break down high-level user goals into smaller deterministic tasks.

**Full flow:** Gateway → Supervisor → Planner → Task Graph Engine → Queue → Workers → Tools → Delivery Service → User

Workflows must be deterministic, modular, and observable.

---

# Workflow Representation

Workflows must be represented as **directed task graphs (DAGs)**. Each node represents a single execution step.

Nodes must define: input, output, dependencies, execution logic.

Example: `collect_data → summarize → generate_report`

---

# Workflow State

Workflow state must use **Pydantic models**.

```python
from typing import Optional
from pydantic import BaseModel

class WorkflowState(BaseModel):
    task_id: str
    status: str
    result: Optional[str] = None
```

---

# Component Roles

- **Planner Agent** (OpenAI): Plans the action, converts user goal → DAG of tasks
- **Task Graph Engine**: Based on tasks, calls different specialized agents; pushes tasks to Queue
- **Workers**: Consume tasks, run specialized OpenAI agents, call Tools
- **Supervisor**: Supervises all agents; handles agent issues; routes agent-to-user communication (agents talk to user only through Supervisor)
- **Delivery Service**: Returns results to User

---

# Supervisor Role

- Supervises each agent during execution
- When agents face issues → Supervisor handles (retry, escalate, or ask user)
- When agents need to talk back to user → Supervisor relays the message
- All agent-user communication flows through Supervisor
