"""
DTO счёта на оплату
"""

from decimal import Decimal
from datetime import datetime
from typing import Any, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer, field_validator, model_validator

from ..enums.general import ClientType
from ..enums.invoice import (
    PaymentMethodType,
    InvoiceStatus,
    InvoiceStatusFilter
)

from ._base import PositiveDecimal, StrNonEmpty, StrStripNone


# ---------------------------------------------------------------------------
# Создание счёта на оплату
# ---------------------------------------------------------------------------
class CreateInvoiceItem(BaseModel):
    """Вложенный объект услуги в запросе на создание счёта на оплату"""

    model_config = ConfigDict(populate_by_name=True)

    name: StrNonEmpty = Field(
        ...,
        description="Название услуги"
    )

    amount: PositiveDecimal = Field(
        ...,
        description="Стоимость услуги"
    )

    quantity: PositiveDecimal = Field(
        ...,
        description="Количество"
    )

    service_number: int = Field(
        default=0,
        description="Номер услуги",
        validation_alias="serviceNumber",
        serialization_alias="serviceNumber",
    )

    @field_serializer("amount", "quantity")
    def serialize_decimal(self, value: Decimal) -> Union[str, float]:
        """Сериализация Decimal в строку или число для API."""
        return str(value)

    def get_total(self) -> Decimal:
        """Общая стоимость позиции (amount * quantity)."""
        return self.amount * self.quantity


class CreateInvoiceClient(BaseModel):
    """Вспомогательный объект для передачи клиента при создании счёта на оплату"""

    type: Optional[ClientType] = Field(
        default=ClientType.FROM_INDIVIDUAL,
        description="Тип клиента"
    )

    name: StrNonEmpty = Field(
        ...,
        description="Имя клиента"
    )

    phone: StrStripNone = Field(
        default=None,
        description="Телефон клиента"
    )

    email: StrStripNone = Field(
        default=None,
        description="Email клиента"
    )

    inn: StrStripNone = Field(
        default=None,
        description="ИНН клиента (для юр. лица)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not (value and str(value).strip()):
            raise ValueError("Название клиента не может быть пустым")
        return value

    @model_validator(mode="after")
    def check_legal_entity_inn(self) -> "CreateInvoiceClient":
        """Проверка ИНН для юридического лица."""
        if self.type == ClientType.FROM_LEGAL_ENTITY:
            if not self.inn:
                raise ValueError("ИНН клиента не может быть пустым для юридического лица")
        return self


class CreateInvoice(BaseModel):
    """Запрос на создание счёта на оплату"""

    model_config = ConfigDict(populate_by_name=True)

    payment_type: PaymentMethodType = Field(
        ...,
        description="Способ оплаты",
        validation_alias="paymentType",
        serialization_alias="paymentType",
    )

    bank_name: StrStripNone = Field(
        default=None,
        description="Название банка (для PaymentMethodType = ACCOUNT)",
        validation_alias="bankName",
        serialization_alias="bankName",
    )

    bank_bik: StrStripNone = Field(
        default=None,
        description="БИК банка (для PaymentMethodType = ACCOUNT)",
        validation_alias="bankBik",
        serialization_alias="bankBik",
    )

    corr_account: StrStripNone = Field(
        default=None,
        description="Корр. счёт (для PaymentMethodType = ACCOUNT)",
        validation_alias="corrAccount",
        serialization_alias="corrAccount",
    )

    current_account: StrStripNone = Field(
        default=None,
        description="Расчётный счёт (для PaymentMethodType = ACCOUNT)",
        validation_alias="currentAccount",
        serialization_alias="currentAccount",
    )

    phone: StrStripNone = Field(
        default=None,
        description="Номер телефона для оплаты (для PaymentMethodType = PHONE)",
    )

    client_type: ClientType = Field(
        default=ClientType.FROM_INDIVIDUAL,
        description="Тип клиента",
        validation_alias="clientType",
        serialization_alias="clientType",
    )

    client_name: StrNonEmpty = Field(
        ...,
        description="Имя клиента",
        validation_alias="clientName",
        serialization_alias="clientName",
    )

    client_phone: StrStripNone = Field(
        default=None,
        description="Телефон клиента",
        validation_alias="clientPhone",
        serialization_alias="clientPhone",
    )

    client_email: StrStripNone = Field(
        default=None,
        description="Email клиента",
        validation_alias="clientEmail",
        serialization_alias="clientEmail",
    )

    client_inn: StrStripNone = Field(
        default=None,
        description="ИНН клиента (для юр. лица)",
        validation_alias="clientInn",
        serialization_alias="clientInn",
    )

    type: str = Field(
        default="MANUAL",
        description="Тип счёта на оплату",
    )

    services: List[CreateInvoiceItem] = Field(
        ...,
        description="Услуги",
        min_length=1,
    )

    @computed_field(alias="totalAmount")
    def total_amount(self) -> str:
        """Сумма счёта на оплату (сумма по services); API ожидает строку."""
        total = sum(s.get_total() for s in self.services)
        return str(total)

    @field_validator("client_name")
    @classmethod
    def validate_client_name(cls, value: str) -> str:
        if not (value and str(value).strip()):
            raise ValueError("Название клиента не может быть пустым")
        return value

    @model_validator(mode="after")
    def check_legal_entity_inn(self) -> "CreateInvoice":
        """Проверка ИНН для юридического лица."""
        if self.client_type == ClientType.FROM_LEGAL_ENTITY:
            if not self.client_inn:
                raise ValueError("ИНН клиента не может быть пустым для юридического лица")
        return self


# ---------------------------------------------------------------------------
# Счёт на оплату
# ---------------------------------------------------------------------------
class InvoiceItem(BaseModel):
    """Вложенный объект услуги в счёте на оплату"""

    model_config = ConfigDict(populate_by_name=True)

    name: StrNonEmpty = Field(
        ...,
        description="Название услуги"
    )

    quantity: PositiveDecimal = Field(
        ...,
        description="Количество"
    )

    service_number: int = Field(
        ...,
        description="Номер услуги",
        alias="serviceNumber"
    )

    amount: PositiveDecimal = Field(
        ...,
        description="Стоимость услуги"
    )

    @field_serializer("amount", "quantity")
    def serialize_decimal(self, value: Decimal) -> Union[str, float]:
        """Сериализация Decimal для API."""
        return str(value)

    def get_total(self) -> Decimal:
        """Общая стоимость позиции."""
        return self.amount * self.quantity


class InvoiceReceipt(BaseModel):
    """Вложенный объект чека для счёта на оплату"""

    model_config = ConfigDict(populate_by_name=True)

    profession: Optional[str] = Field(
        default=None,
        description="Профессия"
    )

    receipt_phone: Optional[str] = Field(
        default=None,
        alias="receiptPhone"
    )

    receipt_email: Optional[str] = Field(
        default=None,
        alias="receiptEmail"
    )

    description: Optional[str] = Field(
        default=None
    )


class Invoice(BaseModel):
    """Счёт"""

    model_config = ConfigDict(populate_by_name=True)

    invoice_id: int = Field(
        ...,
        description="ID счёта на оплату",
        alias="invoiceId"
    )

    uuid: StrNonEmpty = Field(
        ...,
        description="UUID счёта на оплату"
    )

    receipt_id: Optional[int] = Field(
        default=None,
        alias="receiptId"
    )

    fid: int = Field(
        ...,
        description="ФИД"
    )

    type: str = Field(
        ...,
        description="Тип счёта на оплату"
    )

    status: InvoiceStatus = Field(
        ...,
        description="Статус счёта на оплату"
    )

    merchant_id: Optional[int] = Field(
        default=None,
        alias="merchantId"
    )

    acquirer_id: Optional[int] = Field(
        default=None,
        alias="acquirerId"
    )

    acquirer_name: Optional[str] = Field(
        default=None,
        alias="acquirerName"
    )

    payment_url: Optional[str] = Field(
        default=None,
        alias="paymentUrl"
    )

    payment_type: PaymentMethodType = Field(
        ...,
        alias="paymentType"
    )

    bank_name: Optional[str] = Field(
        default=None,
        alias="bankName"
    )

    bank_bik: Optional[str] = Field(
        default=None,
        alias="bankBik"
    )

    current_account: Optional[str] = Field(
        default=None,
        alias="currentAccount"
    )

    corr_account: Optional[str] = Field(
        default=None,
        alias="corrAccount"
    )

    phone: Optional[str] = Field(
        default=None
    )

    client_type: ClientType = Field(
        ...,
        alias="clientType"
    )

    client_name: StrNonEmpty = Field(
        ...,
        alias="clientName"
    )

    client_inn: Optional[str] = Field(
        default=None,
        alias="clientInn"
    )

    client_phone: Optional[str] = Field(
        default=None,
        alias="clientPhone"
    )

    client_email: Optional[str] = Field(
        default=None,
        alias="clientEmail"
    )

    total_amount: PositiveDecimal = Field(
        ...,
        alias="totalAmount"
    )

    total_tax: Optional[Decimal] = Field(
        default=None,
        alias="totalTax"
    )

    services: List[InvoiceItem] = Field(
        ...,
        description="Услуги"
    )

    created_at: Optional[datetime] = Field(
        default=None,
        alias="createdAt"
    )

    paid_at: Optional[datetime] = Field(
        default=None,
        alias="paidAt"
    )

    cancelled_at: Optional[datetime] = Field(
        default=None,
        alias="cancelledAt"
    )

    transition_page_url: Optional[str] = Field(
        default=None,
        alias="transitionPageURL"
    )

    commission: Optional[Any] = Field(
        default=None
    )

    receipt_template: Optional[InvoiceReceipt] = Field(
        default=None,
        alias="receiptTemplate",
    )

    auto_create_receipt: Optional[Any] = Field(
        default=None,
        alias="autoCreateReceipt"
    )

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Union[Decimal, int, float]) -> Union[str, int, float]:
        """Сохранение числа или строки как в API (в т.ч. 1E+1)."""
        if isinstance(value, Decimal):
            return str(value)
        return value


# ---------------------------------------------------------------------------
# Список счетов на оплату
# ---------------------------------------------------------------------------
class SearchInvoicesFilterItem(BaseModel):
    """Элемент фильтра списка счетов на оплату"""

    id: str = Field(
        ...,
        description="Идентификатор фильтра (status, context, from, to)"
    )

    value: Union[str, InvoiceStatusFilter, datetime, None] = Field(
        ...,
        description="Значение (строка, статус или дата)",
    )


class SearchInvoicesSortItem(BaseModel):
    """Элемент сортировки списка счетов на оплату"""

    id: str = Field(
        ...,
        description="Поле сортировки (например createdAt)"
    )

    desc: bool = Field(
        ...,
        description="По убыванию"
    )


class SearchInvoices(BaseModel):
    """Запрос списка счетов на оплату (offset, limit, filtered, sorted)"""

    offset: int = Field(
        default=0,
        description="Смещение"
    )

    limit: int = Field(
        default=10,
        description="Лимит"
    )

    filtered: List[SearchInvoicesFilterItem] = Field(
        default_factory=list,
        description="Фильтры",
    )

    sorted: List[SearchInvoicesSortItem] = Field(
        default_factory=list,
        description="Сортировка",
    )


class ListInvoices(BaseModel):
    """Ответ со списком счетов на оплату"""

    model_config = ConfigDict(populate_by_name=True)

    items: List[Invoice] = Field(
        ...,
        description="Счета на оплату"
    )

    has_more: bool = Field(
        ...,
        description="Есть ли ещё элементы",
        alias="hasMore"
    )

    current_offset: int = Field(
        ...,
        alias="currentOffset"
    )

    current_limit: int = Field(
        ...,
        alias="currentLimit"
    )
