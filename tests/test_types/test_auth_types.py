"""Tests for types/auth.py: Credentials, Token, AuthData, DeviceInfo."""

import pytest
from datetime import datetime, timezone, timedelta

from pydantic import ValidationError

from my_tax.types.auth import Credentials, Token, AuthData, DeviceInfo


class TestCredentials:
    def test_creation(self, sample_credentials):
        assert sample_credentials.username == "770000000000"
        assert sample_credentials.password == "secret"

    def test_frozen(self):
        creds = Credentials(username="test", password="pass")
        with pytest.raises(ValidationError):
            creds.username = "new"


class TestToken:
    def test_from_api_json(self, sample_token_data):
        token = Token.model_validate(sample_token_data)
        assert token.access_token == "access-abc-123"
        assert token.refresh_token == "refresh-xyz-456"
        assert token.access_expire_in is not None

    def test_populate_by_name(self):
        """Token accepts both alias (API) and snake_case."""
        token = Token(
            access_token="abc",
            access_expire_in=datetime.now(timezone.utc),
            refresh_token="xyz",
        )
        assert token.access_token == "abc"

    def test_model_copy_update(self, sample_token):
        new = sample_token.model_copy(update={"access_token": "new-token"})
        assert new.access_token == "new-token"
        assert new.refresh_token == sample_token.refresh_token


class TestAuthData:
    def test_creation(self, sample_auth_data):
        assert sample_auth_data.inn == "770000000000"
        assert sample_auth_data.display_name == "Test User"

    def test_serialization_by_alias(self, sample_auth_data):
        json_str = sample_auth_data.model_dump_json(by_alias=True)
        assert "770000000000" in json_str

    def test_deserialization_roundtrip(self, sample_auth_data):
        json_str = sample_auth_data.model_dump_json(by_alias=True)
        restored = AuthData.model_validate_json(json_str)
        assert restored.inn == sample_auth_data.inn
        assert restored.token.access_token == sample_auth_data.token.access_token


class TestDeviceInfo:
    def test_defaults(self):
        d = DeviceInfo(source_device_id="test-id")
        assert d.source_type == "WEB"
        assert d.app_version == "1.0.0"

    def test_to_payload(self):
        d = DeviceInfo(source_device_id="dev-123")
        payload = d.to_payload()
        assert payload["sourceDeviceId"] == "dev-123"
        assert payload["sourceType"] == "WEB"
        assert "metaDetails" in payload
        assert "userAgent" in payload["metaDetails"]
