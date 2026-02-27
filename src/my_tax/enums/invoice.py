"""
Enums для счетов на оплату (invoice) ЛК НПД
"""

from enum import Enum


class PaymentMethodType(str, Enum):
    """Способ оплаты (рассчётный счёт/телефон)"""

    ACCOUNT = "ACCOUNT"
    PHONE = "PHONE"


class InvoiceStatus(str, Enum):
    """Статус счёта на оплату"""

    CREATED = "CREATED"
    TO_PAYMENT = "TO_PAYMENT"
    FUND_RECEIVED = "FUND_RECEIVED"
    PAID = "PAID"
    PAID_WITH_RECEIPT = "PAID_WITH_RECEIPT"
    PAID_WITHOUT_RECEIPT = "PAID_WITHOUT_RECEIPT"
    CANCELLED = "CANCELLED"


class InvoiceStatusFilter(str, Enum):
    """Значение фильтра по статусу при запросе списка счетов на оплату"""

    ALL = "ALL"
    CREATED = "CREATED"
    TO_PAYMENT = "TO_PAYMENT"
    FUND_RECEIVED = "FUND_RECEIVED"
    PAID = "PAID"
    PAID_WITH_RECEIPT = "PAID_WITH_RECEIPT"
    PAID_WITHOUT_RECEIPT = "PAID_WITHOUT_RECEIPT"
    CANCELLED = "CANCELLED"
