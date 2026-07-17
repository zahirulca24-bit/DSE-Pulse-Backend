"""Boundary proof for the central locked signal rules."""

import pytest

from app.core.signal_rules import classify_score


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, ("A+", "qualified")),
        (95, ("A+", "qualified")),
        (94, ("A", "qualified")),
        (90, ("A", "qualified")),
        (89, ("B+", "watch")),
        (85, ("B+", "watch")),
        (84, ("Reject", "rejected")),
        (0, ("Reject", "rejected")),
    ],
)
def test_signal_rule_boundaries(score: int, expected: tuple[str, str]) -> None:
    assert classify_score(score) == expected


@pytest.mark.parametrize("score", [-1, 101])
def test_signal_rule_rejects_out_of_range_score(score: int) -> None:
    with pytest.raises(ValueError):
        classify_score(score)
