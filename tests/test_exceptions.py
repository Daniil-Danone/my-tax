"""Tests for exceptions.py: sensitive data masking."""

from my_tax.exceptions import BaseDomainException


class TestUrlMasking:
    def test_masks_token_param(self):
        url = "https://api.example.com/auth?token=secret123&other=ok"
        masked = BaseDomainException._mask_sensitive_url(url)
        assert "secret123" not in masked
        assert "token=***" in masked
        assert "other=ok" in masked

    def test_masks_key_param(self):
        url = "https://api.example.com?key=abc123"
        masked = BaseDomainException._mask_sensitive_url(url)
        assert "abc123" not in masked
        assert "key=***" in masked

    def test_masks_password_param(self):
        url = "https://api.example.com?password=mypass"
        masked = BaseDomainException._mask_sensitive_url(url)
        assert "mypass" not in masked

    def test_clean_url_unchanged(self):
        url = "https://api.example.com/users?limit=10"
        assert BaseDomainException._mask_sensitive_url(url) == url


class TestHeaderMasking:
    def test_masks_authorization(self):
        headers = {"authorization": "Bearer secret-token", "content-type": "application/json"}
        masked = BaseDomainException._mask_sensitive_headers(headers)
        assert masked["authorization"] == "***"
        assert masked["content-type"] == "application/json"

    def test_masks_cookie(self):
        headers = {"cookie": "session=abc", "x-api-key": "key123"}
        masked = BaseDomainException._mask_sensitive_headers(headers)
        assert masked["cookie"] == "***"
        assert masked["x-api-key"] == "***"

    def test_case_insensitive(self):
        headers = {"Authorization": "Bearer tok"}
        masked = BaseDomainException._mask_sensitive_headers(headers)
        assert masked["Authorization"] == "***"


class TestBodyMasking:
    def _make_response(self, text):
        from unittest.mock import MagicMock
        import httpx
        resp = MagicMock(spec=httpx.Response)
        resp.text = text
        return resp

    def test_masks_token(self):
        resp = self._make_response('{"token":"secret-access-token","other":"ok"}')
        body = BaseDomainException._get_safe_response_body(resp)
        assert "secret-access-token" not in body
        assert '"token":"***"' in body
        assert '"other":"ok"' in body

    def test_masks_refresh_token(self):
        resp = self._make_response('{"refreshToken":"ref-123"}')
        body = BaseDomainException._get_safe_response_body(resp)
        assert "ref-123" not in body

    def test_masks_password(self):
        resp = self._make_response('{"password":"mypass123"}')
        body = BaseDomainException._get_safe_response_body(resp)
        assert "mypass123" not in body

    def test_masks_challenge_token(self):
        resp = self._make_response('{"challengeToken":"ch-tok-456"}')
        body = BaseDomainException._get_safe_response_body(resp)
        assert "ch-tok-456" not in body


class TestExceptionHierarchy:
    def test_authorization_error_is_subclass(self):
        from my_tax.exceptions import AuthorizationError
        assert issubclass(AuthorizationError, BaseDomainException)

    def test_access_token_error_is_subclass(self):
        from my_tax.exceptions import AccessTokenNotFoundError
        assert issubclass(AccessTokenNotFoundError, BaseDomainException)

    def test_sms_challenge_error_is_subclass(self):
        from my_tax.exceptions import SmsChallengeError
        assert issubclass(SmsChallengeError, BaseDomainException)

    def test_exception_without_response(self):
        exc = BaseDomainException("test error")
        assert str(exc) == "test error"
        assert exc.response is None
