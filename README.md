# 🧾 my-tax

[![PyPI version](https://img.shields.io/pypi/v/my-tax?color=blue)](https://pypi.org/project/my-tax/)
[![Python 3.11+](https://img.shields.io/badge/python-3.10+-lightgreen.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Async](https://img.shields.io/badge/async-supported-blueviolet.svg)]()

**Неофициальный** асинхронный HTTP-клиент для работы с API [Личного кабинета самозанятого (ЛК НПД)](https://lknpd.nalog.ru) «Мой налог» (ФНС России).

---

## ✨ Возможности

| Функция | Описание |
|---------|----------|
| 🔐 **Авторизация по ИНН/паролю** | Автоматическое получение и обновление токена |
| 📱 **Авторизация по SMS** | Старт челленджа → ввод кода → верификация |
| 🧾 **Чеки (Income)** | Создание, список с фильтрацией и пагинацией, отмена |
| 📄 **Счета (Invoice)** | Создание, список с поиском, отмена |
| 💳 **Способы оплаты** | Получение справочника (банковские счета, телефоны) |
| 👤 **Профиль** | Получение данных пользователя и аватара |
| 💰 **Налог** | Сводка (к оплате, долг, пени), начисления по периодам, платежи |
| 🎁 **Бонус (вычет)** | Остаток налогового бонуса и расчёт списания |
| 📊 **Ставка** | Определение ставки (4%/6%) и расчёт налога по операции |
| 🔄 **Автоматический retry при 401** | Обновление токена и повтор запроса под `asyncio.Lock` |
| 💾 **Кэширование сессии в Redis** | Переиспользование токена между запусками |
| 🛡️ **Маскирование чувствительных данных** | Токены, пароли, ключи не попадают в логи |

---

## 📦 Установка

**Требования:** Python ≥ 3.10

```bash
pip install my-tax
```

С поддержкой Redis:

```bash
pip install my-tax[redis]
```

Из исходников (для разработки):

```bash
git clone https://github.com/Daniil-Danone/python-my-tax.git
cd python-my-tax
pip install -e ".[dev]"
```

---

## 🚀 Быстрый старт

### Авторизация по ИНН/паролю

```python
import asyncio
from my_tax import MyTaxClient, Credentials

async def main():
    credentials = Credentials(username="770000000000", password="your_password")

    async with MyTaxClient(credentials=credentials) as client:
        user = await client.user.get_user()
        print(f"ИНН: {user.inn}")
        print(f"Имя: {user.display_name}")

asyncio.run(main())
```

### Авторизация по SMS

```python
import asyncio
from my_tax import MyTaxClient

async def main():
    async with MyTaxClient() as client:
        # 1. Запрос SMS-кода
        challenge_token = await client.auth_by_phone.start_challenge("79991234567")

        # 2. Ввод кода
        code = input("Код из SMS: ")

        # 3. Подтверждение
        auth = await client.auth_by_phone.verify_and_login("79991234567", code)
        print(f"Авторизация успешна! ИНН: {auth.inn}")

asyncio.run(main())
```

### Авторизация по SMS (Web API — два HTTP-запроса)

Когда `start_challenge` и `verify_and_login` вызываются в разных запросах (разные экземпляры клиента), передайте `challenge_token` явно:

```python
# Запрос 1: POST /auth/sms/start
async with MyTaxClient() as client:
    challenge_token = await client.auth_by_phone.start_challenge("79991234567")
    # Сохранить challenge_token в Redis / БД / сессию

# Запрос 2: POST /auth/sms/verify (другой экземпляр клиента)
async with MyTaxClient() as client:
    auth = await client.auth_by_phone.verify_and_login(
        "79991234567", code, challenge_token=challenge_token
    )
```

---

## 📚 API

### 🧾 Чеки (Income)

#### Создание чека

```python
from decimal import Decimal
from my_tax import CreateIncomeItem, CreateIncomeClient
from my_tax.enums.general import ClientType

# Одна услуга (физ. лицо)
income = await client.income.create(
    service=CreateIncomeItem(
        name="Разработка сайта",
        amount=Decimal("15000"),
        quantity=Decimal("1"),
    )
)

# Несколько услуг
income = await client.income.create(
    services=[
        CreateIncomeItem(name="Дизайн", amount=Decimal("5000"), quantity=Decimal("1")),
        CreateIncomeItem(name="Вёрстка", amount=Decimal("3000"), quantity=Decimal("2")),
    ]
)

# Юридическое лицо
income = await client.income.create(
    service=CreateIncomeItem(name="Консультация", amount=Decimal("50000"), quantity=Decimal("1")),
    client=CreateIncomeClient(
        type=ClientType.FROM_LEGAL_ENTITY,
        name="ООО Ромашка",
        inn="7700000001",
    ),
)
```

#### Список чеков

```python
from datetime import datetime, timedelta, timezone
from my_tax.enums.income import SearchIncomesSortBy, SearchIncomesStatusFilter

# За последние 7 дней
result = await client.income.get_list(
    from_date=datetime.now(timezone.utc) - timedelta(days=7),
    to_date=datetime.now(timezone.utc),
)

for inc in result.content:
    print(f"{inc.uuid} | {inc.name} | {inc.total_amount} руб.")

# С фильтрами и сортировкой
result = await client.income.get_list(
    status=SearchIncomesStatusFilter.REGISTERED,
    sort_by=SearchIncomesSortBy.AMOUNT_DESC,
    limit=10,
)
```

#### Отмена чека

```python
from my_tax.enums.income import CancelReason

canceled = await client.income.cancel(
    receipt_uuid="uuid-чека",
    comment=CancelReason.MISTAKE,  # или CancelReason.REFUND
)
```

---

### 📄 Счета (Invoice)

#### Создание счёта

```python
from decimal import Decimal
from my_tax import CreateInvoiceItem, CreateInvoiceClient

# Получаем способ оплаты
methods = await client.payment_type.get_table()
method = methods.items[0]

# Создаём счёт
invoice = await client.invoice.create(
    service=CreateInvoiceItem(
        name="Разработка приложения",
        amount=Decimal("150000"),
        quantity=Decimal("1"),
    ),
    client=CreateInvoiceClient(
        name="Иванов Иван Иванович",
        phone="79991234567",
    ),
    payment_method=method,
)

print(f"Счёт #{invoice.invoice_id} — {invoice.total_amount} руб.")
```

#### Список и отмена счетов

```python
from my_tax.enums.invoice import InvoiceStatusFilter

# Список
result = await client.invoice.get_list(
    status=InvoiceStatusFilter.CREATED,
    search="Дизайн",
)

for inv in result.items:
    print(f"#{inv.invoice_id} | {inv.client_name} | {inv.status.value}")

# Отмена
canceled = await client.invoice.cancel(invoice_id=123)
```

---

### 💳 Способы оплаты (PaymentMethod)

```python
from my_tax.enums.invoice import PaymentMethodType

# Все избранные
methods = await client.payment_type.get_table(favorite=True)

# Только банковские счета
accounts = await client.payment_type.get_table(type=PaymentMethodType.ACCOUNT)

for m in accounts.items:
    print(f"{m.bank_name} | БИК {m.bank_bik} | р/с {m.current_account}")
```

---

### 👤 Профиль пользователя (User)

```python
user = await client.user.get_user()

print(f"ИНН: {user.inn}")
print(f"Имя: {user.display_name}")
print(f"Телефон: {user.phone}")
print(f"Активен: {user.is_active()}")
print(f"Дата регистрации: {user.registration_date}")
```

---

### 💰 Налог (Tax)

#### Сводка и бонус

```python
summary = await client.tax.get_summary()

print(f"К оплате: {summary.total_for_payment} ₽")
print(f"Налог: {summary.tax} ₽")
print(f"Задолженность: {summary.debt} ₽")
print(f"Пени: {summary.penalty} ₽")

bonus = await client.tax.get_bonus()

print(f"Остаток бонуса: {bonus.amount} из {bonus.limit} ₽")
print(f"Израсходовано: {bonus.spent} ₽")
```

#### Начисления по периодам

Налог, списанный бонус и срок уплаты ФНС раскрывает только здесь — агрегатом
по налоговому периоду и ОКТМО:

```python
history = await client.tax.get_history()

for charge in history.records:
    print(
        f"{charge.tax_period_id}: налог {charge.tax_amount} ₽, "
        f"бонус −{charge.bonus_amount} ₽, "
        f"к уплате {charge.unpaid_amount} ₽ до {charge.due_date:%d.%m.%Y}"
    )

print(f"Задекларировано всего: {history.get_total_base()} ₽")
```

#### Платежи

```python
payments = await client.tax.get_payments(only_paid=True)

print(f"Оплачено всего: {payments.get_total()} ₽")
```

#### Ставка и расчёт налога по операции

API ставку не отдаёт — её определяет тип клиента в чеке. Бонус гасит 1 п.п.
по доходам от физлиц и 2 п.п. по доходам от юрлиц, поэтому пока бонус не
исчерпан, эффективная ставка — 3% и 4%:

```python
from decimal import Decimal
from my_tax import rate_for, estimate_tax
from my_tax.enums.general import ClientType

rate = rate_for(ClientType.FROM_LEGAL_ENTITY)
print(f"Ставка: {rate.rate:.0%}, с бонусом: {rate.effective_rate:.0%}")   # 6%, с бонусом: 4%

estimate = estimate_tax(Decimal("2500"), ClientType.FROM_LEGAL_ENTITY)
print(f"{estimate.nominal_tax} ₽ − {estimate.bonus_applied} ₽ = {estimate.tax} ₽")  # 150.00 ₽ − 50.00 ₽ = 100.00 ₽
```

Списание ограничено остатком бонуса — передайте его, чтобы расчёт был честным:

```python
bonus = await client.tax.get_bonus()
estimate = estimate_tax(Decimal("2500"), ClientType.FROM_LEGAL_ENTITY, bonus_available=bonus.amount)
```

> ⚠️ `estimate_tax()` — **оценка**. ФНС не раскрывает налог в разрезе отдельного
> чека и начисляет налог раз в месяц. Фактические суммы — только в `get_history()`.

#### Регионы

```python
regions = await client.tax.get_regions()

user = await client.user.get_user()
region = regions.find_by_oktmo(user.registration_oktmo_code)
print(f"Регион: {region.name}")
```

---

## 🔄 Кэширование сессии в Redis

При передаче `redis` и `redis_prefix` сессия сохраняется по ключу `{redis_prefix}:session` и при следующем запросе подставляется из кэша (без повторной авторизации).

```python
from redis.asyncio import Redis
from my_tax import MyTaxClient, Credentials

redis = Redis(host="localhost", port=6379, db=0)

async with MyTaxClient(
    credentials=Credentials(username="770000000000", password="..."),
    redis=redis,
    redis_prefix="my_tax:770000000000",
    redis_ttl_seconds=3600,
) as client:
    user = await client.user.get_user()  # авторизация + сохранение в Redis
    incomes = await client.income.get_list()  # токен из Redis

await redis.aclose()
```

> Любой объект, реализующий `AuthStorage` протокол (`get` / `set`), подходит в качестве хранилища.

---

## ⚠️ Обработка ошибок

Все исключения наследуются от `BaseDomainException`:

| Исключение | Описание |
|------------|----------|
| `AuthorizationError` | Ошибка авторизации (неверный пароль, истёк токен) |
| `AccessTokenNotFoundError` | Нет access-токена при попытке refresh |
| `SmsChallengeError` | Ошибка SMS-челленджа (нет `challengeToken`, не вызван `start_challenge`) |

```python
from my_tax import AuthorizationError, SmsChallengeError

try:
    await client.income.get_list()
except AuthorizationError as e:
    print(f"Ошибка авторизации: {e}")
except SmsChallengeError as e:
    print(f"Ошибка SMS: {e}")
```

Чувствительные данные (токены, пароли, ключи API) **автоматически маскируются** в логах.

---

## 🗂️ Структура проекта

```
src/my_tax/
├── __init__.py              # Экспорт клиента, типов, исключений
├── _client.py               # MyTaxClient (request, 401-retry, Redis кэш)
├── _transport.py             # HTTP-транспорт (httpx.AsyncClient)
├── _auth.py                  # PasswordAuth, PhoneSmsAuth
├── _helpers.py               # Утилиты (device_id, token freshness, headers)
├── constants.py              # URL API, пути, ставки НПД и лимит бонуса
├── exceptions.py             # Иерархия исключений + маскирование данных
├── logger.py                 # Настройка логгера
├── enums/
│   ├── general.py            # ClientType
│   ├── income.py             # IncomePaymentType, CancelReason, фильтры, сортировка
│   └── invoice.py            # PaymentMethodType, InvoiceStatus, InvoiceStatusFilter
├── types/
│   ├── _base.py              # AtomDateTime, PositiveDecimal, StrNonEmpty, StrStripNone
│   ├── auth.py               # Credentials, Token, AuthData, DeviceInfo
│   ├── user.py               # User
│   ├── income.py             # CreateIncome, Income, ListIncomes, CancelIncome, ...
│   ├── invoice.py            # CreateInvoice, Invoice, ListInvoices, ...
│   ├── payment_method.py     # PaymentMethod, ListPaymentMethods
│   └── tax.py                # TaxRate, TaxBonus, TaxSummary, TaxCharge, rate_for, estimate_tax
└── api/
    ├── _base.py              # BaseApi, RequestClient (протокол)
    ├── _user.py              # UserApi (get_user, get_avatar)
    ├── _income.py            # IncomeApi (create, get_list, cancel)
    ├── _invoice.py           # InvoiceApi (create, get_list, cancel)
    ├── _payment_method.py    # PaymentMethodApi (get_table)
    └── _tax.py               # TaxApi (get_summary, get_bonus, get_history, get_payments)
```

---

## 🧪 Тестирование

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 📄 Зависимости

| Пакет | Версия | Назначение |
|-------|--------|------------|
| [httpx](https://www.python-httpx.org/) | ≥ 0.28.1 | Асинхронный HTTP-клиент |
| [pydantic](https://docs.pydantic.dev/) | ≥ 2.0.0 | Валидация и сериализация данных |
| [redis](https://redis-py.readthedocs.io/) | ≥ 5.0.0 | Кэш сессии *(опционально)* |

---

## 📝 Лицензия

Проект распространяется под лицензией **MIT**. Подробности в файле [LICENSE](LICENSE).

**Автор:** [Daniil-Danone](https://github.com/Daniil-Danone)

© 2026 Daniil-Danone
