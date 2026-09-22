"""The per-session student profile (FR-3, plan.md §4.1).

This object is the SDK's local run context. It is passed as `context=` to
`Runner.run` and read by tools through `RunContextWrapper` — it is never
interpolated into prompt text (constitution.md Article IV).
"""

from dataclasses import dataclass

TIERS = ("regular", "scholarship")


@dataclass
class StudentProfile:
    name: str
    roll_no: str
    course_id: str
    tier: str = "regular"  # "regular" | "scholarship" — validated in __post_init__
    open_tickets: int = 0  # validated >= 0 in __post_init__

    def __post_init__(self) -> None:
        if self.tier not in TIERS:
            raise ValueError(f"Invalid tier: {self.tier!r}")
        if self.open_tickets < 0:
            raise ValueError("open_tickets cannot be negative")
