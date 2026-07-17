"""
Состояние по налогу: ставка, бонус, начисления и расчёт по операции.
"""

import asyncio
from decimal import Decimal

from my_tax import MyTaxClient, Credentials, rate_for, estimate_tax
from my_tax.enums.general import ClientType


async def main():
    credentials = Credentials(username="770000000000", password="your_password")

    async with MyTaxClient(credentials=credentials) as client:
        # --- Сводка ---
        summary = await client.tax.get_summary()

        print(f"К оплате: {summary.total_for_payment} руб.")
        print(f"Налог: {summary.tax} руб.")
        print(f"Задолженность: {summary.debt} руб. | Пени: {summary.penalty} руб.")

        # --- Бонус (налоговый вычет) ---
        bonus = await client.tax.get_bonus()

        print(f"\nБонус: {bonus.amount} из {bonus.limit} руб. (израсходовано {bonus.spent})")

        # --- Регион постановки на учёт ---
        user = await client.user.get_user()
        if user.registration_oktmo_code:
            regions = await client.tax.get_regions()
            region = regions.find_by_oktmo(user.registration_oktmo_code)
            if region:
                print(f"Регион: {region.name}")

        # --- Начисления по периодам ---
        history = await client.tax.get_history()

        print(f"\nНачислений: {len(history.records)}")
        for charge in history.records:
            due = f" до {charge.due_date:%d.%m.%Y}" if charge.due_date else ""
            print(
                f"  {charge.tax_period_id}: налог {charge.tax_amount} руб., "
                f"бонус -{charge.bonus_amount} руб., к уплате {charge.unpaid_amount} руб.{due}"
            )

        print(f"\nЗадекларировано всего: {history.get_total_base()} руб.")
        print(f"Начислено налога: {history.get_total_tax()} руб.")
        print(f"Списано бонуса: {history.get_total_bonus()} руб.")

        # --- Платежи ---
        payments = await client.tax.get_payments(only_paid=True)
        print(f"Оплачено всего: {payments.get_total()} руб.")

        # --- Ставки ---
        print()
        for client_type in ClientType:
            rate = rate_for(client_type)
            print(f"{client_type.value}: {rate.rate:.0%}, с бонусом {rate.effective_rate:.0%}")

        # --- Расчёт налога по операции (с учётом остатка бонуса) ---
        estimate = estimate_tax(
            Decimal("2500"),
            ClientType.FROM_LEGAL_ENTITY,
            bonus_available=bonus.amount,
        )

        print(
            f"\n2500 руб. от юрлица: {estimate.nominal_tax} - {estimate.bonus_applied} "
            f"= {estimate.tax} руб. (эфф. ставка {estimate.effective_rate:.2%})"
        )


if __name__ == "__main__":
    asyncio.run(main())
