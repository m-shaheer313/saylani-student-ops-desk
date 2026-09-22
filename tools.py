"""Course-lookup tools (FR-2).

Every tool re-reads `courses.json` on each call, so an edit to the file shows up on
the very next lookup (plan.md §4.3). Per constitution.md Article III, no exception
ever leaves a tool: failures come back as strings the model can act on, and are
logged (Art. III.4) so they stay visible as defects to fix.
"""

import json
import logging
from pathlib import Path
from typing import Literal

from agents import AgentBase, RunContextWrapper, function_tool

from student_profile import StudentProfile
from ticket import Ticket

logger = logging.getLogger(__name__)

COURSES_PATH = Path(__file__).parent / "courses.json"

UNAVAILABLE = (
    "Course data is currently unavailable. Tell the student this is a temporary "
    "problem on our side, not that the course does not exist."
)


def _load_courses() -> tuple[list[dict], str]:
    """Read the data source fresh.

    Returns `(courses, "")` on success, or `([], reason)` if the file is missing,
    unreadable, or malformed — never raises.
    """
    try:
        with COURSES_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("Course data file not found at %s", COURSES_PATH)
        return [], UNAVAILABLE
    except json.JSONDecodeError as exc:
        logger.error("Course data file is not valid JSON: %s", exc)
        return [], UNAVAILABLE
    except OSError as exc:
        logger.error("Course data file could not be read: %s", exc)
        return [], UNAVAILABLE

    if not isinstance(data, dict) or not isinstance(data.get("courses"), list):
        logger.error("Course data file does not match the expected schema")
        return [], UNAVAILABLE

    courses = [c for c in data["courses"] if isinstance(c, dict)]
    return courses, ""


def _known_ids(courses: list[dict]) -> list[str]:
    return [str(c.get("id")) for c in courses if c.get("id")]


def _find_course(courses: list[dict], course_id: str) -> dict | None:
    for course in courses:
        if str(course.get("id")) == course_id:
            return course
    return None


def lookup_course_title(course_id: str) -> str | None:
    """Resolve a course id to its title, or None if unknown/unavailable.

    Shares `_load_courses` with the tools below, so it is read fresh too. Used by
    the Desk's per-turn instruction builder (FR-4), which needs the title without
    going through a model-callable tool.
    """
    courses, error = _load_courses()
    if error:
        return None

    course = _find_course(courses, course_id)
    if course is None:
        return None

    title = str(course.get("title", "")).strip()
    return title or None


@function_tool
def list_courses() -> list[dict] | str:
    """List every course the institute currently offers, as id/title pairs."""
    courses, error = _load_courses()
    if error:
        return error
    if not courses:
        return "There are no courses in the course data right now."
    return [
        {"id": str(c.get("id", "")), "title": str(c.get("title", "Untitled course"))}
        for c in courses
    ]


@function_tool
def get_course(course_id: str) -> dict | str:
    """Get the title, schedule, and policies for one course by its id."""
    courses, error = _load_courses()
    if error:
        return error

    course = _find_course(courses, course_id)
    if course is None:
        return f"No course with id '{course_id}'. Known ids: {_known_ids(courses)}"

    policies = course.get("policies")
    return {
        "id": course_id,
        "title": str(course.get("title", "Untitled course")),
        "schedule": str(course.get("schedule", "No schedule recorded for this course.")),
        "policies": policies if isinstance(policies, dict) else {},
    }


@function_tool
def get_assignment(course_id: str, assignment_id: str) -> dict | str:
    """Get the title and due date of one assignment within one course."""
    courses, error = _load_courses()
    if error:
        return error

    course = _find_course(courses, course_id)
    if course is None:
        return f"No course with id '{course_id}'. Known ids: {_known_ids(courses)}"

    assignments = course.get("assignments")
    if not isinstance(assignments, list):
        assignments = []
    assignments = [a for a in assignments if isinstance(a, dict)]

    for assignment in assignments:
        if str(assignment.get("id")) == assignment_id:
            return {
                "course_id": course_id,
                "id": assignment_id,
                "title": str(assignment.get("title", "Untitled assignment")),
                "due": str(assignment.get("due", "No due date recorded.")),
            }

    known = _known_ids(assignments)
    if not known:
        return f"Course '{course_id}' has no assignments recorded."
    return (
        f"No assignment with id '{assignment_id}' in course '{course_id}'. "
        f"Known assignment ids: {known}"
    )


@function_tool
def get_account_status(ctx: RunContextWrapper[StudentProfile]) -> str:
    """Get the current student's account tier and how many tickets they have open."""
    # Art. IV.2 — read from the run context, never from a model-supplied argument.
    # This tool's generated schema therefore has zero parameters.
    profile = ctx.context
    return f"Tier: {profile.tier}. Open tickets: {profile.open_tickets}."


PRIORITY_REVIEW_ACK = "Your request has been flagged for priority review."


def _is_scholarship(
    ctx: RunContextWrapper[StudentProfile], agent: AgentBase
) -> bool:
    """Whether this run's student is scholarship tier (FR-9a)."""
    return getattr(ctx.context, "tier", None) == "scholarship"


@function_tool(is_enabled=_is_scholarship)
def request_priority_review(justification: str) -> str:
    """Flag this student's request for priority review by staff."""
    # No tier check in the body: for a regular-tier run this tool is never built
    # into the run's tool list, so the model is never told it exists (FR-9a).
    return PRIORITY_REVIEW_ACK


@function_tool
def close_ticket(
    category: Literal["assignment", "career", "admin"],
    summary: str,
    next_step: str,
    resolved: bool,
    escalate: bool,
) -> Ticket:
    """Close this conversation with a finished ticket. Ends the conversation."""
    # No try/except by design (FR-9b): invalid fields raise ValidationError and are
    # handled exactly like FR-7's structured-output failures — reported back to the
    # model, no special-casing, and no exception reaching the runner.
    return Ticket(
        category=category,
        summary=summary,
        next_step=next_step,
        resolved=resolved,
        escalate=escalate,
    )
