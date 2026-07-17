"""Fixed demo candidates used when no real DSE dataset is configured."""

from dataclasses import dataclass

from app.core.sectors import SectorName


@dataclass(frozen=True, slots=True)
class DemoCandidate:
    """Raw candidate inputs classified by the central signal rules."""

    symbol: str
    company: str
    sector: SectorName
    score: int
    risk_reward: float


DEMO_CANDIDATES: tuple[DemoCandidate, ...] = (
    DemoCandidate(
        symbol="SQURPHARMA",
        company="Square Pharmaceuticals PLC.",
        sector="Pharmaceuticals & Chemicals",
        score=97,
        risk_reward=3.12,
    ),
    DemoCandidate(
        symbol="GP",
        company="Grameenphone Ltd.",
        sector="Telecommunication",
        score=96,
        risk_reward=2.75,
    ),
    DemoCandidate(
        symbol="BATBC",
        company="British American Tobacco Bangladesh Company Limited",
        sector="Food & Allied",
        score=92,
        risk_reward=2.20,
    ),
    DemoCandidate(
        symbol="CITYBANK",
        company="The City Bank PLC.",
        sector="Bank",
        score=87,
        risk_reward=1.65,
    ),
    DemoCandidate(
        symbol="BRACBANK",
        company="BRAC Bank PLC.",
        sector="Bank",
        score=82,
        risk_reward=1.10,
    ),
)
