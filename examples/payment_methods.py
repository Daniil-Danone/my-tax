"""
Получение справочника способов оплаты.
"""

import asyncio

from my_tax import MyTaxClient, Credentials
from my_tax.enums.invoice import PaymentMethodType


async def main():
    credentials = Credentials(username="770000000000", password="your_password")

    async with MyTaxClient(credentials=credentials) as client:
        # --- Все избранные способы оплаты ---
        methods = await client.payment_type.get_table(favorite=True)

        print(f"Способов оплаты: {len(methods.items)}\n")
        for m in methods.items:
            if m.type == PaymentMethodType.ACCOUNT:
                print(f"  [Счёт] {m.bank_name} | р/с {m.current_account}")
            elif m.type == PaymentMethodType.PHONE:
                print(f"  [Телефон] {m.phone}")

        # --- Только банковские счета ---
        accounts = await client.payment_type.get_table(
            type=PaymentMethodType.ACCOUNT,
        )

        print(f"\nБанковских счетов: {len(accounts.items)}")
        for m in accounts.items:
            print(f"  {m.bank_name} | БИК {m.bank_bik} | р/с {m.current_account}")


if __name__ == "__main__":
    asyncio.run(main())
