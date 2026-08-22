import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from appstore_ppp_prices.llm import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    MAX_ATTEMPTS,
    LLMError,
    base_url,
    chat_completion,
    configured_api_key,
    model_name,
)

MESSAGES = [{"role": "user", "content": "hi"}]


def _response(status: int, body: object = None, text: str = ""):
    """A stand-in for httpx.Response that only implements what the client touches."""
    r = MagicMock(spec=httpx.Response)
    r.status_code = status
    r.text = text
    if isinstance(body, Exception):
        r.json.side_effect = body
    else:
        r.json.return_value = body
    return r


def _ok(content: str):
    return _response(200, {"choices": [{"message": {"content": content}}]})


class TestEndpointConfiguration:
    def test_defaults_to_openai(self):
        with patch.dict(os.environ, {}, clear=True):
            assert base_url() == DEFAULT_BASE_URL
            assert model_name() == DEFAULT_MODEL

    def test_base_url_is_overridable(self):
        """Any OpenAI-compatible provider works by pointing the base URL at it."""
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "https://openrouter.ai/api/v1"}):
            assert base_url() == "https://openrouter.ai/api/v1"

    def test_trailing_slash_is_dropped(self):
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "http://localhost:11434/v1/"}):
            assert base_url() == "http://localhost:11434/v1"

    def test_model_is_overridable(self):
        """A different provider needs a different model name."""
        with patch.dict(os.environ, {"LLM_MODEL": "llama-3.3-70b"}):
            assert model_name() == "llama-3.3-70b"

    def test_openai_spellings_still_work(self):
        """OPENAI_* is the de facto standard and is often already exported."""
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "https://groq.example/v1",
                                     "OPENAI_MODEL": "mixtral",
                                     "OPENAI_API_KEY": "sk-old"}, clear=True):
            assert base_url() == "https://groq.example/v1"
            assert model_name() == "mixtral"
            assert configured_api_key() == "sk-old"

    def test_llm_spelling_wins_over_openai(self):
        with patch.dict(os.environ, {"LLM_MODEL": "new", "OPENAI_MODEL": "old",
                                     "LLM_API_KEY": "sk-new", "OPENAI_API_KEY": "sk-old"}):
            assert model_name() == "new"
            assert configured_api_key() == "sk-new"

    def test_empty_value_falls_through(self):
        """An exported but empty variable should not shadow the fallback."""
        with patch.dict(os.environ, {"LLM_MODEL": "", "OPENAI_MODEL": "fallback"}):
            assert model_name() == "fallback"


class TestRequest:
    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_returns_message_content(self, mock_post):
        mock_post.return_value = _ok("hello")
        assert chat_completion("k", MESSAGES) == "hello"

    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_sends_bearer_token_and_payload(self, mock_post):
        mock_post.return_value = _ok("hello")
        with patch.dict(os.environ, {}, clear=True):
            chat_completion("secret-key", MESSAGES, temperature=0.3, max_tokens=2000)

        url = mock_post.call_args.args[0]
        kwargs = mock_post.call_args.kwargs
        assert url == f"{DEFAULT_BASE_URL}/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer secret-key"
        assert kwargs["json"]["model"] == DEFAULT_MODEL
        assert kwargs["json"]["messages"] == MESSAGES
        assert kwargs["json"]["temperature"] == 0.3
        assert kwargs["json"]["max_completion_tokens"] == 2000

    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_always_sets_a_timeout(self, mock_post):
        """A request without a timeout can hang forever."""
        mock_post.return_value = _ok("hello")
        chat_completion("k", MESSAGES)
        assert mock_post.call_args.kwargs["timeout"] > 0

    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_omits_optional_fields_when_unset(self, mock_post):
        mock_post.return_value = _ok("hello")
        chat_completion("k", MESSAGES)
        payload = mock_post.call_args.kwargs["json"]
        assert "temperature" not in payload
        assert "max_completion_tokens" not in payload


class TestRetries:
    @patch("appstore_ppp_prices.llm.time.sleep")
    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_retries_rate_limit_then_succeeds(self, mock_post, mock_sleep):
        mock_post.side_effect = [_response(429), _ok("recovered")]
        assert chat_completion("k", MESSAGES) == "recovered"
        assert mock_post.call_count == 2

    @patch("appstore_ppp_prices.llm.time.sleep")
    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_retries_server_errors(self, mock_post, mock_sleep):
        mock_post.side_effect = [_response(503), _response(500), _ok("recovered")]
        assert chat_completion("k", MESSAGES) == "recovered"
        assert mock_post.call_count == 3

    @patch("appstore_ppp_prices.llm.time.sleep")
    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_retries_timeouts(self, mock_post, mock_sleep):
        mock_post.side_effect = [httpx.ReadTimeout("slow"), _ok("recovered")]
        assert chat_completion("k", MESSAGES) == "recovered"

    @patch("appstore_ppp_prices.llm.time.sleep")
    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_gives_up_after_max_attempts(self, mock_post, mock_sleep):
        mock_post.side_effect = [_response(503)] * MAX_ATTEMPTS
        with pytest.raises(LLMError, match="after 3 attempts"):
            chat_completion("k", MESSAGES)
        assert mock_post.call_count == MAX_ATTEMPTS

    @patch("appstore_ppp_prices.llm.time.sleep")
    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_backs_off_exponentially(self, mock_post, mock_sleep):
        mock_post.side_effect = [_response(503)] * MAX_ATTEMPTS
        with pytest.raises(LLMError):
            chat_completion("k", MESSAGES)
        assert [c.args[0] for c in mock_sleep.call_args_list] == [1, 2]

    @patch("appstore_ppp_prices.llm.time.sleep")
    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_does_not_retry_client_errors(self, mock_post, mock_sleep):
        """A bad key or a malformed request will fail again just as fast."""
        mock_post.return_value = _response(401, {"error": {"message": "Invalid API key"}})
        with pytest.raises(LLMError, match="Invalid API key"):
            chat_completion("k", MESSAGES)
        assert mock_post.call_count == 1
        mock_sleep.assert_not_called()


class TestErrorReporting:
    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_surfaces_the_providers_own_message(self, mock_post):
        mock_post.return_value = _response(400, {"error": {"message": "model not found"}})
        with pytest.raises(LLMError, match="model not found"):
            chat_completion("k", MESSAGES)

    @patch("appstore_ppp_prices.llm.time.sleep")
    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_falls_back_to_body_text_when_not_json(self, mock_post, mock_sleep):
        """502 is retryable, so this also proves a non-JSON body does not crash the retry loop."""
        mock_post.return_value = _response(502, ValueError("no json"), text="<html>bad gateway</html>")
        with pytest.raises(LLMError):
            chat_completion("k", MESSAGES)


class TestMalformedResponses:
    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_rejects_empty_choices(self, mock_post):
        mock_post.return_value = _response(200, {"choices": []})
        with pytest.raises(LLMError, match="no choices"):
            chat_completion("k", MESSAGES)

    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_rejects_missing_choices(self, mock_post):
        mock_post.return_value = _response(200, {})
        with pytest.raises(LLMError, match="no choices"):
            chat_completion("k", MESSAGES)

    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_rejects_empty_content(self, mock_post):
        mock_post.return_value = _response(200, {"choices": [{"message": {"content": ""}}]})
        with pytest.raises(LLMError, match="empty message"):
            chat_completion("k", MESSAGES)

    @patch("appstore_ppp_prices.llm.httpx.post")
    def test_rejects_non_object_body(self, mock_post):
        mock_post.return_value = _response(200, ["not", "an", "object"])
        with pytest.raises(LLMError):
            chat_completion("k", MESSAGES)


class TestTemplateStaysInSync:
    def test_env_example_documents_the_real_default_model(self):
        """Changing DEFAULT_MODEL without updating .env.example would mislead users."""
        import re
        from pathlib import Path

        template = Path(__file__).resolve().parent.parent / ".env.example"
        active = re.findall(r"^LLM_MODEL=(.+)$", template.read_text(encoding="utf-8"), re.M)
        assert active == [DEFAULT_MODEL]
