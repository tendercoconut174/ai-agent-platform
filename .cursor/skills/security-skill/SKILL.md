---
name: security-skill
description: Generate authentication, authorization, API key handling, and input validation. Use when implementing auth, securing endpoints, or when the user mentions JWT, OAuth, API keys, or rate limiting.
---

# Security Skill – AI Agent Platform

## When this skill applies

Use this skill when generating:

- authentication (JWT, OAuth, API keys)
- authorization and role checks
- input validation and sanitization
- rate limiting
- secrets management

---

# Authentication

- Store API keys and secrets in environment variables.
- Never commit secrets to the repository.
- Use `python-dotenv` for local `.env`; inject via Docker in production.
- Validate tokens before processing requests.

---

# API Security

1. Validate all inputs with Pydantic.
2. Reject oversized payloads (set body size limits).
3. Sanitize user input before passing to agents/tools.
4. Use HTTPS in production.
5. Return generic error messages; avoid leaking internal details.

---

# Rate Limiting

- Apply rate limits at the gateway layer.
- Use Redis for distributed rate limiting.
- Return 429 with Retry-After header when exceeded.
- Different limits for authenticated vs anonymous.

---

# Rules

- Do NOT log secrets, tokens, or PII.
- Do NOT expose stack traces to clients.
- Use parameterized queries; never concatenate user input into SQL.
