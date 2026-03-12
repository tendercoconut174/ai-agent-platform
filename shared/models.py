"""Pydantic models for task payloads, results, and API schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """Request payload for the /message endpoint."""

    message: str = Field(..., description="User message or task description")


class TaskPayload(BaseModel):
    """Task payload enqueued to Redis and processed by workers."""

    task_id: str = Field(..., description="Unique task identifier")
    message: str = Field(..., description="Task message or query")
    task_type: str = Field(default="general", description="Task type for routing to specialized agent")


class TaskResult(BaseModel):
    """Structured result returned by agents."""

    result: str = Field(..., description="Agent result")


class AgentState(BaseModel):
    """State schema for agents."""

    task: str = Field(..., description="Task or query to process")
    result: Optional[str] = Field(default=None, description="Agent result")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")


# --- Orchestrator / Planner / Task Graph ---


class TaskNode(BaseModel):
    """Single node in a task graph."""

    node_id: str = Field(..., description="Unique node identifier")
    task_type: str = Field(..., description="Task type (e.g. research, summarize)")
    message: str = Field(..., description="Task message or query")
    dependencies: List[str] = Field(default_factory=list, description="IDs of nodes this depends on")


class TaskGraph(BaseModel):
    """DAG of tasks from the Planner."""

    workflow_id: str = Field(..., description="Workflow identifier")
    nodes: List[TaskNode] = Field(default_factory=list, description="Task nodes in execution order")


class OrchestratorRequest(BaseModel):
    """Request to the orchestrator."""

    message: str = Field(..., description="User message or goal")


class OrchestratorResponse(BaseModel):
    """Response from the orchestrator."""

    result: str = Field(..., description="Final result delivered to user")
    workflow_id: Optional[str] = Field(default=None, description="Workflow identifier")


# --- Agent-to-Supervisor communication ---


class AgentToSupervisorMessage(BaseModel):
    """Message from agent to Supervisor (e.g. when agent needs to talk to user)."""

    agent_id: str = Field(..., description="Agent identifier")
    task_id: str = Field(..., description="Task identifier")
    message_type: str = Field(..., description="issue | user_question | status")
    content: str = Field(..., description="Message content")
