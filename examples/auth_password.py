"""
Авторизация по ИНН/паролю и получение профиля пользователя.
"""

import asyncio
from my_tax import MyTaxClient, Credentials


async def main():
    # Инициализация клиента с логином/паролем от ЛК НПД
    credentials = Credentials(username="770000000000", password="your_password")

    async with MyTaxClient(credentials=credentials) as client:
        # Получение профиля текущего пользователя
        user = await client.user.get_user()

        print(f"ИНН: {user.inn}")
        print(f"Имя: {user.display_name}")
        print(f"Телефон: {user.phone}")
        print(f"Статус НПД: {user.status}")


if __name__ == "__main__":
    asyncio.run(main())
