from services.workers.agents.research_agent import research_agent

def execute(task):

    message = task.get("message", "")

    if "research" in message:
        return research_agent(task)

    return {"result": "unknown task"}