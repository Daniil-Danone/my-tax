"""
Авторизация по номеру телефона через SMS.

Два сценария:
  1. Интерактивный — start_challenge и verify в одном процессе.
  2. Web API — start_challenge и verify в разных HTTP-запросах;
     challenge_token передаётся явно.
"""

import asyncio
from my_tax import MyTaxClient


# ---------------------------------------------------------------------------
# Сценарий 1: интерактивный (одна сессия)
# ---------------------------------------------------------------------------

async def interactive():
    async with MyTaxClient() as client:
        phone = "79991234567"

        # 1. Запрос SMS-кода
        challenge_token = await client.auth_by_phone.start_challenge(phone)
        print(f"SMS отправлено. Challenge token: {challenge_token}")

        # 2. Ввод кода из SMS
        code = input("Введите код из SMS: ")

        # 3. Подтверждение и авторизация
        auth_data = await client.auth_by_phone.verify_and_login(phone, code)
        print(f"Авторизация успешна! ИНН: {auth_data.inn}")

        # 4. Теперь можно делать запросы
        user = await client.user.get_user()
        print(f"Профиль: {user.display_name}")


# ---------------------------------------------------------------------------
# Сценарий 2: Web API (два раздельных запроса)
# ---------------------------------------------------------------------------

async def web_api_start():
    """HTTP-обработчик: POST /auth/sms/start {phone}"""
    async with MyTaxClient() as client:
        phone = "79991234567"
        challenge_token = await client.auth_by_phone.start_challenge(phone)

        # Сохранить challenge_token в Redis / БД / сессию:
        # await redis.set(f"sms_challenge:{phone}", challenge_token, ex=300)

        return {"challenge_token": challenge_token}


async def web_api_verify():
    """HTTP-обработчик: POST /auth/sms/verify {phone, code, challenge_token}"""
    phone = "79991234567"
    code = "1234"

    # Достать challenge_token из хранилища:
    # challenge_token = await redis.get(f"sms_challenge:{phone}")
    challenge_token = "token-from-storage"

    async with MyTaxClient() as client:
        auth_data = await client.auth_by_phone.verify_and_login(
            phone, code, challenge_token=challenge_token
        )
        return {"inn": auth_data.inn}


if __name__ == "__main__":
    asyncio.run(interactive())
