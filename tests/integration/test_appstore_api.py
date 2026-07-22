"""Integration tests for App Store Connect API (read-only).

These tests require real credentials in .env:
  ASC_KEY_ID, ASC_ISSUER_ID, ASC_PRIVATE_KEY_PATH, TEST_APP_ID, TEST_PRODUCT_ID

Run: python3 -m pytest tests/integration/ -v
"""
from __future__ import annotations

from src.appstore import AppInfo, AppStoreConnectClient, Product, PricePoint


class TestFetchAppInfo:
    def test_returns_app_info(self, client: AppStoreConnectClient, app_id: str):
        info = client.fetch_app_info(app_id)
        assert isinstance(info, AppInfo)
        assert info.id == app_id
        assert info.name  # non-empty
        assert info.bundle_id  # non-empty


class TestFetchAllProducts:
    def test_returns_products(self, client: AppStoreConnectClient, app_id: str):
        products = client.fetch_all_products(app_id)
        assert isinstance(products, list)
        assert len(products) > 0
        for p in products:
            assert isinstance(p, Product)
            assert p.id
            assert p.product_id

    def test_product_has_correct_fields(self, client: AppStoreConnectClient, app_id: str):
        products = client.fetch_all_products(app_id)
        p = products[0]
        assert isinstance(p.name, str)
        assert isinstance(p.product_type, str)
        assert isinstance(p.is_subscription, bool)


class TestFetchUsPrice:
    def test_returns_float_for_known_product(self, client: AppStoreConnectClient, app_id: str, product_id: str):
        products = client.fetch_all_products(app_id)
        product = next((p for p in products if p.product_id == product_id), None)
        assert product is not None, f"Product {product_id} not found in app {app_id}"

        us_price = client.fetch_us_price(product)
        assert us_price is not None
        assert isinstance(us_price, float)
        assert us_price > 0


class TestFetchUsdPricePoints:
    def test_returns_sorted_price_tiers(self, client: AppStoreConnectClient, app_id: str, product_id: str):
        products = client.fetch_all_products(app_id)
        product = next(p for p in products if p.product_id == product_id)

        points = client.fetch_usd_price_points(product)
        assert isinstance(points, list)
        assert len(points) > 0

        for pp in points:
            assert isinstance(pp, PricePoint)
            assert pp.customer_price >= 0
            assert pp.territory_3 == "USA"

        # Verify sorted ascending
        prices = [pp.customer_price for pp in points]
        assert prices == sorted(prices)


class TestFetchEqualizations:
    def test_returns_territory_price_map(self, client: AppStoreConnectClient, app_id: str, product_id: str):
        products = client.fetch_all_products(app_id)
        product = next(p for p in products if p.product_id == product_id)

        usd_points = client.fetch_usd_price_points(product)
        assert len(usd_points) > 0

        # Pick a mid-range tier
        mid = usd_points[len(usd_points) // 2]
        eq = client.fetch_all_equalizations(product, mid.id)

        assert isinstance(eq, dict)
        assert len(eq) > 50  # Apple has 175 territories

        for territory, pp in eq.items():
            assert isinstance(territory, str)
            assert len(territory) == 3
            assert isinstance(pp, PricePoint)
            assert pp.customer_price > 0
