# Constitution — Saylani Student Ops Desk

**Version:** 1.1.0
**Status:** Ratified
**Applies to:** All source code, configuration, and documentation produced for this project.

## Preamble

This document defines the non-negotiable rules governing the design and implementation of the
Saylani Student Ops Desk. Every requirement in `spec.md`, every architectural decision in
`plan.md`, and every task in `tasks.md` MUST comply with the articles below. Where a conflict
exists between this document and any other project artifact, this document takes precedence, and
the conflicting artifact MUST be corrected before work continues.

The keywords **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are to be interpreted
as in RFC 2119.

---

## Article I — Model Provider and Configuration

1. The Desk MUST use `gemini-3.6-flash` as its underlying language model, accessed through an
   OpenAI-compatible client pointed at the Gemini API endpoint.
2. The model client MUST be configured at the **agent level** — i.e. passed into each `Agent`
   definition's own model/client configuration.
3. `set_default_openai_client`, or any equivalent global/process-wide client override, MUST NOT
   appear anywhere in the codebase, in any form (including inside test files or notebooks kept in
   the repo).
4. No agent MAY select or override its model at the **per-run** level (inside the code that calls
   `Runner.run`). Model selection is a property of the agent definition, never of a single
   invocation.
5. Every agent definition MUST declare its own model settings (temperature, max tokens, etc.)
   explicitly. An agent MAY inherit settings only from the specific base agent it was cloned from
   (see Article on Cloning in `plan.md`) — silent inheritance from anywhere else is prohibited.

**Amendment history:** `gemini-2.5-flash` was replaced with `gemini-3.6-flash` on 2026-09-22 after
Google blocked the former for this project's API key ahead of its stated retirement (not before
2026-10-16). See commit AMENDMENT_HASH.

## Article II — Secrets Management

1. All credentials (Gemini API key, tracing export key) MUST live exclusively in a `.env` file at
   the project root.
2. `.env` MUST already be listed in `.gitignore` in the very first commit that touches it. A commit
   that introduces `.env` containing a real secret is a violation regardless of whether it is later
   removed — history is permanent.
3. An `.env.example` file containing only placeholder values (e.g. `GEMINI_API_KEY=your-key-here`)
   MUST be committed so a third party can run the project.
4. If a required environment variable is missing or empty at startup, the program MUST fail fast
   with one human-readable error naming the missing variable — e.g. *"Missing required environment
   variable: GEMINI_API_KEY. Copy .env.example to .env and fill it in."* A raw stack trace,
   `ImportError`, or `KeyError` as the first visible symptom is a violation.
5. No secret MUST be logged, printed, embedded in a trace span, or written into the audit trail at
   any verbosity level, including debug logging.

## Article III — Tool Safety

1. No tool function exposed to an agent MUST allow an unhandled exception to propagate out of the
   tool and into the agent runner.
2. Every tool MUST catch every exception it can foreseeably raise (missing file, malformed JSON,
   missing key, wrong type, out-of-range id) internally and return a short, model-actionable string
   or structured value instead of raising.
3. A tool that cannot complete its purpose (e.g. the requested course id does not exist) MUST say so
   in a way the model can act on — e.g. *"No course with id 'x'. Known ids: [...]"* — rather than
   returning `None`, an empty value, or letting an exception surface.
4. A caught exception inside a tool MUST still be visible in logs or the audit trail (it is a defect
   to fix later, per Article VIII) even though it is never re-raised to the agent runner.

## Article IV — Student Data Isolation

1. Student-identifying data (name, roll number, tier, open-ticket count) MUST reach the model only
   through the SDK's local run-context mechanism, never by being interpolated into a static prompt
   template that the model then reads as ordinary instruction text.
2. Any tool that reads the student profile MUST take the run context as its context parameter, not
   as a model-supplied argument. The generated parameter schema for such a tool MUST NOT contain a
   field for name, roll number, or tier.
3. Grepping the source tree for a real student's name or roll number MUST find it only inside the
   code that constructs the `StudentProfile` object (or test fixtures) — never inside a prompt
   string, an f-string handed to the model, or a hardcoded instruction.
4. Course data (`courses.json`) MUST reach the model only through tool return values, never by being
   loaded wholesale into a system prompt.

## Article V — Specification-First Development

1. No implementation file (`.py`, runtime `.json`, `.env`, `pyproject.toml`, etc.) may be committed
   before `constitution.md`, `spec.md`, `plan.md`, and `tasks.md` are all committed.
2. A single commit MUST NOT contain both a Phase 0 specification artifact and implementation code.
   Mixing them fails Phase 0 regardless of whether the resulting code works.
3. `git log` (in chronological order) MUST show all four Phase 0 documents added in commits that
   precede the first commit touching any runtime file. This is mechanically checked — see NFR-5 in
   `spec.md`.

## Article VI — Cost and Ceiling Discipline

1. Every agent MUST declare explicit model settings; none may generate under an unbounded
   configuration.
2. Every run MUST be protected by a maximum-turn ceiling. When exceeded, the SDK's max-turns
   exception MUST be caught at the boundary that invoked the run and reported to the student as a
   graceful message — never as an unhandled crash.
3. The guardrail MUST reject disqualifying input before the Desk's primary model is invoked, so a
   rejected request incurs no billed generation call from that model.

## Article VII — Observability and Auditability

1. Tracing MUST be enabled for every run, exported under the developer's own tracing key — never a
   shared or hardcoded key committed to source.
2. One end-to-end student conversation, including any handoff, MUST appear as a single trace, never
   as multiple disconnected traces.
3. The audit timeline produced by the run-level hooks MUST be persisted somewhere durable (a file or
   database), not only printed to the terminal.

## Article VIII — Failure Philosophy

1. A tool raising an exception into the runner is a **defect** in this project, not an acceptable
   failure mode. Article III governs how this is prevented.
2. Any exception that is an expected part of normal operation — guardrail tripwire, turn-ceiling
   exceeded, structured-output parse failure — MUST be caught at a well-defined boundary and turned
   into a specific, polite message. The student MUST NOT ever see a Python traceback.
3. When the Desk cannot resolve a request that reached it (i.e. it passed the guardrail), it MUST
   still produce a `Ticket` with `resolved: false` — never terminate with no output. A request
   rejected by the guardrail *before* reaching the Desk is the only case where no `Ticket` is
   produced (see `spec.md` §4.8).

## Article IX — Amendments

Any change to this document MUST be its own commit with a message beginning `constitution:`, and
MUST be reflected the same day in any part of `spec.md`, `plan.md`, or `tasks.md` it affects.
