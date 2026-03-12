"""Interface for agents to communicate with Supervisor.

Agents never talk to user directly. All agent-to-user communication goes through Supervisor.
"""

from typing import Optional

from shared.models import AgentToSupervisorMessage


def agent_to_supervisor(
    agent_id: str,
    task_id: str,
    message_type: str,
    content: str,
) -> None:
    """Send message from agent to Supervisor (e.g. when agent needs to talk to user).

    Args:
        agent_id: Agent identifier.
        task_id: Task identifier.
        message_type: issue | user_question | status
        content: Message content.
    """
    msg = AgentToSupervisorMessage(
        agent_id=agent_id,
        task_id=task_id,
        message_type=message_type,
        content=content,
    )
    # TODO: Push to supervisor queue or callback; Supervisor relays to user
    # For now, log; full implementation would enqueue to supervisor_input queue
    import logging
    logging.getLogger(__name__).info(
        "AgentToSupervisor",
        extra={"agent_id": agent_id, "task_id": task_id, "type": message_type, "content": content[:100]},
    )
