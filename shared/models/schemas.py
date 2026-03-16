"""Pydantic schemas for API requests and responses."""

from typing import Any, Optional

from pydantic import BaseModel, Field


# --- Gateway request/response ---


class MessageRequest(BaseModel):
    """Request payload for POST /message (sync) and POST /workflow (async)."""

    message: str = Field(..., description="User message or task description")
    output_format: str = Field(default="json", description="json | pdf | xl | audio | image")
    mode: str = Field(default="auto", description="auto | chat | task")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation continuity")
    callback_url: Optional[str] = Field(default=None, description="Webhook URL for async result delivery")
    metadata: Optional[dict] = Field(default=None, description="Extra context for the request")
    workflow_id: Optional[str] = Field(
        default=None,
        description="When resuming after clarification: the workflow_id from the needs_clarification response",
    )
    require_code_approval: bool = Field(
        default=False,
        description="When true, pause for user approval before running Python code",
    )
    code_approval_id: Optional[str] = Field(
        default=None,
        description="When resuming after code approval: the approval_id from the needs_code_approval response",
    )


class WorkflowResponse(BaseModel):
    """Response for async workflow creation."""

    workflow_id: str
    status: str
    message: str = "Workflow created"


class WorkflowStatusResponse(BaseModel):
    """Response for workflow status polling."""

    workflow_id: str
    status: str
    goal: str
    iteration_count: int = 0
    steps: list["StepStatus"] = Field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None


class StepStatus(BaseModel):
    """Status of an individual workflow step."""

    node_id: str
    agent_type: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None


class StepResultSummary(BaseModel):
    """Summary of a workflow step for UI display."""

    node_id: str
    agent_type: str
    result: Optional[str] = None
    error: Optional[str] = None
    success: bool = True


class MessageResponse(BaseModel):
    """Response for sync /message endpoint."""

    result: str
    workflow_id: Optional[str] = None
    output_format: str = "json"
    content_base64: Optional[str] = None
    content_type: Optional[str] = None
    filename: Optional[str] = None
    session_id: Optional[str] = None
    needs_clarification: bool = False
    question: Optional[str] = Field(default=None, description="Clarifying question when needs_clarification is true")
    intent: Optional[str] = None
    step_results: Optional[list[StepResultSummary]] = Field(default=None, description="Workflow steps executed")


class HealthResponse(BaseModel):
    status: str = "ok"


# --- Internal orchestrator schemas ---


class OrchestratorRequest(BaseModel):
    """Request to the orchestrator service."""

    message: str
    output_format: str = "json"
    mode: str = "auto"
    session_id: Optional[str] = None
    callback_url: Optional[str] = None
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    workflow_id: Optional[str] = Field(
        default=None,
        description="When resuming: workflow_id from needs_clarification response",
    )
    require_code_approval: bool = Field(default=False, description="Pause for user approval before running code")
    code_approval_id: Optional[str] = Field(
        default=None,
        description="When resuming after code approval: approval_id from needs_code_approval response",
    )


class TaskPayload(BaseModel):
    """Task payload for Redis Streams."""

    task_id: str
    workflow_id: str
    step_id: str
    agent_type: str
    message: str
    output_format: str = "json"
    context: Optional[dict] = None


class TaskResult(BaseModel):
    """Result from an agent."""

    result: str
    metadata: Optional[dict] = None
    error: Optional[str] = None


class AgentMessage(BaseModel):
    """Message between agents or agent-to-supervisor."""

    from_agent: str
    to_agent: str = "supervisor"
    message_type: str  # status | result | error | question
    content: str
    metadata: Optional[dict] = None
