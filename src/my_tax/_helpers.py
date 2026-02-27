"""
Общие хелперы для авторизации и транспорта.
"""

import secrets
import string
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import Any, Dict, Optional

import httpx

from .constants import ACCESS_TOKEN_LIFETIME
from .exceptions import AuthorizationError
from .types import AuthData, DeviceInfo, Token


# ---------------------------------------------------------------------------
# Хелперы: устройство и тело запроса
# ---------------------------------------------------------------------------


def create_device_id(length: int = 22) -> str:
    """Генерация случайного идентификатора устройства для deviceInfo."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_device_info(device_id: Optional[str] = None) -> DeviceInfo:
    """Создание объекта DeviceInfo с опциональным device_id."""
    return DeviceInfo(source_device_id=device_id or create_device_id())


def build_body_with_device(device_info: DeviceInfo, **kwargs: Any) -> Dict[str, Any]:
    """Сборка тела запроса с deviceInfo и произвольными полями."""
    return {
        "deviceInfo": device_info.to_payload(),
        **kwargs,
    }


# ---------------------------------------------------------------------------
# Хелперы: токен и заголовки
# ---------------------------------------------------------------------------


def is_token_fresh(expire_in: datetime) -> bool:
    """Проверка, что токен ещё действителен (с запасом по времени)."""
    return expire_in > datetime.now(tz=timezone.utc) + ACCESS_TOKEN_LIFETIME


def build_bearer_headers(access_token: str) -> Dict[str, str]:
    """Формирование заголовка Authorization с Bearer-токеном."""
    return {"authorization": f"Bearer {access_token}"}


def auth_details_from_response(data: Dict[str, Any]) -> AuthData:
    """Сборка AuthDetails из JSON-ответа с profile и токеном."""
    profile: Dict[str, Any] = data.get("profile", {})

    return AuthData(
        inn=profile.get("inn", ""),
        token=Token.model_validate(data),
        display_name=profile.get("displayName"),
    )


# ---------------------------------------------------------------------------
# Обработка ошибок авторизации
# ---------------------------------------------------------------------------


def _extract_auth_error_message(response: httpx.Response) -> str:
    """Извлечение сообщения об ошибке из ответа API."""
    try:
        body = response.json()
        if isinstance(body, dict) and "message" in body:
            return str(body["message"])
    except (JSONDecodeError, TypeError):
        pass
    return "Unknown"


# ---------------------------------------------------------------------------
# Базовая стратегия авторизации (абстракция)
# ---------------------------------------------------------------------------


class AuthStrategy(ABC):
    """Абстракция стратегии авторизации: получение заголовков с токеном."""

    @property
    @abstractmethod
    def session(self) -> Optional[AuthData]:
        """Текущая сессия после успешной авторизации."""
        ...

    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Есть ли активная сессия."""
        ...

    @abstractmethod
    def token_is_fresh(self) -> bool:
        """Действителен ли текущий access-токен (с учётом запаса по времени)."""
        ...
