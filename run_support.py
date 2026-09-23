"""Shared run-boundary helper for transient provider throttling.

Currently a pass-through: `MAX_ATTEMPTS = 1` means every exception reaches the
run boundary's own handlers unchanged, exactly as it did before this module
existed. The OpenAI client's request-level retry already covers transient 503s.

The wrapper and its wiring stay in place so raising `MAX_ATTEMPTS` is a
one-line change if the provider's own retry ever stops being enough.
"""

import asyncio
import logging
import re

from openai import InternalServerError, RateLimitError

logger = logging.getLogger(__name__)

# 1 = structurally inactive: attempt once, let the exception propagate to the
# run boundary's existing handlers. The OpenAI client already retries transient
# 503s at the request level and was observed self-healing within ~90s, so a
# second retry layer on top only adds a stall in front of a live audience while
# re-spending the quota it is waiting for. Raise this only if the client-level
# retry stops being enough.
MAX_ATTEMPTS = 1

# The provider's stated retryDelay assumes one queued call. A turn costs several
# (guardrail, Desk, tools), so each retry re-spends the per-minute budget — the
# floor gives the bucket real time to refill instead of failing again instantly.
MIN_WAIT_SECONDS = 15.0
DEFAULT_WAIT_SECONDS = 20.0
MAX_WAIT_SECONDS = 60.0

_RETRY_DELAY = re.compile(r"retry in ([0-9.]+)s", re.IGNORECASE)


def _wait_for(exc: Exception) -> float:
    """How long to wait, preferring the delay the provider asked for."""
    match = _RETRY_DELAY.search(str(exc))
    if match:
        try:
            stated = float(match.group(1)) + 1.0
            return min(max(stated, MIN_WAIT_SECONDS), MAX_WAIT_SECONDS)
        except ValueError:
            pass
    return DEFAULT_WAIT_SECONDS


async def run_with_retry(run_coro_factory):
    """Await `run_coro_factory()`, retrying only throttling/overload errors.

    `run_coro_factory` must build a *fresh* coroutine on each call — a coroutine
    can only be awaited once. Every other exception propagates untouched, so the
    guardrail tripwire, turn-ceiling and validation paths behave exactly as they
    did before.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await run_coro_factory()
        except (RateLimitError, InternalServerError) as exc:
            if attempt == MAX_ATTEMPTS:
                if MAX_ATTEMPTS > 1:
                    logger.error(
                        "Provider still unavailable after %d attempts: %s",
                        MAX_ATTEMPTS,
                        type(exc).__name__,
                    )
                # With retry off there is nothing to report here: the run
                # boundary logs and handles the exception itself.
                raise
            wait = _wait_for(exc)
            logger.warning(
                "Provider busy (%s), attempt %d/%d — waiting %.1fs",
                type(exc).__name__,
                attempt,
                MAX_ATTEMPTS,
                wait,
            )
            await asyncio.sleep(wait)
    raise RuntimeError("unreachable")
