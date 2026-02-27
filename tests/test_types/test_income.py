"""Tests for types/income.py: validators, serialization, deserialization."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import ValidationError

from my_tax.types.income import (
    CreateIncomeItem,
    CreateIncomeClient,
    CreateIncome,
    Income,
    ListIncomes,
    SearchIncomes,
    CancelIncome,
    CanceledIncome,
    CancelationInfo,
)
from my_tax.enums.general import ClientType
from my_tax.enums.income import CancelReason, IncomePaymentType


# ---------------------------------------------------------------------------
# CreateIncomeClient — validator tests
# ---------------------------------------------------------------------------

class TestCreateIncomeClientValidator:
    def test_individual_defaults(self):
        c = CreateIncomeClient()
        assert c.type == ClientType.FROM_INDIVIDUAL

    def test_legal_entity_requires_name(self):
        with pytest.raises(ValidationError, match="Название клиента обязательно"):
            CreateIncomeClient(type=ClientType.FROM_LEGAL_ENTITY, inn="7700000001")

    def test_legal_entity_requires_inn(self):
        with pytest.raises(ValidationError, match="ИНН обязателен"):
            CreateIncomeClient(type=ClientType.FROM_LEGAL_ENTITY, name="OOO Test")

    def test_legal_entity_valid(self):
        c = CreateIncomeClient(
            type=ClientType.FROM_LEGAL_ENTITY, name="OOO Test", inn="7700000001"
        )
        assert c.name == "OOO Test"
        assert c.inn == "7700000001"

    def test_foreign_agency_requires_name(self):
        with pytest.raises(ValidationError, match="Название клиента обязательно"):
            CreateIncomeClient(type=ClientType.FROM_FOREIGN_AGENCY)

    def test_foreign_agency_valid_without_inn(self):
        c = CreateIncomeClient(type=ClientType.FROM_FOREIGN_AGENCY, name="Foreign Co")
        assert c.name == "Foreign Co"


# ---------------------------------------------------------------------------
# CreateIncomeItem — serialization
# ---------------------------------------------------------------------------

class TestCreateIncomeItem:
    def test_decimal_serializes_to_string(self):
        item = CreateIncomeItem(name="Svc", amount=Decimal("100.50"), quantity=Decimal("2"))
        dumped = item.model_dump()
        assert dumped["amount"] == "100.50"
        assert dumped["quantity"] == "2"

    def test_get_total(self):
        item = CreateIncomeItem(name="Svc", amount=Decimal("100"), quantity=Decimal("3"))
        assert item.get_total() == Decimal("300")

    def test_rejects_zero_amount(self):
        with pytest.raises(ValidationError):
            CreateIncomeItem(name="Svc", amount=Decimal("0"), quantity=Decimal("1"))

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            CreateIncomeItem(name="", amount=Decimal("100"), quantity=Decimal("1"))


# ---------------------------------------------------------------------------
# CreateIncome — serialization & computed fields
# ---------------------------------------------------------------------------

class TestCreateIncome:
    def test_total_amount_computed(self, sample_income_item):
        income = CreateIncome(services=[sample_income_item])
        assert income.total_amount == Decimal("1000")

    def test_total_amount_multiple_services(self):
        items = [
            CreateIncomeItem(name="A", amount=Decimal("100"), quantity=Decimal("2")),
            CreateIncomeItem(name="B", amount=Decimal("300"), quantity=Decimal("1")),
        ]
        income = CreateIncome(services=items)
        assert income.total_amount == Decimal("500")

    def test_model_dump_by_alias(self, sample_income_item):
        income = CreateIncome(services=[sample_income_item])
        dumped = income.model_dump(by_alias=True)
        assert "operationTime" in dumped
        assert "requestTime" in dumped
        assert "totalAmount" in dumped
        assert "paymentType" in dumped
        # Key: datetime is flat string, not nested
        assert isinstance(dumped["operationTime"], str)
        assert dumped["operationTime"].endswith("Z")

    def test_default_operation_time_is_utc(self, sample_income_item):
        income = CreateIncome(services=[sample_income_item])
        assert income.operation_time.tzinfo is not None

    def test_requires_at_least_one_service(self):
        with pytest.raises(ValidationError):
            CreateIncome(services=[])


# ---------------------------------------------------------------------------
# Income — deserialization from API JSON
# ---------------------------------------------------------------------------

INCOME_API_JSON = {
    "approvedReceiptUuid": "abc-def-123",
    "name": "Test Receipt",
    "paymentType": "CASH",
    "incomeType": "FROM_INDIVIDUAL",
    "services": [
        {"name": "Service 1", "amount": "1500", "quantity": "1", "serviceNumber": 0}
    ],
    "totalAmount": "1500",
    "taxPeriodId": 202601,
    "operationTime": "2026-01-15T10:30:00Z",
    "requestTime": "2026-01-15T10:30:00Z",
    "registerTime": "2026-01-15T10:30:01Z",
}


class TestIncomeDeserialization:
    def test_model_validate_from_api(self):
        income = Income.model_validate(INCOME_API_JSON)
        assert income.uuid == "abc-def-123"
        assert income.total_amount == Decimal("1500")
        assert income.operation_time.year == 2026
        assert income.operation_time.tzinfo is not None

    def test_with_cancelation_info(self):
        data = {
            **INCOME_API_JSON,
            "cancelationInfo": {
                "operationTime": "2026-02-01T12:00:00Z",
                "registerTime": "2026-02-01T12:00:01Z",
                "taxPeriodId": 202602,
                "comment": "Чек сформирован ошибочно",
            },
        }
        income = Income.model_validate(data)
        assert income.cancelation_info is not None
        assert income.cancelation_info.comment == CancelReason.MISTAKE

    def test_optional_fields_none(self):
        income = Income.model_validate(INCOME_API_JSON)
        assert income.client_inn is None
        assert income.partner_code is None
        assert income.cancelation_info is None


# ---------------------------------------------------------------------------
# SearchIncomes — defaults
# ---------------------------------------------------------------------------

class TestSearchIncomes:
    def test_default_from_date_30_days_ago(self):
        s = SearchIncomes()
        now = datetime.now(timezone.utc)
        diff = abs(now - s.from_date)
        assert 29 <= diff.days <= 31

    def test_default_to_date_is_now(self):
        s = SearchIncomes()
        now = datetime.now(timezone.utc)
        diff = abs(now - s.to_date)
        assert diff.total_seconds() < 5

    def test_model_dump_uses_aliases(self):
        s = SearchIncomes()
        dumped = s.model_dump(by_alias=True)
        assert "from" in dumped
        assert "to" in dumped
        assert "sortBy" in dumped


# ---------------------------------------------------------------------------
# CancelIncome — serialization
# ---------------------------------------------------------------------------

class TestCancelIncome:
    def test_model_dump_by_alias(self):
        c = CancelIncome(
            comment=CancelReason.MISTAKE,
            receipt_uuid="abc-123",
        )
        dumped = c.model_dump(by_alias=True)
        assert "operationTime" in dumped
        assert "requestTime" in dumped
        assert "receiptUuid" in dumped
        assert isinstance(dumped["operationTime"], str)


# ---------------------------------------------------------------------------
# ListIncomes — deserialization
# ---------------------------------------------------------------------------

class TestListIncomes:
    def test_model_validate(self):
        data = {
            "content": [INCOME_API_JSON],
            "hasMore": False,
            "currentOffset": 0,
            "currentLimit": 50,
        }
        result = ListIncomes.model_validate(data)
        assert len(result.content) == 1
        assert result.has_more is False
        assert result.offset == 0
