"""LangGraph Supervisor – the main orchestration graph.

Flow: classify -> route -> (chat_respond | ask_user | plan -> execute -> evaluate -> [replan | deliver])
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from collections.abc import AsyncGenerator

from langgraph.graph import END, StateGraph

from services.orchestrator.supervisor.nodes.ask_user import ask_user
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
        today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
        messages: list[dict[str, str]] = [
            {"role": "system", "content": f"You are a friendly AI assistant. Today's date is {today}. Use the conversation history to maintain context."},
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
    if intent == "needs_clarification":
        return "ask_user"
    return "plan"


def _route_after_evaluate(state: WorkflowState) -> str:
    """Route based on evaluation result."""
    if state.get("needs_code_approval", False):
        return "deliver"
    if state.get("goal_achieved", False):
        return "deliver"
    return "plan"  # Replan if goal not achieved


def build_supervisor_graph() -> StateGraph:
    """Build and compile the supervisor LangGraph."""
    graph = StateGraph(WorkflowState)

    # Add nodes
    graph.add_node("classify", classify)
    graph.add_node("chat_respond", _chat_respond)
    graph.add_node("ask_user", ask_user)
    graph.add_node("plan", plan)
    graph.add_node("execute", execute)
    graph.add_node("evaluate", evaluate)
    graph.add_node("deliver", deliver)

    # Set entry point
    graph.set_entry_point("classify")

    # Conditional routing after classification
    graph.add_conditional_edges("classify", _route_after_classify, {
        "chat_respond": "chat_respond",
        "ask_user": "ask_user",
        "plan": "plan",
    })

    # Chat respond -> deliver
    graph.add_edge("chat_respond", "deliver")

    # Ask user (human-in-the-loop) -> END
    graph.add_edge("ask_user", END)

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
    require_code_approval: bool = False,
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

    workflow_deadline = t0 + 110  # 110s deadline, 10s buffer before gateway's 120s timeout

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
        "deadline": workflow_deadline,
        "final_result": None,
        "error": None,
        "needs_clarification": False,
        "clarification_question": None,
        "require_code_approval": require_code_approval,
    }

    result = await graph.ainvoke(initial_state)
    logger.info("[workflow] ===== END %s ===== | intent=%s | achieved=%s | iterations=%d | %.2fs",
                wf_id, result.get("intent", "?"), result.get("goal_achieved"), result.get("iteration_count", 0),
                time.perf_counter() - t0)
    return result


async def run_workflow_stream(
    goal: str,
    output_format: str = "json",
    session_id: str | None = None,
    workflow_id: str | None = None,
    callback_url: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    require_code_approval: bool = False,
) -> AsyncGenerator[dict, None]:
    """Run workflow and stream progress events (node transitions + per-step updates)."""
    t0 = time.perf_counter()
    wf_id = workflow_id or str(uuid.uuid4())
    history = conversation_history or []
    logger.info("[workflow] ===== STREAM START %s =====", wf_id)

    graph = get_supervisor_graph()
    workflow_deadline = t0 + 110
    progress_queue: asyncio.Queue = asyncio.Queue()
    graph_queue: asyncio.Queue = asyncio.Queue()

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
        "deadline": workflow_deadline,
        "final_result": None,
        "error": None,
        "needs_clarification": False,
        "clarification_question": None,
        "require_code_approval": require_code_approval,
        "progress_queue": progress_queue,
    }

    final_state: WorkflowState | None = None
    graph_done = False

    async def _run_graph() -> None:
        nonlocal final_state
        try:
            async for chunk in graph.astream(initial_state, stream_mode="values"):
                await graph_queue.put(("chunk", chunk))
            await graph_queue.put(("done", None))
        except Exception as e:
            await graph_queue.put(("error", e))

    graph_task = asyncio.create_task(_run_graph())

    try:
        while not graph_done:
            progress_task = asyncio.create_task(progress_queue.get())
            graph_task_get = asyncio.create_task(graph_queue.get())

            done, pending = await asyncio.wait(
                [progress_task, graph_task_get],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=120.0,
            )

            for t in pending:
                t.cancel()

            for task in done:
                try:
                    if task == progress_task:
                        ev = progress_task.result()
                        yield {"type": ev["type"], **{k: v for k, v in ev.items() if k != "type"}}
                    else:
                        kind, payload = graph_task_get.result()
                        if kind == "done":
                            graph_done = True
                        elif kind == "error":
                            raise payload
                        elif kind == "chunk" and isinstance(payload, dict):
                            # stream_mode="values" yields the full state dict per node, not node->state
                            state_update = payload
                            step_results = state_update.get("step_results") or []
                            yield {
                                "type": "node_done",
                                "node": "__state__",
                                "intent": state_update.get("intent"),
                                "step_results": [
                                    {"node_id": r.node_id, "agent_type": r.agent_type, "result": (r.result or "")[:300], "success": r.success}
                                    for r in step_results
                                ],
                            }
                            final_state = state_update
                except asyncio.CancelledError:
                    pass

            while not progress_queue.empty():
                try:
                    ev = progress_queue.get_nowait()
                    yield {"type": ev["type"], **{k: v for k, v in ev.items() if k != "type"}}
                except asyncio.QueueEmpty:
                    break

        await graph_task
        if final_state is None:
            final_state = await graph.ainvoke(initial_state)

        # Run delivery for formatted output (pdf, xl, audio)
        output_format = initial_state.get("output_format", "json")
        result_text = final_state.get("final_result", "")
        needs_code_approval = final_state.get("needs_code_approval", False)

        if needs_code_approval:
            delivery = {
                "result": result_text,
                "workflow_id": wf_id,
                "output_format": output_format,
                "needs_code_approval": True,
                "code_approval_id": final_state.get("pending_code_approval_id"),
                "code": final_state.get("code_to_approve"),
                "original_goal": final_state.get("goal", ""),
                "step_id": final_state.get("pending_step_id", "step_1"),
            }
        elif not final_state.get("needs_clarification") and result_text:
            from services.delivery.delivery_service import deliver
            delivery = await asyncio.to_thread(
                deliver,
                result={"result": result_text},
                workflow_id=wf_id,
                output_format=output_format,
            )
        else:
            delivery = {
                "result": final_state.get("clarification_question") or result_text,
                "workflow_id": wf_id,
                "output_format": output_format,
                "needs_clarification": final_state.get("needs_clarification", False),
                "question": final_state.get("clarification_question"),
            }

        yield {
            "type": "done",
            "workflow_id": wf_id,
            "intent": final_state.get("intent"),
            "needs_clarification": final_state.get("needs_clarification", False),
            "needs_code_approval": needs_code_approval,
            "code_approval_id": final_state.get("pending_code_approval_id"),
            "code_to_approve": final_state.get("code_to_approve"),
            "clarification_question": final_state.get("clarification_question"),
            "final_result": final_state.get("final_result"),
            "step_results": [
                {"node_id": r.node_id, "agent_type": r.agent_type, "result": (r.result or "")[:500], "success": r.success}
                for r in (final_state.get("step_results") or [])
            ],
            "delivery": delivery,
        }
    except Exception as e:
        graph_task.cancel()
        logger.exception("[workflow] Stream failed: %s", e)
        yield {"type": "error", "error": str(e)}
    finally:
        logger.info("[workflow] ===== STREAM END %s ===== | %.2fs", wf_id, time.perf_counter() - t0)
