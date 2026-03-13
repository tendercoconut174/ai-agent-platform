"""Workflow state for the LangGraph supervisor graph."""

from typing import Any, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class PlanStep(BaseModel):
    """A single step in the execution plan."""

    node_id: str
    agent_type: str  # research | analysis | generator | code | monitor | chat
    message: str
    dependencies: list[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    """The full execution plan created by the planner."""

    steps: list[PlanStep] = Field(default_factory=list)
    reasoning: str = ""


class StepResult(BaseModel):
    """Result from executing a single step."""

    node_id: str
    agent_type: str
    result: str
    error: Optional[str] = None
    success: bool = True


class WorkflowState(TypedDict, total=False):
    """State that flows through the supervisor graph."""

    # Input
    goal: str
    output_format: str
    session_id: Optional[str]
    workflow_id: Optional[str]
    callback_url: Optional[str]
    conversation_history: list[dict[str, str]]

    # Classification
    intent: str  # casual | simple | complex | monitor

    # Planning
    plan: Optional[ExecutionPlan]

    # Execution
    step_results: list[StepResult]
    current_step_index: int

    # Evaluation
    iteration_count: int
    max_iterations: int
    goal_achieved: bool

    # Output
    final_result: Optional[str]
    error: Optional[str]
