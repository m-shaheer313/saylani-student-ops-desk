"""Check whether an OpenAI-compatible provider can actually run this app.

The Desk needs more than chat completions: function calling (tools *and* the
handoff transfer tools), strict structured output (`Ticket`, `TopicCheck`), and
a working tool -> result -> answer loop. A provider can serve plain chat
perfectly and still fail all three.

Run it before pointing config.py at a new provider:

    .venv\\Scripts\\python.exe scripts\\probe_provider.py ^
        --base-url https://apinex.bond/v1 ^
        --model <model-id> ^
        --key <api-key>

The key may also come from PROBE_API_KEY so it stays out of your shell history.
Costs about four requests. Exit code 0 = safe to switch, 1 = it will break.
"""

import argparse
import asyncio
import json
import os
import sys

from openai import AsyncOpenAI

WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_course",
        "description": "Look up a course by id.",
        "parameters": {
            "type": "object",
            "properties": {"course_id": {"type": "string"}},
            "required": ["course_id"],
            "additionalProperties": False,
        },
    },
}

# The same shape the SDK sends for output_type=Ticket.
TICKET_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "Ticket",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["assignment", "career", "admin"],
                },
                "summary": {"type": "string"},
                "next_step": {"type": "string"},
                "resolved": {"type": "boolean"},
                "escalate": {"type": "boolean"},
            },
            "required": [
                "category",
                "summary",
                "next_step",
                "resolved",
                "escalate",
            ],
            "additionalProperties": False,
        },
    },
}


async def check_chat(client, model) -> tuple[bool, str]:
    r = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with the single word: ready"}],
        max_tokens=10,
    )
    text = (r.choices[0].message.content or "").strip()
    return bool(text), f"replied {text[:40]!r}"


async def check_tools(client, model) -> tuple[bool, str]:
    r = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "Look up the course with id agentic-ai-w4 using your tool.",
            }
        ],
        tools=[WEATHER_TOOL],
    )
    calls = r.choices[0].message.tool_calls
    if not calls:
        return False, "model returned prose instead of a tool call"
    name = calls[0].function.name
    args = calls[0].function.arguments
    return name == "get_course", f"called {name}({args})"


async def check_tool_loop(client, model) -> tuple[bool, str]:
    """Tool call -> feed the result back -> model answers from it."""
    first = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Look up course agentic-ai-w4."}],
        tools=[WEATHER_TOOL],
    )
    msg = first.choices[0].message
    if not msg.tool_calls:
        return False, "no tool call to continue from"

    second = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "Look up course agentic-ai-w4."},
            msg.model_dump(exclude_none=True),
            {
                "role": "tool",
                "tool_call_id": msg.tool_calls[0].id,
                "content": '{"title": "Agentic AI - weekdays batch 4"}',
            },
        ],
        tools=[WEATHER_TOOL],
    )
    text = (second.choices[0].message.content or "").lower()
    return "agentic" in text, f"answered {text[:60]!r}"


async def check_structured(client, model) -> tuple[bool, str]:
    r = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    "A student asked when assignment a3 is due. You told them "
                    "2026-10-02. Produce the ticket."
                ),
            }
        ],
        response_format=TICKET_SCHEMA,
    )
    raw = r.choices[0].message.content or ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False, f"not JSON: {raw[:60]!r}"

    missing = {
        "category",
        "summary",
        "next_step",
        "resolved",
        "escalate",
    } - data.keys()
    if missing:
        return False, f"missing fields {sorted(missing)}"
    if data["category"] not in ("assignment", "career", "admin"):
        return False, f"category not in enum: {data['category']!r}"
    return True, f"valid Ticket (category={data['category']})"


CHECKS = [
    ("chat completions", check_chat, "nothing will work"),
    ("function calling", check_tools, "all tools and both handoffs break"),
    ("tool result loop", check_tool_loop, "tools return but answers ignore them"),
    ("structured output", check_structured, "Ticket/TopicCheck break (FR-7, FR-8)"),
]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", help="model id to probe (omit with --list)")
    ap.add_argument("--key", default=os.getenv("PROBE_API_KEY", ""))
    ap.add_argument(
        "--list",
        action="store_true",
        help="just list the model ids this provider offers, then exit",
    )
    args = ap.parse_args()

    if not args.key:
        print("Need --key or PROBE_API_KEY.")
        return 1

    client = AsyncOpenAI(api_key=args.key, base_url=args.base_url)

    if args.list:
        try:
            models = await client.models.list()
        except Exception as exc:
            print(f"Could not list models: {type(exc).__name__}: {str(exc)[:200]}")
            return 1
        finally:
            await client.close()
        for m in sorted(models.data, key=lambda m: m.id):
            print(f"  {m.id}")
        return 0

    if not args.model:
        print("Need --model (or use --list to see what is available).")
        await client.close()
        return 1
    print(f"Probing {args.base_url} with model {args.model}\n")

    failures = []
    for name, check, consequence in CHECKS:
        try:
            ok, detail = await check(client, args.model)
        except Exception as exc:
            # Provider refusals explain themselves in the message body, so keep
            # enough of it to be actionable.
            ok, detail = False, f"{type(exc).__name__}: {str(exc)[:400]}"

        print(f"  {'PASS' if ok else 'FAIL'}  {name:20} {detail}")
        if not ok:
            failures.append(f"{name} — {consequence}")

    await client.close()

    print()
    if failures:
        print("NOT SAFE to switch. Failures:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("All four capabilities present — this provider can run the Desk.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
