"""Tests for types/invoice.py: validators, serialization, deserialization."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from pydantic import ValidationError

from my_tax.types.invoice import (
    CreateInvoiceItem,
    CreateInvoiceClient,
    CreateInvoice,
    Invoice,
    ListInvoices,
    SearchInvoices,
)
from my_tax.enums.general import ClientType
from my_tax.enums.invoice import PaymentMethodType, InvoiceStatus


# ---------------------------------------------------------------------------
# CreateInvoiceClient — validators
# ---------------------------------------------------------------------------

class TestCreateInvoiceClientValidator:
    def test_valid_individual(self):
        c = CreateInvoiceClient(name="John Doe")
        assert c.type == ClientType.FROM_INDIVIDUAL

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            CreateInvoiceClient(name="")

    def test_legal_entity_requires_inn(self):
        with pytest.raises(ValidationError, match="ИНН клиента не может быть пустым"):
            CreateInvoiceClient(
                name="OOO Test",
                type=ClientType.FROM_LEGAL_ENTITY,
            )

    def test_legal_entity_valid(self):
        c = CreateInvoiceClient(
            name="OOO Test",
            type=ClientType.FROM_LEGAL_ENTITY,
            inn="7700000001",
        )
        assert c.inn == "7700000001"


# ---------------------------------------------------------------------------
# CreateInvoiceItem
# ---------------------------------------------------------------------------

class TestCreateInvoiceItem:
    def test_decimal_serialization(self):
        item = CreateInvoiceItem(name="Svc", amount=Decimal("500"), quantity=Decimal("3"))
        dumped = item.model_dump()
        assert dumped["amount"] == "500"
        assert dumped["quantity"] == "3"

    def test_get_total(self):
        item = CreateInvoiceItem(name="Svc", amount=Decimal("250"), quantity=Decimal("4"))
        assert item.get_total() == Decimal("1000")


# ---------------------------------------------------------------------------
# CreateInvoice — computed field & validator
# ---------------------------------------------------------------------------

class TestCreateInvoice:
    def test_total_amount_computed(self, sample_invoice_item):
        inv = CreateInvoice(
            payment_type=PaymentMethodType.PHONE,
            phone="79991234567",
            client_name="Test",
            services=[sample_invoice_item],
        )
        assert inv.total_amount == str(Decimal("10000"))

    def test_legal_entity_requires_inn(self):
        item = CreateInvoiceItem(name="Svc", amount=Decimal("100"), quantity=Decimal("1"))
        with pytest.raises(ValidationError, match="ИНН клиента не может быть пустым"):
            CreateInvoice(
                payment_type=PaymentMethodType.PHONE,
                phone="79991234567",
                client_name="OOO Test",
                client_type=ClientType.FROM_LEGAL_ENTITY,
                services=[item],
            )

    def test_model_dump_by_alias(self, sample_invoice_item):
        inv = CreateInvoice(
            payment_type=PaymentMethodType.PHONE,
            phone="79991234567",
            client_name="Test",
            services=[sample_invoice_item],
        )
        dumped = inv.model_dump(by_alias=True)
        assert "paymentType" in dumped
        assert "clientName" in dumped
        assert "totalAmount" in dumped


# ---------------------------------------------------------------------------
# Invoice — deserialization
# ---------------------------------------------------------------------------

INVOICE_API_JSON = {
    "invoiceId": 42,
    "uuid": "inv-uuid-123",
    "fid": 1,
    "type": "MANUAL",
    "status": "CREATED",
    "paymentType": "PHONE",
    "phone": "79991234567",
    "clientType": "FROM_INDIVIDUAL",
    "clientName": "John Doe",
    "totalAmount": "5000",
    "services": [
        {"name": "Service", "amount": "5000", "quantity": "1", "serviceNumber": 0}
    ],
}


class TestInvoiceDeserialization:
    def test_model_validate(self):
        inv = Invoice.model_validate(INVOICE_API_JSON)
        assert inv.invoice_id == 42
        assert inv.uuid == "inv-uuid-123"
        assert inv.status == InvoiceStatus.CREATED
        assert inv.total_amount == Decimal("5000")

    def test_optional_fields(self):
        inv = Invoice.model_validate(INVOICE_API_JSON)
        assert inv.bank_name is None
        assert inv.paid_at is None
        assert inv.cancelled_at is None


# ---------------------------------------------------------------------------
# ListInvoices — deserialization
# ---------------------------------------------------------------------------

class TestListInvoices:
    def test_model_validate(self):
        data = {
            "items": [INVOICE_API_JSON],
            "hasMore": True,
            "currentOffset": 0,
            "currentLimit": 10,
        }
        result = ListInvoices.model_validate(data)
        assert len(result.items) == 1
        assert result.has_more is True


# ---------------------------------------------------------------------------
# SearchInvoices — defaults
# ---------------------------------------------------------------------------

class TestSearchInvoices:
    def test_defaults(self):
        s = SearchInvoices()
        assert s.offset == 0
        assert s.limit == 10
        assert s.filtered == []
        assert s.sorted == []
