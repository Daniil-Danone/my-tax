"""My Tax — async HTTP client for lknpd.nalog.ru API."""

from ._client import MyTaxClient

from .exceptions import (
    AccessTokenNotFoundError,
    ApiRequestError,
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
    CancellationInfo,
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

    # ===   Tax   ====

    TaxRate,
    TaxBonus,
    TaxEstimate,
    TaxSummary,
    TaxCharge,
    TaxHistory,
    TaxPayment,
    TaxPayments,
    Region,
    ListRegions,
    rate_for,
    estimate_tax,
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
    "ApiRequestError",
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
    "CancellationInfo",
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

    # ===   Tax   ====
    "TaxRate",
    "TaxBonus",
    "TaxEstimate",
    "TaxSummary",
    "TaxCharge",
    "TaxHistory",
    "TaxPayment",
    "TaxPayments",
    "Region",
    "ListRegions",
    "rate_for",
    "estimate_tax",
]
