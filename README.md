# my-tax

НЕОФИЦИАЛЬНЫЙ HTTP-клиент для работы с API [Личного кабинета самозанятого (ЛК НПД)](https://lknpd.nalog.ru) «Мой налог» (ФНС России). Поддерживает синхронный и асинхронный режимы, авторизацию по логину/паролю (ИНН) и по номеру телефона с кодом из SMS, опциональное кэширование сессии в Redis и автоматический retry при 401 с обновлением токена.

## Для чего этот пакет

- **Обращение к API ЛК НПД** — получение профиля пользователя (GET /user) и расширяемый набор ручек в `api/`.
- **Два способа авторизации:**
  - по **логину и паролю** (учётная запись по ИНН);
  - по **телефону и коду из SMS** (старт челленджа → ввод кода → верификация).
- **Синхронный и асинхронный клиенты** — `SyncMyTaxClient` и `AsyncMyTaxClient` с единым стилем.
- **Обработка 401 на уровне клиента** — один общий метод `request()`: при 401 обновление токена (под lock) и один повтор запроса; в ручках API не нужно прописывать retry.
- **Опциональное хранение сессии в Redis** — переиспользование токена между запусками при передаче `redis` и `redis_key`.

## Зависимости

**Обязательные:**

- [httpx](https://www.python-httpx.org/) ≥ 0.28.1 — HTTP-клиент (sync/async).
- [pydantic](https://docs.pydantic.dev/) ≥ 2.0.0 — валидация и схемы данных.
- [pytz](https://pythonhosted.org/pytz/) ≥ 2025.1 — временные зоны (логгер).

**Опциональные:**

- [redis](https://redis-py.readthedocs.io/) ≥ 5.0.0 — кэш сессии: `pip install my-tax[redis]`.

Требуется **Python ≥ 3.14**.

## Установка

```bash
pip install my-tax
# или с Redis:
pip install my-tax[redis]
```

Из репозитория (режим разработки):

```bash
pip install -e .
pip install -e ".[redis]"
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
    code = input("Введите код подтверждения: ")
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
# первый вызов — авторизация, сессия сохраняется в Redis
headers = client.get_auth_headers()
# последующие вызовы берут токен из Redis, пока он действителен
client.close()
```

### Ручки API и свойство `user`

```python
from my_tax import SyncMyTaxClient, Credentials

client = SyncMyTaxClient(credentials=Credentials(username="...", password="..."))
# через клиента
user = client.get_user()
# или через ручку пользователя
user = client.user.get_user()
client.close()
```

### Низкоуровневый запрос с авторизацией и 401-retry

```python
from my_tax import SyncMyTaxClient, Credentials

client = SyncMyTaxClient(credentials=Credentials(username="...", password="..."))
# request() сам подставляет заголовки и при 401 обновляет токен и повторяет запрос
response = client.request("GET", "/user")
response.raise_for_status()
data = response.json()
client.close()
```

## Структура проекта

```
src/my_tax/
├── __init__.py          # экспорт клиентов, сущностей, исключений
├── clients.py           # SyncMyTaxClient, AsyncMyTaxClient (request(), get_auth_headers, 401-retry)
├── _http.py             # транспорт (sync/async), стратегии авторизации (пароль, SMS)
├── constants.py         # URL API, заголовки
├── logger.py            # настройка логгера (TZFormatter, setup_logger)
├── api/
│   ├── base.py          # BaseSyncApi, BaseAsyncApi (ручки вызывают client.request())
│   └── user.py          # UserSyncApi, UserAsyncApi (GET /user)
└── domain/
    ├── exceptions.py    # BaseDomainException, AuthorizationError, AccessTokenNotFoundError, SmsChallengeError
    └── entites/         # AuthData, Credentials, Token, DeviceInfo, User (Pydantic/сущности)
```

## Лицензия и авторство

Проект распространяется под лицензией **MIT**.

- **Автор:** [Daniil-Danone](https://github.com/Daniil-Danone)
- **Copyright:** © 2026 Daniil-Danone

Текст лицензии см. в файле [LICENSE](LICENSE).
