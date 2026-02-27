"""
Получение списка счетов и отмена счёта.
"""

import asyncio

from my_tax import MyTaxClient, Credentials
from my_tax.enums.invoice import InvoiceStatusFilter


async def main():
    credentials = Credentials(username="770000000000", password="your_password")

    async with MyTaxClient(credentials=credentials) as client:
        # --- Список всех счетов ---
        result = await client.invoice.get_list()

        print(f"Счетов: {len(result.items)}")
        for inv in result.items:
            print(
                f"  #{inv.invoice_id} | {inv.client_name} | "
                f"{inv.total_amount} руб. | {inv.status.value}"
            )

        # --- Только созданные (не оплаченные) ---
        created = await client.invoice.get_list(
            status=InvoiceStatusFilter.CREATED,
        )

        print(f"\nНеоплаченных: {len(created.items)}")

        # --- Поиск по тексту ---
        found = await client.invoice.get_list(search="Дизайн")
        print(f"По запросу 'Дизайн': {len(found.items)}")

        # --- Отмена счёта ---
        if created.items:
            inv = created.items[0]
            canceled = await client.invoice.cancel(inv.invoice_id)
            print(f"\nСчёт #{canceled.invoice_id} отменён, статус: {canceled.status.value}")


if __name__ == "__main__":
    asyncio.run(main())
