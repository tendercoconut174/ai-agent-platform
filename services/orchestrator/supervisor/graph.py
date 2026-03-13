"""LangGraph Supervisor – the main orchestration graph.

Flow: classify -> route -> (chat_respond | plan -> execute -> evaluate -> [replan | deliver])
"""

import logging
import time
import uuid

from langgraph.graph import END, StateGraph

from services.orchestrator.supervisor.nodes.classify import classify
from services.orchestrator.supervisor.nodes.deliver import deliver
from services.orchestrator.supervisor.nodes.evaluate import evaluate
from services.orchestrator.supervisor.nodes.execute import execute
from services.orchestrator.supervisor.nodes.plan import plan
from services.orchestrator.supervisor.state import WorkflowState

logger = logging.getLogger(__name__)


async def _chat_respond(state: WorkflowState) -> WorkflowState:
    """Direct async chat response without planning (for casual intent)."""
    t0 = time.perf_counter()
    goal = state.get("goal", "")
    history = state.get("conversation_history") or []
    logger.info("[chat_respond] START | goal=%s | history=%d msgs", goal[:120], len(history))

    from shared.llm import get_llm, is_llm_available

    if is_llm_available("chat"):
        llm = get_llm("chat", temperature=0.7)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": "You are a friendly AI assistant. Use the conversation history to maintain context."},
        ]
        for msg in history:
            role = msg.get("role", "user")
            if role in ("user", "assistant", "system"):
                messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": goal})

        response = await llm.ainvoke(messages)
        result = (response.content or "").strip() or "Hello! How can I help you?"
    else:
        result = "Hello! I'm the AI assistant. No LLM API key configured."

    logger.info("[chat_respond] DONE  | %.2fs", time.perf_counter() - t0)
    return {**state, "final_result": result, "goal_achieved": True}


def _route_after_classify(state: WorkflowState) -> str:
    """Route based on classified intent."""
    intent = state.get("intent", "simple")
    if intent == "casual":
        return "chat_respond"
    return "plan"


def _route_after_evaluate(state: WorkflowState) -> str:
    """Route based on evaluation result."""
    if state.get("goal_achieved", False):
        return "deliver"
    return "plan"  # Replan if goal not achieved


def build_supervisor_graph() -> StateGraph:
    """Build and compile the supervisor LangGraph."""
    graph = StateGraph(WorkflowState)

    # Add nodes
    graph.add_node("classify", classify)
    graph.add_node("chat_respond", _chat_respond)
    graph.add_node("plan", plan)
    graph.add_node("execute", execute)
    graph.add_node("evaluate", evaluate)
    graph.add_node("deliver", deliver)

    # Set entry point
    graph.set_entry_point("classify")

    # Conditional routing after classification
    graph.add_conditional_edges("classify", _route_after_classify, {
        "chat_respond": "chat_respond",
        "plan": "plan",
    })

    # Chat respond -> END
    graph.add_edge("chat_respond", "deliver")

    # Plan -> Execute -> Evaluate
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "evaluate")

    # Evaluate -> replan or deliver
    graph.add_conditional_edges("evaluate", _route_after_evaluate, {
        "plan": "plan",
        "deliver": "deliver",
    })

    # Deliver -> END
    graph.add_edge("deliver", END)

    return graph.compile()


# Module-level compiled graph (reusable)
_compiled_graph = None


def get_supervisor_graph():
    """Get or create the compiled supervisor graph (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_supervisor_graph()
    return _compiled_graph


async def run_workflow(
    goal: str,
    output_format: str = "json",
    session_id: str | None = None,
    workflow_id: str | None = None,
    callback_url: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> WorkflowState:
    """Run the full supervisor workflow asynchronously.

    Args:
        goal: User message or task description.
        output_format: Desired output format.
        session_id: Optional session ID.
        workflow_id: Optional workflow ID (generated if not provided).
        callback_url: Optional webhook for async delivery.
        conversation_history: Previous messages in the session.

    Returns:
        Final WorkflowState with results.
    """
    t0 = time.perf_counter()
    wf_id = workflow_id or str(uuid.uuid4())
    history = conversation_history or []
    logger.info("[workflow] ===== START %s =====", wf_id)
    logger.info("[workflow] goal=%s | format=%s | session=%s | history=%d msgs",
                goal[:120], output_format, session_id, len(history))

    graph = get_supervisor_graph()

    initial_state: WorkflowState = {
        "goal": goal,
        "output_format": output_format,
        "session_id": session_id,
        "workflow_id": wf_id,
        "callback_url": callback_url,
        "conversation_history": history,
        "intent": "",
        "plan": None,
        "step_results": [],
        "current_step_index": 0,
        "iteration_count": 0,
        "max_iterations": 5,
        "goal_achieved": False,
        "final_result": None,
        "error": None,
    }

    result = await graph.ainvoke(initial_state)
    logger.info("[workflow] ===== END %s ===== | intent=%s | achieved=%s | iterations=%d | %.2fs",
                wf_id, result.get("intent", "?"), result.get("goal_achieved"), result.get("iteration_count", 0),
                time.perf_counter() - t0)
    return result
