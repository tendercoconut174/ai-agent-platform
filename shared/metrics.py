"""Prometheus metrics for observability."""

from prometheus_client import Counter, Histogram, generate_latest

# Request metrics
REQUEST_COUNT = Counter(
    "ai_agent_requests_total",
    "Total number of requests",
    ["service", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "ai_agent_request_duration_seconds",
    "Request latency in seconds",
    ["service", "endpoint"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

# Workflow metrics
WORKFLOW_COUNT = Counter(
    "ai_agent_workflows_total",
    "Total workflows by intent and outcome",
    ["intent", "outcome"],
)
AGENT_TOOL_CALLS = Counter(
    "ai_agent_tool_calls_total",
    "Tool calls by agent and tool",
    ["agent_type", "tool_name", "status"],
)
LLM_CALLS = Counter(
    "ai_agent_llm_calls_total",
    "LLM invocations by component",
    ["component", "status"],
)


def get_metrics() -> bytes:
    """Return Prometheus exposition format."""
    return generate_latest()
