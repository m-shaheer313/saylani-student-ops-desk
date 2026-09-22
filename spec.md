# Specification — Saylani Student Ops Desk

**Version:** 1.0.0
**Governs:** Behavior only. No implementation detail, library name, or code shape is normative
here — see `plan.md` for architecture and `tasks.md` for build order. Any behavior described here
that conflicts with `constitution.md` is void; the constitution wins.

RFC 2119 keywords (MUST / MUST NOT / SHOULD / MAY) apply throughout.

---

## 1. Purpose

The Ops Desk is the single front door for a student's questions about their own bootcamp. A student
asks something in plain language; the Desk determines whether it concerns an assignment, a career
question, or course administration, answers using real, current course data, and — for every
request that reaches it — closes the exchange with a structured record suitable for downstream
filing.

## 2. Scope

### 2.1 In scope

- Answering questions about: assignment details/due dates, course schedule, course policies
  (e.g. late-submission rules), and career guidance related to the bootcamp.
- Identifying which of the above three categories a question belongs to.
- Refusing questions unrelated to the bootcamp.
- Producing one structured `Ticket` per resolved (or explicitly unresolved) request.
- Personalizing tone and greeting to the specific, already-known student.
- Full auditability of every run.

### 2.2 Out of scope (explicit non-goals)

1. **NG-1 — Read-only course data.** The Desk does not create, update, or delete entries in the
   course data source. It is read-only from the Desk's perspective; changes are made by an
   administrator editing the data source directly, outside the running application.
2. **NG-2 — No authentication.** The Desk does not authenticate or verify student identity. It
   trusts that the student profile handed to it by the hosting session has already been verified
   upstream. Determining who is physically at the keyboard is out of scope.
3. **NG-3 — No external ticketing integration.** The Desk does not file, email, or forward the
   `Ticket` it produces to any external system (helpdesk, spreadsheet, chat channel). Producing a
   valid structured `Ticket` object is the full extent of this project's ticketing behavior.

## 3. Actors

| Actor | Description |
|---|---|
| **Student** | The end user chatting with the Desk. Always already-identified (NG-2). |
| **Ops Desk** | The first agent every message reaches. Classifies, answers admin questions directly, or hands off. |
| **Assignments Specialist** | Answers assignment/schedule/policy questions once handed off to. |
| **Careers Specialist** | Answers career-guidance questions once handed off to. |
| **Course Data Source** | The system of record for course facts (read-only, per NG-1). |
| **Developer** | Builds and owns the system; not present at runtime. |

## 4. Functional Requirements

Each requirement is stated as: behavior, preconditions, edge cases, error handling, and acceptance
criteria. A requirement is not "done" until every edge case listed under it is demonstrable.

### 4.1 FR-1 — Gemini-backed agent, asynchronous entry point

**Behavior.** The Desk is powered by a single language model backend, configured once per agent
definition, never globally and never per-call. The application starts and runs asynchronously from
its first line of execution.

**Edge cases**
- The configured model is unreachable or the API key is rejected by the provider at call time (not
  at startup) → treated as a runtime failure, not a startup failure; MUST be caught at the run
  boundary and reported to the student as a generic "temporarily unable to help" message, never a
  raw exception.
- A model response takes longer than a reasonable interactive wait → out of scope for this
  iteration; no client-side timeout is required beyond what the SDK provides by default.

**Acceptance criteria**
- A question typed at the terminal is answered by the configured model.
- No global default-client override exists anywhere in the code.
- The program's entry point is declared asynchronous and is launched through the async runner, not
  called synchronously.

### 4.2 FR-2 — Course knowledge, reachable only through tools

**Behavior.** Course facts (courses, schedules, policies, assignments) live in a single external
data source. The Desk and its specialists MUST NOT have this data pre-loaded into their
instructions; they may only obtain it by invoking a lookup capability, at the moment a question
requires it.

**Edge cases**
- A course id mentioned by the student does not exist in the data source → the lookup capability
  MUST report clearly that no such course exists; the agent MUST relay this to the student rather
  than guessing or inventing a plausible-sounding answer.
- An assignment id does not exist within an existing course → same treatment: reported as not
  found, never fabricated.
- The data source is empty, missing, or malformed at the moment of lookup → the lookup capability
  MUST return a clear "course data is currently unavailable" result rather than raising; the agent
  MUST relay this as a temporary limitation, not silently pretend no courses exist forever.
- An entry is removed from the data source between two questions in the same session → the very
  next lookup MUST reflect the removal with zero code changes (i.e. the data source is read fresh,
  not cached for the life of the process).

**Acceptance criteria**
- Deleting a course from the data source removes it from the Desk's answers with no code change.
- The Desk never invents an assignment id, due date, or policy value that is not present in the
  data source.

### 4.3 FR-3 — The student is in context, never in the prompt

**Behavior.** A student profile (name, roll number, enrolled course, tier, count of currently open
tickets) is supplied once per session and is available to every tool and every instruction-building
step as contextual data — never as literal text baked into a prompt that the model treats as
ordinary instruction.

**Edge cases**
- The profile's `course_id` does not correspond to any course in the data source → any capability
  reading it MUST report this plainly (e.g. "no record found for your enrolled course") rather than
  crashing or silently defaulting to a different course.
- The profile's `tier` value is anything other than the two allowed values (`"regular"`,
  `"scholarship"`) → this MUST be rejected at the moment the profile is constructed, with a clear
  validation error, before any run begins. It MUST NOT be silently coerced or ignored once a run is
  underway.
- `open_tickets` is negative → same treatment: rejected at profile-construction time, not at use
  time.
- The student's name is an empty string → any greeting logic MUST fall back to a neutral,
  non-broken greeting (e.g. "Student") rather than producing a malformed sentence.

**Acceptance criteria**
- Any capability that reads the student's identity does so without the model needing to supply that
  identity as an argument — the model never needs to "tell the Desk who it's talking to."
- Searching the codebase for a real student's name or roll number finds it only where the profile
  object is constructed, never inside prompt text.

### 4.4 FR-4 — Instructions that change per turn

**Behavior.** The instructions given to the Desk agent are freshly composed at the start of every
run from the current student profile: they greet the student by name and name their enrolled
course. Once the student's open-ticket count reaches the escalation threshold, the tone becomes
noticeably terser.

**Design decision — threshold.** The terse mode activates when `open_tickets >= 3` (inclusive of 3,
not only when strictly greater).

**Edge cases**
- `open_tickets == 3` exactly → terse mode MUST be active (boundary is inclusive).
- `open_tickets == 2` → terse mode MUST NOT be active.
- The enrolled course cannot be found in the data source → the greeting MUST still be produced,
  substituting a neutral phrase (e.g. "your course") instead of failing to greet at all.

**Acceptance criteria**
- Three profiles that differ in name, course, and open-ticket count (crossing the threshold of 3 in
  at least one pair) produce three visibly different resolved instruction texts.
- The fully resolved instruction text can be inspected/printed before any model call is made for
  that run.

### 4.5 FR-5 — Two specialists, cloned from one base, reached by handoff

**Behavior.** One base specialist definition is cloned twice to produce an Assignments specialist
and a Careers specialist, differing only in their instructions and model settings. When the Desk
determines a question belongs to one of these two categories, it transfers the conversation to the
matching specialist, and that specialist — not the Desk — produces the answer the student sees for
that sub-topic.

**Design decision — tone.** Assignments runs cold and factual (low temperature, no embellishment,
citations to policy/due-date data required). Careers runs warmer (higher temperature, encouraging
tone permitted) since career guidance is inherently more advisory and less fact-lookup-driven.

**Design decision — category tie-break.** When a single message plausibly touches more than one
category, the Desk MUST resolve it deterministically in this priority order: **Assignment** signals
take precedence over **Career** signals, which take precedence over treating it as **Admin** (kept
and answered by the Desk itself). This ordering exists precisely so category selection is testable
and repeatable rather than a coin flip.

**Edge cases**
- A message contains no signal for either specialist category → it is treated as Admin and answered
  by the Desk directly, without any handoff.
- The specialist reached by handoff itself fails to produce a valid response (e.g. its own
  structured-output validation fails) → this is treated identically to FR-7's parsing-failure case:
  caught, reported, and — where possible — surfaced as an unresolved `Ticket` rather than a crash.
- A conversation is handed off, and a later message in the *same* session shifts to a different
  category → a fresh handoff decision MUST be made per message; the Desk is not permanently bound
  to the first specialist it chose.

**Acceptance criteria**
- After a run, the specific agent that authored the final answer is identifiable in code.
- The handoff event appears in the run's recorded items.
- Both specialists share the base agent's model configuration without re-declaring it identically —
  only the differing instructions/settings are restated.

### 4.6 FR-6 — One specialist exposed as a tool, not a handoff

**Behavior.** A summarizing capability condenses a long policy answer down to three lines or fewer.
It is exposed to the Desk as an invocable capability (not a handoff target), so the Desk retains
the conversation and the final message the student sees is still authored in the Desk's own voice.

**Edge cases**
- The input text is already three lines or shorter → the capability MUST NOT pad it to force a
  longer or restructured result; it returns the input reformatted to at most three lines, unchanged
  in meaning.
- The input text is empty or whitespace-only → the capability MUST return an explicit "nothing to
  summarize" result rather than an empty string or an error.

**Acceptance criteria**
- The distinction between this capability (a tool) and the two specialists (handoffs) can be
  clearly stated: a handoff transfers authorship of the reply; a tool call does not.
- The message the student receives immediately after a summarization is still voiced by the Desk,
  not by a separate persona.

### 4.7 FR-7 — Every resolved conversation produces a structured ticket

**Behavior.** The final output of any run that reaches the Desk (i.e. was not rejected by the
guardrail) is a typed record, not free-form prose, with these fields:

| Field | Type | Constraint |
|---|---|---|
| `category` | one of `"assignment"`, `"career"`, `"admin"` | exactly one of the three; no other value is valid |
| `summary` | short text | non-empty |
| `next_step` | short text | non-empty; what happens next, for the student or staff |
| `resolved` | boolean | see meaning table below |
| `escalate` | boolean | see meaning table below |

**Meaning of the `resolved` / `escalate` combination**

| `resolved` | `escalate` | Meaning |
|---|---|---|
| `true` | `false` | Answered directly; nothing further needed. |
| `true` | `true` | Answered, but flagged for staff awareness anyway (expected to be rare). |
| `false` | `true` | Not answered; needs human/staff follow-up. |
| `false` | `false` | Not fully answered and not escalated (e.g. student ended the chat before resolution). |

**Edge cases**
- The model attempts to produce a `category` outside the three allowed values → this MUST fail
  validation and surface as a structured-output parsing error (see Article VIII of
  `constitution.md`), never be silently coerced to a default category.
- A request is rejected by the guardrail (§4.8) → no `Ticket` is produced at all for that turn; this
  is the sole exception to "every resolved conversation produces a ticket," because the request
  never reached the Desk.

**Acceptance criteria**
- `type(result.final_output)` is the ticket type, checked in code.
- `resolved` is branched on in a Python conditional somewhere in the system (e.g. to decide whether
  to prompt the student for more detail), not merely displayed to a human.
- A deliberately impossible request (one that cannot be validly categorized) surfaces the SDK's own
  parsing error rather than returning a half-filled record.

### 4.8 FR-8 — A guardrail that refuses non-course questions

**Behavior.** Before the Desk's primary model is invoked, an input check evaluates whether the
message is about the bootcamp at all. If it is not, the request is refused politely and the primary
model is never invoked for that turn.

**Design decision — pleasantries and borderline cases.**
- Greetings, thanks, and conversational closers ("hi", "thanks", "that's all") MUST NOT be rejected
  — they are treated as acceptable framing around an in-scope conversation, not as the substance of
  the request.
- A message that is plausibly bootcamp-related even if broad (e.g. "what programming language
  should I learn?") MUST be treated as in-scope (Career category), not rejected.
- A message mixing an in-scope request with an unrelated aside (e.g. "what's my assignment due
  date, and also what's today's weather?") MUST be evaluated by its primary intent: if the primary
  intent is in-scope, the request passes, and the agent that ultimately answers SHOULD note that it
  cannot help with the unrelated part rather than ignoring it silently.
- A message with no discernible bootcamp-related intent at all MUST be rejected.

**Edge cases**
- The check itself fails to run (e.g. its own underlying error) → this MUST be caught at a defined
  boundary and treated as if the check could not confirm relevance; the system MUST NOT crash, and
  SHOULD fail toward asking the student to rephrase rather than silently answering an unchecked
  message.

**Acceptance criteria**
- An off-topic question produces a courteous, specific refusal.
- The refusal costs nothing at the Desk's primary model — that model is never invoked for a
  rejected turn.
- The point in the code where the rejection is caught can be shown directly.

### 4.9 FR-9 — Tool gating, a stopping rule, and a ceiling

Three independent controls, all present simultaneously:

**9a — Tier-gated capability.** A capability exists that is offered only to students whose `tier`
is `"scholarship"`. For every other student, this capability is **absent** from what the model is
even told is available — not present-but-refused, not present-but-declined. It simply does not
appear in that run's capability list.

**9b — Stopping rule.** A "close ticket" capability, once invoked, ends the run immediately; its
output becomes the run's final result. No further model turns occur after it is invoked.

**9c — Ceiling.** A maximum-turn ceiling is enforced on every run. Exceeding it raises an exception
rather than allowing the run to loop indefinitely; that exception is caught at the run boundary and
reported to the student as a graceful message.

**Edge cases**
- A profile with an invalid `tier` never reaches a run at all, per FR-3's validation-at-construction
  rule — so 9a has no "invalid tier" case to handle at run time.
- The "close ticket" capability is invoked with incomplete or invalid data → this is treated
  identically to FR-7's structured-output validation failure: caught, reported, run ends without a
  crash.
- The ceiling is reached mid-handoff (a specialist is active when the ceiling triggers) → the
  exception MUST still be caught at the single, top-level run boundary regardless of which agent
  was active at the time.

**Acceptance criteria**
- The same question, run once as a regular-tier student and once as a scholarship-tier student,
  results in two demonstrably different capability lists offered to the model.
- The chosen ceiling value is a specific, named number with a stated rationale (see `plan.md`).

### 4.10 FR-10 — An audit trail across the whole run, and one agent watched closely

**Behavior.** Every run produces an ordered, timestamped timeline of every agent involved in that
conversation, including the moment of handoff. Separately, one specific specialist has finer-grained
lifecycle observability attached to it alone.

**Design decision — which specialist.** The Assignments specialist is the one with finer-grained
observability, because its outputs (due dates, late-penalty terms) carry a higher real-world cost
if wrong than a career-advice slip does.

**Edge cases**
- A conversation never hands off at all (a pure Admin question the Desk answers itself) → the
  timeline legitimately contains only one agent entry; this is a valid outcome, not an error.
- Fine-grained observability attached to the Assignments specialist naturally produces no events
  while control is with the Desk or the Careers specialist — this is expected, not a bug, and MUST
  be explainable as such (the finer-grained hooks are scoped to the agent they're attached to, and
  simply have nothing to report while a different agent holds the conversation).

**Acceptance criteria**
- One student question that triggers a handoff yields one timeline naming both agents involved, in
  the order they participated.
- The reason the fine-grained hooks produce no events during the portion of the conversation held by
  a different agent can be clearly explained.

### 4.11 FR-11 — A custom runner wrapping every run *(cut-list priority 1 — see §7)*

**Behavior.** Every invocation of the run mechanism, wherever it occurs in the process, is wrapped
by a single custom layer that stamps a request identifier and elapsed time around it. This layer is
registered once, at startup, and no individual agent definition is modified to accommodate it.

**Edge cases**
- If a future change introduces more than one top-level run invocation in a single student turn
  (today there is exactly one, encompassing the Desk and any specialist reached via handoff within
  it), every such invocation MUST go through the same wrapper without any change to the wrapper
  itself.

**Acceptance criteria**
- The wrapper's stamped output is visible for the run regardless of which agent(s) ultimately
  participated in it.
- No agent definition file references or imports the wrapper.

### 4.12 FR-12 — A Chainlit interface with per-session memory

**Behavior.** The Desk is usable from a browser. The agent and the student's profile are constructed
once, when a session begins — not rebuilt on every message. The conversation remembers earlier turns
within that same session.

**Edge cases**
- Two separate browser sessions (e.g. two different students, or the same student in two tabs) MUST
  NOT see or influence each other's conversation history or profile. No state may be shared through
  a process-wide or module-level mutable variable.
- A message handler that does not wait for the run to finish before proceeding is a defect: the
  student would see a blank or premature response.
- Session history is retained only for the lifetime of that browser session in this iteration;
  persisting history beyond a session (e.g. across browser restarts) is out of scope, matching NG-3
  and NG-1's spirit of a minimal, in-scope system.

**Acceptance criteria**
- A second message that refers back to the first ("what about the one after that?") is understood
  correctly.
- Two simultaneously open browser sessions never share conversation history.
- The message handler awaits completion of the run rather than proceeding without the result.

### 4.13 FR-13 — Traceable conversations

**Behavior.** Tracing is enabled for every run and exported under the developer's own key. One full
student conversation — including any handoff — appears as a single trace, not several disconnected
ones.

**Edge cases**
- A guardrail-rejected turn MUST still appear as a span within the trace (showing the check ran and
  that no primary-model generation call followed it), so that FR-8's "cost nothing" claim can be
  demonstrated directly from the trace rather than only asserted.

**Acceptance criteria**
- A trace can be opened and every span in it can be named and explained.
- At least one call the Desk made that, in hindsight, it did not strictly need to make can be
  pointed to directly from the trace — this is a reflective/discussion criterion for the viva, not a
  pass/fail behavior.

## 5. Non-Functional Requirements

### NFR-1 — Secrets
Governed in full by Article II of `constitution.md`. Restated as a testable requirement: starting
the program with a required key absent MUST produce one clear, human-readable error naming the
missing variable — never a raw exception trace.

### NFR-2 — Cost
Governed by Article VI of `constitution.md`. Every agent declares its own model settings; nothing in
the system generates without an enforced turn ceiling (FR-9c).

### NFR-3 — Observability
Every conversation MUST be traceable (FR-13) and the audit timeline (FR-10) MUST be written to
durable storage, not only printed to the terminal. The storage mechanism itself is a `plan.md`
decision.

### NFR-4 — Failure
A tool that encounters bad or missing data MUST return a sentence the model can act on (Article III
of `constitution.md`). A tool that raises an exception into the runner is treated as a defect to be
fixed, not a tolerated failure mode.

### NFR-5 — Provenance
`git log`, read in chronological order, MUST show the four Phase 0 artifacts (`constitution.md`,
`spec.md`, `plan.md`, `tasks.md`) committed before the first commit touching any runtime file. This
is checked mechanically, not by inspection of code quality.

## 6. Data Contracts (behavioral shape only)

### 6.1 Student Profile
A record identifying the current student, holding at minimum: full name, roll number, enrolled
course identifier, tier (`"regular"` or `"scholarship"`, defaulting to `"regular"` if unspecified),
and a count of currently open tickets (defaulting to `0`). Invalid values are rejected at
construction time (§4.3).

### 6.2 Ticket
A record with `category`, `summary`, `next_step`, `resolved`, and `escalate` as defined in §4.7.

### 6.3 Course Data Source
A collection of courses, each with an identifier, a title, a schedule, a set of named policies (each
a short text value), and a list of assignments, each with an identifier, a title, and a due date.

## 7. Cut List (in order, if time runs short during implementation)

1. FR-11 (custom runner)
2. FR-6 (Summariser-as-tool)
3. The fine-grained, single-specialist half of FR-10 (the run-wide timeline in FR-10 is retained)

**FR-7 (structured ticket) and FR-8 (guardrail) MUST NOT be cut under any circumstance** — they are
the two requirements the final defense is built around.

## 8. Glossary

- **Desk** — the first agent every message reaches; classifies and either answers (Admin) or hands
  off (Assignment/Career).
- **Specialist** — an agent reached by handoff that answers on the Desk's behalf for one category.
- **Handoff** — transferring authorship of the reply to a different agent for the rest of that turn.
- **Tool / capability** — a function an agent can invoke without transferring authorship of the reply.
- **Guardrail** — a check run before the primary model, capable of rejecting a request outright.
- **Tripwire** — the signal a guardrail raises when it rejects a request.
- **Ticket** — the structured record produced as the final output of a run that reached the Desk.
- **Trace / span** — the recorded structure of one run, and one named unit of work within it.
- **Hook (run-level vs. agent-level)** — run-level hooks observe every agent in a run; agent-level
  hooks are attached to exactly one specific agent and only report on it.
- **Ceiling** — the maximum number of turns a single run may take before it is forcibly stopped.
