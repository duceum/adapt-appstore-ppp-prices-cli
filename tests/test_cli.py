import argparse
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from appstore_ppp_prices import __version__
from appstore_ppp_prices.appstore import Product
from appstore_ppp_prices.cli import (
    VALID_CATEGORIES,
    _extract_api_error,
    _positive_float,
    build_parser,
    load_config,
    main,
    parse_coefficients,
    validate_subscription_flags,
)


class TestPositiveFloat:
    def test_valid_price(self):
        assert _positive_float("5.99") == 5.99

    def test_valid_integer(self):
        assert _positive_float("10") == 10.0

    def test_rejects_zero(self):
        with pytest.raises(argparse.ArgumentTypeError, match="positive"):
            _positive_float("0")

    def test_rejects_negative(self):
        with pytest.raises(argparse.ArgumentTypeError, match="positive"):
            _positive_float("-1.5")

    def test_rejects_text(self):
        with pytest.raises(argparse.ArgumentTypeError, match="not a valid number"):
            _positive_float("abc")

    def test_rejects_empty(self):
        with pytest.raises(argparse.ArgumentTypeError, match="not a valid number"):
            _positive_float("")


class TestBuildParser:
    def test_us_price_parsed(self):
        parser = build_parser()
        args = parser.parse_args(["--app-id", "123", "--iap", "weekly", "--us-price", "5.99"])
        assert args.us_price == 5.99

    def test_us_price_defaults_to_none(self):
        parser = build_parser()
        args = parser.parse_args(["--app-id", "123"])
        assert args.us_price is None

    def test_us_price_rejects_bad_value(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--app-id", "123", "--us-price", "abc"])

    def test_coeff_single(self):
        parser = build_parser()
        args = parser.parse_args(["--app-id", "123", "--iap", "w", "--coeff", "emerging=0.70"])
        assert args.coeff == ["emerging=0.70"]

    def test_coeff_multiple(self):
        parser = build_parser()
        args = parser.parse_args([
            "--app-id", "123", "--iap", "w",
            "--coeff", "emerging=0.70", "--coeff", "lower_middle=0.60",
        ])
        assert args.coeff == ["emerging=0.70", "lower_middle=0.60"]

    def test_coeff_defaults_to_none(self):
        parser = build_parser()
        args = parser.parse_args(["--app-id", "123"])
        assert args.coeff is None


class TestParseCoefficients:
    def test_single_coefficient(self):
        assert parse_coefficients(["emerging=0.70"]) == {"emerging": 0.7}

    def test_multiple_coefficients(self):
        result = parse_coefficients(["emerging=0.70", "lower_middle=0.60"])
        assert result == {"emerging": 0.7, "lower_middle": 0.6}

    def test_none_returns_empty(self):
        assert parse_coefficients(None) == {}

    def test_empty_list_returns_empty(self):
        assert parse_coefficients([]) == {}

    def test_rejects_missing_equals(self):
        with pytest.raises(argparse.ArgumentTypeError, match="Expected category=value"):
            parse_coefficients(["emerging"])

    def test_rejects_unknown_category(self):
        with pytest.raises(argparse.ArgumentTypeError, match="Unknown category"):
            parse_coefficients(["unknown=0.5"])

    def test_rejects_non_numeric_value(self):
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid coefficient value"):
            parse_coefficients(["emerging=abc"])

    def test_rejects_too_low(self):
        with pytest.raises(argparse.ArgumentTypeError, match="out of range"):
            parse_coefficients(["emerging=0.05"])

    def test_rejects_too_high(self):
        with pytest.raises(argparse.ArgumentTypeError, match="out of range"):
            parse_coefficients(["emerging=3.0"])

    def test_all_valid_categories(self):
        for cat in VALID_CATEGORIES:
            result = parse_coefficients([f"{cat}=0.80"])
            assert result[cat] == 0.8

    def test_rounds_to_three_decimals(self):
        result = parse_coefficients(["emerging=0.6666"])
        assert result["emerging"] == 0.667

    def test_boundary_min(self):
        result = parse_coefficients(["emerging=0.1"])
        assert result["emerging"] == 0.1

    def test_boundary_max(self):
        result = parse_coefficients(["premium=2.0"])
        assert result["premium"] == 2.0

    def test_whitespace_around_equals(self):
        result = parse_coefficients(["emerging = 0.70"])
        assert result["emerging"] == 0.7

    def test_uppercase_category_normalized(self):
        result = parse_coefficients(["EMERGING=0.70"])
        assert result["emerging"] == 0.7

    def test_duplicate_category_last_wins(self):
        result = parse_coefficients(["emerging=0.50", "emerging=0.70"])
        assert result["emerging"] == 0.7

    def test_overrides_ai_coefficients(self):
        """Manual coefficients override only specified keys, rest untouched."""
        ai = {"premium": 1.10, "high_income": 0.90, "emerging": 0.55}
        manual = parse_coefficients(["emerging=0.70"])
        ai.update(manual)
        assert ai == {"premium": 1.10, "high_income": 0.90, "emerging": 0.70}

    def test_overrides_on_empty_ai(self):
        """Manual coefficients create dict when AI returned None."""
        ai = None
        manual = parse_coefficients(["emerging=0.70", "lower_middle=0.60"])
        if manual:
            if ai is None:
                ai = {}
            ai.update(manual)
        assert ai == {"emerging": 0.70, "lower_middle": 0.60}

    def test_no_override_preserves_none(self):
        """No --coeff keeps ai_coefficients unchanged."""
        ai = {"premium": 1.10, "emerging": 0.55}
        manual = parse_coefficients(None)
        if manual:
            ai.update(manual)
        assert ai == {"premium": 1.10, "emerging": 0.55}


class TestClearCacheFlag:
    def test_clears_cache_and_exits(self, capsys):
        with patch("appstore_ppp_prices.cli.build_parser") as mock_parser:
            mock_args = MagicMock()
            mock_args.clear_cache = True
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch("appstore_ppp_prices.ai_analyzer.clear_cache", return_value=3) as mock_clear:
                main()

            mock_clear.assert_called_once()
            assert "3" in capsys.readouterr().out

    def test_works_without_app_id(self):
        parser = build_parser()
        args = parser.parse_args(["--clear-cache"])
        assert args.clear_cache is True
        assert args.app_id is None


class TestLoadConfig:
    def test_exits_on_missing_credentials(self, tmp_path):
        """Missing ASC_KEY_ID/ASC_ISSUER_ID/ASC_PRIVATE_KEY_PATH exits cleanly."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(SystemExit):
                load_config(tmp_path)

    def test_exits_on_missing_p8_file(self, tmp_path):
        """Non-existent .p8 path exits cleanly."""
        env = {
            "ASC_KEY_ID": "key",
            "ASC_ISSUER_ID": "issuer",
            "ASC_PRIVATE_KEY_PATH": "nonexistent.p8",
        }
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(SystemExit):
                load_config(tmp_path)


class TestMainErrorHandling:
    """Test that main() catches various exceptions and exits cleanly."""

    def _run_main_with_error(self, error):
        """Helper: run main() where fetch_app_info raises the given error."""
        with patch("appstore_ppp_prices.cli.build_parser") as mock_parser, \
             patch("appstore_ppp_prices.cli.load_config") as mock_config, \
             patch("appstore_ppp_prices.cli.AppStoreConnectClient") as mock_client_cls:

            mock_args = MagicMock()
            mock_args.app_id = "123"
            mock_args.iap = "weekly"
            mock_args.config = "/tmp"
            mock_args.clear_cache = False
            mock_parser.return_value.parse_args.return_value = mock_args

            mock_config.return_value = ("key", "issuer", Path("/tmp/k.p8"), None)

            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.fetch_app_info.side_effect = error
            mock_client_cls.return_value = mock_client

            with pytest.raises(SystemExit):
                main()

    def test_handles_connect_error(self):
        self._run_main_with_error(httpx.ConnectError("connection refused"))

    def test_handles_connect_timeout(self):
        self._run_main_with_error(httpx.ConnectTimeout("timed out"))

    def test_handles_read_timeout(self):
        self._run_main_with_error(httpx.ReadTimeout("read timed out"))

    def test_handles_http_status_error(self):
        response = MagicMock()
        response.status_code = 401
        response.json.return_value = {"errors": [{"detail": "Unauthorized"}]}
        self._run_main_with_error(
            httpx.HTTPStatusError("401", request=MagicMock(), response=response)
        )

    def test_invalid_p8_key_exits_cleanly(self):
        """Binary/corrupt .p8 file gives clean error, not raw traceback."""
        with patch("appstore_ppp_prices.cli.build_parser") as mock_parser, \
             patch("appstore_ppp_prices.cli.load_config") as mock_config, \
             patch("appstore_ppp_prices.cli.AppStoreConnectClient") as mock_client_cls:

            mock_args = MagicMock()
            mock_args.app_id = "123"
            mock_args.config = "/tmp"
            mock_args.clear_cache = False
            mock_parser.return_value.parse_args.return_value = mock_args

            mock_config.return_value = ("key", "issuer", Path("/tmp/k.p8"), None)
            mock_client_cls.side_effect = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid")

            with pytest.raises(SystemExit):
                main()


class TestExtractApiError:
    def test_extracts_detail_from_response(self):
        response = MagicMock()
        response.json.return_value = {"errors": [{"detail": "Not Found"}]}
        exc = httpx.HTTPStatusError("404", request=MagicMock(), response=response)
        with pytest.raises(SystemExit):
            _extract_api_error(exc)

    def test_handles_no_response_attr(self):
        """Should not crash if exc.response is missing."""
        exc = httpx.HTTPStatusError.__new__(httpx.HTTPStatusError)
        exc.args = ("error",)
        with pytest.raises(SystemExit):
            _extract_api_error(exc)


class TestSubscriptionFlags:
    def test_parses_preserved_and_start_date(self):
        parser = build_parser()
        args = parser.parse_args(
            ["--app-id", "123", "--iap", "w", "--preserved", "--start-date", "2099-01-15"])
        assert args.preserved is True
        assert args.start_date == date(2099, 1, 15)

    def test_defaults_off(self):
        args = build_parser().parse_args(["--app-id", "123"])
        assert args.preserved is False
        assert args.start_date is None

    def test_accepts_tomorrow(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        args = build_parser().parse_args(["--app-id", "123", "--start-date", tomorrow])
        assert args.start_date == date.fromisoformat(tomorrow)

    def test_rejects_today_and_past(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--app-id", "123", "--start-date", date.today().isoformat()])
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--app-id", "123", "--start-date", "2020-01-01"])

    def test_rejects_invalid_date_format(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--app-id", "123", "--start-date", "someday"])


class TestValidateSubscriptionFlags:
    def _iap(self) -> Product:
        return Product(id="i1", name="Pack", product_id="com.app.pack", product_type="CONSUMABLE")

    def _sub(self) -> Product:
        return Product(id="s1", name="Weekly", product_id="com.app.weekly",
                       product_type="AUTOMATICALLY_RENEWABLE_SUBSCRIPTION", is_subscription=True)

    def test_rejects_flags_for_non_subscription(self):
        with pytest.raises(SystemExit):
            validate_subscription_flags(self._iap(), preserved=True, start_date=None)
        with pytest.raises(SystemExit):
            validate_subscription_flags(self._iap(), preserved=False, start_date=date(2099, 1, 15))

    def test_allows_flags_for_subscription(self):
        validate_subscription_flags(self._sub(), preserved=True, start_date=date(2099, 1, 15))

    def test_allows_non_subscription_without_flags(self):
        validate_subscription_flags(self._iap(), preserved=False, start_date=None)


class TestVersionFlag:
    def test_reports_the_installed_version(self, capsys):
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args(["--version"])
        assert exc.value.code == 0
        assert __version__ in capsys.readouterr().out

    def test_version_is_not_a_placeholder(self):
        """Guards against the package being importable but not installed in CI."""
        assert __version__ != "0.0.0+unknown"
