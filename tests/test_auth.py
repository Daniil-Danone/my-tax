"""Tests for _auth.py: PasswordAuth, PhoneSmsAuth."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx

from my_tax._auth import PasswordAuth, PhoneSmsAuth, _handle_auth_errors
from my_tax._transport import Transport
from my_tax.types.auth import Credentials
from my_tax.exceptions import (
    AuthorizationError,
    AccessTokenNotFoundError,
    SmsChallengeError,
)


def _make_auth_response(access_token="tok-123", refresh_token="ref-456"):
    """Create a mock auth API response."""
    return {
        "profile": {"inn": "770000000000", "displayName": "Test"},
        "token": access_token,
        "tokenExpireIn": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "refreshToken": refresh_token,
    }


def _mock_transport():
    transport = MagicMock(spec=Transport)
    transport.post = AsyncMock()
    return transport


def _ok_response(json_data, status_code=200):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    return response


# ---------------------------------------------------------------------------
# PasswordAuth
# ---------------------------------------------------------------------------

class TestPasswordAuth:
    @pytest.fixture
    def auth(self):
        transport = _mock_transport()
        creds = Credentials(username="770000000000", password="secret")
        return PasswordAuth(transport, creds), transport

    async def test_obtain_token(self, auth):
        pa, transport = auth
        transport.post.return_value = _ok_response(_make_auth_response())

        result = await pa.obtain_token()
        assert result.inn == "770000000000"
        assert result.token.access_token == "tok-123"
        assert pa.is_authenticated is True
        transport.post.assert_called_once()

    async def test_refresh_token(self, auth):
        pa, transport = auth
        # First obtain
        transport.post.return_value = _ok_response(_make_auth_response())
        await pa.obtain_token()

        # Then refresh
        transport.post.return_value = _ok_response({"token": "new-tok"})
        new = await pa.refresh_token()
        assert new == "new-tok"
        assert pa.session.token.access_token == "new-tok"

    async def test_refresh_without_session_raises(self, auth):
        pa, _ = auth
        with pytest.raises(AccessTokenNotFoundError):
            await pa.refresh_token()

    async def test_get_auth_headers_auto_obtains(self, auth):
        pa, transport = auth
        transport.post.return_value = _ok_response(_make_auth_response())
        headers = await pa.get_auth_headers()
        assert "authorization" in headers
        assert headers["authorization"].startswith("Bearer ")

    async def test_http_error_wrapped(self, auth):
        pa, transport = auth
        response = MagicMock(spec=httpx.Response)
        response.status_code = 401
        response.json.return_value = {"message": "Bad creds"}
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=response
        )
        transport.post.return_value = response

        with pytest.raises(AuthorizationError, match="Bad creds"):
            await pa.obtain_token()


# ---------------------------------------------------------------------------
# PhoneSmsAuth
# ---------------------------------------------------------------------------

class TestPhoneSmsAuth:
    @pytest.fixture
    def auth(self):
        transport = _mock_transport()
        return PhoneSmsAuth(transport), transport

    async def test_start_challenge(self, auth):
        pa, transport = auth
        transport.post.return_value = _ok_response({"challengeToken": "ch-tok-123"})

        token = await pa.start_challenge("79991234567")
        assert token == "ch-tok-123"

    async def test_start_challenge_missing_token(self, auth):
        pa, transport = auth
        transport.post.return_value = _ok_response({})

        with pytest.raises(SmsChallengeError, match="challengeToken"):
            await pa.start_challenge("79991234567")

    async def test_verify_without_any_token_raises(self, auth):
        pa, _ = auth
        with pytest.raises(SmsChallengeError, match="challenge_token"):
            await pa.verify_and_login("79991234567", "1234")

    async def test_verify_and_login(self, auth):
        pa, transport = auth
        # Start challenge
        transport.post.return_value = _ok_response({"challengeToken": "ch-tok"})
        await pa.start_challenge("79991234567")

        # Verify
        transport.post.return_value = _ok_response(_make_auth_response())
        result = await pa.verify_and_login("79991234567", "1234")
        assert result.inn == "770000000000"
        assert pa.is_authenticated is True

    async def test_verify_with_external_challenge_token(self, auth):
        """verify_and_login works without start_challenge when challenge_token is passed."""
        pa, transport = auth
        transport.post.return_value = _ok_response(_make_auth_response())

        result = await pa.verify_and_login(
            "79991234567", "1234", challenge_token="ext-tok-999"
        )
        assert result.inn == "770000000000"
        assert pa.is_authenticated is True

        # Verify the token was sent in the request body
        call_kwargs = transport.post.call_args
        assert call_kwargs.kwargs["json"]["challengeToken"] == "ext-tok-999"

    async def test_verify_prefers_external_token(self, auth):
        """External challenge_token takes priority over in-memory one."""
        pa, transport = auth
        # Start challenge (in-memory token = "in-mem-tok")
        transport.post.return_value = _ok_response({"challengeToken": "in-mem-tok"})
        await pa.start_challenge("79991234567")

        # Verify with explicit token — should use "ext-tok", not "in-mem-tok"
        transport.post.return_value = _ok_response(_make_auth_response())
        await pa.verify_and_login("79991234567", "1234", challenge_token="ext-tok")

        call_kwargs = transport.post.call_args
        assert call_kwargs.kwargs["json"]["challengeToken"] == "ext-tok"

    async def test_get_auth_headers_without_auth_raises(self, auth):
        pa, _ = auth
        with pytest.raises(AuthorizationError, match="Нет сессии"):
            await pa.get_auth_headers()


# ---------------------------------------------------------------------------
# _handle_auth_errors decorator
# ---------------------------------------------------------------------------

class TestHandleAuthErrors:
    async def test_wraps_json_decode_error(self):
        from json import JSONDecodeError

        @_handle_auth_errors
        async def bad_json(self):
            raise JSONDecodeError("", "", 0)

        with pytest.raises(AuthorizationError, match="JSON"):
            await bad_json(None)

    async def test_wraps_key_error(self):
        @_handle_auth_errors
        async def bad_key(self):
            raise KeyError("missing")

        with pytest.raises(AuthorizationError, match="структура"):
            await bad_key(None)

    async def test_preserves_original_as_cause(self):
        @_handle_auth_errors
        async def bad_type(self):
            raise TypeError("wrong type")

        with pytest.raises(AuthorizationError) as exc_info:
            await bad_type(None)
        assert isinstance(exc_info.value.__cause__, TypeError)
