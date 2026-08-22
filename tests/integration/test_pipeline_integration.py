"""Integration test for the full pricing pipeline (read-only, no apply).

Requires: ASC_KEY_ID, ASC_ISSUER_ID, ASC_PRIVATE_KEY_PATH, TEST_APP_ID, TEST_PRODUCT_ID in .env.

Run: python3 -m pytest tests/integration/ -v
"""
from __future__ import annotations

from appstore_ppp_prices.appstore import AppStoreConnectClient
from appstore_ppp_prices.pipeline import find_product, calculate_targets, resolve_territory_prices


class TestFullPipeline:
    def test_calculate_and_resolve_prices(self, client: AppStoreConnectClient, app_id: str, product_id: str):
        """End-to-end: fetch product -> get US price -> calculate targets -> resolve territory prices."""
        # 1. Fetch products and find the one we want
        products = client.fetch_all_products(app_id)
        product = find_product(products, product_id)

        # 2. Fetch US price
        us_price = client.fetch_us_price(product)
        assert us_price is not None
        assert us_price > 0

        # 3. Calculate target prices for all territories
        target_prices = calculate_targets(product, us_price, exclude="", ai_coefficients=None)
        assert len(target_prices) > 100

        # Every target should have sane values
        for tp in target_prices:
            assert tp.us_price == us_price
            assert 0 < tp.coefficient <= 1.5
            assert tp.target_price_usd > 0

        # 4. Fetch USD tiers
        usd_points = client.fetch_usd_price_points(product)
        assert len(usd_points) > 0

        # 5. Resolve territory prices (map targets to Apple tiers)
        territory_prices = resolve_territory_prices(client, product, target_prices, usd_points)
        assert len(territory_prices) > 50

        # Each resolved price should be a real Apple tier
        for territory, pp in territory_prices.items():
            assert len(territory) == 3
            assert pp.customer_price > 0

    def test_exclude_countries(self, client: AppStoreConnectClient, app_id: str, product_id: str):
        """Verify --exclude filters countries from target prices."""
        products = client.fetch_all_products(app_id)
        product = find_product(products, product_id)
        us_price = client.fetch_us_price(product)

        all_targets = calculate_targets(product, us_price, exclude="", ai_coefficients=None)
        filtered = calculate_targets(product, us_price, exclude="DEU,GBR,FRA", ai_coefficients=None)

        excluded_codes = {tp.country_code for tp in all_targets} - {tp.country_code for tp in filtered}
        assert "DEU" in excluded_codes
        assert "GBR" in excluded_codes
        assert "FRA" in excluded_codes
        assert len(filtered) < len(all_targets)
