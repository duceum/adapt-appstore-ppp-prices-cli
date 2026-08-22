from __future__ import annotations

from dataclasses import dataclass

from appstore_ppp_prices.countries import Country


@dataclass
class TargetPrice:
    country_code: str
    country_name: str
    product_id: str
    product_name: str
    us_price: float
    coefficient: float
    target_price_usd: float


def get_coefficient(country: Country, ai_coefficients: dict[str, float] | None) -> float:
    if ai_coefficients and country.category in ai_coefficients:
        return ai_coefficients[country.category]
    return country.default_coefficient


def calculate_target_prices(
    products: list[dict],
    countries: list[Country],
    ai_coefficients: dict[str, float] | None = None,
) -> list[TargetPrice]:
    """Calculate target USD prices for all products across all countries.

    products: list of {"id": str, "name": str, "product_id": str, "us_price": float}
    ai_coefficients: optional dict like {"premium": 1.10, "high_income": 0.85, ...}

    Applies minimum price protection with ratio preservation:
    if the cheapest product × coefficient falls below the country minimum,
    all products get a scaled-up coefficient to keep ratios intact.
    """
    if not products or not countries:
        return []

    us_prices = [p["us_price"] for p in products]
    cheapest_us = min(us_prices)

    results: list[TargetPrice] = []

    for country in countries:
        base_coeff = get_coefficient(country, ai_coefficients)
        min_price = country.minimum_price

        # Ratio preservation: if cheapest product hits floor, scale all up
        coeff = max(base_coeff, min_price / cheapest_us)

        for p in products:
            target = round(p["us_price"] * coeff, 2)
            results.append(TargetPrice(
                country_code=country.code,
                country_name=country.name,
                product_id=p["id"],
                product_name=p.get("name", p["product_id"]),
                us_price=p["us_price"],
                coefficient=coeff,
                target_price_usd=target,
            ))

    return results
