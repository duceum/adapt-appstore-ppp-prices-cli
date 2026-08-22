from datetime import date
from unittest.mock import MagicMock, patch

import httpx
import pytest

from appstore_ppp_prices.appstore import Product, PricePoint
from appstore_ppp_prices.pipeline import find_product, resolve_territory_prices, calculate_targets, apply_prices
from appstore_ppp_prices.pricing import TargetPrice


def _product(pid: str, is_sub: bool = False) -> Product:
    return Product(id=f"id_{pid}", name=pid, product_id=pid, product_type="CONSUMABLE", is_subscription=is_sub)


class TestFindProduct:
    def test_finds_by_product_id(self):
        products = [_product("weekly"), _product("monthly"), _product("yearly")]
        result = find_product(products, "monthly")
        assert result.product_id == "monthly"

    def test_finds_subscription(self):
        products = [_product("weekly", is_sub=True), _product("gems")]
        result = find_product(products, "weekly")
        assert result.is_subscription is True

    def test_exits_on_not_found(self):
        products = [_product("weekly")]
        with pytest.raises(SystemExit):
            find_product(products, "nonexistent")

    def test_exits_on_empty_list(self):
        with pytest.raises(SystemExit):
            find_product([], "weekly")


class TestResolveTerritoryPrices:
    def _make_target(self, country: str, coefficient: float) -> TargetPrice:
        return TargetPrice(
            country_code=country, country_name=country,
            product_id="id_w", product_name="weekly",
            us_price=5.99, coefficient=coefficient,
            target_price_usd=round(5.99 * coefficient, 2),
        )

    def _us_point(self) -> PricePoint:
        return PricePoint(id="usd_599", customer_price=5.99, territory_3="USA")

    def _client(self, baselines: dict, grids: dict) -> MagicMock:
        client = MagicMock()
        client.fetch_all_equalizations.return_value = baselines
        client.fetch_territory_price_points.return_value = grids
        return client

    def test_scales_the_local_price_by_the_coefficient(self):
        """A premium country pays its own currency times the coefficient."""
        client = self._client(
            baselines={"CHE": PricePoint(id="che_500", customer_price=5.00, territory_3="CHE")},
            grids={"CHE": [PricePoint(id=f"che_{p}", customer_price=p, territory_3="CHE")
                           for p in (5.00, 5.10, 5.50, 6.00)]},
        )
        targets = [self._make_target("CHE", 1.10)]

        result, baselines = resolve_territory_prices(client, _product("weekly"), targets, self._us_point())

        assert result["CHE"].customer_price == 5.50  # 5.00 x 1.10, not the 6.00 an equalized tier gives
        assert baselines["CHE"].customer_price == 5.00

    def test_rounds_up_for_a_premium_country(self):
        """No exact point: above the base price it takes the next one up."""
        client = self._client(
            baselines={"NOR": PricePoint(id="nor_79", customer_price=79.0, territory_3="NOR")},
            grids={"NOR": [PricePoint(id=f"nor_{p}", customer_price=p, territory_3="NOR")
                           for p in (79.0, 86.0, 87.0, 89.0)]},
        )
        targets = [self._make_target("NOR", 1.10)]  # 79 x 1.10 = 86.9

        result, _ = resolve_territory_prices(client, _product("weekly"), targets, self._us_point())
        assert result["NOR"].customer_price == 87.0

    def test_rounds_down_for_a_discounted_country(self):
        client = self._client(
            baselines={"IND": PricePoint(id="inr_599", customer_price=599.0, territory_3="IND")},
            grids={"IND": [PricePoint(id=f"inr_{p}", customer_price=p, territory_3="IND")
                           for p in (199.0, 239.0, 249.0, 599.0)]},
        )
        targets = [self._make_target("IND", 0.40)]  # 599 x 0.40 = 239.6

        result, _ = resolve_territory_prices(client, _product("weekly"), targets, self._us_point())
        assert result["IND"].customer_price == 239.0

    def test_skips_a_territory_without_a_grid(self):
        """A batch that failed to load must not take the other territories down."""
        client = self._client(
            baselines={
                "CHE": PricePoint(id="che_500", customer_price=5.00, territory_3="CHE"),
                "NOR": PricePoint(id="nor_79", customer_price=79.0, territory_3="NOR"),
            },
            grids={"CHE": [PricePoint(id="che_550", customer_price=5.50, territory_3="CHE")]},
        )
        targets = [self._make_target("CHE", 1.10), self._make_target("NOR", 1.10)]

        result, _ = resolve_territory_prices(client, _product("weekly"), targets, self._us_point())
        assert "CHE" in result
        assert "NOR" not in result

    def test_exits_when_apple_defaults_cannot_be_loaded(self):
        client = self._client(baselines={}, grids={})
        targets = [self._make_target("CHE", 1.10)]

        with pytest.raises(SystemExit):
            resolve_territory_prices(client, _product("weekly"), targets, self._us_point())


class TestApplyPrices:
    def test_exits_when_all_subscription_territories_fail(self):
        """apply_prices should sys.exit(1) when every territory fails."""
        product = _product("weekly", is_sub=True)
        client = MagicMock()
        client.delete_pending_subscription_prices.return_value = 0
        client.set_subscription_price.side_effect = httpx.HTTPStatusError(
            "conflict", request=MagicMock(), response=MagicMock(),
        )
        territory_prices = {
            "DEU": PricePoint(id="pp1", customer_price=3.99, territory_3="DEU"),
            "IND": PricePoint(id="pp2", customer_price=1.99, territory_3="IND"),
        }
        with pytest.raises(SystemExit):
            apply_prices(client, product, territory_prices)


class TestCalculateTargetsMissingCsv:
    @patch("appstore_ppp_prices.pipeline.load_countries", side_effect=FileNotFoundError("countries.csv"))
    def test_exits_on_missing_countries_csv(self, _mock):
        product = _product("weekly")
        with pytest.raises(SystemExit):
            calculate_targets(product, 4.99, "", None)


class TestApplyPricesSubscriptionFlags:
    def _territory_prices(self):
        return {"DEU": PricePoint(id="pp1", customer_price=3.99, territory_3="DEU")}

    def test_passes_preserved_and_start_date_to_client(self):
        product = _product("weekly", is_sub=True)
        client = MagicMock()
        client.delete_pending_subscription_prices.return_value = 0
        prices = self._territory_prices()

        apply_prices(client, product, prices, preserved=True, start_date=date(2099, 1, 15))

        client.set_subscription_price.assert_called_once_with(
            "id_weekly", "DEU", prices["DEU"], preserved=True, start_date=date(2099, 1, 15))

    def test_defaults_are_not_preserved_and_no_date(self):
        product = _product("weekly", is_sub=True)
        client = MagicMock()
        client.delete_pending_subscription_prices.return_value = 0
        prices = self._territory_prices()

        apply_prices(client, product, prices)

        client.set_subscription_price.assert_called_once_with(
            "id_weekly", "DEU", prices["DEU"], preserved=False, start_date=None)
