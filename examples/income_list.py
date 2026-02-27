"""
Получение списка чеков с фильтрацией.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from my_tax import MyTaxClient, Credentials
from my_tax.enums.income import (
    SearchIncomesSortBy,
    SearchIncomesStatusFilter,
)


async def main():
    credentials = Credentials(username="770000000000", password="your_password")

    async with MyTaxClient(credentials=credentials) as client:
        # --- Все чеки за последние 7 дней ---
        result = await client.income.get_list(
            from_date=datetime.now(timezone.utc) - timedelta(days=7),
            to_date=datetime.now(timezone.utc),
        )

        print(f"Найдено чеков: {len(result.content)}")
        for inc in result.content:
            print(f"  {inc.uuid} | {inc.name} | {inc.total_amount} руб.")

        # --- Только действительные, сортировка по сумме ---
        result = await client.income.get_list(
            status=SearchIncomesStatusFilter.REGISTERED,
            sort_by=SearchIncomesSortBy.AMOUNT_DESC,
            limit=10,
        )

        print(f"\nТоп-10 по сумме:")
        for inc in result.content:
            print(f"  {inc.total_amount} руб. — {inc.name}")

        # --- Пагинация ---
        offset = 0
        total = 0
        while True:
            page = await client.income.get_list(limit=20, offset=offset)
            total += len(page.content)
            if not page.has_more:
                break
            offset += 20

        print(f"\nВсего чеков: {total}")


if __name__ == "__main__":
    asyncio.run(main())
