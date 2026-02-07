"""Типы данных для авторизации и API."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Credentials:
    """Логин и пароль для авторизации по ИНН"""

    username: str
    password: str


@dataclass
class Token:
    """Access и refresh токены с сроком действия"""

    access_token: str
    access_expire_in: datetime
    refresh_token: str
    refresh_expire_in: datetime


@dataclass
class AuthData:
    """Результат авторизации"""

    inn: str
    token: Token
    display_name: Optional[str] = None


@dataclass
class DeviceInfo:
    """Информация о устройстве для запросов"""

    source_device_id: str
    source_type: str = "WEB"
    app_version: str = "1.0.0"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
    )

    def to_payload(self) -> dict:
        return {
            "sourceDeviceId": self.source_device_id,
            "sourceType": self.source_type,
            "appVersion": self.app_version,
            "metaDetails": {"userAgent": self.user_agent},
        }


@dataclass
class SmsChallengeState:
    """Состояние после начала SMS-челленджа (перед верификацией)"""

    phone: str
    challenge_token: str


@dataclass
class User:
    """Профиль пользователя ЛК НПД (ответ GET /user)."""

    id: int
    inn: str
    login: str
    display_name: str
    email: str
    phone: str
    snils: str
    avatar_exists: bool
    status: str
    restricted_mode: bool
    pfr_url: str
    hide_cancelled_receipt: bool
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    initial_registration_date: Optional[datetime] = None
    registration_date: Optional[datetime] = None
    first_receipt_register_time: Optional[datetime] = None
    first_receipt_cancel_time: Optional[datetime] = None
    register_available: Optional[bool] = None
