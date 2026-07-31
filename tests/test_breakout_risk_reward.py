"""Regression tests for setup-aware scanner risk/reward calculations."""

from app.services.scanner_engine import ScannerEngine


def test_early_breakout_can_clear_qualified_risk_reward_gate() -> None:
    risk_reward = ScannerEngine._risk_reward(
        setup="20-Day Breakout",
        close=111.0,
        support=90.0,
        resistance=112.0,
        prior_high20=110.0,
    )

    assert risk_reward == 39.0 / 21.0
    assert risk_reward >= 1.5


def test_breakout_risk_reward_fails_closed_after_exhausting_projection() -> None:
    risk_reward = ScannerEngine._risk_reward(
        setup="20-Day Breakout",
        close=151.0,
        support=90.0,
        resistance=152.0,
        prior_high20=110.0,
    )

    assert risk_reward == 0.0


def test_non_breakout_risk_reward_keeps_resistance_model() -> None:
    risk_reward = ScannerEngine._risk_reward(
        setup="EMA Trend Pullback",
        close=100.0,
        support=95.0,
        resistance=110.0,
        prior_high20=108.0,
    )

    assert risk_reward == 2.0
