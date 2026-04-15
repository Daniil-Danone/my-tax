"""
Клиент API ЛК НПД.

Поддерживает авторизацию по ИНН/паролю и по телефону (SMS).
Опционально — сохранение состояния авторизации во внешнем хранилище.
Обработка 401 (refresh токена и один retry) — на уровне клиента в методе request().
"""

import json
import asyncio
from typing import Any, Optional, Protocol, Union

import httpx

from ._transport import Transport, ProxyType
from ._auth import PasswordAuth, PhoneSmsAuth
from .api._user import UserApi
from .api._income import IncomeApi
from .api._invoice import InvoiceApi
from .api._payment_method import PaymentMethodApi
from ._helpers import build_bearer_headers, is_token_fresh
from .types import AuthData, Credentials, User


# ---------------------------------------------------------------------------
# Протокол хранилища состояния (без жёсткой зависимости от redis)
# ---------------------------------------------------------------------------


class AuthStorage(Protocol):
    """Протокол хранилища состояния авторизации (например redis.asyncio)."""

    async def get(self, name: str) -> Optional[Union[str, bytes]]:
        """Получение значения по ключу."""
        ...

    async def set(
        self,
        name: str,
        value: Union[str, bytes],
        ex: Optional[int] = None,
    ) -> None:
        """Сохранение значения. ex — TTL в секундах."""
        ...


# ---------------------------------------------------------------------------
# Сериализация состояния авторизации (сессия + device_id для refresh)
# ---------------------------------------------------------------------------

def _serialize_session(auth: AuthData, device_id: str) -> str:
    """Сериализация сессии и device_id в JSON. API привязывает refresh к device."""
    return json.dumps({
        "session": auth.model_dump(mode="json", by_alias=True),
        "device_id": device_id,
    })


def _deserialize_session(
    payload: Union[str, bytes],
) -> Optional[tuple[AuthData, str]]:
    """Десериализация из Redis. Возвращает (session, device_id) или None."""
    try:
        raw = payload.decode() if isinstance(payload, bytes) else payload
        data = json.loads(raw)
        
        if not isinstance(data, dict) or "session" not in data or "device_id" not in data:
            return None
        
        session = AuthData.model_validate(data["session"])
        device_id = str(data["device_id"])
        
        return (session, device_id)
   
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Клиент
# ---------------------------------------------------------------------------


class MyTaxClient:
    """
    Клиент API ЛК НПД.

    Поддерживает авторизацию по ИНН/паролю и по телефону + SMS.
    При передаче redis и redis_prefix состояние авторизации сохраняется
    в Redis по ключу «{redis_prefix}:session» и подставляется из кэша при следующем запросе.
    """

    SESSION_KEY = "session"

    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        *,
        timeout: float = 5.0,
        read_timeout: float = 5.0,
        write_timeout: float = 5.0,
        connect_timeout: float = 5.0,
        redis: Optional[AuthStorage] = None,
        redis_prefix: Optional[str] = None,
        redis_ttl_seconds: Optional[int] = None,
        proxy: ProxyType = None,
        verify: Union[bool, str] = True,
    ) -> None:
        """
        Args:
            credentials: ИНН/пароль для PasswordAuth. Можно не передавать, если
                используется авторизация по телефону (phone_auth).
            timeout/connect_timeout/read_timeout/write_timeout: таймауты httpx.
            redis/redis_prefix/redis_ttl_seconds: опциональное кэширование сессии.
            proxy: прокси для всех запросов к lknpd.nalog.ru. Принимает URL-строку
                (`"http://user:pass@host:port"`, `"socks5://host:port"`) или
                `httpx.Proxy`. Обязателен при деплое вне РФ — API ФНС
                доступен только с российских IP.
            verify: проверка SSL (True/False/путь к ca-bundle).
        """
        self._credentials = credentials

        self._transport = Transport(
            timeout=timeout,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
            proxy=proxy,
            verify=verify,
        )

        self._password_auth: Optional[PasswordAuth] = (
            PasswordAuth(self._transport, credentials)
            if credentials else None
        )

        self._phone_auth = PhoneSmsAuth(self._transport)

        self._redis = redis
        self._redis_prefix = redis_prefix
        self._redis_ttl = redis_ttl_seconds
        self._refresh_lock = asyncio.Lock()
        self._user_api = UserApi(self)
        self._income_api = IncomeApi(self)
        self._invoice_api = InvoiceApi(self)
        self._payment_type_api = PaymentMethodApi(self)

    async def __aenter__(self) -> "MyTaxClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    @property
    def transport(self) -> Transport:
        """Низкоуровневый транспорт (httpx.AsyncClient)."""
        return self._transport

    @property
    def auth_by_password(self) -> Optional[PasswordAuth]:
        """Стратегия авторизации по ИНН/паролю. None, если credentials не передавались."""
        return self._password_auth

    @property
    def auth_by_phone(self) -> PhoneSmsAuth:
        """Стратегия авторизации по SMS: start_challenge(phone) → verify_and_login(phone, code)."""
        return self._phone_auth

    @property
    def user(self) -> UserApi:
        """Ручки API для ресурса пользователя (GET /user и др.)."""
        return self._user_api

    @property
    def income(self) -> IncomeApi:
        """Ручки API для чеков (создание, отмена)."""
        return self._income_api

    @property
    def invoice(self) -> InvoiceApi:
        """Ручки API для счёта (создание, список, отмена)."""
        return self._invoice_api

    @property
    def payment_type(self) -> PaymentMethodApi:
        """Ручки API для справочника способов оплаты (payment-type/table)."""
        return self._payment_type_api

    def _get_active_auth(self) -> Union[PasswordAuth, PhoneSmsAuth]:
        """Возвращает активную стратегию авторизации (пароль или телефон)."""
        if self._password_auth is not None:
            return self._password_auth
        return self._phone_auth

    def _session_storage_key(self) -> str:
        """Ключ Redis для сессии: «{prefix}:session»."""
        return f"{self._redis_prefix}:{self.SESSION_KEY}"

    async def _load_session_from_redis(self) -> Optional[tuple[AuthData, str]]:
        """Загрузка сессии и device_id из Redis."""
        if not self._redis or not self._redis_prefix:
            return None

        raw = await self._redis.get(self._session_storage_key())
        if not raw:
            return None

        return _deserialize_session(raw)

    async def _save_session_to_redis(
        self, auth: AuthData, device_id: str
    ) -> None:
        """Сохранение сессии и device_id в Redis."""
        if not self._redis or not self._redis_prefix:
            return

        payload = _serialize_session(auth, device_id)
        await self._redis.set(
            self._session_storage_key(), payload, ex=self._redis_ttl
        )

    async def get_auth_headers(self, force_refresh: bool = False) -> dict[str, str]:
        """
        Заголовки с Bearer-токеном для запросов к API.

        Сначала проверяется Redis (если передан и не force_refresh): при валидной
        сессии в кэше заголовки берутся из неё. Иначе выполняется авторизация
        (пароль или телефон), при force_refresh — принудительное обновление токена.
        Результат при наличии redis сохраняется в кэш.
        """
        if not force_refresh:
            loaded = await self._load_session_from_redis()
            if loaded is not None:
                session, device_id = loaded
                auth = self._get_active_auth()
                auth.restore_session(session, device_id=device_id)
                if is_token_fresh(session.token.access_expire_in):
                    return build_bearer_headers(session.token.access_token)

        auth = self._get_active_auth()
        if force_refresh and auth.is_authenticated:
            await auth.refresh_token()
        headers = await auth.get_auth_headers()

        session = auth.session
        if session is not None:
            await self._save_session_to_redis(session, device_id=auth.device_id)

        return headers

    async def request(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        """
        Запрос к API с подстановкой авторизации и обработкой 401.

        При 401 — один retry: обновление токена (под lock) и повтор запроса.
        Вызов raise_for_status() не выполняется — это делает вызывающий код.
        """
        headers = await self.get_auth_headers(force_refresh=False)
        response = await self._transport.raw_client.request(
            method=method,
            url=path,
            headers=headers,
            **kwargs
        )

        if response.status_code == 401:
            async with self._refresh_lock:
                new_headers = await self.get_auth_headers(force_refresh=True)
                response = await self._transport.raw_client.request(
                    method=method,
                    url=path,
                    headers=new_headers,
                    **kwargs
                )

        return response

    async def get_user(self) -> User:
        """Получение профиля текущего пользователя (GET /user)."""
        return await self._user_api.get_user()

    async def aclose(self) -> None:
        """Закрытие HTTP-клиента."""
        await self._transport.aclose()
