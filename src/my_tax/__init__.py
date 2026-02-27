"""My Tax — async HTTP client for lknpd.nalog.ru API."""

from ._client import MyTaxClient

from .exceptions import (
    AccessTokenNotFoundError,
    AuthorizationError,
    BaseDomainException,
    SmsChallengeError,
)

from .types import (
    # ===   Auth   ====

    AuthData,
    Credentials,
    DeviceInfo,
    Token,
    User,

    # ===   Income   ====

    CreateIncome,
    CreateIncomeItem,
    CreateIncomeClient,
    Income,
    IncomeItem,
    ListIncomes,
    SearchIncomes,
    CancelationInfo,
    CancelIncome,
    CanceledIncome,

    # ===   Invoice   ====

    CreateInvoice,
    CreateInvoiceItem,
    CreateInvoiceClient,
    Invoice,
    InvoiceItem,
    ListInvoices,
    SearchInvoices,
    SearchInvoicesSortItem,
    SearchInvoicesFilterItem,
    InvoiceReceipt,

    # ===   Payment Method   ====

    PaymentMethod,
    ListPaymentMethods,
)

__all__ = [
    # -------------------------
    # CLIENT
    # -------------------------

    "MyTaxClient",

    # -------------------------
    # EXCEPTIONS
    # -------------------------

    "BaseDomainException",
    "AuthorizationError",
    "AccessTokenNotFoundError",
    "SmsChallengeError",

    # -------------------------
    # TYPES
    # -------------------------

    # ===   Auth   ====
    "AuthData",
    "Credentials",
    "DeviceInfo",
    "Token",
    "User",

    # ===   Income   ====
    "CreateIncome",
    "CreateIncomeItem",
    "CreateIncomeClient",
    "Income",
    "IncomeItem",
    "ListIncomes",
    "SearchIncomes",
    "CancelationInfo",
    "CancelIncome",
    "CanceledIncome",

    # ===   Invoice   ====
    "CreateInvoice",
    "CreateInvoiceItem",
    "CreateInvoiceClient",
    "Invoice",
    "InvoiceItem",
    "ListInvoices",
    "SearchInvoices",
    "SearchInvoicesSortItem",
    "SearchInvoicesFilterItem",
    "InvoiceReceipt",

    # ===   Payment Method   ====
    "PaymentMethod",
    "ListPaymentMethods",
]
