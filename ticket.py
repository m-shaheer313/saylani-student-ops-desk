"""The structured final output every run produces (FR-7, plan.md §4.2)."""

from typing import Literal

from pydantic import BaseModel, Field


class Ticket(BaseModel):
    category: Literal["assignment", "career", "admin"]
    summary: str = Field(min_length=1)
    next_step: str = Field(min_length=1)
    resolved: bool
    escalate: bool


# spec.md §4.7 — the semantics of the two flags, shared verbatim by every agent
# that produces a Ticket so they cannot drift apart.
TICKET_INSTRUCTIONS = (
    "Every reply you produce is a Ticket, not free prose. Fill it in as follows.\n\n"
    "category: 'assignment' for due dates, submissions, policy, attendance or "
    "schedules; 'career' for jobs, roles, portfolios or interviews; 'admin' for "
    "anything else. Exactly one of those three — no other value is valid.\n"
    "summary: what the student asked and what you told them. Never empty.\n"
    "next_step: what happens next, for the student or for staff. Never empty. If "
    "genuinely nothing is needed, say so explicitly rather than leaving it blank.\n\n"
    "resolved and escalate together carry the outcome:\n"
    "- resolved=true, escalate=false: you answered it; nothing further is needed. "
    "This is the normal case.\n"
    "- resolved=true, escalate=true: you answered it, but a staff member should "
    "still be aware of it. Rare — use it only when something genuinely warrants "
    "attention, not as a hedge.\n"
    "- resolved=false, escalate=true: you could not answer it and a human must "
    "follow up.\n"
    "- resolved=false, escalate=false: not fully answered and not escalated either "
    "— for example the student ended the conversation partway through.\n\n"
    "If you could not resolve the request, still produce a Ticket with "
    "resolved=false. Never end a run with no Ticket at all.\n\n"
    # FR-9b — makes close_ticket the actual path to a final answer, so the
    # stopping rule is exercised rather than dormant.
    "Once you have fully composed your final Ticket for this turn, call "
    "close_ticket with those exact field values rather than returning the Ticket "
    "as plain structured output."
)
