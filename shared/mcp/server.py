"""MCP Tool Server – registers tools and exposes them for agent discovery and invocation."""

import logging
from typing import Any, Callable

from langchain_core.tools import StructuredTool, tool

from shared.code_approval_context import CodeApprovalRequired, get_code_approval_context
from shared.mcp.tools.code_executor import execute_python
from shared.mcp.tools.email_sender import send_email
from shared.mcp.tools.file_io import list_files, read_file, write_file
from shared.mcp.tools.media_processor import describe_image, text_to_speech, transcribe_audio
from shared.mcp.tools.scheduler import (
    tool_cancel_scheduled_task,
    tool_list_scheduled_tasks,
    tool_schedule_task,
)
from shared.mcp.tools.url_scraper import scrape_url
from shared.mcp.tools.web_search import web_search

logger = logging.getLogger(__name__)


# --- LangChain tool wrappers ---


@tool
def tool_web_search(query: str, max_results: int = 10) -> str:
    """Search the web for real-time information. Use for research, price comparisons, news, facts.
    Returns numbered results with title, snippet, and URL."""
    results = web_search(query=query, max_results=max_results)
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}\n   {r['body']}\n   URL: {r['href']}")
    return "\n\n".join(lines)


@tool
def tool_scrape_url(url: str, max_length: int = 5000) -> str:
    """Fetch and extract readable text from a web page. Use to get details from a specific URL."""
    result = scrape_url(url=url, max_length=max_length)
    if result.get("error"):
        return f"Error scraping {url}: {result['error']}"
    return f"Title: {result['title']}\n\n{result['text']}"


@tool
def tool_execute_python(code: str) -> str:
    """Execute Python code and return the output. Use for calculations, data processing, analysis.
    Only safe standard library modules are available (math, json, re, datetime, collections, statistics, csv)."""
    ctx = get_code_approval_context()
    if ctx is not None:
        raise CodeApprovalRequired(
            code=code,
            workflow_id=ctx.workflow_id,
            step_id=ctx.step_id,
            session_id=ctx.session_id,
        )
    result = execute_python(code=code)
    output = ""
    if result["stdout"]:
        output += result["stdout"]
    if result["stderr"]:
        output += f"\nSTDERR: {result['stderr']}"
    if result["error"]:
        output += f"\nERROR: {result['error']}"
    return output or "Code executed with no output."


@tool
def tool_read_file(filename: str) -> str:
    """Read a file from the agent workspace."""
    result = read_file(filename=filename)
    if not result["exists"]:
        return f"File '{filename}' not found."
    return result["content"]


@tool
def tool_write_file(filename: str, content: str) -> str:
    """Write content to a file in the agent workspace."""
    result = write_file(filename=filename, content=content)
    return f"Written {result['size']} bytes to {filename}"


@tool
def tool_list_files(directory: str = ".") -> str:
    """List files in the agent workspace directory."""
    result = list_files(directory=directory)
    if result.get("error"):
        return f"Error: {result['error']}"
    if not result["files"]:
        return "Directory is empty."
    lines = []
    for f in result["files"]:
        prefix = "[DIR] " if f["is_dir"] else f"[{f['size']}b] "
        lines.append(f"{prefix}{f['name']}")
    return "\n".join(lines)


@tool
def tool_send_email(to_email: str, subject: str, body: str) -> str:
    """Send an email. Use when the user asks to email something (reports, summaries, news).
    Requires SMTP_HOST, SMTP_USER, SMTP_PASSWORD in environment. For Gmail, use an App Password."""
    result = send_email(to_email=to_email, subject=subject, body=body)
    if result["success"]:
        return result["message"]
    return f"Email failed: {result.get('message', result.get('error', 'Unknown error'))}"


@tool
def tool_transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file to text using OpenAI Whisper."""
    result = transcribe_audio(file_path=file_path)
    if result.get("error"):
        return f"Transcription error: {result['error']}"
    return result["text"]


@tool
def tool_text_to_speech(text: str, output_path: str, voice: str = "alloy") -> str:
    """Convert text to speech audio file. Voices: alloy, echo, fable, onyx, nova, shimmer."""
    result = text_to_speech(text=text, output_path=output_path, voice=voice)
    if result.get("error"):
        return f"TTS error: {result['error']}"
    return f"Audio saved to {result['output_path']} ({result['size']} bytes)"


@tool
def tool_describe_image(file_path: str) -> str:
    """Describe the contents of an image using GPT-4 Vision."""
    result = describe_image(file_path=file_path)
    if result.get("error"):
        return f"Image description error: {result['error']}"
    return result["description"]


# --- Tool Registry ---


TOOL_REGISTRY: dict[str, list] = {
    "research": [tool_web_search, tool_scrape_url],
    "analysis": [tool_web_search, tool_execute_python, tool_read_file],
    "generator": [tool_web_search, tool_write_file, tool_read_file, tool_execute_python, tool_send_email],
    "code": [tool_execute_python, tool_read_file, tool_write_file, tool_list_files],
    "monitor": [tool_web_search, tool_scrape_url],
    "chat": [],
    "scheduler": [tool_schedule_task, tool_list_scheduled_tasks, tool_cancel_scheduled_task],
}

ALL_TOOLS = [
    tool_web_search,
    tool_scrape_url,
    tool_execute_python,
    tool_read_file,
    tool_write_file,
    tool_list_files,
    tool_send_email,
    tool_transcribe_audio,
    tool_text_to_speech,
    tool_describe_image,
    tool_schedule_task,
    tool_list_scheduled_tasks,
    tool_cancel_scheduled_task,
]


def get_tools_for_agent(agent_type: str) -> list:
    """Return the list of LangChain tools available for a given agent type."""
    return TOOL_REGISTRY.get(agent_type, [])


def get_all_tools() -> list:
    """Return all registered tools."""
    return ALL_TOOLS


def list_tool_names() -> list[str]:
    """Return names of all registered tools."""
    return [t.name for t in ALL_TOOLS]
