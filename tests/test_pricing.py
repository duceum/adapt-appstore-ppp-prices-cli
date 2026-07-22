from src.countries import Country
from src.pricing import calculate_target_prices, get_coefficient


def _country(code: str, category: str, coeff: float, gdp: int = 50000) -> Country:
    return Country(code=code, name=f"Test {code}", gdp_per_capita=gdp, category=category, default_coefficient=coeff)


def _product(product_id: str, us_price: float) -> dict:
    return {"id": f"id_{product_id}", "name": product_id, "product_id": product_id, "us_price": us_price}


class TestGetCoefficient:
    def test_uses_default_when_no_ai(self):
        c = _country("DEU", "high_income", 0.90)
        assert get_coefficient(c, None) == 0.90

    def test_uses_ai_coefficient_when_available(self):
        c = _country("DEU", "high_income", 0.90)
        assert get_coefficient(c, {"high_income": 0.85}) == 0.85

    def test_falls_back_to_default_when_category_missing_in_ai(self):
        c = _country("DEU", "high_income", 0.90)
        assert get_coefficient(c, {"emerging": 0.40}) == 0.90


class TestCalculateTargetPrices:
    def test_basic_calculation(self):
        countries = [_country("DEU", "high_income", 0.90)]
        products = [_product("weekly", 4.99)]
        results = calculate_target_prices(products, countries)
        assert len(results) == 1
        assert results[0].target_price_usd == round(4.99 * 0.90, 2)
        assert results[0].coefficient == 0.90

    def test_multiple_products_multiple_countries(self):
        countries = [
            _country("DEU", "high_income", 0.90),
            _country("IND", "emerging", 0.40, gdp=2818),
        ]
        products = [_product("weekly", 4.99), _product("monthly", 9.99)]
        results = calculate_target_prices(products, countries)
        assert len(results) == 4

    def test_minimum_price_protection(self):
        """If cheapest product x coeff < minimum, all coefficients scale up."""
        countries = [_country("IND", "emerging", 0.40, gdp=2818)]
        # 0.99 * 0.40 = 0.396 < 0.49 (developing minimum)
        products = [_product("cheap", 0.99), _product("expensive", 9.99)]
        results = calculate_target_prices(products, countries)

        cheap_result = next(r for r in results if r.product_name == "cheap")
        expensive_result = next(r for r in results if r.product_name == "expensive")

        # cheap must be >= 0.49
        assert cheap_result.target_price_usd >= 0.49
        # ratio must be preserved: expensive/cheap should equal 9.99/0.99
        original_ratio = 9.99 / 0.99
        actual_ratio = expensive_result.target_price_usd / cheap_result.target_price_usd
        assert abs(actual_ratio - original_ratio) < 0.01

    def test_no_scaling_when_above_minimum(self):
        """No scaling needed when cheapest product stays above minimum."""
        countries = [_country("DEU", "high_income", 0.90)]
        products = [_product("weekly", 4.99)]
        results = calculate_target_prices(products, countries)
        assert results[0].coefficient == 0.90

    def test_empty_products(self):
        countries = [_country("DEU", "high_income", 0.90)]
        assert calculate_target_prices([], countries) == []

    def test_empty_countries(self):
        products = [_product("weekly", 4.99)]
        assert calculate_target_prices(products, []) == []

    def test_ai_coefficients_override(self):
        countries = [_country("DEU", "high_income", 0.90)]
        products = [_product("weekly", 4.99)]
        ai = {"high_income": 0.80}
        results = calculate_target_prices(products, countries, ai)
        assert results[0].target_price_usd == round(4.99 * 0.80, 2)

    def test_developed_market_minimum(self):
        """Developed markets have $0.99 minimum."""
        countries = [_country("DEU", "high_income", 0.10)]  # artificially low coeff
        products = [_product("cheap", 1.99)]
        results = calculate_target_prices(products, countries)
        # 1.99 * 0.10 = 0.199 < 0.99 (developed minimum for DEU)
        assert results[0].target_price_usd >= 0.99
