"""
Создание счёта на оплату.
"""

import asyncio
from decimal import Decimal

from my_tax import MyTaxClient, Credentials, CreateInvoiceItem, CreateInvoiceClient
from my_tax.enums.general import ClientType


async def main():
    credentials = Credentials(username="770000000000", password="your_password")

    async with MyTaxClient(credentials=credentials) as client:
        # 1. Получаем способы оплаты
        payment_methods = await client.payment_type.get_table()

        if not payment_methods.items:
            print("Нет доступных способов оплаты. Добавьте в ЛК НПД.")
            return

        method = payment_methods.items[0]
        print(f"Способ оплаты: {method.type.value} — {method.bank_name or method.phone}")

        # 2. Создаём счёт для физ. лица
        invoice = await client.invoice.create(
            service=CreateInvoiceItem(
                name="Разработка мобильного приложения",
                amount=Decimal("150000"),
                quantity=Decimal("1"),
            ),
            client=CreateInvoiceClient(
                name="Иванов Иван Иванович",
                phone="79991234567",
            ),
            payment_method=method,
        )

        print(f"Счёт создан: #{invoice.invoice_id}")
        print(f"UUID: {invoice.uuid}")
        print(f"Сумма: {invoice.total_amount} руб.")
        print(f"Статус: {invoice.status.value}")

        # 3. Счёт для юридического лица
        invoice = await client.invoice.create(
            services=[
                CreateInvoiceItem(
                    name="Этап 1: Дизайн",
                    amount=Decimal("50000"),
                    quantity=Decimal("1"),
                ),
                CreateInvoiceItem(
                    name="Этап 2: Вёрстка",
                    amount=Decimal("30000"),
                    quantity=Decimal("1"),
                ),
            ],
            client=CreateInvoiceClient(
                type=ClientType.FROM_LEGAL_ENTITY,
                name="ООО Технологии",
                inn="7700000001",
                email="buh@tech.ru",
            ),
            payment_method=method,
        )

        print(f"\nСчёт для юр. лица: #{invoice.invoice_id}")
        print(f"Сумма: {invoice.total_amount} руб.")


if __name__ == "__main__":
    asyncio.run(main())
