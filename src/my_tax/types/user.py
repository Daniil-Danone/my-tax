"""
DTO пользователя
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from ._base import AtomDateTime


class User(BaseModel):
    """Профиль пользователя ЛК НПД"""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(
        ...,
        description="ID пользователя"
    )

    inn: str = Field(
        ...,
        description="ИНН пользователя"
    )

    login: str = Field(
        ...,
        description="Логин пользователя"
    )

    last_name: Optional[str] = Field(
        ...,
        description="Фамилия пользователя",
        alias="lastName"
    )

    display_name: str = Field(
        ...,
        description="Имя пользователя",
        alias="displayName"
    )

    middle_name: Optional[str] = Field(
        ...,
        description="Отчество пользователя",
        alias="middleName"
    )

    email: str = Field(
        ...,
        description="Email пользователя"
    )

    phone: str = Field(
        ...,
        description="Телефон пользователя"
    )

    snils: str = Field(
        ...,
        description="СНИЛС пользователя"
    )

    avatar_exists: bool = Field(
        ...,
        description="Флаг наличия аватара пользователя",
        alias="avatarExists"
    )

    status: str = Field(
        ...,
        description="Статус пользователя"
    )

    restricted_mode: bool = Field(
        ...,
        description="Режим ограничения пользователя",
        alias="restrictedMode"
    )

    pfr_url: str = Field(
        ...,
        description="URL ПФР пользователя",
        alias="pfrUrl"
    )

    hide_canceled_receipt: bool = Field(
        ...,
        description="Флаг скрытия отмененных чеков",
        alias="hideCancelledReceipt"
    )

    initial_registration_date: Optional[AtomDateTime] = Field(
        ...,
        description="Дата начальной регистрации пользователя",
        alias="initialRegistrationDate"
    )

    registration_date: Optional[AtomDateTime] = Field(
        ...,
        description="Дата регистрации пользователя",
        alias="registrationDate"
    )

    first_receipt_register_time: Optional[AtomDateTime] = Field(
        ...,
        description="Дата первого регистра чека пользователя",
        alias="firstReceiptRegisterTime"
    )

    first_receipt_cancel_time: Optional[AtomDateTime] = Field(
        ...,
        description="Дата первой отмены чека пользователя",
        alias="firstReceiptCancelTime"
    )

    register_available: Optional[bool] = Field(
        ...,
        description="Флаг наличия регистрации пользователя",
        alias="registerAvailable"
    )

    def is_avatar_exists(self) -> bool:
        """Проверка, существует ли аватар пользователя"""
        return self.avatar_exists

    def is_active(self) -> bool:
        """Проверка, является ли пользователь активным"""
        return self.status == "ACTIVE"

    def is_restricted_mode(self) -> bool:
        """Проверка, находится ли пользователь в режиме ограничения"""
        return self.restricted_mode

    def is_hide_canceled_receipt(self) -> bool:
        """Проверка, скрывают ли отмененные чеки пользователя"""
        return self.hide_canceled_receipt
