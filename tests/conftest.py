import pytest

from appstore_ppp_prices import ai_analyzer


@pytest.fixture(autouse=True)
def isolate_ai_cache(tmp_path, monkeypatch):
    """Keep the suite out of the real AI cache directory.

    analyze_app() calls _save_cache() on success, so any test that exercises it
    with a mocked OpenAI response writes a fake analysis into the cache the tool
    actually reads — and a later real run for an app with the same name picks it
    up, because the cache key is a hash of the app name.
    """
    monkeypatch.setattr(ai_analyzer, "CACHE_DIR", tmp_path / "ai-cache")
