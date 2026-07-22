from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import httpx
import jwt

log = logging.getLogger(__name__)

BASE_URL = "https://api.appstoreconnect.apple.com"
TOKEN_LIFETIME = 1200  # 20 minutes
REQUEST_TIMEOUT = int(os.getenv("ASC_REQUEST_TIMEOUT", "30"))


@dataclass
class AppInfo:
    id: str
    name: str
    bundle_id: str
    category: str = ""
    subtitle: str = ""


@dataclass
class Product:
    """Represents either an in-app purchase or a subscription."""
    id: str
    name: str
    product_id: str
    product_type: str
    is_subscription: bool = False


@dataclass
class PricePoint:
    id: str
    customer_price: float
    territory_3: str  # 3-letter code


class AppStoreConnectClient:
    def __init__(self, key_id: str, issuer_id: str, private_key_path: Path):
        self._key_id = key_id
        self._issuer_id = issuer_id
        self._private_key = private_key_path.read_text()
        self._token: str | None = None
        self._token_expiry: float = 0
        self._token_lock = threading.Lock()
        self._client = httpx.Client(timeout=REQUEST_TIMEOUT)

    def _generate_token(self) -> str:
        now = int(time.time())
        payload = {
            "iss": self._issuer_id,
            "iat": now,
            "exp": now + TOKEN_LIFETIME,
            "aud": "appstoreconnect-v1",
        }
        return jwt.encode(payload, self._private_key, algorithm="ES256", headers={"kid": self._key_id})

    @property
    def token(self) -> str:
        with self._token_lock:
            if not self._token or time.time() >= self._token_expiry - 60:
                self._token = self._generate_token()
                self._token_expiry = time.time() + TOKEN_LIFETIME
            return self._token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _check_response(self, resp: httpx.Response, context: str) -> None:
        if resp.status_code >= 400:
            log.debug("API %s %s: %s", resp.status_code, context, resp.text[:500])
        resp.raise_for_status()

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{BASE_URL}{path}"
        resp = self._client.get(url, headers=self._headers(), params=params)
        self._check_response(resp, path)
        return resp.json()

    def _get_all_pages(self, path: str, params: dict | None = None) -> tuple[list[dict], list[dict]]:
        """Fetch all pages. Returns (data, included)."""
        all_data: list[dict] = []
        all_included: list[dict] = []
        url = f"{BASE_URL}{path}"

        while url:
            resp = self._client.get(url, headers=self._headers(), params=params)
            self._check_response(resp, url)
            body = resp.json()
            all_data.extend(body.get("data", []))
            all_included.extend(body.get("included", []))
            url = body.get("links", {}).get("next")
            params = None  # next URL already contains query params

        return all_data, all_included

    def _post(self, path: str, body: dict) -> dict:
        url = f"{BASE_URL}{path}"
        resp = self._client.post(url, headers=self._headers(), json=body)
        self._check_response(resp, f"POST {path}")
        return resp.json()

    # ── App info ──

    def fetch_app_info(self, app_id: str) -> AppInfo:
        data = self._get(f"/v1/apps/{app_id}", params={"fields[apps]": "name,bundleId"})
        attrs = data["data"]["attributes"]
        info = AppInfo(id=app_id, name=attrs.get("name", ""), bundle_id=attrs.get("bundleId", ""))

        # Fetch category and subtitle from appInfos
        try:
            ai_data, ai_included = self._get_all_pages(
                f"/v1/apps/{app_id}/appInfos",
                params={"include": "primaryCategory", "fields[appCategories]": "name", "limit": "1"},
            )
            if ai_included:
                for inc in ai_included:
                    if inc.get("type") == "appCategories":
                        info.category = inc.get("attributes", {}).get("name", "")
                        break
            if ai_data:
                app_info_id = ai_data[0]["id"]
                loc_data, _ = self._get_all_pages(
                    f"/v1/appInfos/{app_info_id}/appInfoLocalizations",
                    params={"fields[appInfoLocalizations]": "subtitle", "limit": "1"},
                )
                if loc_data:
                    info.subtitle = loc_data[0].get("attributes", {}).get("subtitle") or ""
        except Exception:
            pass  # Category/subtitle are optional enrichments

        return info

    # ── Fetch all purchasable items (IAPs + subscriptions) ──

    def fetch_all_products(self, app_id: str) -> list[Product]:
        """Fetch both consumable/non-consumable IAPs (v2) and subscriptions."""
        products: list[Product] = []

        iap_data, _ = self._get_all_pages(f"/v1/apps/{app_id}/inAppPurchasesV2", params={"limit": "200"})
        for entry in iap_data:
            attrs = entry.get("attributes", {})
            product_type = attrs.get("inAppPurchaseType", "")
            if product_type == "AUTOMATICALLY_RENEWABLE_SUBSCRIPTION":
                continue
            products.append(Product(
                id=entry["id"], name=attrs.get("name", ""),
                product_id=attrs.get("productId", ""), product_type=product_type,
            ))

        groups_data, _ = self._get_all_pages(f"/v1/apps/{app_id}/subscriptionGroups")
        for group in groups_data:
            subs_data, _ = self._get_all_pages(
                f"/v1/subscriptionGroups/{group['id']}/subscriptions", params={"limit": "200"},
            )
            for sub in subs_data:
                attrs = sub.get("attributes", {})
                products.append(Product(
                    id=sub["id"], name=attrs.get("name", ""),
                    product_id=attrs.get("productId", ""),
                    product_type="AUTOMATICALLY_RENEWABLE_SUBSCRIPTION", is_subscription=True,
                ))

        return products

    # ── Price points ──

    def fetch_usd_price_points(self, product: Product) -> list[PricePoint]:
        """Fetch all USD (USA territory) price points for a product."""
        path = (f"/v1/subscriptions/{product.id}/pricePoints" if product.is_subscription
                else f"/v2/inAppPurchases/{product.id}/pricePoints")
        data, _ = self._get_all_pages(path, params={"filter[territory]": "USA", "limit": "200"})

        points: list[PricePoint] = []
        for pp in data:
            price = pp.get("attributes", {}).get("customerPrice")
            if price is None:
                continue
            try:
                points.append(PricePoint(id=pp["id"], customer_price=float(price), territory_3="USA"))
            except (ValueError, TypeError):
                log.warning("Skipping price point %s: invalid price %r", pp.get("id"), price)
        return sorted(points, key=lambda p: p.customer_price)

    def fetch_all_equalizations(self, product: Product, usd_price_point_id: str) -> dict[str, PricePoint]:
        """Get equalized price points for ALL territories from a USD base price."""
        path = (f"/v1/subscriptionPricePoints/{usd_price_point_id}/equalizations" if product.is_subscription
                else f"/v1/inAppPurchasePricePoints/{usd_price_point_id}/equalizations")
        try:
            data, _ = self._get_all_pages(path, params={"limit": "200"})
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as e:
            log.warning("Failed to fetch equalizations for %s: %s", usd_price_point_id, e)
            return {}

        result: dict[str, PricePoint] = {}
        for pp in data:
            price = pp.get("attributes", {}).get("customerPrice")
            terr = self._extract_territory(pp["id"])
            if price is None or not terr:
                continue
            try:
                result[terr] = PricePoint(id=pp["id"], customer_price=float(price), territory_3=terr)
            except (ValueError, TypeError):
                log.warning("Skipping equalization %s: invalid price %r", pp.get("id"), price)
        return result

    @staticmethod
    def _extract_territory(price_point_id: str) -> str:
        """Decode territory from base64-encoded price point ID."""
        try:
            decoded = base64.b64decode(price_point_id + "==").decode("utf-8")
            return json.loads(decoded).get("t", "")
        except Exception:
            return ""

    def fetch_us_price(self, product: Product) -> float | None:
        """Get the current US price for a product."""
        if product.is_subscription:
            return self._fetch_us_price_subscription(product.id)
        return self._fetch_us_price_iap(product.id)

    def _fetch_us_price_iap(self, iap_id: str) -> float | None:
        """Get US price for a consumable/non-consumable IAP."""
        try:
            data, included = self._get_all_pages(
                f"/v1/inAppPurchasePriceSchedules/{iap_id}/manualPrices",
                params={
                    "include": "inAppPurchasePricePoint",
                    "fields[inAppPurchasePricePoints]": "customerPrice",
                },
            )
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError):
            return None

        pp_map = {inc["id"]: inc for inc in included if inc.get("type") == "inAppPurchasePricePoints"}

        for price in data:
            if price.get("attributes", {}).get("startDate") is not None:
                continue
            pp_id = (price.get("relationships", {})
                     .get("inAppPurchasePricePoint", {}).get("data", {}).get("id", ""))
            if self._extract_territory(pp_id) == "USA":
                pp = pp_map.get(pp_id)
                if pp:
                    return float(pp["attributes"]["customerPrice"])
        return None

    def _fetch_us_price_subscription(self, sub_id: str) -> float | None:
        """Get US price for a subscription."""
        try:
            data, included = self._get_all_pages(
                f"/v1/subscriptions/{sub_id}/prices",
                params={
                    "include": "subscriptionPricePoint,territory",
                    "fields[subscriptionPricePoints]": "customerPrice",
                    "fields[territories]": "currency",
                    "limit": "200",
                },
            )
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError):
            return None

        pp_map = {inc["id"]: inc for inc in included if inc.get("type") == "subscriptionPricePoints"}

        for price in data:
            terr_id = (price.get("relationships", {})
                       .get("territory", {}).get("data", {}).get("id", ""))
            if terr_id != "USA":
                continue
            pp_id = (price.get("relationships", {})
                     .get("subscriptionPricePoint", {}).get("data", {}).get("id", ""))
            pp = pp_map.get(pp_id)
            if pp:
                return float(pp["attributes"]["customerPrice"])
        return None

    # ── Set prices ──

    def set_iap_prices(self, iap_id: str, price_points: dict[str, PricePoint]) -> dict:
        """Set prices for a consumable/non-consumable product (single atomic request)."""
        manual_prices_refs = []
        included = []

        for i, (territory, point) in enumerate(price_points.items()):
            temp_id = f"${{price{i}}}"
            manual_prices_refs.append({"type": "inAppPurchasePrices", "id": temp_id})
            included.append({
                "type": "inAppPurchasePrices",
                "id": temp_id,
                "attributes": {"startDate": None},
                "relationships": {
                    "inAppPurchaseV2": {"data": {"type": "inAppPurchases", "id": iap_id}},
                    "inAppPurchasePricePoint": {"data": {"type": "inAppPurchasePricePoints", "id": point.id}},
                },
            })

        body = {
            "data": {
                "type": "inAppPurchasePriceSchedules",
                "relationships": {
                    "inAppPurchase": {"data": {"type": "inAppPurchases", "id": iap_id}},
                    "baseTerritory": {"data": {"type": "territories", "id": "USA"}},
                    "manualPrices": {"data": manual_prices_refs},
                },
            },
            "included": included,
        }
        return self._post("/v1/inAppPurchasePriceSchedules", body)

    def delete_pending_subscription_prices(self, sub_id: str) -> int:
        """Delete all future (pending) subscription prices to avoid 409 conflicts."""
        today = date.today().isoformat()
        data, _ = self._get_all_pages(f"/v1/subscriptions/{sub_id}/prices", params={"limit": "200"})

        deleted = 0
        for price in data:
            start = price.get("attributes", {}).get("startDate")
            if start and start >= today:
                url = f"{BASE_URL}/v1/subscriptionPrices/{price['id']}"
                try:
                    resp = self._client.delete(url, headers=self._headers())
                    if resp.status_code == 204:
                        deleted += 1
                    else:
                        log.warning("Failed to delete pending price %s: HTTP %s", price["id"], resp.status_code)
                except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as e:
                    log.warning("Failed to delete pending price %s: %s", price["id"], e)
        return deleted

    def set_subscription_price(self, sub_id: str, territory_3: str, price_point: PricePoint,
                               preserved: bool = False, start_date: date | None = None) -> dict:
        """Set price for a subscription in a specific territory.

        preserved: keep the current price for existing subscribers.
        start_date: when the new price takes effect (default: 2 days from now).
        """
        start = (start_date or date.today() + timedelta(days=2)).isoformat()
        body = {
            "data": {
                "type": "subscriptionPrices",
                "attributes": {"preserveCurrentPrice": preserved, "startDate": start},
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": price_point.id}},
                    "territory": {"data": {"type": "territories", "id": territory_3}},
                },
            },
        }
        return self._post("/v1/subscriptionPrices", body)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._client.close()
