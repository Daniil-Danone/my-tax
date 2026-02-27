"""
Кэширование сессии авторизации в Redis.

При повторных запросах клиент берёт токен из Redis,
а не авторизуется заново. При истечении токена — обновляет автоматически.

Требуется: pip install redis
"""

import asyncio

from redis.asyncio import Redis

from my_tax import MyTaxClient, Credentials


async def main():
    redis = Redis(host="localhost", port=6379, db=0)
    credentials = Credentials(username="770000000000", password="your_password")

    async with MyTaxClient(
        credentials=credentials,
        redis=redis,
        redis_key="my_tax:session:770000000000",
        redis_ttl_seconds=3600,  # TTL 1 час
    ) as client:
        # Первый запрос — авторизация + сохранение в Redis
        user = await client.user.get_user()
        print(f"Пользователь: {user.display_name}")

        # Второй запрос — токен из Redis (без повторной авторизации)
        incomes = await client.income.get_list(limit=5)
        print(f"Чеков: {len(incomes.content)}")

    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
