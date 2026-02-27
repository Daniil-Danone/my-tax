"""Tests for _client.py: MyTaxClient."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from my_tax._client import MyTaxClient, _serialize_session, _deserialize_session
from my_tax.types.auth import Credentials, Token, AuthData
from my_tax.api._user import UserApi
from my_tax.api._income import IncomeApi
from my_tax.api._invoice import InvoiceApi
from my_tax.api._payment_method import PaymentMethodApi
from tests.conftest import FakeRedis


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:
    async def test_aenter_aexit(self):
        client = MyTaxClient()
        async with client as c:
            assert c is client
        # aclose was called (transport closed)

    async def test_has_async_context_methods(self):
        client = MyTaxClient()
        assert hasattr(client, "__aenter__")
        assert hasattr(client, "__aexit__")
        await client.aclose()


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

class TestProperties:
    def test_api_properties(self):
        client = MyTaxClient()
        assert isinstance(client.user, UserApi)
        assert isinstance(client.income, IncomeApi)
        assert isinstance(client.invoice, InvoiceApi)
        assert isinstance(client.payment_type, PaymentMethodApi)

    def test_auth_by_password_none_without_credentials(self):
        client = MyTaxClient()
        assert client.auth_by_password is None

    def test_auth_by_password_set_with_credentials(self):
        client = MyTaxClient(credentials=Credentials(username="u", password="p"))
        assert client.auth_by_password is not None

    def test_auth_by_phone_always_set(self):
        client = MyTaxClient()
        assert client.auth_by_phone is not None


# ---------------------------------------------------------------------------
# Session serialization
# ---------------------------------------------------------------------------

class TestSessionSerialization:
    def test_serialize_deserialize_roundtrip(self, sample_auth_data):
        serialized = _serialize_session(sample_auth_data)
        restored = _deserialize_session(serialized)
        assert restored is not None
        assert restored.inn == sample_auth_data.inn
        assert restored.token.access_token == sample_auth_data.token.access_token

    def test_deserialize_invalid_json(self):
        assert _deserialize_session("not json") is None

    def test_deserialize_bytes(self, sample_auth_data):
        serialized = _serialize_session(sample_auth_data).encode()
        restored = _deserialize_session(serialized)
        assert restored is not None


# ---------------------------------------------------------------------------
# Redis cache
# ---------------------------------------------------------------------------

class TestRedisCache:
    async def test_cache_miss_then_hit(self, sample_auth_data):
        redis = FakeRedis()
        client = MyTaxClient(
            credentials=Credentials(username="u", password="p"),
            redis=redis,
            redis_key="test:session",
        )

        # Manually save session
        from my_tax._client import _serialize_session
        await redis.set("test:session", _serialize_session(sample_auth_data))

        # Should load from cache
        headers = await client.get_auth_headers()
        assert "authorization" in headers
        assert "Bearer" in headers["authorization"]
        await client.aclose()

    async def test_no_redis_works(self):
        client = MyTaxClient()
        # _load_session_from_redis returns None when no redis
        result = await client._load_session_from_redis()
        assert result is None
        await client.aclose()


# ---------------------------------------------------------------------------
# request() with 401 retry
# ---------------------------------------------------------------------------

class TestRequest401Retry:
    async def test_successful_request(self):
        client = MyTaxClient(credentials=Credentials(username="u", password="p"))

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        client.get_auth_headers = AsyncMock(return_value={"authorization": "Bearer tok"})
        client._transport._client = MagicMock()
        client._transport._client.request = AsyncMock(return_value=mock_response)
        client._transport._client.aclose = AsyncMock()

        response = await client.request("GET", "/user")
        assert response.status_code == 200
        await client.aclose()

    async def test_401_retry(self):
        client = MyTaxClient(credentials=Credentials(username="u", password="p"))

        first_response = MagicMock(spec=httpx.Response)
        first_response.status_code = 401

        second_response = MagicMock(spec=httpx.Response)
        second_response.status_code = 200

        client.get_auth_headers = AsyncMock(return_value={"authorization": "Bearer tok"})
        client._transport._client = MagicMock()
        client._transport._client.request = AsyncMock(
            side_effect=[first_response, second_response]
        )
        client._transport._client.aclose = AsyncMock()

        response = await client.request("GET", "/user")
        assert response.status_code == 200
        # get_auth_headers called twice: initial + force_refresh
        assert client.get_auth_headers.call_count == 2
        await client.aclose()

    async def test_no_retry_on_other_status(self):
        client = MyTaxClient(credentials=Credentials(username="u", password="p"))

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500

        client.get_auth_headers = AsyncMock(return_value={"authorization": "Bearer tok"})
        client._transport._client = MagicMock()
        client._transport._client.request = AsyncMock(return_value=mock_response)
        client._transport._client.aclose = AsyncMock()

        response = await client.request("GET", "/user")
        assert response.status_code == 500
        # Only one call to get_auth_headers (no retry)
        assert client.get_auth_headers.call_count == 1
        await client.aclose()
