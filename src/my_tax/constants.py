"""Константы для API ЛК НПД."""

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
