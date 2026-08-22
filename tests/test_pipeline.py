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
    def _make_target(self, country: str, target_usd: float) -> TargetPrice:
        return TargetPrice(
            country_code=country, country_name=country,
            product_id="id_w", product_name="weekly",
            us_price=4.99, coefficient=0.7, target_price_usd=target_usd,
        )

    def _make_usd_points(self) -> list[PricePoint]:
        return [
            PricePoint(id="tier_1", customer_price=0.99, territory_3="USA"),
            PricePoint(id="tier_5", customer_price=4.99, territory_3="USA"),
        ]

    def test_continues_when_one_tier_fails(self):
        """If one equalization fetch fails, other tiers still resolve."""
        product = _product("weekly")
        targets = [
            self._make_target("DEU", 4.99),  # maps to tier_5
            self._make_target("IND", 0.99),  # maps to tier_1
        ]
        usd_points = self._make_usd_points()

        client = MagicMock()

        def mock_eq(prod, uid):
            if uid == "tier_5":
                raise ConnectionError("network down")
            return {"IND": PricePoint(id="ind_pp", customer_price=79.0, territory_3="IND")}

        client.fetch_all_equalizations.side_effect = mock_eq

        result = resolve_territory_prices(client, product, targets, usd_points)

        assert "IND" in result
        assert "DEU" not in result

    def test_returns_empty_when_all_tiers_fail(self):
        """If all equalization fetches fail, returns empty dict."""
        product = _product("weekly")
        targets = [self._make_target("DEU", 4.99)]
        usd_points = self._make_usd_points()

        client = MagicMock()
        client.fetch_all_equalizations.side_effect = ConnectionError("timeout")

        result = resolve_territory_prices(client, product, targets, usd_points)

        assert result == {}

    def test_skips_targets_when_usd_points_empty(self):
        """Empty usd_points should not crash — targets are skipped gracefully."""
        product = _product("weekly")
        targets = [self._make_target("DEU", 4.99)]
        client = MagicMock()

        result = resolve_territory_prices(client, product, targets, [])
        assert result == {}
        client.fetch_all_equalizations.assert_not_called()


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
