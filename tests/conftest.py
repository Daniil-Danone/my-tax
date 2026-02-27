"""Shared fixtures for my_tax tests."""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from my_tax.types.auth import Credentials, Token, AuthData, DeviceInfo
from my_tax.types.income import CreateIncomeItem, CreateIncomeClient
from my_tax.types.invoice import CreateInvoiceItem, CreateInvoiceClient
from my_tax.enums.general import ClientType


@pytest.fixture
def sample_credentials():
    return Credentials(username="770000000000", password="secret")


@pytest.fixture
def sample_token_data():
    """Raw dict как приходит от API."""
    return {
        "token": "access-abc-123",
        "tokenExpireIn": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "refreshToken": "refresh-xyz-456",
        "refreshTokenExpiresIn": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }


@pytest.fixture
def sample_token(sample_token_data):
    return Token.model_validate(sample_token_data)


@pytest.fixture
def sample_auth_data(sample_token):
    return AuthData(inn="770000000000", token=sample_token, display_name="Test User")


@pytest.fixture
def sample_income_item():
    return CreateIncomeItem(name="Consulting", amount=Decimal("1000"), quantity=Decimal("1"))


@pytest.fixture
def sample_invoice_item():
    return CreateInvoiceItem(name="Web dev", amount=Decimal("5000"), quantity=Decimal("2"))


@pytest.fixture
def sample_income_client_legal():
    return CreateIncomeClient(
        type=ClientType.FROM_LEGAL_ENTITY,
        name="OOO Test",
        inn="7700000001",
    )


@pytest.fixture
def sample_invoice_client():
    return CreateInvoiceClient(name="John Doe", type=ClientType.FROM_INDIVIDUAL)


class FakeRedis:
    """In-memory mock для AuthStorage protocol."""

    def __init__(self):
        self._store: dict[str, str | bytes] = {}

    async def get(self, name: str):
        return self._store.get(name)

    async def set(self, name: str, value, ex=None):
        self._store[name] = value
