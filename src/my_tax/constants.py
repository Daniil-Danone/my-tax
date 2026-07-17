"""Константы для API ЛК НПД."""

from decimal import Decimal
from datetime import timedelta

# ---------------------------------------------------------------------------
# Базовые URL
# ---------------------------------------------------------------------------

BASE_URL_V1 = "https://lknpd.nalog.ru/api/v1"
BASE_URL_V2 = "https://lknpd.nalog.ru/api/v2"

INCOME_PATH = "/income"
INCOME_LIST_PATH = "/incomes"
INCOME_CANCEL_PATH = "/cancel"
INCOME_PRINT_PATH = "/receipt/{inn}/{receipt_uuid}/print"

INVOICE_PATH = "/invoice"
INVOICE_LIST_PATH = "/invoice/table"
INVOICE_CANCEL_PATH = "/invoice/{invoice_id}/cancel"
INVOICE_PRINT_PATH = "/invoice/{invoice_uuid}/pdf/print"

PAYMENT_TYPE_PATH = "/payment-type/table"

TAXPAYER_PATH = "/taxpayer"
TAXPAYER_BONUS_PATH = "/taxpayer/bonus"

TAXES_PATH = "/taxes"
TAXES_HISTORY_PATH = "/taxes/history"
TAXES_PAYMENTS_PATH = "/taxes/payments"

REGION_PATH = "/region"


# ---------------------------------------------------------------------------
# Заголовки запросов
# ---------------------------------------------------------------------------

DEFAULT_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "content-type": "application/json",
}

# ---------------------------------------------------------------------------
# Время действия токена
# ---------------------------------------------------------------------------

# Access-токен действителен 1 час, берём с запасом
ACCESS_TOKEN_LIFETIME = timedelta(minutes=45)

# ---------------------------------------------------------------------------
# Ставки НПД и налоговый бонус (ст. 10-12 ФЗ-422)
#
# API ставку не отдаёт — её определяет тип клиента в каждом чеке (incomeType).
# Бонус («налоговый вычет») гасит часть налога: 1 п.п. по доходам от физлиц
# и 2 п.п. по доходам от юрлиц/иностранных агентств. Пока бонус не исчерпан,
# эффективная ставка — 3% и 4% соответственно.
# ---------------------------------------------------------------------------

TAX_RATES: dict[str, Decimal] = {
    "FROM_INDIVIDUAL": Decimal("0.04"),
    "FROM_LEGAL_ENTITY": Decimal("0.06"),
    "FROM_FOREIGN_AGENCY": Decimal("0.06"),
}

BONUS_RATES: dict[str, Decimal] = {
    "FROM_INDIVIDUAL": Decimal("0.01"),
    "FROM_LEGAL_ENTITY": Decimal("0.02"),
    "FROM_FOREIGN_AGENCY": Decimal("0.02"),
}

# Базовый лимит бонуса при регистрации. У части плательщиков, зарегистрированных
# в 2020 году, остаток был разово увеличен на «ковидную» надбавку — тогда
# фактический остаток может превышать лимит, полагаться на него как на потолок нельзя.
BONUS_LIMIT = Decimal("10000") 
