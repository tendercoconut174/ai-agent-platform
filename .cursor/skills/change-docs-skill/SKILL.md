---
name: change-docs-skill
description: Enforces documentation updates alongside code changes. After every code change, update README.md, relevant docs, and Cursor skills to reflect the new state. Use proactively after any feature, refactor, bugfix, or architectural change.
---

# Change Documentation Skill

## Core Rule

**Every code change must be accompanied by documentation updates.** Never finish a task without checking whether README.md, docs, or skills need updating.

---

## After Every Change, Check This List

1. **README.md** -- Does the change affect any of these sections?
   - Architecture diagram or component descriptions
   - Key Features list
   - Environment Variables table
   - Project Structure tree
   - Quick Start or API Usage examples
   - Prerequisites or dependencies

2. **docs/** -- Does the change touch:
   - API contracts → update `docs/api-reference.md`
   - System architecture → update `docs/architecture.md`
   - Agent or tool behavior → update `docs/agents-and-tools.md`
   - Dev setup or workflow → update `docs/development.md`

3. **Cursor skills** (`.cursor/skills/`) -- Does the change alter:
   - Code patterns (e.g. sync→async, new factory) → update `coding-skill`
   - Agent structure or registry → update `agent-skill`
   - Workflow or supervisor logic → update `workflow-skill`
   - Infrastructure or deployment → update `devops-skill`
   - Tool system or MCP → update `tool-skill`

---

## What to Update

### README.md Updates

- **New feature**: Add to Key Features, update Architecture diagram if needed, add API example
- **New env var**: Add row to Environment Variables table
- **New file or module**: Add to Project Structure tree
- **Dependency change**: Update Prerequisites or install instructions
- **Breaking change**: Note prominently at the top of the relevant section

### docs/ Updates

Keep docs accurate and current. Don't let them drift from the implementation. When updating:
- Use concrete code snippets, not vague descriptions
- Update Mermaid diagrams if the flow changed
- Remove references to deleted/renamed components

### Skill Updates

When a code pattern changes (e.g. agents became async), update the skill's example code to match. Outdated skill patterns cause the agent to generate wrong code in future tasks.

---

## What NOT to Do

- Don't create new doc files unless a genuinely new area is introduced
- Don't rewrite entire README for minor changes -- surgical updates only
- Don't document internal implementation details in README (keep it user-facing)
- Don't add redundant comments in code that just narrate the change

---

## Quick Reference: README Sections to File Mapping

| Change Area | README Section | Doc File |
|-------------|---------------|----------|
| New API endpoint | API Usage | `docs/api-reference.md` |
| New agent type | Architecture, Project Structure | `docs/agents-and-tools.md` |
| New env var | Environment Variables | `docs/development.md` |
| New dependency | Prerequisites, pyproject.toml | `docs/development.md` |
| Workflow change | Supervisor Flow Detail | `docs/architecture.md` |
| New tool | Architecture | `docs/agents-and-tools.md` |
| Async/sync change | -- | `coding-skill` |
| New LLM provider | Environment Variables, LLM section | `docs/development.md` |
