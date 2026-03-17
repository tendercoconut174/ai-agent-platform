# API Reference

The platform exposes two services: the **Gateway** (port 8000) and the **Orchestrator** (port 8001). Users interact with the Gateway only; the Orchestrator is an internal service.

## Gateway Endpoints (port 8000)

### GET /health

Health check.

**Response:**

```json
{"status": "ok"}
```

---

### POST /message

Synchronous message endpoint. Sends the user message to the orchestrator, waits for the result, and returns it. For file formats (PDF, Excel, audio), returns a binary file download.

**Request Body** (`application/json`):

```json
{
  "message": "research top tech companies",
  "output_format": "json",
  "mode": "auto",
  "session_id": null,
  "callback_url": null,
  "metadata": null,
  "workflow_id": null,
  "require_code_approval": false,
  "code_approval_id": null
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `message` | string | yes | -- | User message or task description |
| `output_format` | string | no | `"json"` | Output format: `json`, `pdf`, `xl`, `audio` |
| `mode` | string | no | `"auto"` | Execution mode: `auto`, `chat`, `task` |
| `session_id` | string | no | auto-generated | Session ID for conversation continuity |
| `callback_url` | string | no | null | Webhook URL for async result delivery |
| `metadata` | object | no | null | Extra context |
| `workflow_id` | string | no | null | When resuming after clarification: the `workflow_id` from the `needs_clarification` response |
| `require_code_approval` | boolean | no | false | When true, pause for user approval before running Python code |
| `code_approval_id` | string | no | null | When resuming after code approval: the `code_approval_id` from the `needs_code_approval` response |

**Preference Inference:**

The gateway uses an LLM to infer preferences from the message text:
- **output_format**: Detects requests for PDF, Excel, JSON, audio, markdown, etc.
- **require_code_approval**: Detects when the user wants to approve code before execution.
- **clean_message**: Strips format/approval hints so agents focus on the actual task.
- **format_hint**: Instruction for the planner (e.g. "Format as markdown table", "Format as concise spoken summary").

No regex or hardcoded patterns are used; inference is fully LLM-based. On resume flows (clarification, code approval), inference is skipped and the merged message is forwarded as-is.

**Response (JSON format):**

```json
{
  "result": "The top tech companies by revenue are...",
  "workflow_id": "4f076e33-f859-437a-ab4a-038d6a05873e",
  "output_format": "json",
  "content_base64": null,
  "content_type": null,
  "filename": null,
  "session_id": "bd87e8c8-d6e7-4d28-87e1-da4685ef5b1b",
  "needs_clarification": false,
  "question": null
}
```

**Response (needs clarification – human-in-the-loop):**

When the request is too vague or ambiguous, the response includes:

```json
{
  "result": "Which industry or sector are you interested in?",
  "workflow_id": "4f076e33-f859-437a-ab4a-038d6a05873e",
  "output_format": "json",
  "session_id": "bd87e8c8-d6e7-4d28-87e1-da4685ef5b1b",
  "needs_clarification": true,
  "question": "Which industry or sector are you interested in?"
}
```

To resume, send a follow-up with the same `session_id` and the **`workflow_id` from the needs_clarification response** (not an older workflow_id), and your clarification as `message`:

```json
{
  "message": "tech sector",
  "workflow_id": "4f076e33-f859-437a-ab4a-038d6a05873e",
  "session_id": "bd87e8c8-d6e7-4d28-87e1-da4685ef5b1b"
}
```

**Response (needs code approval – human-in-the-loop):**

When `require_code_approval` is true and an agent proposes Python code, the response includes:

```json
{
  "result": "I've prepared code to calculate the result. Please approve and run it.",
  "workflow_id": "4f076e33-f859-437a-ab4a-038d6a05873e",
  "output_format": "json",
  "session_id": "bd87e8c8-d6e7-4d28-87e1-da4685ef5b1b",
  "needs_code_approval": true,
  "code_approval_id": "abc123-def456-...",
  "code": "print(2 + 2)"
}
```

To resume, send a follow-up with the same `session_id` and **`code_approval_id`**. The gateway runs the approved code and forwards the output to the orchestrator. You can send any message (e.g. "approved" or "run"):

```json
{
  "message": "approved",
  "code_approval_id": "abc123-def456-...",
  "session_id": "bd87e8c8-d6e7-4d28-87e1-da4685ef5b1b"
}
```

**Response (file format):**

When `output_format` is `pdf`, `xl`, or `audio` and the conversion succeeds, the response is a binary file download:

| Header | Value |
|--------|-------|
| `Content-Type` | `application/pdf`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, or `audio/mpeg` |
| `Content-Disposition` | `attachment; filename="result_<workflow_id>.pdf"` (or `.xlsx`, `.mp3`) |

**Error Response:**

```json
{
  "detail": "Orchestrator error: <error message>"
}
```

Status code: `502 Bad Gateway`

---

### POST /message/stream

Stream workflow progress via Server-Sent Events. Same request body as `POST /message`. Returns SSE events with live step updates and final delivery. Use when you want real-time progress (e.g. in a UI with a steps panel).

**Request Body:** Same as `POST /message` (including `require_code_approval`, `code_approval_id`).

**Response:** `text/event-stream` with JSON events:

| Event `type` | Description |
|--------------|-------------|
| `step` | Workflow step update (node_id, agent_type, result, etc.) |
| `done` | Final delivery (result, needs_clarification, needs_code_approval, etc.) |
| `error` | Error occurred |

When `done` includes `needs_code_approval: true`, the event contains `code_approval_id` and `code` for the user to approve.

---

### POST /message/upload

Multipart upload endpoint for multi-modal input. Accepts text, audio, images, and file attachments.

**Request Body** (`multipart/form-data`):

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `message` | string | no | null | Text message |
| `output_format` | string | no | `"json"` | Output format |
| `mode` | string | no | `"auto"` | Execution mode |
| `session_id` | string | no | null | Session ID |
| `audio` | file | no | null | Audio file (WAV, MP3, etc.) -- transcribed via Whisper |
| `image` | file | no | null | Image file (PNG, JPG, etc.) -- described via GPT-4V |
| `files` | file[] | no | null | File attachments (PDF, Excel, CSV, TXT) -- text extracted |

At least one of `message`, `audio`, `image`, or `files` must be provided.

**Input Processing:**

1. **Audio**: Transcribed to text using OpenAI Whisper, prepended as `[Voice transcription]: ...`
2. **Image**: Described using GPT-4 Vision, prepended as `[Image description]: ...`
3. **Files**: Text extracted based on file type:
   - PDF: text extracted page by page
   - Excel/CSV: converted to markdown tables
   - TXT: read directly
   - File content prepended as `[File: filename.ext]: ...`

All inputs are combined into a single text message for the orchestrator.

**Response:** Same as `POST /message`.

**Example:**

```bash
curl -X POST http://localhost:8000/message/upload \
  -F message="summarize this meeting" \
  -F audio=@meeting_recording.wav \
  -F files=@meeting_notes.pdf
```

---

## Orchestrator Endpoints (port 8001)

These are internal endpoints called by the Gateway. Not intended for direct user access.

### GET /health

Health check.

**Response:**

```json
{"status": "ok"}
```

---

### POST /orchestrate

Runs the full supervisor workflow for a given message.

**Request Body:**

```json
{
  "message": "research top tech companies",
  "output_format": "json",
  "mode": "auto",
  "session_id": "uuid",
  "callback_url": null,
  "format_hint": "",
  "is_clarification_resume": false
}
```

| Field | Description |
|-------|-------------|
| `format_hint` | Agent-inferred instruction for planner. Set by gateway from preference inference. |
| `is_clarification_resume` | Set by gateway when resuming after clarification; orchestrator skips classify and routes to plan. |

**Response:**

Returns a `MessageResponse` dict from the delivery service:

```json
{
  "result": "...",
  "workflow_id": "uuid",
  "output_format": "json",
  "content_base64": "base64string...",
  "content_type": "application/pdf",
  "filename": "result_uuid.pdf",
  "session_id": null
}
```

For JSON format, `content_base64`, `content_type`, and `filename` are null.

**Error Response:**

```json
{
  "detail": "error message"
}
```

Status code: `500 Internal Server Error`

---

## Response Models

### MessageResponse

```python
class MessageResponse(BaseModel):
    result: str
    workflow_id: Optional[str] = None
    output_format: str = "json"
    content_base64: Optional[str] = None
    content_type: Optional[str] = None
    filename: Optional[str] = None
    session_id: Optional[str] = None
    needs_clarification: bool = False
    question: Optional[str] = None  # Clarifying question when needs_clarification is true
```

### WorkflowResponse

```python
class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    message: str = "Workflow created"
```

### WorkflowStatusResponse

```python
class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str
    goal: str
    iteration_count: int = 0
    steps: list[StepStatus] = []
    result: Optional[str] = None
    error: Optional[str] = None
```

---

## Common Patterns

### Session Continuity

```bash
# First request -- get session_id from response
RESP=$(curl -s -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the top AI companies?"}')
SESSION=$(echo $RESP | jq -r '.session_id')

# Follow-up using same session
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"tell me more about the first one\", \"session_id\": \"$SESSION\"}"
```

### File Download

```bash
# PDF download
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "give me a pdf of world cup winners"}' \
  --output result.pdf

# Excel download
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "give me excel of top 10 countries by GDP"}' \
  --output result.xlsx
```

### Human-in-the-Loop (Clarification)

```bash
# Step 1: Vague request – receive clarifying question
RESP=$(curl -s -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "research companies"}')
echo $RESP | jq .
# {"result": "Which industry?", "workflow_id": "uuid", "needs_clarification": true, "question": "Which industry?", ...}

# Step 2: Resume with clarification
WF_ID=$(echo $RESP | jq -r '.workflow_id')
SESSION=$(echo $RESP | jq -r '.session_id')
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"tech sector\", \"workflow_id\": \"$WF_ID\", \"session_id\": \"$SESSION\"}"
```

### Human-in-the-Loop (Code Approval)

```bash
# Step 1: Request with code approval enabled – agent proposes code
RESP=$(curl -s -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "calculate 2+2 in Python", "require_code_approval": true}')
echo $RESP | jq .
# {"result": "...", "needs_code_approval": true, "code_approval_id": "uuid", "code": "print(2+2)", ...}

# Step 2: Resume with approval – gateway runs code and forwards output
APPROVAL_ID=$(echo $RESP | jq -r '.code_approval_id')
SESSION=$(echo $RESP | jq -r '.session_id')
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"approved\", \"code_approval_id\": \"$APPROVAL_ID\", \"session_id\": \"$SESSION\"}"
```

### Explicit Format

```bash
# Explicitly set output_format (no auto-detection needed)
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message": "list all ICC T20 world cup winners", "output_format": "xl"}' \
  --output result.xlsx
```
