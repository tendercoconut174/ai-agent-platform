# Agents and Tools

## Agent Architecture

All agents are built using the same factory function (`create_react_agent` in `services/agents/base_agent.py`). This function:

1. Looks up the MCP tools allowed for the agent type via `get_tools_for_agent(agent_type)`
2. Returns a `run(message: str) -> str` callable
3. On invocation, creates a LangChain ReAct agent (`langchain.agents.create_agent`) with the system prompt and tools
4. Invokes the agent with the user message and extracts the final AI response

If `OPENAI_API_KEY` is not set, agents return a placeholder message instead of failing.

### Agent Registry

The registry (`services/agents/registry.py`) maps agent type strings to runner functions:

```python
AGENT_REGISTRY = {
    "research":  research_agent.run,
    "analysis":  analysis_agent.run,
    "generator": generator_agent.run,
    "code":      code_agent.run,
    "monitor":   monitor_agent.run,
    "chat":      chat_agent.run,
}
```

`get_agent(agent_type)` returns the runner for the given type, falling back to `research_agent.run` for unknown types.

---

## Agent Types

### Research Agent

**File:** `services/agents/research_agent.py`
**Tools:** `web_search`, `scrape_url`
**Purpose:** Web search, data gathering, fact-finding

System prompt directives:
- Always use `web_search` for real data (never fabricate)
- Use `scrape_url` for details from specific pages
- Cite sources with URLs
- Format tabular data as markdown tables
- Try different search queries if results are insufficient

### Analysis Agent

**File:** `services/agents/analysis_agent.py`
**Tools:** `web_search`, `execute_python`, `read_file`
**Purpose:** Summarization, comparison, pattern extraction

System prompt directives:
- Analyze data systematically
- Use `execute_python` for calculations and statistics
- Produce structured output (tables, bullet points, numbered lists)
- Cite sources when using web data

### Generator Agent

**File:** `services/agents/generator_agent.py`
**Tools:** `web_search`, `write_file`, `read_file`, `execute_python`
**Purpose:** Report and document generation

System prompt directives:
- Create well-structured documents
- Use markdown formatting (headings, tables, lists)
- Use `write_file` to save generated content
- For data-driven reports, gather data first with `web_search`

### Code Agent

**File:** `services/agents/code_agent.py`
**Tools:** `execute_python`, `read_file`, `write_file`, `list_files`
**Purpose:** Code execution, calculations, data processing

System prompt directives:
- Write clean Python code
- Use `execute_python` to run calculations
- Read/write files in the workspace
- Handle errors gracefully

### Monitor Agent

**File:** `services/agents/monitor_agent.py`
**Tools:** `web_search`, `scrape_url`
**Purpose:** Long-running observation and tracking tasks

System prompt directives:
- Designed for monitoring/observation tasks
- Periodically check sources
- Report changes and updates

### Chat Agent

**File:** `services/agents/chat_agent.py`
**Tools:** (none)
**Purpose:** Casual conversation

System prompt directives:
- Friendly and helpful
- Handle greetings, small talk, general questions
- No tool access needed

---

## Tool System (MCP)

Tools follow Model Context Protocol (MCP) principles:
- Structured input and output
- Stateless and idempotent
- Single responsibility
- Discoverable via the tool registry

### Tool Registry

The registry in `shared/mcp/server.py` maps agent types to allowed tools:

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

### Tool Implementations

#### web_search (`shared/mcp/tools/web_search.py`)

Searches the web using DuckDuckGo's metasearch API (`ddgs` library).

- **Input:** `query` (string), `max_results` (int, 1-20, default 10)
- **Output:** List of `{title, body, href}` dicts
- **Backends:** Tries `google` → `duckduckgo` → `brave` → `yahoo` in order until one succeeds
- **LangChain wrapper:** `tool_web_search` returns formatted numbered results

#### scrape_url (`shared/mcp/tools/url_scraper.py`)

Fetches a web page and extracts readable text content.

- **Input:** `url` (string), `max_length` (int, default 5000)
- **Output:** `{title, text, url, error}` dict
- **Implementation:** `httpx.get()` → `BeautifulSoup` text extraction, truncated to `max_length`
- **LangChain wrapper:** `tool_scrape_url` returns formatted title + text

#### execute_python (`shared/mcp/tools/code_executor.py`)

Executes Python code in a sandboxed environment.

- **Input:** `code` (string)
- **Output:** `{stdout, stderr, error, return_value}` dict
- **Safety:** Only safe stdlib modules are allowed: `math`, `json`, `re`, `datetime`, `collections`, `statistics`, `csv`, `itertools`, `functools`, `string`, `textwrap`, `random`
- **Timeout:** 30 seconds
- **LangChain wrapper:** `tool_execute_python` returns stdout/stderr/error as text

#### file_io (`shared/mcp/tools/file_io.py`)

File operations within the agent workspace directory (`FILE_WORKSPACE` env var, defaults to `/tmp/agent_workspace`).

Three functions:

- **`read_file(filename)`** → `{content, exists, size, error}` -- reads file content
- **`write_file(filename, content)`** → `{written, size, error}` -- writes content to file
- **`list_files(directory)`** → `{files: [{name, size, is_dir}], error}` -- lists directory contents

All paths are restricted to the workspace directory.

#### media_processor (`shared/mcp/tools/media_processor.py`)

Multi-modal media processing via OpenAI APIs.

- **`transcribe_audio(file_path)`** → `{text, error}` -- Whisper API transcription
- **`text_to_speech(text, output_path, voice)`** → `{output_path, size, error}` -- TTS with voice selection (alloy, echo, fable, onyx, nova, shimmer)
- **`describe_image(file_path)`** → `{description, error}` -- GPT-4 Vision image description

---

## Adding a New Agent

1. Create `services/agents/my_agent.py`:

```python
from services.agents.base_agent import create_react_agent

SYSTEM_PROMPT = "You are a specialist in ..."

_agent = create_react_agent("my_agent", SYSTEM_PROMPT)

def run(message: str) -> str:
    return _agent(message)
```

2. Register the agent in `services/agents/registry.py`:

```python
from services.agents import my_agent

AGENT_REGISTRY["my_agent"] = my_agent.run
```

3. Assign tools in `shared/mcp/server.py`:

```python
TOOL_REGISTRY["my_agent"] = [tool_web_search, tool_execute_python]
```

## Adding a New Tool

1. Create the raw function in `shared/mcp/tools/my_tool.py`:

```python
def my_tool(input: str) -> dict:
    """Structured input, structured output."""
    return {"result": "..."}
```

2. Create the LangChain wrapper in `shared/mcp/server.py`:

```python
@tool
def tool_my_tool(input: str) -> str:
    """Description for the LLM to understand when to use this tool."""
    result = my_tool(input=input)
    return result["result"]
```

3. Add to `ALL_TOOLS` and the relevant agent entries in `TOOL_REGISTRY`.
