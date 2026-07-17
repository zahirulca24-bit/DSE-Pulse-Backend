"""Small local metadata map; unmapped symbols remain explicitly unknown."""

from app.core.sectors import SectorName

SYMBOL_SECTORS: dict[str, SectorName] = {
    "SQURPHARMA": "Pharmaceuticals & Chemicals",
    "GP": "Telecommunication",
    "BATBC": "Food & Allied",
    "CITYBANK": "Bank",
    "BRACBANK": "Bank",
}
