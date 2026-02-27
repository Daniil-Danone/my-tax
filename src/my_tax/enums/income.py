"""
Enums для чеков
"""

from enum import Enum


class IncomePaymentType(str, Enum):
    """Метод оплаты"""

    CASH = "CASH"
    ACCOUNT = "ACCOUNT"


class CancelReason(str, Enum):
    """Причина отмены"""

    MISTAKE = "Чек сформирован ошибочно"
    REFUND = "Возврат средств"


class SearchIncomesClientFilter(str, Enum):
    """Фильтр по клиенту"""

    PERSON = "PERSON" # Физическое лицо
    COMPANY = "COMPANY" # Юридическое лицо / ИП
    FOREIGN_AGENCY = "FOREIGN_AGENCY" # Иностранная организация


class SearchIncomesStatusFilter(str, Enum):
    """Фильтр по статусу"""

    REGISTERED = "REGISTERED" # Действителен
    CANCELED = "CANCELLED" # Аннулирован


class SearchIncomesSortBy(str, Enum):
    """Сортировка по сумме или дате"""

    AMOUNT_ASC = "total_amount:asc"
    AMOUNT_DESC = "total_amount:desc"
    DATE_ASC = "operation_time:asc"
    DATE_DESC = "operation_time:desc"
