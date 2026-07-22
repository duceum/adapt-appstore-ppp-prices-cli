from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
import httpx

from src.appstore import AppStoreConnectClient, Product
from src.display import status, find_closest_price_point, list_products, print_dry_run_table
from src.pipeline import (
    apply_prices,
    calculate_targets,
    find_product,
    resolve_territory_prices,
    run_ai_analysis,
)

DESCRIPTION = """\
Automated regional pricing for App Store in-app purchases and subscriptions.

Usage:
  1. List all products:  adapt-prices-bot --app-id ID
  2. Preview prices:     adapt-prices-bot --app-id ID --iap PRODUCT_ID --dry-run
  3. Apply prices:       adapt-prices-bot --app-id ID --iap PRODUCT_ID
  4. Clear AI cache:     adapt-prices-bot --clear-cache

Setup:
  1. Create an API key at https://appstoreconnect.apple.com/access/api
  2. Download the .p8 private key file
  3. Create a .env file (or use --config to point to a directory):
       ASC_KEY_ID=YOUR_KEY_ID
       ASC_ISSUER_ID=YOUR_ISSUER_ID
       ASC_PRIVATE_KEY_PATH=AuthKey_XXXX.p8
       OPENAI_API_KEY=sk-...  (optional, enables AI analysis)

Examples:
  adapt-prices-bot --app-id 123456789
  adapt-prices-bot --app-id 123456789 --iap com.app.weekly --dry-run
  adapt-prices-bot --app-id 123456789 --iap com.app.weekly
  adapt-prices-bot --app-id 123456789 --iap com.app.weekly --us-price 5.99 --dry-run
  adapt-prices-bot --app-id 123456789 --iap com.app.weekly --no-ai --dry-run
  adapt-prices-bot --app-id 123456789 --iap com.app.weekly --coeff emerging=0.70
  adapt-prices-bot --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
  adapt-prices-bot --app-id 123456789 --iap com.app.weekly --preserved --start-date 2026-08-01
  adapt-prices-bot --app-id 123456789 --iap com.app.weekly --config ~/keys/
  adapt-prices-bot --clear-cache
"""


VALID_CATEGORIES = frozenset({"premium", "high_income", "upper_middle", "lower_middle", "emerging"})


def _positive_float(value: str) -> float:
    try:
        result = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid number")
    if result <= 0:
        raise argparse.ArgumentTypeError(f"price must be positive, got {result}")
    return result


def _future_date(value: str) -> date:
    try:
        result = date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid date (expected YYYY-MM-DD)")
    if result <= date.today():
        raise argparse.ArgumentTypeError(f"start date must be in the future, got {value}")
    return result


def parse_coefficients(raw: list[str] | None) -> dict[str, float]:
    """Parse --coeff arguments like 'emerging=0.70' into a dict."""
    if not raw:
        return {}
    result: dict[str, float] = {}
    for item in raw:
        if "=" not in item:
            raise argparse.ArgumentTypeError(
                f"Invalid coefficient format: '{item}'. Expected category=value (e.g. emerging=0.70)")
        cat, val_str = item.split("=", 1)
        cat = cat.strip().lower()
        if cat not in VALID_CATEGORIES:
            raise argparse.ArgumentTypeError(
                f"Unknown category '{cat}'. Valid: {', '.join(sorted(VALID_CATEGORIES))}")
        try:
            val = float(val_str.strip())
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid coefficient value: '{val_str}'")
        if not 0.1 <= val <= 2.0:
            raise argparse.ArgumentTypeError(f"Coefficient {val} out of range [0.1, 2.0]")
        result[cat] = round(val, 3)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adapt-prices-bot",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--app-id", help="App Store app ID (required unless --clear-cache)")
    parser.add_argument("--iap", metavar="PRODUCT_ID", help="Product ID to process (omit to list all)")
    parser.add_argument("--us-price", type=_positive_float, help="Override US price (also sets new USA price on apply)")
    parser.add_argument("--dry-run", action="store_true", help="Show calculated prices without applying")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI analysis")
    parser.add_argument("--coeff", action="append", metavar="CAT=VAL",
                        help="Override coefficient for a category (e.g. --coeff emerging=0.70). Can be repeated.")
    parser.add_argument("--exclude", type=str, default="", help="Exclude countries (e.g. RUS,BLR,IRN)")
    parser.add_argument("--preserved", action="store_true",
                        help="Keep the current price for existing subscribers (subscriptions only)")
    parser.add_argument("--start-date", type=_future_date, metavar="YYYY-MM-DD",
                        help="Date the new prices take effect (subscriptions only; default: 2 days from now)")
    parser.add_argument("--clear-cache", action="store_true", help="Delete all cached AI analysis results and exit")
    project_root = str(Path(__file__).resolve().parent.parent)
    parser.add_argument("--config", type=str, default=project_root, help="Config directory with .env and .p8 key")
    return parser


def validate_subscription_flags(product: Product, preserved: bool, start_date: date | None) -> None:
    """--preserved and --start-date only make sense for subscriptions; fail fast otherwise."""
    if not product.is_subscription and (preserved or start_date):
        print(f"Error: --preserved and --start-date apply only to subscriptions; "
              f"'{product.product_id}' is not a subscription.")
        sys.exit(1)


def load_config(config_dir: Path) -> tuple[str, str, Path, str | None]:
    """Load .env and validate App Store Connect credentials."""
    env_path = config_dir / ".env"
    load_dotenv(env_path if env_path.exists() else None)

    key_id = os.getenv("ASC_KEY_ID")
    issuer_id = os.getenv("ASC_ISSUER_ID")
    pk_path_str = os.getenv("ASC_PRIVATE_KEY_PATH")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not all([key_id, issuer_id, pk_path_str]):
        print("Error: Missing App Store Connect credentials.")
        print("Set ASC_KEY_ID, ASC_ISSUER_ID, ASC_PRIVATE_KEY_PATH in .env")
        print(f"Looked in: {env_path}")
        sys.exit(1)

    pk_path = Path(pk_path_str)
    if not pk_path.is_absolute():
        pk_path = config_dir / pk_path
    if not pk_path.exists():
        print(f"Error: Private key not found: {pk_path}")
        sys.exit(1)

    return key_id, issuer_id, pk_path, openai_key


def _extract_api_error(exc: httpx.HTTPStatusError):
    """Print a clean error message from an App Store Connect API error and exit."""
    try:
        resp = getattr(exc, "response", None)
        errors = resp.json().get("errors", []) if resp is not None else []
        detail = errors[0]["detail"] if errors else str(exc)
    except Exception:
        detail = str(exc)
    print(f"Error: {detail}")
    sys.exit(1)


def main():
    args = build_parser().parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    if args.clear_cache:
        from src.ai_analyzer import clear_cache
        removed = clear_cache()
        print(f"Cleared {removed} cached AI result(s).")
        return

    if not args.app_id:
        build_parser().error("the following arguments are required: --app-id")

    config_dir = Path(args.config).expanduser().resolve()
    key_id, issuer_id, pk_path, openai_key = load_config(config_dir)
    try:
        client = AppStoreConnectClient(key_id, issuer_id, pk_path)
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error: Cannot read private key file {pk_path}: {e}")
        sys.exit(1)

    try:
        with client:
            status(f"\n[1/6] Fetching app info for {args.app_id}...")
            app_info = client.fetch_app_info(args.app_id)
            status(f"  App: {app_info.name} ({app_info.bundle_id})")
            if app_info.category:
                status(f"  Category: {app_info.category}")
            if app_info.subtitle:
                status(f"  Subtitle: {app_info.subtitle}")

            status("\n[2/6] Fetching all IAPs and subscriptions...")
            all_products = client.fetch_all_products(args.app_id)
            status(f"  Found {len(all_products)} product(s)")

            if not args.iap:
                list_products(client, args.app_id, all_products, app_info.name)
                return

            product = find_product(all_products, args.iap)
            label = "Subscription" if product.is_subscription else "In-App Purchase"
            status(f"\n  Selected: [{label}] {product.name} ({product.product_id})")
            validate_subscription_flags(product, args.preserved, args.start_date)

            status("\n[3/6] Fetching US price...")
            if args.us_price is not None:
                us_price = args.us_price
                status(f"  US price: ${us_price:.2f} (override)")
            else:
                us_price = client.fetch_us_price(product)
                if us_price is None:
                    print(f"Error: Could not fetch US price for {product.product_id}")
                    sys.exit(1)
                status(f"  US price: ${us_price:.2f}")

            # Fetch all product prices only when AI is enabled and cache is empty
            all_products_with_prices: list[dict] = []
            ai_enabled = openai_key and not args.no_ai
            if ai_enabled:
                from src.ai_analyzer import _load_cache
                if not _load_cache(app_info.name):
                    status("  Loading all product prices for AI context...")
                    for p in all_products:
                        p_price = us_price if p.product_id == product.product_id else client.fetch_us_price(p)
                        if p_price is not None:
                            all_products_with_prices.append(
                                {"name": p.name, "product_id": p.product_id, "us_price": p_price}
                            )
                    status(f"  {len(all_products_with_prices)} product price(s) loaded.")

            ai_coefficients = run_ai_analysis(
                openai_key, args.no_ai, app_info.name, all_products_with_prices,
                category=app_info.category, subtitle=app_info.subtitle,
            )

            try:
                manual_coefficients = parse_coefficients(args.coeff)
            except argparse.ArgumentTypeError as e:
                print(f"Error: {e}")
                sys.exit(1)

            if manual_coefficients:
                if ai_coefficients is None:
                    ai_coefficients = {}
                ai_coefficients.update(manual_coefficients)
                status("  Manual coefficient overrides:")
                for cat, val in sorted(manual_coefficients.items()):
                    status(f"    {cat}: {val:.3f}")

            target_prices = calculate_targets(product, us_price, args.exclude, ai_coefficients)

            status("\n[6/6] Loading Apple price tiers...")
            usd_points = client.fetch_usd_price_points(product)
            status(f"  {len(usd_points)} USD price tiers loaded.")
            if not usd_points:
                print("Error: No USD price points available for this product.")
                sys.exit(1)

            territory_prices = resolve_territory_prices(client, product, target_prices, usd_points)
            if not territory_prices:
                print("Error: No territory price points could be resolved.")
                sys.exit(1)

            us_tier = find_closest_price_point(usd_points, us_price)
            if not us_tier:
                print("Error: No matching Apple price tier for US price.")
                sys.exit(1)
            territory_prices["USA"] = us_tier
            if args.us_price is not None:
                status(f"  USA price: ${us_tier.customer_price:.2f} (nearest Apple tier)")

            if args.dry_run:
                print_dry_run_table(target_prices, f"{product.name} ({product.product_id})", usd_points,
                                    us_price_override=territory_prices.get("USA"))
                status(f"\n  Dry run complete. {len(target_prices)} prices calculated.")
                status("  Remove --dry-run to apply.")
                return

            apply_prices(client, product, territory_prices,
                         preserved=args.preserved, start_date=args.start_date)

    except httpx.HTTPStatusError as e:
        _extract_api_error(e)
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        print(f"Error: Cannot connect to App Store Connect API: {e}")
        sys.exit(1)
    except httpx.TimeoutException as e:
        print(f"Error: Request timed out: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
