from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import httpx

from appstore_ppp_prices.ai_analyzer import analyze_app
from appstore_ppp_prices.appstore import AppStoreConnectClient, Product, PricePoint
from appstore_ppp_prices.countries import load_countries
from appstore_ppp_prices.display import status, find_price_point
from appstore_ppp_prices.pricing import TargetPrice, calculate_target_prices

log = logging.getLogger(__name__)


def find_product(all_products: list[Product], product_id: str) -> Product:
    """Find product by product_id or exit with error."""
    product = next((p for p in all_products if p.product_id == product_id), None)
    if not product:
        print(f"Error: Product ID '{product_id}' not found.")
        print("Available product IDs:")
        for p in all_products:
            print(f"  [{'SUB' if p.is_subscription else 'IAP'}] {p.product_id}")
        sys.exit(1)
    return product


def run_ai_analysis(
    openai_key: str | None,
    skip_ai: bool,
    app_name: str,
    all_products_with_prices: list[dict],
    category: str = "",
    subtitle: str = "",
) -> dict[str, float] | None:
    """Run AI analysis for the whole app. Returns coefficients dict or None.

    all_products_with_prices: [{"name": str, "product_id": str, "us_price": float}, ...]
    Coefficients are per-app, not per-product — same multipliers apply to all IAPs/subs.
    """
    if not openai_key or skip_ai:
        status("\n[4/6] AI analysis skipped.")
        return None

    status("\n[4/6] Running AI analysis...")
    result = analyze_app(
        openai_key, app_name, all_products_with_prices,
        category=category, subtitle=subtitle,
    )
    if not result:
        status("  AI analysis failed, using default coefficients.")
        return None

    status(f"  App type: {result.app_type}")
    status(f"  Elasticity: {result.elasticity}")
    status(f"  Reasoning: {result.reasoning}")
    status("  Coefficients:")
    for cat, coeff in sorted(result.coefficients.items()):
        status(f"    {cat}: {coeff:.3f}")
    return result.coefficients


def calculate_targets(
    product: Product,
    us_price: float,
    exclude: str,
    ai_coefficients: dict[str, float] | None,
) -> list[TargetPrice]:
    """Load countries, calculate target prices for all territories."""
    exclude_countries = {c.strip().upper() for c in exclude.split(",") if c.strip()}
    try:
        countries = load_countries(exclude=exclude_countries)
    except FileNotFoundError:
        print("Error: countries.csv not found. Ensure it exists in the project root.")
        sys.exit(1)
    status(f"\n[5/6] Calculating prices for {len(countries)} countries...")
    if exclude_countries:
        status(f"  Excluded: {', '.join(sorted(exclude_countries))}")

    products_data = [{"id": product.id, "name": product.name, "product_id": product.product_id, "us_price": us_price}]
    target_prices = calculate_target_prices(products_data, countries, ai_coefficients)
    status(f"  {len(target_prices)} target prices calculated.")
    return target_prices


def resolve_territory_prices(
    client: AppStoreConnectClient,
    product: Product,
    target_prices: list[TargetPrice],
    us_point: PricePoint,
) -> tuple[dict[str, PricePoint], dict[str, PricePoint]]:
    """Pick a local price point per territory: Apple's own price for the US
    price, scaled by that country's coefficient.

    The scaling happens in the local currency, not in dollars. Equalizing a
    USD price point lands on a coarse subset of each territory's grid — CHF 5
    and CHF 6 with nothing between — so a coefficient applied in dollars
    arrives distorted. Returns (chosen points, Apple's default points).
    """
    status("  Loading Apple's default territory prices...")
    baselines = client.fetch_all_equalizations(product, us_point.id)
    if not baselines:
        print("Error: Could not load Apple's territory prices for the US price.")
        sys.exit(1)

    codes = [t.country_code for t in target_prices]
    status(f"  Loading local price points for {len(codes)} territories...")
    grids = client.fetch_territory_price_points(product, codes)
    status(f"  {sum(len(g) for g in grids.values())} local price points loaded.")

    territory_prices: dict[str, PricePoint] = {}
    for target in target_prices:
        base = baselines.get(target.country_code)
        grid = grids.get(target.country_code)
        if not base or not grid:
            log.warning("No local price grid for %s, skipping", target.country_code)
            continue
        local_target = base.customer_price * target.coefficient
        point = find_price_point(grid, local_target, base.customer_price)
        if point:
            territory_prices[target.country_code] = point

    status(f"  {len(territory_prices)} territory price points resolved.")
    return territory_prices, baselines


def apply_prices(client: AppStoreConnectClient, product: Product, territory_prices: dict[str, PricePoint],
                 preserved: bool = False, start_date: date | None = None):
    """Apply resolved prices to the App Store."""
    status(f"\n  Applying prices for {product.name}...")

    if not product.is_subscription:
        status(f"    Sending {len(territory_prices)} territory prices (single request)...")
        client.set_iap_prices(product.id, territory_prices)
        status(f"  Done: prices applied for {product.name}.")
        return

    start_label = start_date.isoformat() if start_date else "in 2 days (default)"
    status(f"    Start date: {start_label} | keep current price for existing subscribers: {preserved}")
    status("    Clearing pending price changes...")
    deleted = client.delete_pending_subscription_prices(product.id)
    if deleted:
        status(f"    Deleted {deleted} pending price(s).")

    total = len(territory_prices)
    applied = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {
            pool.submit(client.set_subscription_price, product.id, t, pp,
                        preserved=preserved, start_date=start_date): t
            for t, pp in territory_prices.items()
        }
        for future in as_completed(futures):
            territory = futures[future]
            try:
                future.result()
                applied += 1
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError, OSError) as e:
                failed += 1
                log.warning("Failed %s in %s: %s", product.name, territory, e)
            done = applied + failed
            if done % 20 == 0 or done == total:
                status(f"    {done}/{total} territories ({failed} failed)")

    status(f"\n  Done: {applied}/{total} territory prices applied.")
    if failed:
        status(f"  {failed} territories failed (see warnings above).")
    if applied == 0 and total > 0:
        print("Error: All territory price updates failed.")
        sys.exit(1)
