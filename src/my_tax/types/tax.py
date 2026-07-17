"""
DTO налогов: ставка, бонус (вычет), начисления и платежи.

Все суммы ФНС отдаёт числами с плавающей точкой — принимаем их в Decimal через
str(), чтобы не тащить бинарную погрешность в денежные расчёты.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field

from ..enums.general import ClientType
from ..constants import TAX_RATES, BONUS_RATES, BONUS_LIMIT

from ._base import AtomDateTime, DecimalOrZero


def _kopecks(value: Decimal) -> Decimal:
    """Округление до копеек (ФНС считает налог по чеку с точностью до копейки)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Ставка
# ---------------------------------------------------------------------------


class TaxRate(BaseModel):
    """
    Ставка НПД для типа клиента.

    API ЛК НПД ставку не возвращает: она однозначно определяется типом клиента
    в чеке, поэтому считается локально.
    """

    client_type: ClientType = Field(
        ...,
        description="Тип клиента, для которого действует ставка"
    )

    rate: Decimal = Field(
        ...,
        description="Базовая ставка налога (0.04 — физлицо, 0.06 — юрлицо)"
    )

    bonus_rate: Decimal = Field(
        ...,
        description="Доля дохода, которую гасит бонус (0.01 — физлицо, 0.02 — юрлицо)"
    )

    @computed_field
    @property
    def effective_rate(self) -> Decimal:
        """Ставка с учётом бонуса, пока он не исчерпан (0.03 — физлицо, 0.04 — юрлицо)."""
        return self.rate - self.bonus_rate


def rate_for(client_type: ClientType) -> TaxRate:
    """Ставка НПД для типа клиента."""
    return TaxRate(
        client_type=client_type,
        rate=TAX_RATES[client_type.value],
        bonus_rate=BONUS_RATES[client_type.value],
    )


# ---------------------------------------------------------------------------
# Бонус (налоговый вычет)
# ---------------------------------------------------------------------------


class TaxBonus(BaseModel):
    """Остаток налогового бонуса (GET /taxpayer/bonus)."""

    model_config = ConfigDict(populate_by_name=True)

    amount: Decimal = Field(
        ...,
        description="Остаток бонуса, ₽",
        alias="bonusAmount"
    )

    @computed_field
    @property
    def limit(self) -> Decimal:
        """Базовый лимит бонуса, ₽. См. BONUS_LIMIT — не является жёстким потолком."""
        return BONUS_LIMIT

    @computed_field
    @property
    def spent(self) -> Decimal:
        """
        Израсходовано бонуса, ₽.

        Оценка «лимит минус остаток»: API израсходованную часть не отдаёт.
        При остатке выше базового лимита возвращает 0, а не отрицательную величину.
        """
        return max(Decimal("0"), BONUS_LIMIT - self.amount)

    def is_exhausted(self) -> bool:
        """Проверка, исчерпан ли бонус"""
        return self.amount <= 0


# ---------------------------------------------------------------------------
# Расчёт налога по сумме
# ---------------------------------------------------------------------------


class TaxEstimate(BaseModel):
    """
    Расчёт налога по одной операции.

    ФНС не раскрывает налог и бонус в разрезе отдельного чека — только суммарно
    за период (см. TaxCharge). Поэтому разбивка по чеку считается локально и
    является оценкой: фактическое начисление приходит раз в месяц.
    """

    amount: Decimal = Field(
        ...,
        description="Сумма операции, ₽"
    )

    client_type: ClientType = Field(
        ...,
        description="Тип клиента"
    )

    rate: Decimal = Field(
        ...,
        description="Базовая ставка налога"
    )

    nominal_tax: Decimal = Field(
        ...,
        description="Налог по базовой ставке, до вычета бонуса, ₽"
    )

    bonus_applied: Decimal = Field(
        ...,
        description="Сколько бонуса списано на эту операцию, ₽"
    )

    @computed_field
    @property
    def tax(self) -> Decimal:
        """Налог к уплате с учётом бонуса, ₽."""
        return _kopecks(self.nominal_tax - self.bonus_applied)

    @computed_field
    @property
    def effective_rate(self) -> Decimal:
        """Фактическая ставка по операции: налог к уплате / сумма."""
        if self.amount == 0:
            return Decimal("0")
        return (self.tax / self.amount).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def estimate_tax(
    amount: Decimal,
    client_type: ClientType = ClientType.FROM_INDIVIDUAL,
    bonus_available: Optional[Decimal] = None,
) -> TaxEstimate:
    """
    Расчёт налога по сумме операции.

    Args:
        amount: Сумма операции, ₽.
        client_type: Тип клиента — определяет ставку (4% физлицо / 6% юрлицо).
        bonus_available: Остаток бонуса, ₽. None — бонус считается неограниченным,
            0 — бонус исчерпан и налог берётся по полной ставке. Списание
            ограничено остатком: если бонуса меньше расчётного, гасится сколько есть.
    """
    tax_rate = rate_for(client_type)

    nominal_tax = _kopecks(amount * tax_rate.rate)
    bonus = _kopecks(amount * tax_rate.bonus_rate)

    if bonus_available is not None:
        bonus = _kopecks(min(bonus, max(Decimal("0"), bonus_available)))

    return TaxEstimate(
        amount=amount,
        client_type=client_type,
        rate=tax_rate.rate,
        nominal_tax=nominal_tax,
        bonus_applied=bonus,
    )


# ---------------------------------------------------------------------------
# Сводка по налогу
# ---------------------------------------------------------------------------


class TaxSummary(BaseModel):
    """Текущее состояние по налогу (GET /taxes)."""

    model_config = ConfigDict(populate_by_name=True)

    total_for_payment: Decimal = Field(
        ...,
        description="Итого к оплате, ₽",
        alias="totalForPayment"
    )

    total: Decimal = Field(
        ...,
        description="Общая сумма начислений, ₽"
    )

    tax: Decimal = Field(
        ...,
        description="Налог, ₽"
    )

    debt: Decimal = Field(
        default=Decimal("0"),
        description="Задолженность, ₽"
    )

    overpayment: Decimal = Field(
        default=Decimal("0"),
        description="Переплата, ₽"
    )

    penalty: Decimal = Field(
        default=Decimal("0"),
        description="Пени, ₽"
    )

    nominal_tax: Optional[Decimal] = Field(
        default=None,
        description="Налог до вычета бонуса, ₽",
        alias="nominalTax"
    )

    nominal_overpayment: Optional[Decimal] = Field(
        default=None,
        description="Переплата до вычета бонуса, ₽",
        alias="nominalOverpayment"
    )

    tax_period_id: Optional[int] = Field(
        default=None,
        description="ID текущего налогового периода",
        alias="taxPeriodId"
    )

    last_payment_amount: Optional[Decimal] = Field(
        default=None,
        description="Сумма последнего платежа, ₽",
        alias="lastPaymentAmount"
    )

    last_payment_date: Optional[AtomDateTime] = Field(
        default=None,
        description="Дата последнего платежа",
        alias="lastPaymentDate"
    )

    regions: Optional[List[Any]] = Field(
        default_factory=list,
        description="Регионы постановки на учёт"
    )


# ---------------------------------------------------------------------------
# Начисления
# ---------------------------------------------------------------------------


class TaxCharge(BaseModel):
    """
    Начисление налога за период (POST /taxes/history).

    Агрегат по налоговому периоду и ОКТМО — именно здесь ФНС раскрывает налог,
    списанный бонус и срок уплаты. Разбивки по отдельным чекам нет,
    есть только их количество (receipt_count).
    """

    model_config = ConfigDict(populate_by_name=True)

    tax_period_id: int = Field(
        ...,
        description="ID налогового периода (YYYYMM)",
        alias="taxPeriodId"
    )

    tax_amount: Decimal = Field(
        ...,
        description="Начисленный налог, ₽",
        alias="taxAmount"
    )

    bonus_amount: DecimalOrZero = Field(
        default=Decimal("0"),
        description="Списано бонуса за период, ₽",
        alias="bonusAmount"
    )

    paid_amount: DecimalOrZero = Field(
        default=Decimal("0"),
        description="Оплачено, ₽",
        alias="paidAmount"
    )

    tax_base_amount: Optional[Decimal] = Field(
        default=None,
        description=(
            "Налоговая база (задекларированный доход за период), ₽. "
            "API часто отдаёт null — базу можно вывести из tax_amount и ставки, "
            "поэтому None здесь значит «не отдано», а не «ноль»"
        ),
        alias="taxBaseAmount"
    )

    charge_date: Optional[AtomDateTime] = Field(
        default=None,
        description="Дата начисления",
        alias="chargeDate"
    )

    due_date: Optional[AtomDateTime] = Field(
        default=None,
        description="Срок уплаты",
        alias="dueDate"
    )

    oktmo: Optional[str] = Field(
        default=None,
        description="Код ОКТМО"
    )

    region_name: Optional[str] = Field(
        default=None,
        description="Название региона",
        alias="regionName"
    )

    kbk: Optional[str] = Field(
        default=None,
        description="КБК"
    )

    tax_organ_code: Optional[str] = Field(
        default=None,
        description="Код налогового органа",
        alias="taxOrganCode"
    )

    type: Optional[str] = Field(
        default=None,
        description="Тип начисления (ACCRUED_CORRECTION / REDUCED_CORRECTION и др.)"
    )

    krsb_tax_charge_id: Optional[int] = Field(
        default=None,
        description="ID начисления в КРСБ",
        alias="krsbTaxChargeId"
    )

    receipt_count: Optional[int] = Field(
        default=None,
        description="Количество чеков в начислении",
        alias="receiptCount"
    )

    @computed_field
    @property
    def unpaid_amount(self) -> Decimal:
        """
        Остаток к уплате за период, ₽.

        tax_amount — налог по полной ставке, бонус его гасит: к уплате остаётся
        tax_amount − bonus_amount (именно эту сумму ЛК показывает как «К оплате»).
        """
        return max(Decimal("0"), self.tax_amount - self.bonus_amount - self.paid_amount)

    def is_paid(self) -> bool:
        """Проверка, погашено ли начисление"""
        return self.unpaid_amount <= 0

    def get_base(self, client_type: ClientType = ClientType.FROM_INDIVIDUAL) -> Decimal:
        """
        Налоговая база за период, ₽.

        API часто не отдаёт taxBaseAmount — тогда база выводится из начисленного
        налога и ставки (tax_amount = база × ставка).
        """
        if self.tax_base_amount is not None:
            return self.tax_base_amount

        rate = rate_for(client_type).rate
        if rate <= 0:
            return Decimal("0")
        return _kopecks(self.tax_amount / rate)

    def get_bonus_ratio(self, client_type: ClientType = ClientType.FROM_INDIVIDUAL) -> Decimal:
        """
        Доля, с которой бонус применялся в периоде: 1 — полностью, 0 — не применялся.

        Полный бонус за период — это tax_amount × (ставка_бонуса / ставка), так что
        доля считается без налоговой базы, которую API может не отдать.
        """
        tax_rate = rate_for(client_type)
        if self.tax_amount <= 0 or tax_rate.rate <= 0:
            return Decimal("0")

        full_bonus = self.tax_amount * (tax_rate.bonus_rate / tax_rate.rate)
        if full_bonus <= 0:
            return Decimal("0")

        return min(Decimal("1"), max(Decimal("0"), self.bonus_amount / full_bonus))


class TaxHistory(BaseModel):
    """Список начислений (POST /taxes/history)."""

    model_config = ConfigDict(populate_by_name=True)

    records: List[TaxCharge] = Field(
        default_factory=list,
        description="Начисления"
    )

    def get_total_tax(self) -> Decimal:
        """Суммарный начисленный налог, ₽"""
        return sum((record.tax_amount for record in self.records), Decimal("0"))

    def get_total_bonus(self) -> Decimal:
        """Суммарно списано бонуса, ₽"""
        return sum((record.bonus_amount for record in self.records), Decimal("0"))

    def get_total_base(self, client_type: ClientType = ClientType.FROM_INDIVIDUAL) -> Decimal:
        """
        Суммарная налоговая база (задекларировано), ₽.

        Там, где API не отдал taxBaseAmount, база выводится из налога и ставки —
        см. TaxCharge.get_base().
        """
        return sum((record.get_base(client_type) for record in self.records), Decimal("0"))


# ---------------------------------------------------------------------------
# Платежи по налогу
# ---------------------------------------------------------------------------


class TaxPayment(BaseModel):
    """Платёж по налогу (POST /taxes/payments)."""

    model_config = ConfigDict(populate_by_name=True)

    amount: Decimal = Field(
        ...,
        description="Сумма платежа, ₽"
    )

    source_type: Optional[str] = Field(
        default=None,
        description="Источник платежа",
        alias="sourceType"
    )

    type: Optional[str] = Field(
        default=None,
        description="Тип платежа"
    )

    document_index: Optional[str] = Field(
        default=None,
        description="Индекс документа (УИН)",
        alias="documentIndex"
    )

    operation_date: Optional[AtomDateTime] = Field(
        default=None,
        description="Дата операции",
        alias="operationDate"
    )

    due_date: Optional[AtomDateTime] = Field(
        default=None,
        description="Срок уплаты",
        alias="dueDate"
    )

    oktmo: Optional[str] = Field(
        default=None,
        description="Код ОКТМО"
    )

    kbk: Optional[str] = Field(
        default=None,
        description="КБК"
    )

    status: Optional[str] = Field(
        default=None,
        description="Статус платежа"
    )

    tax_period_id: Optional[int] = Field(
        default=None,
        description="ID налогового периода",
        alias="taxPeriodId"
    )

    region_name: Optional[str] = Field(
        default=None,
        description="Название региона",
        alias="regionName"
    )

    krsb_accepted_date: Optional[AtomDateTime] = Field(
        default=None,
        description="Дата принятия в КРСБ",
        alias="krsbAcceptedDate"
    )


class TaxPayments(BaseModel):
    """Список платежей по налогу (POST /taxes/payments)."""

    model_config = ConfigDict(populate_by_name=True)

    records: List[TaxPayment] = Field(
        default_factory=list,
        description="Платежи"
    )

    def get_total(self) -> Decimal:
        """Суммарно оплачено, ₽"""
        return sum((record.amount for record in self.records), Decimal("0"))


# ---------------------------------------------------------------------------
# Регионы
# ---------------------------------------------------------------------------


class Region(BaseModel):
    """Регион из справочника (GET /region)."""

    model_config = ConfigDict(populate_by_name=True)

    oktmo: Optional[str] = Field(
        default=None,
        description="Код ОКТМО"
    )

    name: Optional[str] = Field(
        default=None,
        description="Название региона"
    )


class ListRegions(BaseModel):
    """Справочник регионов (GET /region)."""

    model_config = ConfigDict(populate_by_name=True)

    items: List[Region] = Field(
        default_factory=list,
        description="Регионы"
    )

    unavailable: Optional[List[Any]] = Field(
        default_factory=list,
        description="Недоступные регионы"
    )

    def find_by_oktmo(self, oktmo: str) -> Optional[Region]:
        """Поиск региона по коду ОКТМО"""
        for item in self.items:
            if item.oktmo == oktmo:
                return item
        return None
