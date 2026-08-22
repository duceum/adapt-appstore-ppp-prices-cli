from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from appstore_ppp_prices.appstore import AppStoreConnectClient

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _env_or_skip(var: str) -> str:
    val = os.getenv(var)
    if not val:
        pytest.skip(f"{var} not set in .env")
    return val


@pytest.fixture(scope="session")
def client() -> AppStoreConnectClient:
    key_id = _env_or_skip("ASC_KEY_ID")
    issuer_id = _env_or_skip("ASC_ISSUER_ID")
    pk_path_str = _env_or_skip("ASC_PRIVATE_KEY_PATH")
    pk_path = Path(pk_path_str)
    if not pk_path.is_absolute():
        pk_path = _PROJECT_ROOT / pk_path
    c = AppStoreConnectClient(key_id, issuer_id, pk_path)
    yield c
    c.close()


@pytest.fixture(scope="session")
def app_id() -> str:
    return _env_or_skip("TEST_APP_ID")


@pytest.fixture(scope="session")
def product_id() -> str:
    return _env_or_skip("TEST_PRODUCT_ID")
