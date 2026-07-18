"""Single source of truth for strict DSE signal qualification gates."""

from dataclasses import dataclass

from app.core.signal_rules import SignalGrade, SignalStatus

MIN_QUALIFIED_VOLUME_RATIO = 1.5
MIN_QUALIFIED_RISK_REWARD = 1.5
MAX_ENTRY_DISTANCE_RATIO = 0.03
QUALIFIED_GRADES: frozenset[SignalGrade] = frozenset({"A+", "A"})
VALID_SETUPS: frozenset[str] = frozenset(
    {
        "20-Day Breakout",
        "EMA Trend Pullback",
        "RSI Momentum Recovery",
        "SMA Trend Continuation",
    }
)


@dataclass(frozen=True, slots=True)
class QualificationDecision:
    """Final hard-gate decision applied after raw score grading."""

    passed: bool
    status: SignalStatus
    failures: tuple[str, ...]
    entry_distance_ratio: float | None


def evaluate_qualification(
    *,
    grade: SignalGrade,
    trend: str,
    setup: str,
    close: float,
    ema20: float,
    sma20: float,
    prior_high20: float,
    volume_ratio: float,
    risk_reward: float,
    latest_volume: int,
) -> QualificationDecision:
    """Apply the locked A+/A production gate independently of the raw score.

    A+/A can become qualified only when every mandatory gate passes.
    B+ is always watch-only. Reject remains rejected.
    """

    if grade == "B+":
        return QualificationDecision(
            passed=False,
            status="watch",
            failures=("B+ is watch-only and cannot become a qualified signal.",),
            entry_distance_ratio=_entry_distance_ratio(
                setup=setup,
                close=close,
                ema20=ema20,
                sma20=sma20,
                prior_high20=prior_high20,
            ),
        )

    if grade == "Reject":
        return QualificationDecision(
            passed=False,
            status="rejected",
            failures=("Score is below the minimum B+ threshold.",),
            entry_distance_ratio=_entry_distance_ratio(
                setup=setup,
                close=close,
                ema20=ema20,
                sma20=sma20,
                prior_high20=prior_high20,
            ),
        )

    failures: list[str] = []

    if grade not in QUALIFIED_GRADES:
        failures.append("Grade is not eligible for qualification.")
    if trend != "BULLISH":
        failures.append("Trend is not confirmed bullish.")
    if setup not in VALID_SETUPS:
        failures.append("No valid production setup is present.")
    if latest_volume <= 0:
        failures.append("Latest candle has no positive volume.")
    if volume_ratio < MIN_QUALIFIED_VOLUME_RATIO:
        failures.append(
            f"Volume confirmation failed: ratio {volume_ratio:.2f} is below {MIN_QUALIFIED_VOLUME_RATIO:.2f}."
        )
    if risk_reward < MIN_QUALIFIED_RISK_REWARD:
        failures.append(
            f"Risk/reward gate failed: {risk_reward:.2f} is below {MIN_QUALIFIED_RISK_REWARD:.2f}."
        )

    entry_distance = _entry_distance_ratio(
        setup=setup,
        close=close,
        ema20=ema20,
        sma20=sma20,
        prior_high20=prior_high20,
    )
    if entry_distance is None:
        failures.append("No valid entry anchor is available for this setup.")
    elif entry_distance > MAX_ENTRY_DISTANCE_RATIO:
        failures.append(
            "Entry proximity gate failed: price is "
            f"{entry_distance * 100:.2f}% from the setup anchor; maximum is "
            f"{MAX_ENTRY_DISTANCE_RATIO * 100:.2f}%."
        )

    passed = not failures
    return QualificationDecision(
        passed=passed,
        status="qualified" if passed else "rejected",
        failures=tuple(failures),
        entry_distance_ratio=entry_distance,
    )


def _entry_distance_ratio(
    *,
    setup: str,
    close: float,
    ema20: float,
    sma20: float,
    prior_high20: float,
) -> float | None:
    """Return distance from the deterministic entry anchor for each current setup."""

    if setup == "20-Day Breakout":
        anchor = prior_high20
    elif setup in {"EMA Trend Pullback", "RSI Momentum Recovery"}:
        anchor = ema20
    elif setup == "SMA Trend Continuation":
        anchor = sma20
    else:
        return None

    if anchor <= 0:
        return None
    return abs(close - anchor) / anchor
