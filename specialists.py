"""The base specialist and its two clones (FR-5, plan.md §2).

`base_specialist` is never exposed to the Desk and never receives a handoff — it
exists only as the single place the shared model configuration is declared. The two
clones restate only what differs: instructions, temperature, and tools.

Note on `clone()`: it shallow-copies, so an unpassed list attribute is shared with
the original. Each clone below is therefore given its own explicit `tools` list.
"""

from agents import Agent, ModelSettings, OpenAIChatCompletionsModel

from config import MODEL_NAME, gemini_client
from student_profile import StudentProfile
from ticket import TICKET_INSTRUCTIONS, Ticket
from tools import get_assignment, get_course

BASE_PLACEHOLDER_INSTRUCTIONS = (
    "You are a Saylani specialist. This placeholder is always overridden by the "
    "clone that is actually used; no student ever sees this agent."
)

# The one place the specialists' model configuration is declared (Art. I.2, I.5).
base_specialist: Agent[StudentProfile] = Agent(
    name="Base Specialist",
    instructions=BASE_PLACEHOLDER_INSTRUCTIONS,
    tools=[],
    model=OpenAIChatCompletionsModel(
        model=MODEL_NAME,
        openai_client=gemini_client,
    ),
    model_settings=ModelSettings(temperature=0.3),
    # Identical for both clones, so it is declared once here (plan.md §2) and
    # inherited — FR-5 asks clones to restate only what differs.
    output_type=Ticket,
)

ASSIGNMENTS_INSTRUCTIONS = (
    "You are the Saylani Assignments Specialist. The Ops Desk has handed this "
    "student to you; you are now the one answering them.\n\n"
    "Be cold and factual. Look up every assignment, due date, schedule, and policy "
    "with your tools, and quote the exact value the tool returned — the literal date "
    "string, the literal policy wording. Never estimate, never round, never soften a "
    "policy with your own opinion about whether it is fair or likely to be enforced.\n\n"
    "If a tool reports that a course, assignment, or the data source itself is not "
    "available, say exactly that and stop. Do not substitute a plausible date or "
    "policy. No encouragement, no filler — the facts and the next step only.\n\n"
    f"{TICKET_INSTRUCTIONS}"
)

assignments_specialist = base_specialist.clone(
    name="Assignments Specialist",
    handoff_description=(
        "Handles assignment questions: due dates, submission and late-submission "
        "policy, attendance rules, and class schedules."
    ),
    instructions=ASSIGNMENTS_INSTRUCTIONS,
    # Low temperature: factual precision over phrasing variety (plan.md §2).
    model_settings=ModelSettings(temperature=0.1),
    tools=[get_course, get_assignment],
)

CAREERS_INSTRUCTIONS = (
    "You are the Saylani Careers Specialist. The Ops Desk has handed this student to "
    "you; you are now the one answering them.\n\n"
    "Be warm and encouraging. Career questions are advisory, so you may offer general "
    "guidance from your own knowledge — portfolios, interview preparation, which "
    "skills tend to matter for a given role — alongside the facts about their course.\n\n"
    "Keep the two kinds of claim separate. Anything specific about a Saylani course "
    "must come from your course tool, quoted as the tool returned it; general career "
    "advice is clearly your own suggestion. Never invent a Saylani course, policy, or "
    "placement statistic.\n\n"
    f"{TICKET_INSTRUCTIONS}"
)

careers_specialist = base_specialist.clone(
    name="Careers Specialist",
    handoff_description=(
        "Handles career guidance: job roles, portfolios, interview preparation, and "
        "how a course relates to the student's career plans."
    ),
    instructions=CAREERS_INSTRUCTIONS,
    # Higher temperature: advisory answers benefit from more latitude (plan.md §2).
    model_settings=ModelSettings(temperature=0.7),
    # No get_assignment — career questions never need an assignment lookup.
    tools=[get_course],
)
