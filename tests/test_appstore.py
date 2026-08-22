import base64
import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import httpx

from appstore_ppp_prices.appstore import AppStoreConnectClient, Product, PricePoint


class TestContextManager:
    @patch.object(AppStoreConnectClient, "__init__", lambda self, *a, **kw: None)
    def test_close_called_on_exit(self):
        """Context manager should call close() on exit."""
        client = AppStoreConnectClient.__new__(AppStoreConnectClient)
        client.close = MagicMock()

        with client:
            pass

        client.close.assert_called_once()


class TestDeletePendingSubscriptionPrices:
    def _make_client(self):
        """Create a client with mocked internals (no spec to allow private attrs)."""
        client = MagicMock()
        client.delete_pending_subscription_prices = AppStoreConnectClient.delete_pending_subscription_prices.__get__(client)
        return client

    def test_deletes_future_prices(self):
        client = self._make_client()
        client._get_all_pages.return_value = ([
            {"id": "p1", "attributes": {"startDate": "2099-01-01"}},
            {"id": "p2", "attributes": {"startDate": "2099-06-01"}},
        ], [])
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        client._client.delete.return_value = mock_resp
        client._headers.return_value = {}

        deleted = client.delete_pending_subscription_prices("sub_1")
        assert deleted == 2

    def test_skips_past_prices(self):
        client = self._make_client()
        client._get_all_pages.return_value = ([
            {"id": "p1", "attributes": {"startDate": "2020-01-01"}},
        ], [])

        deleted = client.delete_pending_subscription_prices("sub_1")
        assert deleted == 0

    def test_counts_only_successful_deletes(self):
        """Failed DELETEs are not counted but don't crash."""
        client = self._make_client()
        client._get_all_pages.return_value = ([
            {"id": "p1", "attributes": {"startDate": "2099-01-01"}},
            {"id": "p2", "attributes": {"startDate": "2099-06-01"}},
        ], [])

        ok_resp = MagicMock()
        ok_resp.status_code = 204
        fail_resp = MagicMock()
        fail_resp.status_code = 409
        client._client.delete.side_effect = [ok_resp, fail_resp]
        client._headers.return_value = {}

        deleted = client.delete_pending_subscription_prices("sub_1")
        assert deleted == 1


class TestExtractTerritory:
    def _encode(self, data: dict) -> str:
        raw = json.dumps(data).encode("utf-8")
        return base64.b64encode(raw).decode("utf-8").rstrip("=")

    def test_extracts_territory_code(self):
        encoded = self._encode({"t": "DEU", "other": "data"})
        assert AppStoreConnectClient._extract_territory(encoded) == "DEU"

    def test_extracts_usa(self):
        encoded = self._encode({"t": "USA"})
        assert AppStoreConnectClient._extract_territory(encoded) == "USA"

    def test_missing_territory_key(self):
        encoded = self._encode({"other": "data"})
        assert AppStoreConnectClient._extract_territory(encoded) == ""

    def test_invalid_base64(self):
        assert AppStoreConnectClient._extract_territory("not-valid-base64!!!") == ""

    def test_invalid_json(self):
        raw = b"not json at all"
        encoded = base64.b64encode(raw).decode("utf-8").rstrip("=")
        assert AppStoreConnectClient._extract_territory(encoded) == ""

    def test_empty_string(self):
        assert AppStoreConnectClient._extract_territory("") == ""


def _price_point_id(territory: str) -> str:
    """Price-point IDs are base64 JSON carrying the territory."""
    raw = json.dumps({"t": territory, "p": "10000"}).encode("utf-8")
    return base64.b64encode(raw).decode("utf-8").rstrip("=")


class TestFetchTerritoryPricePoints:
    def _make_client(self):
        client = MagicMock()
        client.fetch_usd_price_points = AppStoreConnectClient.fetch_usd_price_points.__get__(client)
        client.fetch_territory_price_points = AppStoreConnectClient.fetch_territory_price_points.__get__(client)
        client._parse_price_points = AppStoreConnectClient._parse_price_points.__get__(client)
        client._extract_territory = AppStoreConnectClient._extract_territory
        return client

    def _product(self):
        return Product(id="p1", name="test", product_id="com.test", product_type="CONSUMABLE")

    def test_skips_invalid_price_values(self):
        """Invalid float values in price points should be skipped, not crash."""
        client = self._make_client()
        client._get_all_pages.return_value = ([
            {"id": _price_point_id("USA"), "attributes": {"customerPrice": "4.99"}},
            {"id": _price_point_id("USA"), "attributes": {"customerPrice": "not_a_number"}},
            {"id": _price_point_id("USA"), "attributes": {"customerPrice": "9.99"}},
        ], [])

        points = client.fetch_usd_price_points(self._product())
        assert [p.customer_price for p in points] == [4.99, 9.99]

    def test_skips_none_price(self):
        """Price points without customerPrice should be skipped."""
        client = self._make_client()
        client._get_all_pages.return_value = ([
            {"id": _price_point_id("USA"), "attributes": {"customerPrice": "4.99"}},
            {"id": _price_point_id("USA"), "attributes": {}},
        ], [])

        assert len(client.fetch_usd_price_points(self._product())) == 1

    def test_groups_by_territory_and_sorts(self):
        client = self._make_client()
        client._get_all_pages.return_value = ([
            {"id": _price_point_id("CHE"), "attributes": {"customerPrice": "6.00"}},
            {"id": _price_point_id("CHE"), "attributes": {"customerPrice": "5.50"}},
            {"id": _price_point_id("NOR"), "attributes": {"customerPrice": "87"}},
        ], [])

        grids = client.fetch_territory_price_points(self._product(), ["CHE", "NOR"])
        assert [p.customer_price for p in grids["CHE"]] == [5.50, 6.00]
        assert [p.customer_price for p in grids["NOR"]] == [87.0]

    def test_batches_territories_into_few_requests(self):
        """175 territories must not become 175 requests."""
        client = self._make_client()
        client._get_all_pages.return_value = ([], [])

        client.fetch_territory_price_points(self._product(), [f"T{i:03d}" for i in range(175)])

        assert client._get_all_pages.call_count == 22
        first_batch = client._get_all_pages.call_args_list[0].kwargs["params"]["filter[territory]"]
        assert len(first_batch.split(",")) == 8

    def test_survives_a_failed_batch(self):
        """One failing batch must not lose the territories fetched by the others."""
        client = self._make_client()
        client._get_all_pages.side_effect = [
            httpx.ReadTimeout("read timed out"),
            ([{"id": _price_point_id("NOR"), "attributes": {"customerPrice": "87"}}], []),
        ]

        grids = client.fetch_territory_price_points(self._product(), [f"T{i:02d}" for i in range(16)])
        assert "NOR" in grids


class TestFetchAllEqualizations:
    def _make_client(self):
        client = MagicMock()
        client.fetch_all_equalizations = AppStoreConnectClient.fetch_all_equalizations.__get__(client)
        client._extract_territory = AppStoreConnectClient._extract_territory
        return client

    def test_returns_empty_on_timeout(self):
        """Timeout during equalization fetch should return empty dict."""
        client = self._make_client()
        product = Product(id="p1", name="test", product_id="com.test", product_type="CONSUMABLE")
        client._get_all_pages.side_effect = httpx.ReadTimeout("read timed out")

        result = client.fetch_all_equalizations(product, "usd_pp_1")
        assert result == {}

    def test_returns_empty_on_connect_error(self):
        """Connection error during equalization fetch should return empty dict."""
        client = self._make_client()
        product = Product(id="p1", name="test", product_id="com.test", product_type="CONSUMABLE")
        client._get_all_pages.side_effect = httpx.ConnectError("connection refused")

        result = client.fetch_all_equalizations(product, "usd_pp_1")
        assert result == {}


class TestSetSubscriptionPrice:
    def _make_client(self):
        client = MagicMock()
        client.set_subscription_price = AppStoreConnectClient.set_subscription_price.__get__(client)
        return client

    def _sent_attributes(self, client) -> dict:
        body = client._post.call_args[0][1]
        return body["data"]["attributes"]

    def test_defaults_change_existing_subscribers_in_two_days(self):
        """Without flags: preserveCurrentPrice=False, start in 2 days (legacy behavior)."""
        client = self._make_client()
        pp = PricePoint(id="pp1", customer_price=3.99, territory_3="DEU")

        client.set_subscription_price("sub_1", "DEU", pp)

        attrs = self._sent_attributes(client)
        assert attrs["preserveCurrentPrice"] is False
        assert attrs["startDate"] == (date.today() + timedelta(days=2)).isoformat()

    def test_preserved_keeps_current_subscribers_price(self):
        client = self._make_client()
        pp = PricePoint(id="pp1", customer_price=3.99, territory_3="DEU")

        client.set_subscription_price("sub_1", "DEU", pp, preserved=True)

        assert self._sent_attributes(client)["preserveCurrentPrice"] is True

    def test_custom_start_date_used_verbatim(self):
        client = self._make_client()
        pp = PricePoint(id="pp1", customer_price=3.99, territory_3="DEU")

        client.set_subscription_price("sub_1", "DEU", pp, start_date=date(2099, 1, 15))

        assert self._sent_attributes(client)["startDate"] == "2099-01-15"
