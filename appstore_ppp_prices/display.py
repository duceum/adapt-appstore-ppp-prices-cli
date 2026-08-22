from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from appstore_ppp_prices.appstore import AppStoreConnectClient, Product, PricePoint
from appstore_ppp_prices.pricing import TargetPrice


def status(msg: str):
    print(msg, flush=True)


def find_price_point(points: list[PricePoint], target: float, base: float) -> PricePoint | None:
    """Pick the price point closest to `target`, rounding away from `base`.

    All three arguments are in the same currency — dollars when resolving the
    US price, the local currency everywhere else. An exact point always wins.
    Otherwise a target above the base price rounds up and one below it rounds
    down, so a market priced above the base never slips under its target and a
    discounted one never creeps over it. Falls back to the nearest point when
    the chosen direction holds none.
    """
    if not points:
        return None
    exact = next((p for p in points if abs(p.customer_price - target) < 0.005), None)
    if exact:
        return exact
    if target > base:
        higher = [p for p in points if p.customer_price > target]
        if higher:
            return min(higher, key=lambda p: p.customer_price)
    elif target < base:
        lower = [p for p in points if p.customer_price < target]
        if lower:
            return max(lower, key=lambda p: p.customer_price)
    return min(points, key=lambda p: abs(p.customer_price - target))


def list_products(client: AppStoreConnectClient, app_id: str, all_products: list[Product], app_name: str):
    """Print a table of all products with their US prices, fetched in parallel."""
    status(f"\nAvailable products for {app_name}:\n")
    status(f"  {'#':<4} {'Type':<5} {'Product ID':<35} {'Name':<30} {'US Price':>8}")
    status(f"  {'-'*4} {'-'*5} {'-'*35} {'-'*30} {'-'*8}")

    rows: dict[int, str] = {}
    next_row = 1
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(client.fetch_us_price, p): (idx, p) for idx, p in enumerate(all_products, 1)}
        for future in as_completed(futures):
            idx, p = futures[future]
            try:
                us_price = future.result()
            except Exception:
                us_price = None
            label = "SUB" if p.is_subscription else "IAP"
            price_str = f"${us_price:.2f}" if us_price is not None else "N/A"
            rows[idx] = f"  {idx:<4} [{label}] {p.product_id:<35} {p.name:<30} {price_str:>8}"
            while next_row in rows:
                status(rows.pop(next_row))
                next_row += 1

    status(f"\nTo process a product, run:")
    status(f"  ppp-pricing --app-id {app_id} --iap <PRODUCT_ID> --dry-run")


def format_local_price(amount: float, currency: str) -> str:
    """1234.0 JPY -> '1,234 JPY'; 5.5 CHF -> '5.50 CHF'."""
    text = f"{amount:,.0f}" if amount == int(amount) and amount >= 100 else f"{amount:,.2f}"
    return f"{text} {currency}".strip()


def print_dry_run_table(
    results: list[TargetPrice],
    iap_name: str,
    territory_prices: dict[str, PricePoint],
    baselines: dict[str, PricePoint],
    currencies: dict[str, str],
):
    """Print every territory's new price next to what Apple charges by default."""
    us_price = results[0].us_price
    status(f"\n{'=' * 82}")
    status(f"  {iap_name}  (US: ${us_price:.2f})")
    status(f"{'=' * 82}")
    status(f"  {'Country':<30} {'Coeff':>6} {'Apple default':>17} {'PPP price':>17} {'Change':>7}")
    status(f"  {'-' * 30} {'-' * 6} {'-' * 17} {'-' * 17} {'-' * 7}")
    for p in sorted(results, key=lambda x: x.country_name):
        point = territory_prices.get(p.country_code)
        base = baselines.get(p.country_code)
        currency = currencies.get(p.country_code, "")
        if not point or not base or not base.customer_price:
            status(f"  {p.country_name:<30} {p.coefficient:>6.3f} {'n/a':>17} {'n/a':>17} {'':>7}")
            continue
        change = (point.customer_price / base.customer_price - 1) * 100
        status(f"  {p.country_name:<30} {p.coefficient:>6.3f} "
               f"{format_local_price(base.customer_price, currency):>17} "
               f"{format_local_price(point.customer_price, currency):>17} {change:>+6.1f}%")
