"""
Ручки API для ресурса «пользователь» (GET /user и др.).
"""

from datetime import datetime
from typing import Any, Optional

from .base import BaseAsyncApi, BaseSyncApi
from ..types import User


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    """Парсинг ISO datetime из строки. При ошибке или None — None."""
    if value is None or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def parse_user_response(data: dict[str, Any]) -> User:
    """Сборка User из JSON-ответа GET /user."""
    return User(
        id=int(data["id"]),
        inn=data.get("inn", ""),
        login=data.get("login", ""),
        display_name=data.get("displayName", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        snils=data.get("snils", ""),
        avatar_exists=data.get("avatarExists", False),
        status=data.get("status", ""),
        restricted_mode=data.get("restrictedMode", False),
        pfr_url=data.get("pfrUrl", ""),
        hide_cancelled_receipt=data.get("hideCancelledReceipt", False),
        last_name=data.get("lastName"),
        middle_name=data.get("middleName"),
        initial_registration_date=_parse_iso_datetime(
            data.get("initialRegistrationDate")
        ),
        registration_date=_parse_iso_datetime(data.get("registrationDate")),
        first_receipt_register_time=_parse_iso_datetime(
            data.get("firstReceiptRegisterTime")
        ),
        first_receipt_cancel_time=_parse_iso_datetime(
            data.get("firstReceiptCancelTime")
        ),
        register_available=data.get("registerAvailable"),
    )


class UserSyncApi(BaseSyncApi):
    """Синхронные ручки для ресурса пользователя (GET /user)."""

    def get_user(self) -> User:
        """Получение профиля текущего пользователя (GET /user)."""
        data = self._request_get("/user")
        return parse_user_response(data)


class UserAsyncApi(BaseAsyncApi):
    """Асинхронные ручки для ресурса пользователя (GET /user)."""

    async def get_user(self) -> User:
        """Получение профиля текущего пользователя (GET /user)."""
        data = await self._request_get("/user")
        return parse_user_response(data)
