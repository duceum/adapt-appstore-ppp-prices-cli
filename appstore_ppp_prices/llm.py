"""Client for the OpenAI chat-completions endpoint, and anything shaped like it.

The same request works against OpenRouter, Groq, Together, Fireworks, DeepSeek and
locally hosted Ollama, LM Studio or vLLM, so the base URL and model are configurable.
Talking to the endpoint directly rather than through a vendor SDK also keeps the
dependency tree free of compiled extensions.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

log = logging.getLogger(__name__)


def _env(*names: str) -> str | None:
    """First of these environment variables that is set to a non-empty value."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-5.2"

# LLM_* are the documented names. The OPENAI_* spellings are accepted because they are
# the de facto standard and are often already exported for other tools.
REQUEST_TIMEOUT = int(_env("LLM_REQUEST_TIMEOUT", "OPENAI_REQUEST_TIMEOUT") or "120")

MAX_ATTEMPTS = 3
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class LLMError(RuntimeError):
    """The provider was unreachable, refused the request, or answered unusably."""


class _Transient(Exception):
    """Internal marker for a failure that is worth retrying."""


def base_url() -> str:
    return (_env("LLM_BASE_URL", "OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def model_name() -> str:
    return _env("LLM_MODEL", "OPENAI_MODEL") or DEFAULT_MODEL


def configured_api_key() -> str | None:
    """The key from the environment, whichever spelling was used."""
    return _env("LLM_API_KEY", "OPENAI_API_KEY")


def chat_completion(
    api_key: str,
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int = REQUEST_TIMEOUT,
) -> str:
    """Send one chat completion and return the assistant's message content.

    Retries 429 and 5xx responses, timeouts and transport errors up to
    MAX_ATTEMPTS with exponential backoff. Every other failure raises LLMError
    immediately, because retrying a 400 or a 401 only wastes time.
    """
    payload: dict = {"model": model or model_name(), "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_completion_tokens"] = max_tokens

    url = f"{base_url()}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code in RETRY_STATUSES:
                raise _Transient(f"HTTP {response.status_code}")
            if response.status_code >= 400:
                raise LLMError(f"HTTP {response.status_code} from {url}: {_detail(response)}")
            return _content(response.json())
        except (_Transient, httpx.TimeoutException, httpx.TransportError) as e:
            last_error = e
            if attempt == MAX_ATTEMPTS:
                break
            delay = 2 ** (attempt - 1)
            log.warning("LLM request failed (%s), retrying in %ss", e, delay)
            time.sleep(delay)

    raise LLMError(f"{url} unreachable after {MAX_ATTEMPTS} attempts: {last_error}")


def _detail(response: httpx.Response) -> str:
    """Pull the provider's own error message out of the body, if there is one."""
    try:
        error = response.json().get("error")
    except ValueError:
        return response.text[:200]
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(error or response.text[:200])


def _content(body: object) -> str:
    if not isinstance(body, dict):
        raise LLMError(f"expected a JSON object, got {type(body).__name__}")
    choices = body.get("choices")
    if not choices:
        raise LLMError("response contained no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not content:
        raise LLMError("response contained an empty message")
    return content
