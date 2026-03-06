"""Тесты для InvoiceApi.get_by_id."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from my_tax.api._invoice import InvoiceApi
from my_tax.types.invoice import Invoice, ListInvoices
from my_tax.enums.invoice import (
    InvoiceStatus,
    InvoiceStatusFilter,
    PaymentMethodType,
)
from my_tax.enums.general import ClientType


def _make_invoice(invoice_id: int, **overrides) -> Invoice:
    """Фабрика минимального Invoice для тестов."""
    defaults = {
        "invoiceId": invoice_id,
        "uuid": f"inv-uuid-{invoice_id}",
        "fid": 1,
        "type": "PAYMENT",
        "status": "CREATED",
        "paymentType": "ACCOUNT",
        "clientType": "FROM_INDIVIDUAL",
        "clientName": "Test Client",
        "totalAmount": "500",
        "services": [{"name": "svc", "amount": 500, "quantity": 1, "serviceNumber": 1}],
    }
    defaults.update(overrides)
    return Invoice.model_validate(defaults)


def _make_list_invoices(
    invoices: list[Invoice],
    has_more: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> ListInvoices:
    return ListInvoices(
        items=invoices,
        has_more=has_more,
        current_offset=offset,
        current_limit=limit,
    )


def _make_api() -> InvoiceApi:
    mock_client = MagicMock()
    return InvoiceApi(client=mock_client)


class TestGetById:
    async def test_found_on_first_page(self):
        api = _make_api()
        target = _make_invoice(42)
        api.get_list = AsyncMock(
            return_value=_make_list_invoices([target])
        )

        result = await api.get_by_id(42)

        assert result.invoice_id == 42
        api.get_list.assert_awaited_once()

    async def test_found_by_string_id(self):
        api = _make_api()
        target = _make_invoice(99)
        api.get_list = AsyncMock(
            return_value=_make_list_invoices([target])
        )

        result = await api.get_by_id("99")
        assert result.invoice_id == 99

    async def test_found_on_second_page(self):
        api = _make_api()
        other = _make_invoice(1)
        target = _make_invoice(2)

        page1 = _make_list_invoices([other], has_more=True, offset=0)
        page2 = _make_list_invoices([target], has_more=False, offset=1)
        api.get_list = AsyncMock(side_effect=[page1, page2])

        result = await api.get_by_id(2, page_size=1)

        assert result.invoice_id == 2
        assert api.get_list.await_count == 2

    async def test_not_found_raises(self):
        api = _make_api()
        api.get_list = AsyncMock(
            return_value=_make_list_invoices([])
        )

        with pytest.raises(ValueError, match="не найден"):
            await api.get_by_id(999)

    async def test_operation_date_narrows_range(self):
        api = _make_api()
        target = _make_invoice(10)
        api.get_list = AsyncMock(
            return_value=_make_list_invoices([target])
        )

        op_date = datetime(2026, 3, 6, 12, 0, 0, tzinfo=timezone.utc)
        await api.get_by_id(10, operation_date=op_date)

        call_kwargs = api.get_list.call_args.kwargs
        assert call_kwargs["from_date"] is not None
        assert call_kwargs["to_date"] is not None

    async def test_no_operation_date_passes_none(self):
        api = _make_api()
        target = _make_invoice(10)
        api.get_list = AsyncMock(
            return_value=_make_list_invoices([target])
        )

        await api.get_by_id(10)

        call_kwargs = api.get_list.call_args.kwargs
        assert call_kwargs.get("from_date") is None
        assert call_kwargs.get("to_date") is None

    async def test_status_filter_forwarded(self):
        api = _make_api()
        target = _make_invoice(10)
        api.get_list = AsyncMock(
            return_value=_make_list_invoices([target])
        )

        await api.get_by_id(
            10,
            status=InvoiceStatusFilter.CREATED,
        )

        call_kwargs = api.get_list.call_args.kwargs
        assert call_kwargs["status"] == InvoiceStatusFilter.CREATED

    async def test_pagination_stops_when_no_more(self):
        api = _make_api()
        other1 = _make_invoice(1)
        other2 = _make_invoice(2)

        page1 = _make_list_invoices([other1], has_more=True, offset=0)
        page2 = _make_list_invoices([other2], has_more=False, offset=1)
        api.get_list = AsyncMock(side_effect=[page1, page2])

        with pytest.raises(ValueError, match="не найден"):
            await api.get_by_id(999, page_size=1)

        assert api.get_list.await_count == 2
