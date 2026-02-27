"""Слой DTO: Pydantic-схемы для авторизации, пользователя и API."""

from .auth import (
    AuthData,
    Credentials,
    DeviceInfo,
    Token,
)

from .user import User

from .income import (
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
)

from .invoice import (
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
)

from .payment_method import (
    PaymentMethod,
    ListPaymentMethods,
)

__all__ = [
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
