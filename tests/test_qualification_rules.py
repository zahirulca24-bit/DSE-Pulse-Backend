"""Strict production qualification-gate tests."""

from app.core.qualification_rules import evaluate_qualification


def test_a_plus_passes_only_when_every_gate_passes() -> None:
    decision = evaluate_qualification(
        grade="A+",
        trend="BULLISH",
        setup="EMA Trend Pullback",
        close=102.0,
        ema20=100.0,
        sma20=99.0,
        prior_high20=108.0,
        volume_ratio=1.8,
        risk_reward=2.0,
        latest_volume=200_000,
    )

    assert decision.passed is True
    assert decision.status == "qualified"
    assert decision.failures == ()
    assert decision.entry_distance_ratio is not None
    assert decision.entry_distance_ratio <= 0.03


def test_high_grade_is_rejected_when_volume_gate_fails() -> None:
    decision = evaluate_qualification(
        grade="A",
        trend="BULLISH",
        setup="EMA Trend Pullback",
        close=102.0,
        ema20=100.0,
        sma20=99.0,
        prior_high20=108.0,
        volume_ratio=1.49,
        risk_reward=2.0,
        latest_volume=200_000,
    )

    assert decision.passed is False
    assert decision.status == "rejected"
    assert any("Volume confirmation failed" in item for item in decision.failures)


def test_high_grade_is_rejected_when_risk_reward_gate_fails() -> None:
    decision = evaluate_qualification(
        grade="A+",
        trend="BULLISH",
        setup="EMA Trend Pullback",
        close=102.0,
        ema20=100.0,
        sma20=99.0,
        prior_high20=108.0,
        volume_ratio=1.8,
        risk_reward=1.49,
        latest_volume=200_000,
    )

    assert decision.passed is False
    assert decision.status == "rejected"
    assert any("Risk/reward gate failed" in item for item in decision.failures)


def test_high_grade_is_rejected_when_entry_is_too_far() -> None:
    decision = evaluate_qualification(
        grade="A+",
        trend="BULLISH",
        setup="EMA Trend Pullback",
        close=105.0,
        ema20=100.0,
        sma20=99.0,
        prior_high20=108.0,
        volume_ratio=1.8,
        risk_reward=2.0,
        latest_volume=200_000,
    )

    assert decision.passed is False
    assert decision.status == "rejected"
    assert any("Entry proximity gate failed" in item for item in decision.failures)


def test_high_grade_is_rejected_without_bullish_trend_or_valid_setup() -> None:
    decision = evaluate_qualification(
        grade="A+",
        trend="NEUTRAL",
        setup="Rejected / No Setup",
        close=100.0,
        ema20=100.0,
        sma20=100.0,
        prior_high20=100.0,
        volume_ratio=2.0,
        risk_reward=2.0,
        latest_volume=200_000,
    )

    assert decision.passed is False
    assert decision.status == "rejected"
    assert "Trend is not confirmed bullish." in decision.failures
    assert "No valid production setup is present." in decision.failures


def test_b_plus_is_always_watch_only() -> None:
    decision = evaluate_qualification(
        grade="B+",
        trend="BULLISH",
        setup="EMA Trend Pullback",
        close=101.0,
        ema20=100.0,
        sma20=99.0,
        prior_high20=108.0,
        volume_ratio=3.0,
        risk_reward=3.0,
        latest_volume=500_000,
    )

    assert decision.passed is False
    assert decision.status == "watch"
    assert decision.failures == ("B+ is watch-only and cannot become a qualified signal.",)
