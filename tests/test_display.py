from unittest.mock import MagicMock

from appstore_ppp_prices.appstore import PricePoint, Product
from appstore_ppp_prices.display import (
    find_price_point,
    format_local_price,
    list_products,
    print_dry_run_table,
)
from appstore_ppp_prices.pricing import TargetPrice


class TestFindPricePoint:
    def _points(self, *prices: float) -> list[PricePoint]:
        return [PricePoint(id=str(i), customer_price=price, territory_3="USA")
                for i, price in enumerate(prices, 1)]

    def test_exact_match_wins(self):
        result = find_price_point(self._points(0.99, 1.99, 4.99), 1.99, base=4.99)
        assert result.customer_price == 1.99

    def test_rounds_up_above_the_base_price(self):
        """A premium market must not slip under its target."""
        result = find_price_point(self._points(4.99, 5.49, 5.99), 5.50, base=4.99)
        assert result.customer_price == 5.99

    def test_rounds_down_below_the_base_price(self):
        """A discounted market must not creep over its target."""
        result = find_price_point(self._points(1.99, 2.99, 4.99), 2.50, base=4.99)
        assert result.customer_price == 1.99

    def test_falls_back_to_nearest_when_nothing_lies_above(self):
        result = find_price_point(self._points(0.99, 1.99), 999.99, base=0.99)
        assert result.customer_price == 1.99

    def test_falls_back_to_nearest_when_nothing_lies_below(self):
        result = find_price_point(self._points(4.99, 9.99), 0.01, base=9.99)
        assert result.customer_price == 4.99

    def test_target_equal_to_the_base_price_takes_nearest(self):
        result = find_price_point(self._points(0.99, 4.99), 3.99, base=3.99)
        assert result.customer_price == 4.99

    def test_empty_list_returns_none(self):
        assert find_price_point([], 4.99, base=4.99) is None

    def test_single_point(self):
        result = find_price_point(self._points(9.99), 0.50, base=9.99)
        assert result.customer_price == 9.99


class TestPrintDryRunTable:
    def _results(self) -> list[TargetPrice]:
        return [TargetPrice(
            country_code="CHE", country_name="Switzerland",
            product_id="id_1", product_name="weekly",
            us_price=5.99, coefficient=1.10, target_price_usd=6.59,
        )]

    def test_shows_local_prices_and_the_change(self, capsys):
        print_dry_run_table(
            self._results(), "weekly (com.app.weekly)",
            {"CHE": PricePoint(id="che_550", customer_price=5.50, territory_3="CHE")},
            {"CHE": PricePoint(id="che_500", customer_price=5.00, territory_3="CHE")},
            {"CHE": "CHF"},
        )
        output = capsys.readouterr().out

        assert "Switzerland" in output
        assert "5.00 CHF" in output
        assert "5.50 CHF" in output
        assert "+10.0%" in output

    def test_marks_a_territory_that_did_not_resolve(self, capsys):
        print_dry_run_table(self._results(), "weekly (com.app.weekly)", {}, {}, {})
        output = capsys.readouterr().out

        assert "Switzerland" in output
        assert "n/a" in output


class TestFormatLocalPrice:
    def test_drops_decimals_on_large_round_amounts(self):
        assert format_local_price(39000.0, "IDR") == "39,000 IDR"

    def test_keeps_decimals_on_small_amounts(self):
        assert format_local_price(5.5, "CHF") == "5.50 CHF"

    def test_survives_a_missing_currency(self):
        assert format_local_price(5.5, "") == "5.50"


class TestListProducts:
    def _make_product(self, pid: str, is_sub: bool = False) -> Product:
        return Product(id=f"id_{pid}", name=pid, product_id=pid, product_type="CONSUMABLE", is_subscription=is_sub)

    def test_shows_na_when_price_fetch_fails(self, capsys):
        """Network error on one product shows N/A, doesn't crash."""
        products = [self._make_product("weekly"), self._make_product("monthly")]

        client = MagicMock()

        def mock_price(product):
            if product.product_id == "weekly":
                raise ConnectionError("network error")
            return 4.99

        client.fetch_us_price.side_effect = mock_price

        list_products(client, "123", products, "Test App")
        output = capsys.readouterr().out

        assert "weekly" in output
        assert "monthly" in output
        assert "N/A" in output
        assert "$4.99" in output

    def test_all_prices_fail_still_shows_list(self, capsys):
        """Even if all price fetches fail, product list is still displayed."""
        products = [self._make_product("weekly")]

        client = MagicMock()
        client.fetch_us_price.side_effect = ConnectionError("down")

        list_products(client, "123", products, "Test App")
        output = capsys.readouterr().out

        assert "weekly" in output
        assert "N/A" in output
