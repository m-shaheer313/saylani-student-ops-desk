"""Run the real Desk against a different provider, changing no project file.

`desk_agent`, `specialists` and `guardrail` all read `gemini_client` and
`MODEL_NAME` from `config` at import time. Patching `config` *before* importing
them therefore builds the entire agent graph — Desk, both specialists,
Summariser, guardrail — against another provider, for this process only.

Nothing on disk changes. Ctrl-C or exit and the project is exactly as it was.

    .venv\\Scripts\\python.exe scripts\\try_provider.py ^
        --base-url https://apinex.bond/v1 ^
        --model <model-id> ^
        --key <api-key> ^
        --ask "When is assignment a3 due?"

The key may also come from PROBE_API_KEY. Exit 0 = a valid Ticket came back.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import AsyncOpenAI  # noqa: E402

import config  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--key", default=os.getenv("PROBE_API_KEY", ""))
    ap.add_argument("--ask", default="When is assignment a3 due?")
    args = ap.parse_args()

    if not args.key:
        print("Need --key or PROBE_API_KEY.")
        return 1

    # Patch the shared config *before* any agent module is imported, so the
    # whole graph is constructed against the provider under test.
    config.gemini_client = AsyncOpenAI(api_key=args.key, base_url=args.base_url)
    config.MODEL_NAME = args.model

    from agents import RunConfig, Runner  # noqa: E402
    from agents.items import HandoffOutputItem, ToolCallItem  # noqa: E402

    from audit import AuditHooks  # noqa: E402
    from desk_agent import desk_agent  # noqa: E402
    from student_profile import StudentProfile  # noqa: E402
    from ticket import Ticket  # noqa: E402

    # Confirm the patch actually took: every agent must hold the new client.
    from specialists import assignments_specialist, careers_specialist  # noqa: E402
    from summariser import summariser  # noqa: E402
    from guardrail import topic_guard_agent  # noqa: E402

    print(f"Provider : {args.base_url}")
    print(f"Model    : {args.model}\n")
    for agent in (
        desk_agent,
        assignments_specialist,
        careers_specialist,
        summariser,
        topic_guard_agent,
    ):
        client_base = str(agent.model._client.base_url)
        on_test = client_base.startswith(args.base_url.rstrip("/")[:24])
        print(f"  {agent.name:24} {agent.model.model:22} {'TEST' if on_test else 'GEMINI (not patched!)'}")

    profile = StudentProfile("Shaheer", "SMIT-2026-0412", "agentic-ai-w4", open_tickets=1)
    hooks = AuditHooks()

    print(f"\nasking: {args.ask}\n")
    try:
        result = await Runner.run(
            desk_agent,
            args.ask,
            context=profile,
            max_turns=config.MAX_TURNS,
            hooks=hooks,
            run_config=RunConfig(
                workflow_name=config.WORKFLOW_NAME, group_id=hooks.request_id
            ),
        )
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {str(exc)[:300]}")
        return 1
    finally:
        await config.gemini_client.close()

    tools = [
        i.raw_item.name for i in result.new_items if isinstance(i, ToolCallItem)
    ]
    handoffs = [
        i.target_agent.name
        for i in result.new_items
        if isinstance(i, HandoffOutputItem)
    ]

    print(f"  last_agent : {result.last_agent.name}")
    print(f"  handoffs   : {handoffs or 'none'}")
    print(f"  tools      : {tools or 'none'}")
    print(f"  output type: {type(result.final_output).__name__}")
    print(f"  ticket     : {result.final_output}")

    if not isinstance(result.final_output, Ticket):
        print("\nFAILED: structured output did not come back as a Ticket.")
        return 1

    print("\nOK — the full agent graph ran on this provider and produced a Ticket.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
