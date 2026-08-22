from unittest.mock import MagicMock

from appstore_ppp_prices.appstore import PricePoint, Product
from appstore_ppp_prices.display import find_closest_price_point, list_products, print_dry_run_table
from appstore_ppp_prices.pricing import TargetPrice


class TestFindClosestPricePoint:
    def test_exact_match(self):
        points = [
            PricePoint(id="1", customer_price=0.99, territory_3="USA"),
            PricePoint(id="2", customer_price=1.99, territory_3="USA"),
            PricePoint(id="3", customer_price=4.99, territory_3="USA"),
        ]
        result = find_closest_price_point(points, 1.99)
        assert result.id == "2"

    def test_rounds_to_nearest(self):
        points = [
            PricePoint(id="1", customer_price=0.99, territory_3="USA"),
            PricePoint(id="2", customer_price=1.99, territory_3="USA"),
            PricePoint(id="3", customer_price=2.99, territory_3="USA"),
        ]
        result = find_closest_price_point(points, 2.50)
        assert result.id == "3"  # 2.99 is closer to 2.50 than 1.99

    def test_rounds_down_when_closer(self):
        points = [
            PricePoint(id="1", customer_price=0.99, territory_3="USA"),
            PricePoint(id="2", customer_price=1.99, territory_3="USA"),
            PricePoint(id="3", customer_price=2.99, territory_3="USA"),
        ]
        result = find_closest_price_point(points, 1.50)
        assert result.id == "2"  # 1.99 is closer to 1.50 than 0.99

    def test_empty_list_returns_none(self):
        result = find_closest_price_point([], 4.99)
        assert result is None

    def test_single_point(self):
        points = [PricePoint(id="1", customer_price=9.99, territory_3="USA")]
        result = find_closest_price_point(points, 0.50)
        assert result.id == "1"

    def test_target_below_all_points(self):
        points = [
            PricePoint(id="1", customer_price=4.99, territory_3="USA"),
            PricePoint(id="2", customer_price=9.99, territory_3="USA"),
        ]
        result = find_closest_price_point(points, 0.01)
        assert result.id == "1"

    def test_target_above_all_points(self):
        points = [
            PricePoint(id="1", customer_price=0.99, territory_3="USA"),
            PricePoint(id="2", customer_price=1.99, territory_3="USA"),
        ]
        result = find_closest_price_point(points, 999.99)
        assert result.id == "2"


class TestPrintDryRunTable:
    def _make_results(self, us_price: float = 4.99) -> list[TargetPrice]:
        return [TargetPrice(
            country_code="DEU", country_name="Germany",
            product_id="id_1", product_name="weekly",
            us_price=us_price, coefficient=0.85, target_price_usd=round(us_price * 0.85, 2),
        )]

    def _make_tiers(self) -> list[PricePoint]:
        return [
            PricePoint(id="t1", customer_price=0.99, territory_3="USA"),
            PricePoint(id="t2", customer_price=4.99, territory_3="USA"),
            PricePoint(id="t3", customer_price=5.99, territory_3="USA"),
        ]

    def test_without_us_override(self, capsys):
        print_dry_run_table(self._make_results(), "weekly (com.app.weekly)", self._make_tiers())
        output = capsys.readouterr().out
        assert "Germany" in output
        assert "United States (override)" not in output

    def test_with_us_override(self, capsys):
        us_pp = PricePoint(id="t3", customer_price=5.99, territory_3="USA")
        print_dry_run_table(self._make_results(5.99), "weekly (com.app.weekly)", self._make_tiers(),
                            us_price_override=us_pp)
        output = capsys.readouterr().out
        assert "United States (override)" in output
        assert "5.99" in output
        assert "Germany" in output


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
