from unittest.mock import MagicMock, patch
import json

from appstore_ppp_prices.ai_analyzer import AIResult, CACHE_DIR, _save_cache, analyze_app, clear_cache
from appstore_ppp_prices.llm import LLMError


class TestAnalyzeApp:
    @patch("appstore_ppp_prices.ai_analyzer._load_cache", return_value=None)
    @patch("appstore_ppp_prices.ai_analyzer.chat_completion")
    def test_returns_coefficients(self, mock_chat, _mock_cache):
        ai_response = json.dumps({
            "app_type": "game",
            "elasticity": "high",
            "reasoning": "games have high elasticity",
            "coefficients": {
                "premium": 1.10,
                "usa": 1.00,
                "high_income": 0.90,
                "emerging": 0.40,
            },
        })
        mock_chat.return_value = ai_response

        result = analyze_app("fake-key", "Test App", [{"name": "weekly", "us_price": 4.99}])

        assert isinstance(result, AIResult)
        assert result.app_type == "game"
        assert result.elasticity == "high"
        assert result.coefficients["premium"] == 1.1
        assert result.coefficients["high_income"] == 0.9
        assert result.coefficients["emerging"] == 0.4
        assert "usa" not in result.coefficients

    @patch("appstore_ppp_prices.ai_analyzer._load_cache", return_value=None)
    @patch("appstore_ppp_prices.ai_analyzer.chat_completion")
    def test_returns_none_on_api_error(self, mock_chat, _mock_cache):
        mock_chat.side_effect = LLMError("API error")
        result = analyze_app("fake-key", "Test App", [])
        assert result is None

    @patch("appstore_ppp_prices.ai_analyzer._load_cache", return_value=None)
    @patch("appstore_ppp_prices.ai_analyzer.chat_completion")
    def test_returns_none_on_invalid_json(self, mock_chat, _mock_cache):
        mock_chat.return_value = "not valid json"

        result = analyze_app("fake-key", "Test App", [])
        assert result is None

    @patch("appstore_ppp_prices.ai_analyzer._load_cache", return_value=None)
    @patch("appstore_ppp_prices.ai_analyzer.chat_completion")
    def test_returns_none_on_missing_coefficients_key(self, mock_chat, _mock_cache):
        mock_chat.return_value = json.dumps({"app_type": "game"})

        result = analyze_app("fake-key", "Test App", [])
        assert result is None

    @patch("appstore_ppp_prices.ai_analyzer.chat_completion")
    @patch("appstore_ppp_prices.ai_analyzer.CACHE_DIR")
    def test_returns_result_even_when_cache_write_fails(self, mock_cache_dir, mock_chat):
        """Cache write failure should not lose the valid AI result."""
        mock_cache_dir.mkdir.side_effect = OSError("read-only filesystem")

        ai_response = json.dumps({
            "app_type": "utility",
            "elasticity": "low",
            "reasoning": "test",
            "coefficients": {"premium": 1.05, "usa": 1.00, "emerging": 0.60},
        })
        mock_chat.return_value = ai_response

        result = analyze_app("fake-key", "Test App", [{"name": "pro", "us_price": 9.99}])
        assert isinstance(result, AIResult)
        assert result.coefficients["emerging"] == 0.6


    @patch("appstore_ppp_prices.ai_analyzer._load_cache", return_value=None)
    @patch("appstore_ppp_prices.ai_analyzer.chat_completion")
    def test_returns_none_on_invalid_coefficient_value(self, mock_chat, _mock_cache):
        """Non-numeric coefficient value should return None, not crash."""
        ai_response = json.dumps({
            "app_type": "game",
            "elasticity": "high",
            "reasoning": "test",
            "coefficients": {"premium": "not_a_number", "usa": 1.00},
        })
        mock_chat.return_value = ai_response

        result = analyze_app("fake-key", "Test App", [{"name": "weekly", "us_price": 4.99}])
        assert result is None


    @patch("appstore_ppp_prices.ai_analyzer._load_cache", return_value=None)
    @patch("appstore_ppp_prices.ai_analyzer.chat_completion")
    def test_handles_markdown_only_backticks(self, mock_chat, _mock_cache):
        """Response of just '```' should not IndexError."""
        mock_chat.return_value = "```"

        result = analyze_app("fake-key", "Test App", [{"name": "weekly", "us_price": 4.99}])
        assert result is None

    @patch("appstore_ppp_prices.ai_analyzer._load_cache", return_value=None)
    @patch("appstore_ppp_prices.ai_analyzer.chat_completion")
    def test_strips_markdown_code_block(self, mock_chat, _mock_cache):
        """JSON wrapped in ```json ... ``` should be parsed correctly."""
        raw_json = json.dumps({
            "app_type": "game", "elasticity": "high", "reasoning": "test",
            "coefficients": {"premium": 1.10, "usa": 1.00, "emerging": 0.40},
        })
        wrapped = f"```json\n{raw_json}\n```"
        mock_chat.return_value = wrapped

        result = analyze_app("fake-key", "Test App", [{"name": "weekly", "us_price": 4.99}])
        assert isinstance(result, AIResult)
        assert result.app_type == "game"


class TestClearCache:
    def test_removes_json_files(self, tmp_path):
        with patch("appstore_ppp_prices.ai_analyzer.CACHE_DIR", tmp_path):
            (tmp_path / "abc123.json").write_text("{}")
            (tmp_path / "def456.json").write_text("{}")
            removed = clear_cache()
            assert removed == 2
            assert not tmp_path.exists()

    def test_returns_zero_when_no_cache_dir(self, tmp_path):
        with patch("appstore_ppp_prices.ai_analyzer.CACHE_DIR", tmp_path / "nonexistent"):
            assert clear_cache() == 0

    def test_ignores_non_json_files(self, tmp_path):
        with patch("appstore_ppp_prices.ai_analyzer.CACHE_DIR", tmp_path):
            (tmp_path / "abc123.json").write_text("{}")
            (tmp_path / "readme.txt").write_text("hi")
            removed = clear_cache()
            assert removed == 1
            assert (tmp_path / "readme.txt").exists()


class TestSaveCache:
    def test_does_not_raise_on_write_error(self):
        """_save_cache should log warning, not raise."""
        result = AIResult(app_type="game", elasticity="high", reasoning="test", coefficients={"emerging": 0.4})
        with patch("appstore_ppp_prices.ai_analyzer.CACHE_DIR") as mock_dir:
            mock_dir.mkdir.side_effect = OSError("permission denied")
            _save_cache("App", result)  # should not raise
