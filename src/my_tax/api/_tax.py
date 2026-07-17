"""
API для налогов (Tax).
"""

from typing import Optional

from ._base import BaseApi
from ..types.tax import TaxBonus, TaxSummary, TaxHistory, TaxPayments, ListRegions
from ..constants import (
    TAXPAYER_BONUS_PATH,
    TAXES_PATH,
    TAXES_HISTORY_PATH,
    TAXES_PAYMENTS_PATH,
    REGION_PATH,
)


class TaxApi(BaseApi):
    """Методы для налогов: бонус (вычет), сводка, начисления и платежи."""

    async def get_bonus(self) -> TaxBonus:
        """Получение остатка налогового бонуса (вычета)."""
        data = await self._request_get(TAXPAYER_BONUS_PATH)
        return TaxBonus.model_validate(data)

    async def get_summary(self) -> TaxSummary:
        """Получение сводки по налогу: к оплате, задолженность, переплата, пени."""
        data = await self._request_get(TAXES_PATH)
        return TaxSummary.model_validate(data)

    async def get_history(self, oktmo: Optional[str] = None) -> TaxHistory:
        """
        Получение начислений налога по периодам.

        Args:
            oktmo: Код ОКТМО. None — начисления по всем регионам.
        """
        data = await self._request_post(TAXES_HISTORY_PATH, json_data={"oktmo": oktmo})
        return TaxHistory.model_validate(data)

    async def get_payments(
        self,
        oktmo: Optional[str] = None,
        only_paid: bool = False,
    ) -> TaxPayments:
        """
        Получение платежей по налогу.

        Args:
            oktmo: Код ОКТМО. None — платежи по всем регионам.
            only_paid: Только оплаченные.
        """
        data = await self._request_post(
            TAXES_PAYMENTS_PATH,
            json_data={"oktmo": oktmo, "onlyPaid": only_paid},
        )
        return TaxPayments.model_validate(data)

    async def get_regions(self) -> ListRegions:
        """Получение справочника регионов (для расшифровки ОКТМО)."""
        data = await self._request_get(REGION_PATH)
        return ListRegions.model_validate(data)
