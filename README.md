# Saylani Student Ops Desk

A multi-agent help desk for bootcamp students. The Desk answers admin questions
itself, hands assignment and career questions to specialists, and ends every
conversation with a structured `Ticket` rather than free prose.

Built with the OpenAI Agents SDK against `gemini-3.6-flash`, with a terminal
entry point and a Chainlit browser interface.

## Running it

```bash
cp .env.example .env          # then fill in GEMINI_API_KEY
uv sync

uv run main.py                # terminal
uv run chainlit run app.py    # browser, http://localhost:8000
```

A missing `GEMINI_API_KEY` fails at startup with one readable line, never a
traceback.

## Layout

| Path | Purpose |
|---|---|
| `config.py` | env loading, the Gemini client, model name, turn ceiling, tracing |
| `main.py` | terminal entry point — async loop over `Runner.run` |
| `app.py` | Chainlit entry point — per-session profile and history |
| `desk_agent.py` | the Ops Desk: routing rules, per-turn instructions, handoffs |
| `specialists.py` | base specialist and its two clones (Assignments, Careers) |
| `summariser.py` | the Summariser, exposed to the Desk as a tool |
| `guardrail.py` | on-topic input guardrail, runs before the Desk's model |
| `tools.py` | course lookups, account status, priority review, `close_ticket` |
| `ticket.py` | the `Ticket` model and the shared ticket instructions |
| `student_profile.py` | the run context — validated at construction |
| `audit.py` | run-level hooks writing `audit_log.jsonl` |
| `run_support.py` | run-boundary retry helper (currently a pass-through) |
| `courses.json` | the course data source, read fresh on every tool call |
| `public/`, `chainlit.md` | Chainlit theme, logo, avatars, welcome screen |
| `scripts/` | live verification for the routing and summariser requirements |

## Specification

The four Phase 0 documents govern everything here and were committed before any
code — `git log` shows the ordering.

| Document | Contents |
|---|---|
| `constitution.md` | non-negotiable rules; takes precedence over all else |
| `spec.md` | the 13 functional requirements and their acceptance criteria |
| `plan.md` | architecture: agents, tools, data structures, design decisions |
| `tasks.md` | the task breakdown and verification for each |

## Notes

- The model client is configured per agent, never globally —
  `set_default_openai_client` appears nowhere in the codebase.
- Student data reaches tools through the SDK's run context, never as a
  model-supplied argument: `get_account_status` has an empty parameter schema.
- Course facts reach the model only through tool return values. Deleting a
  course from `courses.json` removes it from answers with no code change.
- Every run is bounded by a 10-turn ceiling and produces a `Ticket`, including
  when it cannot resolve the request.
