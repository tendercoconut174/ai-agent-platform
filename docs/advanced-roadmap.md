# Advanced Platform Roadmap

Ways to make the AI Agent Platform more powerful, reliable, and production-ready.

## Implemented (v0.2)

- **Retry + fallback** – `shared/retry.py`, LLM fallback via `with_fallbacks`, agent retry on ConnectionError/OSError
- **Health checks** – `GET /health`, `GET /ready` (Gateway checks DB)
- **Rate limiting** – In-memory limiter, 60 req/min per IP (`RATE_LIMIT_RPM`), applied to `/message`, `/message/stream`, `/message/upload`
- **Plan-and-Execute agent** – `plan_execute` agent type; planner creates steps, executor (analysis) runs each
- **Output validation** – Deliver node truncates results > 100k chars
- **Prometheus metrics** – `GET /metrics`, `ai_agent_requests_total`, `ai_agent_request_duration_seconds`, `ai_agent_workflows_total`
- **LangSmith tracing** – Set `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY` in `.env`
- **Streaming** – `POST /message/stream` SSE endpoint; live workflow steps and results
- **Code approval (human-in-the-loop)** – `require_code_approval` pauses for user approval before running Python code; `code_approval_id` to resume; `pending_code_approvals` table

---

## 1. Agent Architecture Upgrades

### Plan-and-Execute (for complex tasks)
- **What:** Separate planning from execution. Planner creates full step list; executor runs each step.
- **Why:** Better for long-horizon tasks, fewer mid-flight decisions, often cheaper.
- **How:** Add a `plan_and_execute` agent type or use it for `complex` intent instead of ReAct.
- **Effort:** Medium – new agent factory, planner LLM, executor (can reuse ReAct).

### Reflexion (learn from failures)
- **What:** After failure, reflect on what went wrong, store in memory, retry with improved strategy.
- **Why:** Higher success rate on hard tasks.
- **How:** Wrap agent execution in try → evaluate → reflect → retry loop; persist reflections.
- **Effort:** Medium.

### Tree of Thoughts (explore alternatives)
- **What:** Generate multiple reasoning paths, score them, prune weak ones, continue with best.
- **Why:** Better for math, puzzles, planning under uncertainty.
- **How:** Add ToT node that branches, scores, and merges; use for `analysis` or `code` on complex queries.
- **Effort:** High – many LLM calls.

---

## 2. Memory & Context

### RAG (Retrieval-Augmented Generation)
- **What:** Store documents in a vector DB; retrieve relevant chunks before answering.
- **Why:** Ground answers in your data (docs, KB, past reports).
- **How:** Add `rag_search` tool; ingest docs into Chroma/Pinecone/Weaviate; inject top-k chunks into agent context.
- **Effort:** Medium.

### Long-term memory
- **What:** Persist important facts across sessions (user preferences, past decisions).
- **Why:** More personalized, consistent behavior.
- **How:** Store summaries in DB; inject into system prompt or as tool (`recall_memory`, `store_memory`).
- **Effort:** Medium.

### Conversation summarization
- **What:** Summarize long threads to stay within context limits.
- **Why:** Handle 50+ message conversations without losing context.
- **How:** Periodically summarize and replace old messages with a summary node.
- **Effort:** Low–Medium.

---

## 3. New Tools & Capabilities

### Shell command execution (sandboxed)
- **What:** Run shell commands (e.g. `ls`, `curl`, `git status`) in a restricted environment.
- **Why:** Broader automation (CLI tools, scripts).
- **How:** Add `execute_shell` tool with allowlist, timeout, no network or restricted paths.
- **Effort:** Medium – security is critical.

### Database access
- **What:** Read/write to SQL DB via natural language.
- **Why:** Query internal data, generate reports from DB.
- **How:** Add `query_database` tool with schema introspection; restrict to read-only or specific tables.
- **Effort:** Medium.

### API / function calling
- **What:** Call external APIs (Slack, Jira, CRM) via tools.
- **Why:** Integrate with existing systems.
- **How:** Add tools per integration; use OAuth or API keys from env.
- **Effort:** Low per integration.

### Image generation
- **What:** Generate images (DALL·E, Stable Diffusion) from descriptions.
- **Why:** Reports with charts, diagrams, marketing assets.
- **How:** Add `generate_image` tool; wire to delivery for image output.
- **Effort:** Low.

---

## 4. Reliability & Robustness

### Retry with exponential backoff
- **What:** Retry failed LLM/tool calls with backoff.
- **Why:** Handle transient API errors.
- **How:** Wrap LLM and tool calls in retry decorator.
- **Effort:** Low.

### Fallback models
- **What:** If primary LLM fails, try a cheaper/smaller model.
- **Why:** Higher availability.
- **How:** Chain of `get_llm("primary")` → on error `get_llm("fallback")`.
- **Effort:** Low.

### Output validation
- **What:** Validate agent output (schema, format) before returning.
- **Why:** Fewer malformed responses.
- **How:** Pydantic validation on final result; retry or fix if invalid.
- **Effort:** Low–Medium.

### Circuit breaker
- **What:** Stop calling a failing service (LLM, search) for a cooldown period.
- **Why:** Avoid cascading failures.
- **How:** Track failure rate; open circuit for N seconds.
- **Effort:** Low.

---

## 5. Observability & Debugging

### Distributed tracing (OpenTelemetry)
- **What:** Trace requests across Gateway → Orchestrator → agents → tools.
- **Why:** Debug latency, see full flow.
- **How:** Add `opentelemetry` + `opentelemetry-instrumentation-fastapi`; export to Jaeger/Tempo.
- **Effort:** Medium.

### Structured metrics
- **What:** Prometheus metrics (request count, latency, error rate, token usage).
- **Why:** Monitor SLAs, cost, performance.
- **How:** Add `prometheus_client`; expose `/metrics`; instrument key paths.
- **Effort:** Medium.

### LangSmith / LangFuse
- **What:** Trace LLM calls, tool calls, token usage.
- **Why:** Debug prompts, compare runs, cost analysis.
- **How:** Set `LANGCHAIN_TRACING_V2=true` and API key.
- **Effort:** Low.

### Audit log
- **What:** Log all tool calls, decisions, and outputs for compliance.
- **Why:** Audit trail, debugging, safety.
- **How:** Persist to DB or log aggregator with workflow_id, user, timestamp.
- **Effort:** Low–Medium.

---

## 6. Performance

### LLM response caching
- **What:** Cache identical prompts (e.g. classify, plan) for a TTL.
- **Why:** Lower cost and latency for repeated patterns.
- **How:** Redis or in-memory cache keyed by hashed prompt.
- **Effort:** Medium.

### Streaming tool results
- **What:** Stream long tool outputs (e.g. web search) to the agent incrementally.
- **Why:** Faster time-to-first-token.
- **How:** Use streaming tool interface if supported.
- **Effort:** High.

### Parallel plan execution (already done)
- You already parallelize independent steps. Consider more aggressive batching where safe.

---

## 7. Security & Safety

### Rate limiting
- **What:** Limit requests per user/session/IP.
- **Why:** Prevent abuse, control cost.
- **How:** `slowapi` or Redis-based rate limiter.
- **Effort:** Low.

### Input sanitization
- **What:** Validate and sanitize user input (prompt injection, XSS).
- **Why:** Reduce injection and misuse.
- **How:** Blocklist patterns, length limits, output encoding.
- **Effort:** Low–Medium.

### Tool execution sandbox
- **What:** Stricter sandbox for `execute_python` (e.g. no subprocess, resource limits).
- **Why:** Safer code execution.
- **How:** Use `restrictedpython` or containerized execution.
- **Effort:** Medium.

### PII redaction
- **What:** Redact PII from logs and traces.
- **Why:** Compliance (GDPR, HIPAA).
- **How:** Regex or NER-based redaction in logging layer.
- **Effort:** Medium.

---

## 8. Multi-Agent Collaboration

### Agent delegation
- **What:** One agent delegates sub-tasks to others (e.g. researcher → analyst → generator).
- **Why:** Better specialization, clearer flow.
- **How:** Add `delegate_to` tool or supervisor node that routes to sub-agents.
- **Effort:** Medium.

### Debate / consensus
- **What:** Multiple agents propose answers; aggregate or vote.
- **Why:** More robust answers.
- **How:** Run N agents in parallel; merge with LLM or voting.
- **Effort:** High.

### Hierarchical planning
- **What:** High-level planner breaks work into sub-goals; each sub-goal has its own plan.
- **Why:** Scale to very complex tasks.
- **How:** Recursive plan → execute with sub-planner.
- **Effort:** High.

---

## 9. Production Readiness

### Health checks
- **What:** `/health` and `/ready` endpoints (DB, LLM, tools).
- **Why:** Load balancer and orchestration know when to route traffic.
- **How:** FastAPI dependency that checks dependencies.
- **Effort:** Low.

### Graceful shutdown
- **What:** Finish in-flight requests before exiting.
- **Why:** No dropped requests during deploy.
- **How:** Handle SIGTERM, drain connections, await pending tasks.
- **Effort:** Low.

### Configurable timeouts
- **What:** Per-endpoint or per-workflow timeouts.
- **Why:** Avoid runaway requests.
- **How:** Env vars + `asyncio.wait_for` at key boundaries.
- **Effort:** Low.

### Horizontal scaling
- **What:** Run multiple Gateway/Orchestrator instances behind a load balancer.
- **Why:** Handle more traffic.
- **How:** Stateless services; shared PostgreSQL/Redis for sessions.
- **Effort:** Low (if already stateless).

---

## Suggested Priority Order

| Priority | Item                    | Impact | Effort |
|----------|-------------------------|--------|--------|
| 1        | Plan-and-Execute agent  | High   | Medium |
| 2        | Retry + fallback        | High   | Low    |
| 3        | LangSmith tracing       | High   | Low    |
| 4        | RAG / document search   | High   | Medium |
| 5        | Shell execution (safe)  | Medium | Medium |
| 6        | Rate limiting           | Medium | Low    |
| 7        | Prometheus metrics      | Medium | Medium |
| 8        | Long-term memory        | Medium | Medium |
| 9        | Output validation      | Medium | Low    |
| 10       | Health checks           | Medium | Low    |

Start with **Plan-and-Execute** for complex tasks and **retry + tracing** for reliability, then add RAG and new tools as needed.
