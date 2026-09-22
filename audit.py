"""Run-level audit hooks and their durable log (FR-10, plan.md §6/§9).

One `AuditHooks` instance is created per `Runner.run()` call, carrying a fresh
`request_id`, and appends one JSON object per line to `audit_log.jsonl`. Every
agent in the run reports through it, so a handoff produces a single ordered
timeline naming both agents.

Nothing here may break a run: a failed write is logged and swallowed, never
raised into the runner (Art. VIII).
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents import Agent, RunHooks

logger = logging.getLogger(__name__)

AUDIT_LOG_PATH = Path(__file__).parent / "audit_log.jsonl"


def _now() -> str:
    """Current UTC time, ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def _describe(output: Any) -> str:
    """A short, non-sensitive description of an agent's output.

    Deliberately structural: the Ticket's summary text contains the student's
    name, and the audit log has no need of it.
    """
    category = getattr(output, "category", None)
    if category is None:
        return type(output).__name__
    return (
        f"Ticket(category={category}, "
        f"resolved={getattr(output, 'resolved', '?')}, "
        f"escalate={getattr(output, 'escalate', '?')})"
    )


class AuditHooks(RunHooks):
    """Records the ordered lifecycle of every agent and tool in one run."""

    def __init__(self, request_id: str | None = None) -> None:
        # One id per run, so a whole conversation's events group together.
        self.request_id = request_id or str(uuid.uuid4())
        self.events: list[dict[str, Any]] = []

    def _record(self, agent_name: str, event_type: str, detail: str) -> None:
        event = {
            "request_id": self.request_id,
            "timestamp": _now(),
            "agent_name": agent_name,
            "event_type": event_type,
            "detail": detail,
        }
        self.events.append(event)

        try:
            with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except OSError as exc:
            # NFR-3 is about durability, not about taking the run down with it.
            logger.error("Could not append to %s: %s", AUDIT_LOG_PATH, exc)

    async def on_agent_start(self, context, agent: Agent) -> None:
        self._record(agent.name, "agent_start", "took the conversation")

    async def on_agent_end(self, context, agent: Agent, output: Any) -> None:
        self._record(agent.name, "agent_end", f"produced {_describe(output)}")

    async def on_handoff(self, context, from_agent: Agent, to_agent: Agent) -> None:
        self._record(
            from_agent.name, "handoff", f"{from_agent.name} -> {to_agent.name}"
        )

    async def on_tool_start(self, context, agent: Agent, tool) -> None:
        self._record(agent.name, "tool_start", f"calling {tool.name}")

    async def on_tool_end(self, context, agent: Agent, tool, result: object) -> None:
        self._record(agent.name, "tool_end", f"{tool.name} returned")

    def timeline(self) -> list[str]:
        """This run's events as readable lines, in order."""
        return [
            f"{e['timestamp']}  {e['agent_name']:24} {e['event_type']:12} {e['detail']}"
            for e in self.events
        ]
