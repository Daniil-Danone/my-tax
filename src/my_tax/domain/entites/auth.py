"""DTO авторизации: учётные данные, токен, сессия, устройство, SMS-челлендж."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Credentials(BaseModel):
    """Логин и пароль для авторизации по ИНН."""

    model_config = ConfigDict(frozen=True)

    username: str
    password: str


class Token(BaseModel):
    """Access- и refresh-токены с датами истечения."""

    model_config = ConfigDict(arbitrary_types_allowed=False)

    access_token: str
    access_expire_in: datetime
    refresh_token: str
    refresh_expire_in: datetime


class AuthData(BaseModel):
    """Результат авторизации: профиль и токен."""

    inn: str
    token: Token
    display_name: Optional[str] = None


class DeviceInfo(BaseModel):
    """Информация об устройстве для тела запросов к API."""

    source_device_id: str
    source_type: str = "WEB"
    app_version: str = "1.0.0"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
    )

    def to_payload(self) -> dict:
        """Словарь для поля deviceInfo в запросе (camelCase)."""
        return {
            "sourceDeviceId": self.source_device_id,
            "sourceType": self.source_type,
            "appVersion": self.app_version,
            "metaDetails": {"userAgent": self.user_agent},
        }


class SmsChallengeState(BaseModel):
    """Состояние после старта SMS-челленджа (до верификации кода)."""

    phone: str
    challenge_token: str
