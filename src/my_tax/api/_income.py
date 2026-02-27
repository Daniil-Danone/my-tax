"""
API для чеков (Income).
"""

from datetime import datetime
from typing import List, Optional, Union, overload

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
    CanceledIncome,
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

        data = await self._request_post(
            path=INCOME_LIST_PATH,
            json_data=request.model_dump(by_alias=True)
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

        data = await self._request_post(
            path=INCOME_LIST_PATH,
            json_data=request.model_dump(by_alias=True),
        )

        return ListIncomes.model_validate(data)

    @overload
    async def create(
        self,
        service: CreateIncomeItem,
        *,
        operation_time: Optional[datetime] = ...,
        client: Optional[CreateIncomeClient] = ...,
    ) -> Income: ...

    @overload
    async def create(
        self,
        services: List[CreateIncomeItem],
        operation_time: Optional[datetime] = ...,
        client: Optional[CreateIncomeClient] = ...,
    ) -> Income: ...

    async def create(
        self,
        service_or_services: Union[CreateIncomeItem, List[CreateIncomeItem]],
        *,
        operation_time: Optional[datetime] = None,
        client: Optional[CreateIncomeClient] = None,
    ) -> Income:
        """
        Создать чек.

        Args:
            service_or_services: Услуга или список услуг.
            operation_time: Время операции (по умолчанию — сейчас).
            client: Данные клиента (по умолчанию — физ. лицо).

        Returns:
            Income: Созданный чек.
        """

        services = (
            [service_or_services]
            if isinstance(service_or_services, CreateIncomeItem)
            else service_or_services
        )

        request = CreateIncome(
            operation_time=operation_time or atom_datetime_now(),
            request_time=atom_datetime_now(),
            services=services,
            client=client or CreateIncomeClient(),
            payment_type=IncomePaymentType.CASH,
            ignore_max_total_income_restriction=False,
        )

        return await self.create_by_model(request)

    async def create_by_model(self, request: CreateIncome) -> Income:
        """
        Создать чек по полной модели запроса.

        Args:
            request: CreateIncome (сервисы, клиент, реквизиты).

        Returns:
            Income: Созданный чек.
        """

        data = await self._request_post(
            path=INCOME_PATH,
            json_data=request.model_dump(by_alias=True)
        )

        return Income.model_validate(data)

    async def cancel(
        self,
        receipt_uuid: str,
        comment: CancelReason,
        operation_time: Optional[datetime] = None,
        request_time: Optional[datetime] = None,
        partner_code: Optional[str] = None,
    ) -> CanceledIncome:
        """
        Отменить чек.

        Args:
            receipt_uuid: UUID чека.
            comment: Причина отмены.
            operation_time: Время операции (по умолчанию — сейчас).
            request_time: Время запроса (по умолчанию — сейчас).
            partner_code: Код партнёра (опционально).

        Returns:
            CanceledIncome: Отмененный чек.
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

        data = await self._request_post(
            path=INCOME_CANCEL_PATH,
            json_data=request.model_dump(by_alias=True)
        )

        return CanceledIncome.model_validate(data.get("incomeInfo"))

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
