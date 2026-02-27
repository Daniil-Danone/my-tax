"""
API для справочника способов оплаты (PaymentMethod).
"""

from typing import Optional
from ._base import BaseApi

from ..types.payment_method import ListPaymentMethods

from ..constants import PAYMENT_TYPE_PATH
from ..enums.invoice import PaymentMethodType


class PaymentMethodApi(BaseApi):
    """Методы для справочника способов оплаты."""

    async def get_table(
        self,
        favorite: bool = True,
        type: Optional[PaymentMethodType] = None
    ) -> ListPaymentMethods:
        """
        Получить таблицу способов оплаты (счета/телефоны).

        GET /payment-type/table?favorite=true&type=ACCOUNT

        Args:
            favorite: Только избранные (по умолчанию True).
            type: Тип способа оплаты (по умолчанию None).
        Returns:
            ListPaymentMethods: Список способов оплаты.
        """
        params = {
            "favorite": str(favorite).lower(),
            "type": type.value if type else None
        }

        data = await self._request_get(
            path=PAYMENT_TYPE_PATH,
            params=params
        )

        return ListPaymentMethods.model_validate(data)
