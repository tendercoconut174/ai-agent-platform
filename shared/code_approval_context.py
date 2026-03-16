"""Context for code execution approval – human-in-the-loop for execute_python."""

import contextvars
from dataclasses import dataclass
from typing import Optional


@dataclass
class CodeApprovalContext:
    """Context passed when code approval is required."""

    workflow_id: str
    step_id: str
    session_id: Optional[str] = None


# When set, tool_execute_python will raise CodeApprovalRequired instead of running
_code_approval_required: contextvars.ContextVar[Optional[CodeApprovalContext]] = contextvars.ContextVar(
    "code_approval_required",
    default=None,
)


def set_code_approval_context(ctx: Optional[CodeApprovalContext]) -> None:
    """Set the code approval context (enables approval mode for execute_python)."""
    _code_approval_required.set(ctx)


def get_code_approval_context() -> Optional[CodeApprovalContext]:
    """Get current code approval context."""
    return _code_approval_required.get()


def clear_code_approval_context() -> None:
    """Clear the code approval context."""
    try:
        _code_approval_required.set(None)
    except LookupError:
        pass


class CodeApprovalRequired(Exception):
    """Raised when code execution requires user approval."""

    def __init__(self, code: str, workflow_id: str, step_id: str, session_id: Optional[str] = None):
        self.code = code
        self.workflow_id = workflow_id
        self.step_id = step_id
        self.session_id = session_id
        super().__init__(f"Code execution requires approval: {step_id}")
