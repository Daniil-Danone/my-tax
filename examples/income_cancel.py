"""
Отмена (аннулирование) чека.
"""

import asyncio
from decimal import Decimal

from my_tax import MyTaxClient, Credentials, CreateIncomeItem
from my_tax.enums.income import CancelReason


async def main():
    credentials = Credentials(username="770000000000", password="your_password")

    async with MyTaxClient(credentials=credentials) as client:
        # 1. Создаём чек
        income = await client.income.create(
            service=CreateIncomeItem(
                name="Тестовая услуга",
                amount=Decimal("100"),
                quantity=Decimal("1"),
            )
        )
        print(f"Чек создан: {income.uuid}")

        # 2. Отменяем чек
        canceled = await client.income.cancel(
            receipt_uuid=income.uuid,
            comment=CancelReason.MISTAKE,  # или CancelReason.REFUND
        )

        print(f"Чек аннулирован: {canceled.uuid}")
        print(f"Причина: {canceled.cancelation_info.comment}")


if __name__ == "__main__":
    asyncio.run(main())
