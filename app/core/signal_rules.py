"""Single source of truth for DSE Pulse signal grading and display status."""

from dataclasses import dataclass
from typing import Literal

SignalGrade = Literal["A+", "A", "B+", "Reject"]
SignalStatus = Literal["qualified", "watch", "rejected"]


@dataclass(frozen=True, slots=True)
class SignalRule:
    """A score boundary and its public display status."""

    minimum: int
    maximum: int
    status: SignalStatus
    display_range: str


SIGNAL_RULES: dict[SignalGrade, SignalRule] = {
    "A+": SignalRule(95, 100, "qualified", "95-100"),
    "A": SignalRule(90, 94, "qualified", "90-94"),
    "B+": SignalRule(85, 89, "watch", "85-89 watch only"),
    "Reject": SignalRule(0, 84, "rejected", "below 85"),
}


def classify_score(score: int) -> tuple[SignalGrade, SignalStatus]:
    """Classify an integer score using the locked central rules."""

    if not 0 <= score <= 100:
        raise ValueError("score must be between 0 and 100")

    for grade in ("A+", "A", "B+", "Reject"):
        rule = SIGNAL_RULES[grade]
        if rule.minimum <= score <= rule.maximum:
            return grade, rule.status

    raise RuntimeError("signal rule configuration does not cover the score")


def public_signal_rules() -> dict[str, str]:
    """Return the frontend-facing score ranges from the central rule map."""

    return {grade: rule.display_range for grade, rule in SIGNAL_RULES.items()}
