from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.appstore import AppStoreConnectClient, Product, PricePoint
from src.pricing import TargetPrice


def status(msg: str):
    print(msg, flush=True)


def find_closest_price_point(points: list[PricePoint], target_usd: float) -> PricePoint | None:
    if not points:
        return None
    return min(points, key=lambda p: abs(p.customer_price - target_usd))


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
    status(f"  adapt-prices-bot --app-id {app_id} --iap <PRODUCT_ID> --dry-run")


def print_dry_run_table(
    results: list[TargetPrice],
    iap_name: str,
    usd_tiers: list[PricePoint],
    us_price_override: PricePoint | None = None,
):
    us_price = results[0].us_price
    status(f"\n{'=' * 78}")
    status(f"  {iap_name}  (US: ${us_price:.2f})")
    status(f"{'=' * 78}")
    status(f"  {'Country':<35} {'Coeff':>6} {'Target':>8} {'Apple Tier':>10}")
    status(f"  {'-' * 35} {'-' * 6} {'-' * 8} {'-' * 10}")
    if us_price_override:
        status(f"  {'United States (override)':<35} {'1.000':>6} ${us_price:>6.2f} ${us_price_override.customer_price:>8.2f}")
    for p in sorted(results, key=lambda x: x.country_name):
        tier = find_closest_price_point(usd_tiers, p.target_price_usd)
        tier_str = f"${tier.customer_price:>8.2f}" if tier else "     N/A"
        status(f"  {p.country_name:<35} {p.coefficient:>6.3f} ${p.target_price_usd:>6.2f} {tier_str}")
