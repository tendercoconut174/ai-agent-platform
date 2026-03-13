---
name: tool-skill
description: Generate MCP tools, LangChain tool wrappers, and agent-tool bindings. Use when creating tools, integrating APIs, or when the user mentions web search, code execution, file I/O, or agent capabilities.
---

# Tool Skill -- AI Agent Platform

## When this skill applies

Use this skill when generating:

- MCP tool implementations
- LangChain `@tool` wrappers
- tool registry entries
- agent-tool bindings
- integrations with external APIs

---

# Tool Philosophy

Tools provide **capabilities to agents**. Agents decide *what to do*. Tools implement *how to do it*.

Tools must remain **simple, stateless, and reusable**.

---

# MCP Compliance

All tools follow **Model Context Protocol (MCP)** principles:

- Tools expose a clear callable interface
- Tools accept structured input (typed parameters)
- Tools return structured output (dicts)
- Tools are stateless

Agents interact with tools through LangChain `@tool` wrappers. Agents must not call external APIs directly.

---

# Tool Architecture

Tools have two layers:

1. **Raw function** in `shared/mcp/tools/<tool>.py` -- returns a dict
2. **LangChain wrapper** in `shared/mcp/server.py` -- `@tool` decorated, returns a string

```python
# shared/mcp/tools/my_tool.py
def my_tool(query: str) -> dict[str, Any]:
    return {"result": "...", "error": None}

# shared/mcp/server.py
@tool
def tool_my_tool(query: str) -> str:
    """Description for LLM tool selection."""
    result = my_tool(query=query)
    return result["result"]
```

---

# Current Tools

| LangChain Wrapper | Raw Function | Module | Description |
|-------------------|-------------|--------|-------------|
| `tool_web_search` | `web_search()` | `web_search.py` | DuckDuckGo multi-backend search |
| `tool_scrape_url` | `scrape_url()` | `url_scraper.py` | Web page text extraction |
| `tool_execute_python` | `execute_python()` | `code_executor.py` | Sandboxed Python execution |
| `tool_read_file` | `read_file()` | `file_io.py` | Read workspace files |
| `tool_write_file` | `write_file()` | `file_io.py` | Write workspace files |
| `tool_list_files` | `list_files()` | `file_io.py` | List workspace directory |
| `tool_transcribe_audio` | `transcribe_audio()` | `media_processor.py` | Whisper transcription |
| `tool_text_to_speech` | `text_to_speech()` | `media_processor.py` | OpenAI TTS |
| `tool_describe_image` | `describe_image()` | `media_processor.py` | GPT-4V image description |

---

# Tool Registry

`TOOL_REGISTRY` in `shared/mcp/server.py` maps agent types to allowed tools:

```python
TOOL_REGISTRY = {
    "research":  [tool_web_search, tool_scrape_url],
    "analysis":  [tool_web_search, tool_execute_python, tool_read_file],
    "generator": [tool_web_search, tool_write_file, tool_read_file, tool_execute_python],
    "code":      [tool_execute_python, tool_read_file, tool_write_file, tool_list_files],
    "monitor":   [tool_web_search, tool_scrape_url],
    "chat":      [],
}
```

---

# Adding a New Tool

1. Create raw function in `shared/mcp/tools/my_tool.py`
2. Create `@tool` wrapper in `shared/mcp/server.py`
3. Add to `ALL_TOOLS` list
4. Add to relevant agent entries in `TOOL_REGISTRY`

---

# Tool Design Rules

Each tool must:

1. Perform a single responsibility
2. Have typed input parameters
3. Return a structured dict (raw) or string (wrapper)
4. Be deterministic and stateless
5. Handle errors gracefully (return error in dict, don't raise)

Tools must not contain agent logic or orchestration code.
