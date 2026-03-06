"""
API для счетов (Invoice).
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union, overload

from ._base import BaseApi

from ..types.payment_method import PaymentMethod
from ..types.invoice import (
    Invoice,
    CreateInvoice,
    CreateInvoiceItem,
    CreateInvoiceClient,
    ListInvoices,
    SearchInvoices,
    SearchInvoicesFilterItem,
    SearchInvoicesSortItem,
)

from ..enums.invoice import InvoiceStatusFilter

from ..constants import (
    INVOICE_PATH,
    INVOICE_LIST_PATH,
    INVOICE_CANCEL_PATH,
    INVOICE_PRINT_PATH,
)


class InvoiceApi(BaseApi):
    """Методы для счетов (invoice)."""

    async def get_list(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        status: Optional[InvoiceStatusFilter] = None,
        search: Optional[str] = None,
        sort_by_date_desc: bool = True,
        offset: int = 0,
        limit: int = 10,
    ) -> ListInvoices:
        """
        Получить список счетов на оплату.

        Args:
            from_date: Дата начала периода.
            to_date: Дата окончания периода.
            status: Фильтр по статусу.
            search: Поисковый запрос.
            sort_by_date_desc: Сортировка по дате в порядке убывания.
            offset: Сдвиг.
            limit: Лимит.
        Returns:
            ListInvoices: Список счетов на оплату.
        """
        filtered = []

        if from_date:
            filtered.append(
                SearchInvoicesFilterItem(
                    id="from",
                    value=from_date,
                )
            )

        if to_date:
            filtered.append(
                SearchInvoicesFilterItem(
                    id="to",
                    value=to_date,
                )
            )

        if status:
            filtered.append(
                SearchInvoicesFilterItem(
                    id="status",
                    value=status,
                )
            )

        if search:
            filtered.append(
                SearchInvoicesFilterItem(
                    id="context",
                    value=search,
                )
            )

        request = SearchInvoices(
            offset=offset,
            limit=limit,
            filtered=filtered,
            sorted=[
                SearchInvoicesSortItem(
                    id="createdAt",
                    desc=sort_by_date_desc,
                )
            ],
        )

        data = await self._request_post(
            path=INVOICE_LIST_PATH,
            json_data=request.model_dump(mode="json", by_alias=True),
        )

        return ListInvoices.model_validate(data)

    async def get_list_by_model(self, request: SearchInvoices) -> ListInvoices:
        """
        Получить список счетов на оплату по полной модели запроса.

        Args:
            request: SearchInvoices (offset, limit, filtered, sorted).
        Returns:
            ListInvoices: Список счетов на оплату.
        """
        data = await self._request_post(
            path=INVOICE_LIST_PATH,
            json_data=request.model_dump(mode="json", by_alias=True),
        )

        return ListInvoices.model_validate(data)

    async def get_by_id(
        self,
        invoice_id: Union[str, int],
        *,
        operation_date: Optional[datetime] = None,
        status: Optional[InvoiceStatusFilter] = None,
        page_size: int = 50,
    ) -> Invoice:
        """
        Получить счёт по ID с итерацией по страницам списка.

        Args:
            invoice_id: ID счёта (str или int).
            operation_date: Дата операции (сужает диапазон поиска).
            status: Фильтр по статусу.
            page_size: Размер страницы при итерации.

        Returns:
            Invoice: Найденный счёт.

        Raises:
            ValueError: Счёт не найден.
        """
        invoice_id_int = int(str(invoice_id).strip())

        if operation_date is not None:
            from_date = operation_date - timedelta(minutes=5)
            to_date = operation_date + timedelta(minutes=5)
        else:
            from_date = None
            to_date = None

        offset = 0
        while True:
            list_res = await self.get_list(
                from_date=from_date,
                to_date=to_date,
                status=status,
                limit=page_size,
                offset=offset,
            )
            for inv in list_res.items:
                if inv.invoice_id == invoice_id_int:
                    return inv

            if not list_res.has_more:
                break
            offset += page_size

        raise ValueError(f"Счёт с id {invoice_id_int!r} не найден")

    @overload
    async def create(
        self,
        *,
        service: CreateInvoiceItem,
        client: CreateInvoiceClient,
        payment_method: PaymentMethod,
    ) -> Invoice: ...

    @overload
    async def create(
        self,
        *,
        services: List[CreateInvoiceItem],
        client: CreateInvoiceClient,
        payment_method: PaymentMethod,
    ) -> Invoice: ...

    async def create(
        self,
        *,
        service: Optional[CreateInvoiceItem] = None,
        services: Optional[List[CreateInvoiceItem]] = None,
        client: CreateInvoiceClient,
        payment_method: PaymentMethod,
    ) -> Invoice:
        """
        Создать счёт.

        Args:
            service: Одна услуга (передать service или services).
            services: Список услуг (передать service или services).
            client: CreateInvoiceClient (тип клиента, имя, телефон, email, ИНН).
            payment_method: PaymentMethod (способ оплаты).

        Returns:
            Invoice: Созданный счёт.
        """
        if service is not None:
            services_list = [service]
        elif services is not None:
            services_list = services
        else:
            raise TypeError(
                "create() missing required argument: pass 'service' or 'services'"
            )

        request = CreateInvoice(
            payment_type=payment_method.type,
            bank_name=payment_method.bank_name,
            bank_bik=payment_method.bank_bik,
            corr_account=payment_method.corr_account,
            current_account=payment_method.current_account,
            phone=payment_method.phone,
            client_name=client.name.strip(),
            client_phone=client.phone,
            client_email=client.email,
            client_inn=client.inn,
            services=services_list,
            client_type=client.type,
        )

        return await self.create_by_model(request)

    async def create_by_model(self, request: CreateInvoice) -> Invoice:
        """
        Создать счёт по полной модели запроса.

        После POST запрашивается список счетов и возвращается полный объект
        созданного счёта (ответ создания может быть неполным).
        """
        data = await self._request_post(
            path=INVOICE_PATH,
            json_data=request.model_dump(mode="json", by_alias=True),
        )
        
        raw_id = data.get("invoiceId")
        if raw_id is None:
            raise ValueError(
                "Ответ создания счёта не содержит invoiceId"
            )

        return await self.get_by_id(
            int(raw_id),
            operation_date=datetime.now(tz=timezone.utc),
            status=InvoiceStatusFilter.CREATED,
        )

    async def cancel(self, invoice_id: Union[str, int]) -> Invoice:
        """
        Отменить счёт по id.

        После POST запрашивается список счетов и возвращается полный объект.

        Args:
            invoice_id: ID счёта (str или int).

        Returns:
            Invoice: Обновлённый счёт (статус CANCELLED).
        """
        invoice_id_str = str(invoice_id).strip()
        if not invoice_id_str:
            raise ValueError("ID счёта (invoice_id) не может быть пустым")

        if not invoice_id_str.isdigit():
            raise ValueError("ID счёта (invoice_id) должен быть числом")

        invoice_id_int = int(invoice_id_str)

        await self._request_post(
            path=INVOICE_CANCEL_PATH.format(invoice_id=invoice_id_str),
        )

        return await self.get_by_id(
            invoice_id_int,
            status=InvoiceStatusFilter.CANCELLED,
        )

    async def print_invoice(self, invoice_uuid: str) -> bytes:
        """
        Получить PDF счёта на оплату.

        GET /invoice/{invoice_uuid}/pdf/print

        Args:
            invoice_uuid: UUID счёта.

        Returns:
            bytes: Бинарные данные PDF.
        """
        path = INVOICE_PRINT_PATH.format(invoice_uuid=invoice_uuid)
        return await self._request_get_binary(path)
