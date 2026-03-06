"""
API для чеков (Income).
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, overload

from ._base import BaseApi

from ..types._base import atom_datetime_now
from ..types.income import (
    Income,
    CreateIncome,
    CreateIncomeItem,
    CreateIncomeClient,
    ListIncomes,
    SearchIncomes,
    CancelIncome,
)

from ..enums.income import (
    IncomePaymentType,
    CancelReason,
    SearchIncomesSortBy,
    SearchIncomesClientFilter,
    SearchIncomesStatusFilter,
)

from ..constants import (
    INCOME_PATH,
    INCOME_CANCEL_PATH,
    INCOME_LIST_PATH,
    INCOME_PRINT_PATH,
)


class IncomeApi(BaseApi):
    """Методы для чеков (income)."""

    async def get_list(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        sort_by: Optional[SearchIncomesSortBy] = None,
        client: Optional[SearchIncomesClientFilter] = None,
        status: Optional[SearchIncomesStatusFilter] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ListIncomes:
        """
        Получить список чеков.

        Args:
            from_date: Дата начала периода.
            to_date: Дата окончания периода.
            sort_by: Сортировка.
            client: Фильтр по клиенту.
            status: Фильтр по статусу.
            limit: Лимит.
            offset: Сдвиг.

        Returns:
            ListIncomes: Список чеков.
        """

        request = SearchIncomes(
            from_date=from_date,
            to_date=to_date,
            sort_by=sort_by,
            client_filter=client,
            status_filter=status,
            limit=limit,
            offset=offset,
        )

        data = await self._request_get(
            path=INCOME_LIST_PATH,
            params=request.model_dump(mode="json", by_alias=True, exclude_none=True),
        )

        return ListIncomes.model_validate(data)

    async def get_list_with_request(self, request: SearchIncomes) -> ListIncomes:
        """
        Получить список чеков по полной модели запроса.

        Args:
            request: SearchIncomes (offset, limit, filtered, sorted).
        Returns:
            ListIncomes: Список чеков.
        """

        data = await self._request_get(
            path=INCOME_LIST_PATH,
            params=request.model_dump(mode="json", by_alias=True, exclude_none=True),
        )

        return ListIncomes.model_validate(data)

    @overload
    async def create(
        self,
        *,
        service: CreateIncomeItem,
        operation_time: Optional[datetime] = ...,
        client: Optional[CreateIncomeClient] = ...,
    ) -> Income: ...

    @overload
    async def create(
        self,
        *,
        services: List[CreateIncomeItem],
        operation_time: Optional[datetime] = ...,
        client: Optional[CreateIncomeClient] = ...,
    ) -> Income: ...

    async def create(
        self,
        *,
        service: Optional[CreateIncomeItem] = None,
        services: Optional[List[CreateIncomeItem]] = None,
        operation_time: Optional[datetime] = None,
        client: Optional[CreateIncomeClient] = None,
    ) -> Income:
        """
        Создать чек.

        Args:
            service: Одна услуга (передать service или services).
            services: Список услуг (передать service или services).
            operation_time: Время операции (по умолчанию — сейчас).
            client: Данные клиента (по умолчанию — физ. лицо).

        Returns:
            Income: Созданный чек.
        """
        if service is not None:
            services_list = [service]
        elif services is not None:
            services_list = services
        else:
            raise TypeError(
                "create() missing required argument: pass 'service' or 'services'"
            )

        request = CreateIncome(
            operation_time=operation_time or atom_datetime_now(),
            request_time=atom_datetime_now(),
            services=services_list,
            client=client or CreateIncomeClient(),
            payment_type=IncomePaymentType.CASH,
            ignore_max_total_income_restriction=False,
        )

        return await self.create_by_model(request)

    async def create_by_model(self, request: CreateIncome) -> Income:
        """
        Создать чек по полной модели запроса.

        После POST запрашивается список чеков и возвращается полный объект
        созданного чека (ответ создания содержит только approvedReceiptUuid).
        """
        data = await self._request_post(
            path=INCOME_PATH,
            json_data=request.model_dump(mode="json", by_alias=True),
        )
        
        receipt_uuid = data.get("approvedReceiptUuid") or data.get("receiptUuid")
        if not receipt_uuid:
            raise ValueError(
                "Ответ создания чека не содержит approvedReceiptUuid"
            )

        now = datetime.now(tz=timezone.utc)
        list_res = await self.get_list(
            from_date=now - timedelta(minutes=5),
            to_date=now + timedelta(minutes=1),
            status=SearchIncomesStatusFilter.REGISTERED,
            limit=50,
        )
        for income in list_res.content:
            if income.uuid == receipt_uuid:
                return income

        raise ValueError(
            f"Чек с uuid {receipt_uuid!r} не найден в списке после создания"
        )

    async def cancel(
        self,
        receipt_uuid: str,
        comment: CancelReason,
        operation_time: Optional[datetime] = None,
        request_time: Optional[datetime] = None,
        partner_code: Optional[str] = None,
    ) -> Income:
        """
        Отменить чек.

        После POST /cancel запрашивается список чеков и возвращается
        полный объект отменённого чека (с cancellationInfo).

        Args:
            receipt_uuid: UUID чека.
            comment: Причина отмены.
            operation_time: Время операции (по умолчанию — сейчас).
            request_time: Время запроса (по умолчанию — сейчас).
            partner_code: Код партнёра (опционально).

        Returns:
            Income: Отменённый чек с cancellationInfo.
        """
        uuid_stripped = (receipt_uuid or "").strip()
        if not uuid_stripped:
            raise ValueError("UUID чека не может быть пустым")

        request = CancelIncome(
            operation_time=operation_time or atom_datetime_now(),
            request_time=request_time or atom_datetime_now(),
            comment=comment,
            receipt_uuid=uuid_stripped,
            partner_code=partner_code,
        )

        await self._request_post(
            path=INCOME_CANCEL_PATH,
            json_data=request.model_dump(mode="json", by_alias=True),
        )

        now = datetime.now(tz=timezone.utc)
        list_res = await self.get_list(
            from_date=now - timedelta(days=30),
            to_date=now + timedelta(minutes=1),
            status=SearchIncomesStatusFilter.CANCELED,
            limit=50,
        )
        for income in list_res.content:
            if income.uuid == uuid_stripped:
                return income

        raise ValueError(
            f"Чек с uuid {uuid_stripped!r} не найден в списке после отмены"
        )

    async def print_receipt(self, inn: str, receipt_uuid: str) -> bytes:
        """
        Получить PDF чека.

        GET /receipt/{inn}/{receipt_uuid}/print

        Args:
            inn: ИНН налогоплательщика.
            receipt_uuid: UUID чека.

        Returns:
            bytes: Бинарные данные PDF.
        """
        path = INCOME_PRINT_PATH.format(inn=inn, receipt_uuid=receipt_uuid)
        return await self._request_get_binary(path)
