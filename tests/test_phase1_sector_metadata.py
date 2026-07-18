"""Locked Phase-1 DSE sector-universe integrity tests."""

from collections import Counter

from app.data.symbol_metadata import (
    PHASE1_SECTOR_SYMBOLS,
    PHASE1_SYMBOL_COUNT,
    PHASE1_SYMBOLS,
    SYMBOL_SECTORS,
)

EXPECTED_COUNTS = {
    "Bank": 36,
    "Cement": 7,
    "Ceramics": 5,
    "Engineering": 42,
    "Financial Institutions": 23,
    "Food & Allied": 21,
    "Fuel & Power": 23,
    "Insurance": 58,
    "IT Sector": 11,
    "Pharmaceuticals & Chemicals": 34,
}


def test_phase1_universe_has_exact_locked_size_and_sector_counts() -> None:
    assert PHASE1_SYMBOL_COUNT == 260
    assert len(PHASE1_SYMBOLS) == 260
    assert len(SYMBOL_SECTORS) == 260
    assert set(PHASE1_SECTOR_SYMBOLS) == set(EXPECTED_COUNTS)
    assert {sector: len(symbols) for sector, symbols in PHASE1_SECTOR_SYMBOLS.items()} == EXPECTED_COUNTS


def test_phase1_symbols_are_unique_uppercase_and_have_one_sector() -> None:
    declared = [symbol for symbols in PHASE1_SECTOR_SYMBOLS.values() for symbol in symbols]
    assert len(declared) == len(set(declared)) == 260
    assert all(symbol == symbol.upper() for symbol in declared)
    assert Counter(SYMBOL_SECTORS.values()) == Counter(EXPECTED_COUNTS)


def test_locked_reference_symbols_map_to_expected_sectors() -> None:
    assert SYMBOL_SECTORS["CITYBANK"] == "Bank"
    assert SYMBOL_SECTORS["BSRMSTEEL"] == "Engineering"
    assert SYMBOL_SECTORS["IDLC"] == "Financial Institutions"
    assert SYMBOL_SECTORS["BATBC"] == "Food & Allied"
    assert SYMBOL_SECTORS["SUMITPOWER"] == "Fuel & Power"
    assert SYMBOL_SECTORS["GREENDELT"] == "Insurance"
    assert SYMBOL_SECTORS["GENEXIL"] == "IT Sector"
    assert SYMBOL_SECTORS["SQURPHARMA"] == "Pharmaceuticals & Chemicals"
    assert "GP" not in PHASE1_SYMBOLS
