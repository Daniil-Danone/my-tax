"""DTO пользователя: профиль (ответ GET /user)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    """Профиль пользователя ЛК НПД (ответ GET /user)."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    inn: str = ""
    login: str = ""
    display_name: str = Field(default="", alias="displayName")
    email: str = ""
    phone: str = ""
    snils: str = ""
    avatar_exists: bool = Field(default=False, alias="avatarExists")
    status: str = ""
    restricted_mode: bool = Field(default=False, alias="restrictedMode")
    pfr_url: str = Field(default="", alias="pfrUrl")
    hide_cancelled_receipt: bool = Field(default=False, alias="hideCancelledReceipt")
    last_name: Optional[str] = Field(default=None, alias="lastName")
    middle_name: Optional[str] = Field(default=None, alias="middleName")
    initial_registration_date: Optional[datetime] = Field(
        default=None, alias="initialRegistrationDate"
    )
    registration_date: Optional[datetime] = Field(
        default=None, alias="registrationDate"
    )
    first_receipt_register_time: Optional[datetime] = Field(
        default=None, alias="firstReceiptRegisterTime"
    )
    first_receipt_cancel_time: Optional[datetime] = Field(
        default=None, alias="firstReceiptCancelTime"
    )
    register_available: Optional[bool] = Field(
        default=None, alias="registerAvailable"
    )
