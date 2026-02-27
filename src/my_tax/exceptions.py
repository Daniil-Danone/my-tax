"""
Исключения для API ЛК НПД
"""

import re
from typing import Any

import httpx

from .logger import setup_logger


logger = setup_logger(name="my_tax")

# Формат лога совпадает со стилем логгера: [level] [time] [name] %(message)s
# Сообщение — одна строка со структурированными полями для парсинга/поиска.
_API_ERROR_LOG_FMT = (
    "[API_ERROR] message=%s status_code=%s url=%s headers=%s body=%s"
)

# Регулярки для чувствительных данных в URL.
_URL_MASK_PATTERNS = [
    (re.compile(r"(token=)[^&]*", re.I), r"\1***"),
    (re.compile(r"(key=)[^&]*", re.I), r"\1***"),
    (re.compile(r"(secret=)[^&]*", re.I), r"\1***"),
    (re.compile(r"(password=)[^&]*", re.I), r"\1***"),
]

# Регулярки для чувствительных полей в JSON-теле ответа.
_BODY_MASK_PATTERNS = [
    
    (re.compile(r'"token"\s*:\s*"[^"]*"', re.I), '"token":"***"'),
    (re.compile(r'"accessToken"\s*:\s*"[^"]*"', re.I), '"accessToken":"***"'),
    (re.compile(r'"refreshToken"\s*:\s*"[^"]*"', re.I), '"refreshToken":"***"'),
    (re.compile(r'"challengeToken"\s*:\s*"[^"]*"', re.I), '"challengeToken":"***"'),
    (re.compile(r'"password"\s*:\s*"[^"]*"', re.I), '"password":"***"'),
    (re.compile(r'"secret"\s*:\s*"[^"]*"', re.I), '"secret":"***"'),
    (re.compile(r'"access_token"\s*:\s*"[^"]*"', re.I), '"access_token":"***"'),
    (re.compile(r'"refresh_token"\s*:\s*"[^"]*"', re.I), '"refresh_token":"***"'),
]

# Заголовки, значения которых не логируются.
_SENSITIVE_HEADER_KEYS = frozenset(
    {"authorization", "x-api-key", "cookie", "set-cookie", "proxy-authorization"}
)


class BaseDomainException(Exception):
    """Базовое исключение для API ЛК НПД."""

    def __init__(
        self,
        message: str,
        response: httpx.Response | None = None,
    ) -> None:
        super().__init__(message)
        self.response = response

        if response is not None:
            self._log_error_details(message, response)

    def _log_error_details(self, message: str, response: httpx.Response) -> None:
        """Логирование деталей ошибки без чувствительных данных в URL и теле ответа."""
        safe_url = self._mask_sensitive_url(str(response.url))
        safe_headers = self._mask_sensitive_headers(self._headers_to_dict(response))
        safe_body = self._get_safe_response_body(response)

        logger.error(
            _API_ERROR_LOG_FMT,
            message,
            response.status_code,
            safe_url,
            safe_headers,
            safe_body,
        )

    @staticmethod
    def _headers_to_dict(response: httpx.Response) -> dict[str, str]:
        """Приведение заголовков к обычному словарю (без чувствительных значений в логе)."""
        try:
            return dict(response.headers)
        except Exception:
            return {}

    @staticmethod
    def _mask_sensitive_url(url: str) -> str:
        """Маскирование потенциально чувствительных параметров в URL."""
        for pattern, replacement in _URL_MASK_PATTERNS:
            url = pattern.sub(replacement, url)
        return url

    @staticmethod
    def _mask_sensitive_headers(headers: dict[str, Any]) -> dict[str, str]:
        """Копия заголовков с заменой чувствительных значений на ***."""
        out: dict[str, str] = {}
        for key, value in headers.items():
            if key.lower() in _SENSITIVE_HEADER_KEYS:
                out[key] = "***"
            else:
                out[key] = str(value) if value is not None else ""
        return out

    @staticmethod
    def _get_safe_response_body(response: httpx.Response) -> str:
        """Тело ответа с замаскированными чувствительными полями."""
        try:
            body = response.text[:1000]
            for pattern, replacement in _BODY_MASK_PATTERNS:
                body = pattern.sub(replacement, body)
            return body
        except Exception:
            return "[Failed to read response body]"


class AuthorizationError(BaseDomainException):
    """Исключение при ошибке авторизации."""


class AccessTokenNotFoundError(BaseDomainException):
    """Исключение при отсутствии access-токена в ответе на refresh."""


class SmsChallengeError(BaseDomainException):
    """Исключение при ошибке SMS-челленджа."""
