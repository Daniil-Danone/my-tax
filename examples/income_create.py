"""
Создание чеков: одна услуга, несколько услуг, юридическое лицо.
"""

import asyncio
from decimal import Decimal

from my_tax import MyTaxClient, Credentials, CreateIncomeItem, CreateIncomeClient
from my_tax.enums.general import ClientType


async def main():
    credentials = Credentials(username="770000000000", password="your_password")

    async with MyTaxClient(credentials=credentials) as client:
        # --- Одна услуга (физ. лицо) ---
        income = await client.income.create(
            service=CreateIncomeItem(
                name="Разработка сайта",
                amount=Decimal("15000"),
                quantity=Decimal("1"),
            )
        )
        print(f"Чек создан: {income.uuid}")
        print(f"Сумма: {income.total_amount} руб.")

        # --- Несколько услуг ---
        income = await client.income.create(
            services=[
                CreateIncomeItem(
                    name="Дизайн логотипа",
                    amount=Decimal("5000"),
                    quantity=Decimal("1"),
                ),
                CreateIncomeItem(
                    name="Дизайн визитки",
                    amount=Decimal("2000"),
                    quantity=Decimal("2"),
                ),
            ]
        )
        print(f"Чек создан: {income.uuid}, сумма: {income.total_amount}")

        # --- Юридическое лицо ---
        income = await client.income.create(
            service=CreateIncomeItem(
                name="Консультация",
                amount=Decimal("50000"),
                quantity=Decimal("1"),
            ),
            client=CreateIncomeClient(
                type=ClientType.FROM_LEGAL_ENTITY,
                name="ООО Ромашка",
                inn="7700000001",
            ),
        )
        print(f"Чек для юр. лица: {income.uuid}")


if __name__ == "__main__":
    asyncio.run(main())
