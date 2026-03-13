---
name: workflow-skill
description: Generate LangGraph supervisor nodes, execution plans, workflow state models, and orchestration logic. Use when creating workflows, modifying the supervisor graph, or when the user mentions LangGraph, DAGs, planning, or orchestration.
---

# Workflow Skill -- AI Agent Platform

## When this skill applies

Use this skill when generating:

- LangGraph supervisor nodes
- execution plans and plan steps
- workflow state models
- orchestration routing logic
- evaluation and replan logic

---

# Workflow Philosophy

The Supervisor is a **LangGraph StateGraph** that orchestrates the entire workflow. It classifies intent, plans execution as a DAG, dispatches agents, evaluates results, and replans if needed.

**Flow:** classify → [chat_respond | plan → execute → evaluate → (replan | deliver)]

Workflows must be goal-oriented, observable, and support iterative refinement.

---

# Supervisor Graph

Defined in `services/orchestrator/supervisor/graph.py`:

```python
graph = StateGraph(WorkflowState)
graph.add_node("classify", classify)
graph.add_node("chat_respond", _chat_respond)
graph.add_node("plan", plan)
graph.add_node("execute", execute)
graph.add_node("evaluate", evaluate)
graph.add_node("deliver", deliver)

graph.set_entry_point("classify")
graph.add_conditional_edges("classify", _route_after_classify, {...})
graph.add_edge("chat_respond", "deliver")
graph.add_edge("plan", "execute")
graph.add_edge("execute", "evaluate")
graph.add_conditional_edges("evaluate", _route_after_evaluate, {...})
graph.add_edge("deliver", END)
```

---

# Workflow State

State flows through the graph as `WorkflowState` (TypedDict):

```python
class WorkflowState(TypedDict, total=False):
    goal: str                          # User's original message
    output_format: str                 # json, pdf, xl, audio
    session_id: Optional[str]
    workflow_id: Optional[str]
    intent: str                        # casual, simple, complex, monitor
    plan: Optional[ExecutionPlan]      # DAG of PlanSteps
    step_results: list[StepResult]     # Results from agents
    iteration_count: int               # Current replan iteration
    max_iterations: int                # Max replan attempts (5)
    goal_achieved: bool
    final_result: Optional[str]
    error: Optional[str]
```

---

# Execution Plan

Plans are DAGs of `PlanStep`s:

```python
class PlanStep(BaseModel):
    node_id: str                       # step_1, step_2, ...
    agent_type: str                    # research, analysis, generator, code, monitor, chat
    message: str                       # Task description for the agent
    dependencies: list[str] = []       # node_ids this step depends on

class ExecutionPlan(BaseModel):
    steps: list[PlanStep] = []
    reasoning: str = ""
```

The planner creates plans using LLM (with fallback to rule-based planning). Format hints are injected into the last step's message based on `output_format`.

---

# Node Responsibilities

| Node | File | Purpose |
|------|------|---------|
| **classify** | `nodes/classify.py` | Determine intent: casual, simple, complex, monitor |
| **chat_respond** | `graph.py` | Direct LLM chat for casual intent (no planning) |
| **plan** | `nodes/plan.py` | LLM-based DAG generation with format-aware instructions |
| **execute** | `nodes/execute.py` | Dispatch steps to agents; parallel execution for independent steps |
| **evaluate** | `nodes/evaluate.py` | LLM-based goal achievement check; triggers replan if needed |
| **deliver** | `nodes/deliver.py` | Format final result text |

---

# Execution Details

The execute node (`nodes/execute.py`):

1. Finds steps whose dependencies are all completed
2. Runs independent steps in parallel via `ThreadPoolExecutor` (max 4 workers)
3. Passes dependency results as context to dependent steps
4. Continues until all steps are executed or no more steps are ready

---

# Adding a New Node

1. Create the node function in `services/orchestrator/supervisor/nodes/my_node.py`:

```python
from services.orchestrator.supervisor.state import WorkflowState

def my_node(state: WorkflowState) -> WorkflowState:
    # Process state
    return {**state, "field": new_value}
```

2. Register it in `services/orchestrator/supervisor/graph.py`:

```python
from services.orchestrator.supervisor.nodes.my_node import my_node
graph.add_node("my_node", my_node)
graph.add_edge("previous_node", "my_node")
```

---

# Key Files

- `services/orchestrator/supervisor/graph.py` -- Graph definition and `run_workflow()`
- `services/orchestrator/supervisor/state.py` -- WorkflowState, PlanStep, ExecutionPlan, StepResult
- `services/orchestrator/supervisor/nodes/` -- Individual node implementations
- `services/orchestrator/api/routes.py` -- `/orchestrate` endpoint calling `run_workflow()`
