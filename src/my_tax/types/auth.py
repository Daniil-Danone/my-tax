"""DTO авторизации: учётные данные, токен, сессия, устройство, SMS-челлендж."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Credentials(BaseModel):
    """Логин и пароль для авторизации по ИНН."""

    model_config = ConfigDict(frozen=True)

    username: str
    password: str


class Token(BaseModel):
    """Access- и refresh-токены с датами истечения."""

    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(
        ...,
        description="Access-токен",
        alias="token"
    )

    access_expire_in: datetime = Field(
        ...,
        description="Время истечения Access-токена",
        alias="tokenExpireIn"
    )

    refresh_token: str = Field(
        ...,
        description="Refresh-токен",
        alias="refreshToken"
    )

    refresh_expire_in: Optional[datetime] = Field(
        default=None,
        description="Время истечения Refresh-токена",
        alias="refreshTokenExpiresIn"
    )


class AuthData(BaseModel):
    """Результат авторизации: профиль и токен."""

    inn: str = Field(
        ...,
        description="ИНН пользователя"
    )

    token: Token = Field(
        ...,
        description="Токен авторизации"
    )

    display_name: Optional[str] = Field(
        default=None,
        description="Имя пользователя"
    )


class DeviceInfo(BaseModel):
    """Информация об устройстве для тела запросов к API."""

    source_device_id: str
    source_type: str = "WEB"
    app_version: str = "1.0.0"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"
    )

    def to_payload(self) -> dict:
        """Словарь для поля deviceInfo в запросе (camelCase)."""
        return {
            "sourceDeviceId": self.source_device_id,
            "sourceType": self.source_type,
            "appVersion": self.app_version,
            "metaDetails": {"userAgent": self.user_agent},
        }
