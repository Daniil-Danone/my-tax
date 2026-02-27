"""
DTO для справочника способов оплаты
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..enums.invoice import PaymentMethodType


class PaymentMethod(BaseModel):
    """Элемент справочника способов оплаты"""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="ID записи")
    type: PaymentMethodType = Field(..., description="ACCOUNT или PHONE")
    bank_name: Optional[str] = Field(default=None, alias="bankName")
    bank_bik: Optional[str] = Field(default=None, alias="bankBik")
    current_account: Optional[str] = Field(default=None, alias="currentAccount")
    corr_account: Optional[str] = Field(default=None, alias="corrAccount")
    phone: Optional[str] = Field(default=None)
    bank_id: Optional[int] = Field(default=None, alias="bankId")
    favorite: bool = Field(default=False, description="В избранном")
    available_for_pa: bool = Field(default=False, alias="availableForPa")


class ListPaymentMethods(BaseModel):
    """Ответ со списком способов оплаты"""

    items: List[PaymentMethod] = Field(
        default_factory=list,
        description="Список способов оплаты",
    )
