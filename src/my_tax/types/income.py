"""
DTO чека
"""

from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Any, cast
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer, model_validator

from ..enums.general import ClientType
from ..enums.income import (
    IncomePaymentType,
    CancelReason,
    SearchIncomesSortBy,
    SearchIncomesClientFilter,
    SearchIncomesStatusFilter
)

from ._base import (
    AtomDateTime,
    atom_datetime_now,
    PositiveDecimal,
    StrNonEmpty,
    StrStripNone
)


# ---------------------------------------------------------------------------
# Создание чека
# ---------------------------------------------------------------------------
class CreateIncomeItem(BaseModel):
    """Вложенный объект услуги в запросе на создание чека"""

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
        description="Количество услуги"
    )

    @field_serializer("amount", "quantity")
    def serialize_decimal(self, value: Decimal) -> str:
        """Сериализация Decimal в строку"""
        return str(value)

    def get_total(self) -> Decimal:
        """Получение общей стоимости услуги"""
        return self.amount * self.quantity


class CreateIncomeClient(BaseModel):
    """Вложенный объект клиента в запросе на создание чека"""

    model_config = ConfigDict(populate_by_name=True)

    type: Optional[ClientType] = Field(
        default=ClientType.FROM_INDIVIDUAL,
        description="Тип клиента",
        validation_alias="incomeType",
        serialization_alias="incomeType",
    )

    phone: StrStripNone = Field(
        default=None,
        description="Телефон клиента",
        validation_alias="contactPhone",
        serialization_alias="contactPhone",
    )

    name: StrStripNone = Field(
        default=None,
        description="Имя клиента",
        validation_alias="displayName",
        serialization_alias="displayName",
    )

    inn: StrStripNone = Field(
        default=None,
        description="ИНН клиента",
        min_length=10,
        max_length=12,
        pattern=r"^\d{10,12}$"
    )

    @model_validator(mode="after")
    def check_legal_entity_fields(self) -> "CreateIncomeClient":
        """Проверка обязательных полей для юр. лица / иностр. агентства."""
        if self.type in (ClientType.FROM_LEGAL_ENTITY, ClientType.FROM_FOREIGN_AGENCY):
            if not self.name:
                raise ValueError("Название клиента обязательно для юр. лица / иностр. агентства")
        if self.type == ClientType.FROM_LEGAL_ENTITY:
            if not self.inn:
                raise ValueError("ИНН обязателен для юр. лица")
        return self


class CreateIncome(BaseModel):
    """Запрос на создание чека"""

    model_config = ConfigDict(populate_by_name=True)

    operation_time: AtomDateTime = Field(
        default_factory=atom_datetime_now,
        description="Время операции",
        validation_alias="operationTime",
        serialization_alias="operationTime",
    )

    request_time: AtomDateTime = Field(
        default_factory=atom_datetime_now,
        description="Время запроса",
        validation_alias="requestTime",
        serialization_alias="requestTime",
    )

    services: List[CreateIncomeItem] = Field(
        ...,
        description="Услуги",
        min_length=1,
        validation_alias="services",
        serialization_alias="services",
    )

    @computed_field(alias="totalAmount")
    def total_amount(self) -> PositiveDecimal:
        """Общая стоимость услуг (сумма по services)."""
        total: Decimal = sum(service.get_total() for service in self.services)
        return cast(PositiveDecimal, total)

    client: CreateIncomeClient = Field(
        default_factory=CreateIncomeClient,
        description="Клиент",
    )

    payment_type: IncomePaymentType = Field(
        default=IncomePaymentType.CASH,
        description="Тип оплаты",
        validation_alias="paymentType",
        serialization_alias="paymentType",
    )

    ignore_max_total_income_restriction: bool = Field(
        default=False,
        validation_alias="ignoreMaxTotalIncomeRestriction",
        serialization_alias="ignoreMaxTotalIncomeRestriction",
    )

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: PositiveDecimal) -> str:
        """Сериализация Decimal в строку"""
        return str(value)


# ---------------------------------------------------------------------------
# Чек
# ---------------------------------------------------------------------------
class CancelationInfo(BaseModel):
    """Вложенный объект информации об отмене чека"""

    operation_time: AtomDateTime = Field(
        ...,
        description="Время операции",
        alias="operationTime"
    )

    register_time: AtomDateTime = Field(
        ...,
        description="Время регистрации",
        alias="registerTime"
    )

    tax_period_id: int = Field(
        ...,
        description="ID налогового периода",
        alias="taxPeriodId"
    )

    comment: CancelReason = Field(
        ...,
        description="Комментарий"
    )


class IncomeItem(BaseModel):
    """Вложенный объект информации о чеке"""

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
        description="Количество услуги"
    )

    service_number: int = Field(
        ...,
        description="Номер услуги",
        alias="serviceNumber"
    )

    @field_serializer("amount", "quantity")
    def serialize_decimal(self, value: Decimal) -> str:
        """Сериализация Decimal в строку"""
        return str(value)

    def get_total(self) -> Decimal:
        """Получение общей стоимости услуги"""
        return self.amount * self.quantity


class Income(BaseModel):
    """Информация о чеке"""

    model_config = ConfigDict(populate_by_name=True)

    uuid: StrNonEmpty = Field(
        ...,
        description="UUID чека",
        alias="approvedReceiptUuid"
    )

    name: StrNonEmpty = Field(
        ...,
        description="Название чека"
    )

    payment_type: IncomePaymentType = Field(
        ...,
        description="Тип оплаты",
        alias="paymentType"
    )

    client_type: ClientType = Field(
        ...,
        description="Тип клиента",
        alias="incomeType"
    )

    client_inn: Optional[str] = Field(
        default=None,
        description="ИНН клиента",
        alias="clientInn"
    )

    client_name: Optional[str] = Field(
        default=None,
        description="Название клиента",
        alias="clientDisplayName"
    )

    services: List[IncomeItem] = Field(
        ...,
        description="Услуги"
    )

    total_amount: PositiveDecimal = Field(
        ...,
        description="Общая стоимость услуг",
        alias="totalAmount"
    )

    tax_period_id: int = Field(
        ...,
        description="ID налогового периода",
        alias="taxPeriodId"
    )

    partner_code: Optional[str] = Field(
        default=None,
        description="Код партнера",
        alias="partnerCode"
    )

    partner_inn: Optional[str] = Field(
        default=None,
        description="ИНН партнера",
        alias="partnerInn"
    )

    partner_display_name: Optional[str] = Field(
        default=None,
        description="Название партнера",
        alias="partnerDisplayName"
    )

    partner_logo: Optional[str] = Field(
        default=None,
        description="Логотип партнера",
        alias="partnerLogo"
    )

    source_device_id: Optional[str] = Field(
        default=None,
        description="ID устройства",
        alias="sourceDeviceId"
    )

    profession: Optional[str] = Field(
        default=None,
        description="Профессия"
    )

    description: Optional[List[Any]] = Field(
        default_factory=list,
        description="Описание"
    )

    invoice_id: Optional[str] = Field(
        default=None,
        description="ID счёта",
        alias="invoiceId"
    )

    cancelation_info: Optional[CancelationInfo] = Field(
        default=None,
        description="Информация об отмене чека",
        alias="cancelationInfo"
    )

    operation_time: AtomDateTime = Field(
        ...,
        description="Время операции",
        alias="operationTime"
    )

    request_time: AtomDateTime = Field(
        ...,
        description="Время запроса",
        alias="requestTime"
    )

    register_time: AtomDateTime = Field(
        ...,
        description="Время регистрации",
        alias="registerTime"
    )


# ---------------------------------------------------------------------------
# Список чеков
# ---------------------------------------------------------------------------
class ListIncomes(BaseModel):
    """Ответ со списком чеков"""

    model_config = ConfigDict(populate_by_name=True)

    content: List[Income] = Field(
        ...,
        description="Список чеков"
    )

    has_more: bool = Field(
        ...,
        description="Есть ли еще чеки",
        alias="hasMore"
    )

    offset: int = Field(
        ...,
        description="Сдвиг",
        alias="currentOffset"
    )

    limit: int = Field(
        ...,
        description="Лимит",
        alias="currentLimit"
    )


class SearchIncomes(BaseModel):
    """Запрос на поиск чеков (с пагинацией и фильтрацией)"""

    model_config = ConfigDict(populate_by_name=True)

    from_date: Optional[AtomDateTime] = Field(
        default_factory=lambda: datetime.now(timezone.utc) - timedelta(days=30),
        description="Дата начала периода",
        validation_alias="from",
        serialization_alias="from",
    )

    to_date: Optional[AtomDateTime] = Field(
        default_factory=atom_datetime_now,
        description="Дата окончания периода",
        validation_alias="to",
        serialization_alias="to",
    )

    sort_by: Optional[SearchIncomesSortBy] = Field(
        default=SearchIncomesSortBy.DATE_DESC,
        description="Сортировка",
        validation_alias="sortBy",
        serialization_alias="sortBy",
    )

    client_filter: Optional[SearchIncomesClientFilter] = Field(
        default=None,
        description="Фильтр по клиенту",
        validation_alias="buyerType",
        serialization_alias="buyerType",
    )

    status_filter: Optional[SearchIncomesStatusFilter] = Field(
        default=None,
        description="Фильтр по статусу",
        validation_alias="receiptType",
        serialization_alias="receiptType",
    )

    limit: Optional[int] = Field(
        default=50,
        description="Лимит"
    )

    offset: Optional[int] = Field(
        default=0,
        description="Сдвиг"
    )


# ---------------------------------------------------------------------------
# Отмена чека
# ---------------------------------------------------------------------------
class CancelIncome(BaseModel):
    """Запрос на отмену чека"""

    model_config = ConfigDict(populate_by_name=True)

    operation_time: AtomDateTime = Field(
        default_factory=atom_datetime_now,
        description="Время операции",
        validation_alias="operationTime",
        serialization_alias="operationTime",
    )

    request_time: AtomDateTime = Field(
        default_factory=atom_datetime_now,
        description="Время запроса",
        validation_alias="requestTime",
        serialization_alias="requestTime",
    )

    comment: CancelReason = Field(
        ...,
        description="Причина отмены"
    )

    receipt_uuid: StrNonEmpty = Field(
        ...,
        description="UUID чека",
        validation_alias="receiptUuid",
        serialization_alias="receiptUuid",
    )

    partner_code: Optional[str] = Field(
        default=None,
        description="Код партнера",
        validation_alias="partnerCode",
        serialization_alias="partnerCode",
    )


# ---------------------------------------------------------------------------
# Отмененный чек
# ---------------------------------------------------------------------------
class CanceledIncome(BaseModel):
    """Вложенный объект информации об отмене чека"""

    model_config = ConfigDict(populate_by_name=True)

    uuid: StrNonEmpty = Field(
        ...,
        description="UUID чека",
        alias="approvedReceiptUuid"
    )

    name: StrNonEmpty = Field(
        ...,
        description="Название чека"
    )

    payment_type: IncomePaymentType = Field(
        ...,
        description="Тип оплаты",
        alias="paymentType"
    )

    total_amount: PositiveDecimal = Field(
        ...,
        description="Общая стоимость услуг",
        alias="totalAmount"
    )

    partner_code: Optional[str] = Field(
        default=None,
        description="Код партнера",
        alias="partnerCode"
    )

    source_device_id: Optional[str] = Field(
        default=None,
        description="ID устройства",
        alias="sourceDeviceId"
    )

    cancelation_info: Optional[CancelationInfo] = Field(
        default=None,
        description="Информация об отмене чека",
        alias="cancelationInfo"
    )

    operation_time: AtomDateTime = Field(
        ...,
        description="Время операции",
        alias="operationTime"
    )

    request_time: AtomDateTime = Field(
        ...,
        description="Время запроса",
        alias="requestTime"
    )
