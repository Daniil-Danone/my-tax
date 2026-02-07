# my-tax

НЕОФИЦИАЛЬНЫЙ HTTP-клиент для работы с API [Личного кабинета самозанятого (ЛК НПД)](https://lknpd.nalog.ru) Кабинет налогоплательщика НПД "Мой налог" России. Поддерживает синхронный и асинхронный режимы, авторизацию по логину/паролю (ИНН) и по номеру телефона с кодом из SMS, а также опциональное кэширование сессии в Redis.

## Для чего этот пакет

- **Обращение к API ЛК НПД** — получение профиля пользователя (GET /user) и возможность расширять список методов через отдельные «ручки» в папке `api/`.
- **Два способа авторизации:**
  - по **логину и паролю** (учётная запись по ИНН);
  - по **телефону и коду из SMS** (старт челленджа → ввод кода → верификация).
- **Синхронный и асинхронный клиенты** — `SyncMyTaxClient` и `AsyncMyTaxClient` с единым стилем использования.
- **Опциональное хранение сессии в Redis** — не передавать логин/пароль при каждом запросе и переиспользовать токен между запусками (при передаче `redis` и `redis_key`).

## Зависимости

**Обязательные:** 
- [httpx](https://www.python-httpx.org/) ≥ 0.28.1 (HTTP-клиент с поддержкой sync/async).
- [pydantic](https://docs.pydantic.dev/) ≥ 2.0.0 (для валидации данных).
- [pytz](https://pythonhosted.org/pytz/) ≥ 2025.1 (для работы с временными зонами).

**Опциональные:** 
- [redis](https://redis-py.readthedocs.io/) ≥ 5.0.0 — только если нужно кэшировать состояние авторизации в Redis (устанавливаются через `pip install my-tax[redis]`).

Требуется **Python ≥ 3.14**.

## Установка

```bash
pip install my-tax
# или с Redis:
pip install my-tax[redis]
```

## Примеры использования

### Синхронный клиент, авторизация по логину и паролю

```python
from my_tax import SyncMyTaxClient, Credentials, User

client = SyncMyTaxClient(
    credentials=Credentials(username="ваш_логин", password="ваш_пароль"),
)
user: User = client.get_user()
print(user.display_name, user.inn)
client.close()
```

### Асинхронный клиент, авторизация по телефону (SMS)

```python
import asyncio
from my_tax import AsyncMyTaxClient, User

async def main():
    client = AsyncMyTaxClient()
    await client.auth_by_phone.start_challenge("79991234567")
    code = input("Введите код подвтерждения: ")
    await client.auth_by_phone.verify_and_login("79991234567", code)
    user: User = await client.get_user()
    print(user.display_name)
    await client.aclose()

asyncio.run(main())
```

### Кэширование сессии в Redis

```python
import redis
from my_tax import SyncMyTaxClient, Credentials

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
client = SyncMyTaxClient(
    credentials=Credentials(username="...", password="..."),
    redis=r,
    redis_key="my_tax:session:user_1",
    redis_ttl_seconds=3600,
)
# первый вызов — авторизация по паролю, сессия сохраняется в Redis
headers = client.get_auth_headers()
# последующие вызовы могут брать токен из Redis, пока он действителен
client.close()
```

### Ручки API и метод через свойство `user`

```python
from my_tax import SyncMyTaxClient, Credentials

client = SyncMyTaxClient(credentials=Credentials(username="...", password="..."))
# через клиента
user = client.get_user()
# или через ручку пользователя
user = client.user.get_user()
client.close()
```

## Структура проекта

- **`my_tax/clients.py`** — синхронный и асинхронный клиенты (`SyncMyTaxClient`, `AsyncMyTaxClient`).
- **`my_tax/_http.py`** — транспорт (sync/async), стратегии авторизации (пароль, SMS).
- **`my_tax/api/`** — ручки API:
  - **`base.py`** — базовые классы `BaseSyncApi`, `BaseAsyncApi` для добавления новых эндпоинтов.
  - **`user.py`** — ручки пользователя (GET /user).
- **`my_tax/types.py`** — типы данных (`Credentials`, `User`, `AuthData`, `Token` и др.).
- **`my_tax/constants.py`** — константы (URL API, заголовки и т.п.).

## Лицензия и авторство

Проект распространяется под лицензией **MIT**.

- **Автор:** [Daniil-Danone](https://github.com/Daniil-Danone) 
- **Copyright:** © 2026 Daniil-Danone  

Текст лицензии см. в файле [LICENSE](LICENSE).
