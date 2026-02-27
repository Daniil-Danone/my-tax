"""Tests for _helpers.py."""

import pytest
import string
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import httpx

from my_tax._helpers import (
    create_device_id,
    create_device_info,
    build_body_with_device,
    is_token_fresh,
    build_bearer_headers,
    auth_details_from_response,
    _extract_auth_error_message,
)
from my_tax.types.auth import DeviceInfo


class TestCreateDeviceId:
    def test_default_length(self):
        did = create_device_id()
        assert len(did) == 22

    def test_custom_length(self):
        did = create_device_id(length=10)
        assert len(did) == 10

    def test_only_lowercase_alphanumeric(self):
        did = create_device_id()
        allowed = set(string.ascii_lowercase + string.digits)
        assert all(c in allowed for c in did)

    def test_different_each_call(self):
        ids = {create_device_id() for _ in range(10)}
        assert len(ids) == 10


class TestCreateDeviceInfo:
    def test_returns_device_info(self):
        info = create_device_info()
        assert isinstance(info, DeviceInfo)
        assert len(info.source_device_id) == 22

    def test_custom_device_id(self):
        info = create_device_info(device_id="custom-123")
        assert info.source_device_id == "custom-123"


class TestBuildBodyWithDevice:
    def test_merges_device_and_kwargs(self):
        info = create_device_info(device_id="test-id")
        body = build_body_with_device(info, username="user", password="pass")
        assert "deviceInfo" in body
        assert body["username"] == "user"
        assert body["password"] == "pass"
        assert body["deviceInfo"]["sourceDeviceId"] == "test-id"


class TestIsTokenFresh:
    def test_fresh_token(self):
        expire = datetime.now(timezone.utc) + timedelta(hours=2)
        assert is_token_fresh(expire) is True

    def test_expired_token(self):
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        assert is_token_fresh(expire) is False

    def test_within_safety_margin(self):
        # Within 45-minute safety margin — should be False
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        assert is_token_fresh(expire) is False


class TestBuildBearerHeaders:
    def test_format(self):
        headers = build_bearer_headers("my-token-123")
        assert headers == {"authorization": "Bearer my-token-123"}


class TestAuthDetailsFromResponse:
    def test_parses_profile_and_token(self):
        data = {
            "profile": {
                "inn": "770000000000",
                "displayName": "Test User",
            },
            "token": "access-abc",
            "tokenExpireIn": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "refreshToken": "refresh-xyz",
        }
        auth = auth_details_from_response(data)
        assert auth.inn == "770000000000"
        assert auth.display_name == "Test User"
        assert auth.token.access_token == "access-abc"
        assert auth.token.refresh_token == "refresh-xyz"

    def test_missing_profile_uses_defaults(self):
        data = {
            "token": "abc",
            "tokenExpireIn": datetime.now(timezone.utc).isoformat(),
            "refreshToken": "xyz",
        }
        auth = auth_details_from_response(data)
        assert auth.inn == ""
        assert auth.display_name is None


class TestExtractAuthErrorMessage:
    def test_extracts_message(self):
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = {"message": "Invalid credentials"}
        assert _extract_auth_error_message(response) == "Invalid credentials"

    def test_no_message_key(self):
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = {"error": "something"}
        assert _extract_auth_error_message(response) == "Unknown"

    def test_non_json_response(self):
        from json import JSONDecodeError
        response = MagicMock(spec=httpx.Response)
        response.json.side_effect = JSONDecodeError("", "", 0)
        assert _extract_auth_error_message(response) == "Unknown"
