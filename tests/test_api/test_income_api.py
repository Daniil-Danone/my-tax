"""Тесты для IncomeApi.get_by_uuid."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from my_tax.api._income import IncomeApi
from my_tax.types.income import Income, ListIncomes
from my_tax.enums.income import IncomePaymentType, SearchIncomesStatusFilter
from my_tax.enums.general import ClientType


def _make_income(uuid: str, **overrides) -> Income:
    """Фабрика минимального Income для тестов."""
    defaults = {
        "approvedReceiptUuid": uuid,
        "name": "Test",
        "paymentType": "CASH",
        "incomeType": "FROM_INDIVIDUAL",
        "services": [{"name": "svc", "amount": 100, "quantity": 1, "serviceNumber": 1}],
        "totalAmount": "100",
        "taxPeriodId": 202601,
        "operationTime": "2026-03-06T12:00:00Z",
        "requestTime": "2026-03-06T12:00:00Z",
        "registerTime": "2026-03-06T12:00:00Z",
    }
    defaults.update(overrides)
    return Income.model_validate(defaults)


def _make_list_incomes(
    incomes: list[Income],
    has_more: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> ListIncomes:
    return ListIncomes(
        content=incomes,
        has_more=has_more,
        offset=offset,
        limit=limit,
    )


def _make_api() -> IncomeApi:
    mock_client = MagicMock()
    return IncomeApi(client=mock_client)


class TestGetByUuid:
    async def test_found_on_first_page(self):
        api = _make_api()
        target = _make_income("abc-123")
        api.get_list = AsyncMock(
            return_value=_make_list_incomes([target])
        )

        result = await api.get_by_uuid("abc-123")

        assert result.uuid == "abc-123"
        api.get_list.assert_awaited_once()

    async def test_found_on_second_page(self):
        api = _make_api()
        other = _make_income("other-1")
        target = _make_income("target-uuid")

        page1 = _make_list_incomes([other], has_more=True, offset=0)
        page2 = _make_list_incomes([target], has_more=False, offset=1)
        api.get_list = AsyncMock(side_effect=[page1, page2])

        result = await api.get_by_uuid("target-uuid", page_size=1)

        assert result.uuid == "target-uuid"
        assert api.get_list.await_count == 2

    async def test_not_found_raises(self):
        api = _make_api()
        api.get_list = AsyncMock(
            return_value=_make_list_incomes([])
        )

        with pytest.raises(ValueError, match="не найден"):
            await api.get_by_uuid("missing-uuid")

    async def test_empty_uuid_raises(self):
        api = _make_api()
        with pytest.raises(ValueError, match="пустым"):
            await api.get_by_uuid("")

    async def test_whitespace_uuid_raises(self):
        api = _make_api()
        with pytest.raises(ValueError, match="пустым"):
            await api.get_by_uuid("   ")

    async def test_strips_whitespace(self):
        api = _make_api()
        target = _make_income("abc-123")
        api.get_list = AsyncMock(
            return_value=_make_list_incomes([target])
        )

        result = await api.get_by_uuid("  abc-123  ")
        assert result.uuid == "abc-123"

    async def test_operation_date_narrows_range(self):
        api = _make_api()
        target = _make_income("uuid-1")
        api.get_list = AsyncMock(
            return_value=_make_list_incomes([target])
        )

        op_date = datetime(2026, 3, 6, 12, 0, 0, tzinfo=timezone.utc)
        await api.get_by_uuid("uuid-1", operation_date=op_date)

        call_kwargs = api.get_list.call_args.kwargs
        assert call_kwargs["from_date"] is not None
        assert call_kwargs["to_date"] is not None

    async def test_no_operation_date_passes_none(self):
        api = _make_api()
        target = _make_income("uuid-1")
        api.get_list = AsyncMock(
            return_value=_make_list_incomes([target])
        )

        await api.get_by_uuid("uuid-1")

        call_kwargs = api.get_list.call_args.kwargs
        assert call_kwargs.get("from_date") is None
        assert call_kwargs.get("to_date") is None

    async def test_status_filter_forwarded(self):
        api = _make_api()
        target = _make_income("uuid-1")
        api.get_list = AsyncMock(
            return_value=_make_list_incomes([target])
        )

        await api.get_by_uuid(
            "uuid-1",
            status=SearchIncomesStatusFilter.REGISTERED,
        )

        call_kwargs = api.get_list.call_args.kwargs
        assert call_kwargs["status"] == SearchIncomesStatusFilter.REGISTERED

    async def test_pagination_stops_when_no_more(self):
        api = _make_api()
        other1 = _make_income("a")
        other2 = _make_income("b")

        page1 = _make_list_incomes([other1], has_more=True, offset=0)
        page2 = _make_list_incomes([other2], has_more=False, offset=1)
        api.get_list = AsyncMock(side_effect=[page1, page2])

        with pytest.raises(ValueError, match="не найден"):
            await api.get_by_uuid("missing", page_size=1)

        assert api.get_list.await_count == 2
