# Tasks — Saylani Student Ops Desk

**Version:** 1.0.0
**Governs:** Build order. Every task names the requirement(s) it satisfies and a concrete
verification step. Tasks within a phase MUST be completed in order where a dependency is listed;
tasks with no dependency on each other within a phase may be done in either order.

Legend: 🔪 = on the cut list (see `spec.md` §7) — safe to skip under time pressure, in the stated
order, only after everything else in its phase is done.

---

## Phase 0 — Specification Gate (target: 0:00–0:35)

| ID | Task | Satisfies | Verification | Depends on |
|---|---|---|---|---|
| T001 | Initialize git repo; create `.gitignore` containing at least `.env`, `__pycache__/`, `.venv/` | Constitution Art. II.2 | `git status` shows `.gitignore` tracked before any secret file exists | — |
| T002 | Write and commit `constitution.md` | Art. V | `git log` shows this as one of the first commits | T001 |
| T003 | Write and commit `spec.md` | Art. V | commit exists, no code files in the same commit | T002 |
| T004 | Write and commit `plan.md` | Art. V | commit exists, no code files in the same commit | T003 |
| T005 | Write and commit `tasks.md` (this file) | Art. V | commit exists, no code files in the same commit | T004 |
| T006 | Create `.env.example` with placeholder keys only; commit it | NFR-1, Art. II.3 | file contains no real secret | T005 |
| T007 | Verify Phase 0 gate: `git log --oneline` shows T002–T006 all preceding any future runtime-file commit | NFR-5 | manual/log inspection | T002–T006 |

**Gate:** do not proceed to Phase 1 until T007 is confirmed.

## Phase 1 — Core Desk (target: 0:35–1:05)

| ID | Task | Satisfies | Verification | Depends on |
|---|---|---|---|---|
| T101 | Add `.env` (untracked) with real `GEMINI_API_KEY`; add startup check that fails fast with a named error if missing | FR-1, NFR-1 | run with the key removed → single clear error, no traceback | T006 |
| T102 | Create the Gemini OpenAI-compatible client and wire it into the Desk agent's own definition (not a global default) | FR-1, Art. I | grep confirms no `set_default_openai_client` anywhere | T101 |
| T103 | Write `courses.json` with at least one course, one policy, one assignment, matching the schema in `plan.md` §4.3 | FR-2 | file validates as JSON; matches schema | T005 |
| T104 | Implement `list_courses` and `get_course` tools, reading `courses.json` fresh on every call, with not-found/unavailable handling per `spec.md` §4.2 | FR-2, Art. III, NFR-4 | delete a course from the file, re-run, it disappears from answers with no code change | T103 |
| T105 | Implement `get_assignment` tool with the same not-found handling | FR-2 | asking for a nonexistent assignment id returns a clear "not found," never a fabricated date | T103 |
| T106 | Define the `StudentProfile` dataclass with `__post_init__` validation exactly as in `plan.md` §4.1 | FR-3 | constructing with an invalid `tier` or negative `open_tickets` raises immediately | — |
| T107 | Implement `get_account_status` tool reading only from run context, with zero model-supplied parameters | FR-3 | inspect the tool's generated schema — it has no parameters | T106 |
| T108 | Implement per-turn dynamic instructions builder for the Desk: greets by name, names the course, applies terse mode when `open_tickets >= 3` | FR-4 | three profiles crossing the threshold produce three visibly different instruction strings; print one before any model call | T106 |
| T109 | Wire an async `main()` entry point using `asyncio.run`, looping on terminal input, calling the Desk agent | FR-1 | typed terminal question receives a Gemini-generated answer | T102, T104, T108 |

**Phase 1 exit check:** FR-1 through FR-4 demonstrable in the terminal.

## Phase 2 — Specialists (target: 1:05–1:35)

| ID | Task | Satisfies | Verification | Depends on |
|---|---|---|---|---|
| T201 | Define the Base Specialist agent (shared model settings, placeholder instructions) | FR-5 | exists as a distinct definition, not yet exposed | T102 |
| T202 | Clone Base into the Assignments Specialist; override instructions to cold/factual and lower temperature | FR-5 | Assignments' instructions differ from Base; model config otherwise matches | T201 |
| T203 | Clone Base into the Careers Specialist; override instructions to warmer tone and higher temperature | FR-5 | Careers' instructions differ from Base and from Assignments | T201 |
| T204 | Wire handoffs from the Desk to Assignments and Careers; encode the Assignment > Career > Admin precedence in the Desk's instructions | FR-5 | ambiguous test question resolves to Assignment when both signals present | T108, T202, T203 |
| T205 | Confirm the answering agent is identifiable after a run that hands off (via the run result's last-agent info) | FR-5 | print/log which agent authored the final message | T204 |
| T206 🔪 | Implement the Summariser agent and expose it to the Desk via `.as_tool(...)`; enforce the ≤3-line / empty-input rules from `spec.md` §4.6 | FR-6 | summarizing a long policy answer yields ≤3 lines, still delivered in the Desk's voice | T108 |
| T207 | Define the `Ticket` Pydantic model exactly as in `plan.md` §4.2; set it as `output_type` on Desk, Assignments, and Careers | FR-7 | `type(result.final_output) is Ticket` in code | T106 |
| T208 | Add a code path that branches on `Ticket.resolved` (e.g. decides whether to prompt for more detail) | FR-7 | demonstrable `if ticket.resolved:` branch in source | T207 |
| T209 | Confirm a deliberately impossible categorization surfaces the SDK's structured-output parsing error rather than a half-filled `Ticket` | FR-7 | trigger it once, observe the exception, catch it at a defined boundary | T207 |
| T210 | Implement the on-topic input guardrail; wire it to run before the Desk agent | FR-8 | off-topic input never reaches the Desk's model | T108 |
| T211 | Catch the guardrail's tripwire at the top-level message handler; reply with a fixed polite refusal; confirm no `Ticket` is produced for that turn | FR-8, Art. VIII | off-topic question → refusal shown, program does not crash | T210 |
| T212 | Confirm pleasantries ("hi", "thanks") and broad-but-relevant questions are NOT rejected by the guardrail | FR-8 | run both test cases, both pass through | T210 |
| T213 | Implement `request_priority_review` tool; construct each run's tool list dynamically so it is included only when `context.tier == "scholarship"` | FR-9a | same question run as regular vs. scholarship shows two different tool lists | T106 |
| T214 | Implement `close_ticket` tool that ends the run immediately on invocation, its output becoming `final_output` | FR-9b | invoking it mid-run stops further turns | T207 |
| T215 | Set the turn ceiling to 10 on every run; catch the max-turns exception at the run boundary with a graceful message | FR-9c | forcing more than 10 turns raises, is caught, does not crash | T109 |

**Phase 2 exit check:** FR-5 through FR-9 demonstrable, including both tool-list variants and one guardrail refusal.

## Phase 3 — Operations and Interface (target: 1:35–1:55)

| ID | Task | Satisfies | Verification | Depends on |
|---|---|---|---|---|
| T301 | Implement `RunHooks` recording agent start/end, handoff, and tool start/end for every agent in a run | FR-10 | one run yields one ordered timeline naming both agents | T204 |
| T302 | Append every recorded event to `audit_log.jsonl` (or equivalent durable store) | FR-10, NFR-3 | file grows with each run; survives process restart | T301 |
| T303 🔪 (AgentHooks half) | Attach `AgentHooks` to the Assignments Specialist only | FR-10 | events appear only while Assignments holds the conversation | T202, T301 |
| T304 🔪 | Implement a custom runner subclass/wrapper stamping `request_id` + elapsed time around every run; register once at startup | FR-11 | wrapper output appears in logs for the run; no agent file imports it | T109 |
| T305 | Set up a Chainlit `on_chat_start` handler constructing one `StudentProfile` and empty history per session, stored session-scoped | FR-12 | two browser tabs never share state | T108 |
| T306 | Set up a Chainlit `on_message` handler that `await`s the run and updates session history | FR-12 | a follow-up message correctly references the prior turn; using the sync run variant is confirmed to break this | T305 |
| T307 | Enable tracing, export under the developer's own key from `.env`; group Desk + specialist spans under the shared `request_id` | FR-13 | one full conversation (with handoff) opens as a single trace | T304, T306 |
| T308 | Walk one recorded trace end-to-end; name every span; identify one call that, in hindsight, was not strictly necessary | FR-13 | discussion-ready answer prepared for the viva | T307 |

**Phase 3 exit check:** FR-10 through FR-13 demonstrable; cut list applied here first if behind schedule, in order T304 → T206 → T303.

## Demo Prep (target: 1:55–2:00)

| ID | Task | Satisfies | Verification |
|---|---|---|---|
| T401 | Run one clean, non-trivial conversation end-to-end (including a handoff) in the Chainlit UI | Overall demo | recorded/screenshotted |
| T402 | Open and display the trace for that exact conversation | FR-13 | trace matches the demoed conversation |
| T403 | Display the resulting `Ticket` object (typed, not prose) | FR-7 | `type()` check shown live |
| T404 | Re-read every diff produced by the coding agent at least once before the viva | Constitution Art. V.2, "you own it" | self-check — be ready to explain any line |

## Pre-Viva Self-Check (map to the eight defense questions)

- [ ] Can show the schema for `get_account_status` and explain why it has no identity parameter (T107).
- [ ] Can open a trace and show a rejected question cost nothing at the Desk's model (T211, T308).
- [ ] Can state exactly which attributes Assignments/Careers share with Base vs. override (T201–T203).
- [ ] Can predict what breaks if a specialist is renamed, and where that name is read from (T204).
- [ ] Can explain why the Chainlit handler awaits the run and what breaks if it doesn't (T306).
- [ ] Can name the exact exception raised by a `Ticket` missing a required field, and which layer raises it (T209).
- [ ] Can give the count of `AgentHooks` vs. `RunHooks` firings for one full ticket (T301, T303).
- [ ] Can state what the custom runner records that the hooks do not (T304).
