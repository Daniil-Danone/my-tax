"""Тесты для TaxApi."""

import httpx
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from my_tax.api._tax import TaxApi


def _make_api(payload: dict) -> tuple[TaxApi, AsyncMock]:
    """TaxApi с моком клиента, отдающим payload на любой запрос."""
    request = AsyncMock(
        return_value=httpx.Response(
            status_code=200,
            json=payload,
            request=httpx.Request("GET", "https://lknpd.nalog.ru/api/v1/"),
        )
    )
    client = MagicMock()
    client.request = request
    return TaxApi(client=client), request


class TestGetBonus:
    async def test_calls_bonus_path(self):
        api, request = _make_api({"bonusAmount": 6320})

        bonus = await api.get_bonus()

        assert request.await_args.args == ("GET", "/taxpayer/bonus")
        assert bonus.amount == Decimal("6320")


class TestGetSummary:
    async def test_calls_taxes_path(self):
        api, request = _make_api({"totalForPayment": 5556, "total": 5556, "tax": 5556})

        summary = await api.get_summary()

        assert request.await_args.args == ("GET", "/taxes")
        assert summary.total_for_payment == Decimal("5556")


class TestGetHistory:
    async def test_posts_null_oktmo_by_default(self):
        api, request = _make_api({"records": []})

        await api.get_history()

        assert request.await_args.args == ("POST", "/taxes/history")
        assert request.await_args.kwargs["json"] == {"oktmo": None}

    async def test_posts_given_oktmo(self):
        api, request = _make_api({"records": []})

        await api.get_history(oktmo="46000000")

        assert request.await_args.kwargs["json"] == {"oktmo": "46000000"}

    async def test_parses_records(self):
        api, _ = _make_api({
            "records": [{"taxPeriodId": 202607, "taxAmount": 8334, "bonusAmount": 2778}]
        })

        history = await api.get_history()

        assert history.get_total_tax() == Decimal("8334")


class TestGetPayments:
    async def test_posts_default_body(self):
        api, request = _make_api({"records": []})

        await api.get_payments()

        assert request.await_args.args == ("POST", "/taxes/payments")
        assert request.await_args.kwargs["json"] == {"oktmo": None, "onlyPaid": False}

    async def test_posts_only_paid(self):
        api, request = _make_api({"records": []})

        await api.get_payments(oktmo="46000000", only_paid=True)

        assert request.await_args.kwargs["json"] == {"oktmo": "46000000", "onlyPaid": True}


class TestGetRegions:
    async def test_calls_region_path(self):
        api, request = _make_api({"items": [{"oktmo": "45000000", "name": "Москва"}]})

        regions = await api.get_regions()

        assert request.await_args.args == ("GET", "/region")
        assert regions.items[0].name == "Москва"
