from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

log = logging.getLogger(__name__)

COUNTRIES_CSV = Path(str(files("appstore_ppp_prices") / "countries.csv"))

MINIMUM_PRICE_HIGH = 0.99  # premium, usa, high_income
MINIMUM_PRICE_LOW = 0.49   # upper_middle, lower_middle, emerging

_HIGH_MINIMUM_CATEGORIES = frozenset({"premium", "usa", "high_income"})


@dataclass(frozen=True)
class Country:
    code: str
    name: str
    gdp_per_capita: int
    category: str
    default_coefficient: float

    @property
    def minimum_price(self) -> float:
        if self.category in _HIGH_MINIMUM_CATEGORIES:
            return MINIMUM_PRICE_HIGH
        return MINIMUM_PRICE_LOW


def load_countries(
    exclude: set[str] | None = None,
    csv_path: Path = COUNTRIES_CSV,
) -> list[Country]:
    exclude = {c.upper() for c in exclude} if exclude else set()
    countries: list[Country] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row["country_code"].strip().upper()
            if code in exclude or code == "USA":
                continue
            try:
                gdp = int(row["gdp_per_capita"])
                coeff = float(row["default_coefficient"])
            except (ValueError, TypeError) as e:
                log.warning("Skipping country %s: invalid data (%s)", code, e)
                continue
            countries.append(Country(
                code=code,
                name=row["country_name"].strip(),
                gdp_per_capita=gdp,
                category=row["category"].strip(),
                default_coefficient=coeff,
            ))
    return countries
