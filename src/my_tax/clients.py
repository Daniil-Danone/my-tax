"""
Синхронный и асинхронный клиенты API ЛК НПД.

Поддерживают авторизацию по ИНН/паролю и по телефону (SMS).
Опционально — сохранение состояния авторизации в Redis.
"""

import json
from datetime import datetime
from typing import Any, Optional, Protocol, Union

from ._http import (
    AsyncTransport,
    PasswordAuth,
    PasswordAuthAsync,
    PhoneSmsAuth,
    PhoneSmsAuthAsync,
    SyncTransport,
    build_bearer_headers,
    is_token_fresh,
)

from .api.user import UserAsyncApi, UserSyncApi

from .types import (
    AuthData,
    Credentials,
    Token,
    User,
)


# ---------------------------------------------------------------------------
# Протоколы хранилища состояния (без жёсткой зависимости от redis)
# ---------------------------------------------------------------------------


class SyncAuthStorage(Protocol):
    """Протокол синхронного хранилища состояния авторизации (например Redis)."""

    def get(self, name: str) -> Optional[Union[str, bytes]]:
        """Получение значения по ключу."""
        ...

    def set(
        self,
        name: str,
        value: Union[str, bytes],
        ex: Optional[int] = None,
    ) -> None:
        """Сохранение значения. ex — TTL в секундах."""
        ...


class AsyncAuthStorage(Protocol):
    """Протокол асинхронного хранилища состояния авторизации (например redis.asyncio)."""

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
# Сериализация состояния авторизации для Redis
# ---------------------------------------------------------------------------


def _auth_data_to_dict(auth: AuthData) -> dict[str, Any]:
    """Сериализация AuthData в словарь для сохранения в Redis."""
    return {
        "inn": auth.inn,
        "display_name": auth.display_name,
        "token": {
            "access_token": auth.token.access_token,
            "access_expire_in": auth.token.access_expire_in.isoformat(),
            "refresh_token": auth.token.refresh_token,
            "refresh_expire_in": auth.token.refresh_expire_in.isoformat(),
        },
    }


def _auth_data_from_dict(data: dict[str, Any]) -> AuthData:
    """Восстановление AuthData из словаря (из Redis)."""
    raw = data.get("token", {})
    
    token = Token(
        access_token=raw.get("access_token", ""),
        access_expire_in=datetime.fromisoformat(raw.get("access_expire_in", "").replace("Z", "+00:00")),
        refresh_token=raw.get("refresh_token", ""),
        refresh_expire_in=datetime.fromisoformat(raw.get("refresh_expire_in", "").replace("Z", "+00:00")),
    )
    
    return AuthData(
        inn=data.get("inn", ""),
        token=token,
        display_name=data.get("display_name")
    )


def _serialize_session(auth: AuthData) -> str:
    """Сериализация сессии в JSON-строку."""
    return json.dumps(_auth_data_to_dict(auth), ensure_ascii=False)


def _deserialize_session(payload: Union[str, bytes]) -> Optional[AuthData]:
    """Десериализация сессии из JSON-строки. При ошибке — None."""
    try:
        raw = payload.decode() if isinstance(payload, bytes) else payload
        return _auth_data_from_dict(json.loads(raw))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Синхронный клиент
# ---------------------------------------------------------------------------


class SyncMyTaxClient:
    """
    Синхронный клиент API ЛК НПД.

    Поддерживает авторизацию по ИНН/паролю (Credentials) и по телефону + SMS.
    При передаче redis и redis_key состояние авторизации сохраняется в Redis
    и при следующем запросе подставляется из кэша, если токен ещё действителен.
    """

    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        *,
        timeout: float = 5.0,
        read_timeout: float = 5.0,
        write_timeout: float = 5.0,
        connect_timeout: float = 5.0,
        redis: Optional[SyncAuthStorage] = None,
        redis_key: Optional[str] = None,
        redis_ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Инициализация синхронного клиента.

        redis — опциональное хранилище (например redis.Redis).
        redis_key — ключ для сохранения сессии
        redis_ttl_seconds — TTL записи в секундах (по умолчанию не задаётся).
        """
        self._credentials = credentials

        self._transport = SyncTransport(
            timeout=timeout,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
        )

        self._password_auth: Optional[PasswordAuth] = (
            PasswordAuth(self._transport, credentials)
            if credentials else None
        )

        self._phone_auth = PhoneSmsAuth(self._transport)
        
        self._redis = redis
        self._redis_key = redis_key
        self._redis_ttl = redis_ttl_seconds
        
        self._user_api = UserSyncApi(self._transport, self.get_auth_headers)

    @property
    def transport(self) -> SyncTransport:
        """Низкоуровневый синхронный транспорт (httpx.Client)."""
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
    def user(self) -> UserSyncApi:
        """Ручки API для ресурса пользователя (GET /user и др.)."""
        return self._user_api

    def _get_active_auth(self) -> Union[PasswordAuth, PhoneSmsAuth]:
        """Возвращает активную стратегию авторизации (пароль или телефон)."""
        if self._password_auth is not None:
            return self._password_auth
        return self._phone_auth

    def _load_session_from_redis(self) -> Optional[AuthData]:
        """Загрузка сессии из Redis. При ошибке или отсутствии ключа — None."""
        if not self._redis or not self._redis_key:
            return None
        
        raw = self._redis.get(self._redis_key)
        if not raw:
            return None
        
        return _deserialize_session(raw)

    def _save_session_to_redis(self, auth: AuthData) -> None:
        """Сохранение сессии в Redis с опциональным TTL."""
        if not self._redis or not self._redis_key:
            return
        
        payload = _serialize_session(auth)
        self._redis.set(self._redis_key, payload, ex=self._redis_ttl)

    def get_auth_headers(self) -> dict[str, str]:
        """
        Заголовки с Bearer-токеном для запросов к API.

        Сначала проверяется Redis (если передан): при валидной сессии в кэше
        заголовки берутся из неё. Иначе выполняется авторизация (пароль или
        телефон), результат при наличии redis сохраняется в кэш.
        """
        cached = self._load_session_from_redis()
        if cached is not None and is_token_fresh(cached.token.access_expire_in):
            return build_bearer_headers(cached.token.access_token)

        auth = self._get_active_auth()
        headers = auth.get_auth_headers()
        
        session = auth.session
        if session is not None:
            self._save_session_to_redis(session)
        
        return headers

    def get_user(self) -> User:
        """Получение профиля текущего пользователя (GET /user)."""
        return self._user_api.get_user()

    def close(self) -> None:
        """Закрытие HTTP-клиента."""
        self._transport.close()


# ---------------------------------------------------------------------------
# Асинхронный клиент
# ---------------------------------------------------------------------------


class AsyncMyTaxClient:
    """
    Асинхронный клиент API ЛК НПД.

    Поддерживает авторизацию по ИНН/паролю и по телефону + SMS.
    При передаче redis (например redis.asyncio.Redis) и redis_key состояние
    авторизации сохраняется в Redis и при следующем запросе подставляется
    из кэша, если токен ещё действителен.
    """

    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        *,
        timeout: float = 5.0,
        read_timeout: float = 5.0,
        write_timeout: float = 5.0,
        connect_timeout: float = 5.0,
        redis: Optional[AsyncAuthStorage] = None,
        redis_key: Optional[str] = None,
        redis_ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Инициализация асинхронного клиента.

        redis — опциональное хранилище (например redis.asyncio.Redis).
        redis_key — ключ для сохранения сессии
        redis_ttl_seconds — TTL записи в секундах (по умолчанию не задаётся).
        """
        self._credentials = credentials
        
        self._transport = AsyncTransport(
            timeout=timeout,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
        )
        
        self._password_auth: Optional[PasswordAuthAsync] = (
            PasswordAuthAsync(self._transport, credentials)
            if credentials else None
        )
        
        self._phone_auth = PhoneSmsAuthAsync(self._transport)
        
        self._redis = redis
        self._redis_key = redis_key
        self._redis_ttl = redis_ttl_seconds
        
        self._user_api = UserAsyncApi(self._transport, self.get_auth_headers)

    @property
    def transport(self) -> AsyncTransport:
        """Низкоуровневый асинхронный транспорт (httpx.AsyncClient)."""
        return self._transport

    @property
    def auth_by_password(self) -> Optional[PasswordAuthAsync]:
        """Стратегия авторизации по ИНН/паролю. None, если credentials не передавались."""
        return self._password_auth

    @property
    def auth_by_phone(self) -> PhoneSmsAuthAsync:
        """Стратегия авторизации по SMS: start_challenge(phone) → verify_and_login(phone, code)."""
        return self._phone_auth

    @property
    def user(self) -> UserAsyncApi:
        """Ручки API для ресурса пользователя (GET /user и др.)."""
        return self._user_api

    def _get_active_auth(self) -> Union[PasswordAuthAsync, PhoneSmsAuthAsync]:
        """Возвращает активную стратегию авторизации (пароль или телефон)."""
        if self._password_auth is not None:
            return self._password_auth
        return self._phone_auth

    async def _load_session_from_redis(self) -> Optional[AuthData]:
        """Загрузка сессии из Redis. При ошибке или отсутствии ключа — None."""
        if not self._redis or not self._redis_key:
            return None
        
        raw = await self._redis.get(self._redis_key)
        if not raw:
            return None
        
        return _deserialize_session(raw)

    async def _save_session_to_redis(self, auth: AuthData) -> None:
        """Сохранение сессии в Redis с опциональным TTL."""
        if not self._redis or not self._redis_key:
            return
        
        payload = _serialize_session(auth)
        await self._redis.set(self._redis_key, payload, ex=self._redis_ttl)

    async def get_auth_headers(self) -> dict[str, str]:
        """
        Заголовки с Bearer-токеном для запросов к API.

        Сначала проверяется Redis (если передан): при валидной сессии в кэше
        заголовки берутся из неё. Иначе выполняется авторизация (пароль или
        телефон), результат при наличии redis сохраняется в кэш.
        """
        cached = await self._load_session_from_redis()
        if cached is not None and is_token_fresh(cached.token.access_expire_in):
            return build_bearer_headers(cached.token.access_token)

        auth = self._get_active_auth()
        headers = await auth.get_auth_headers()
        
        session = auth.session
        if session is not None:
            await self._save_session_to_redis(session)
        
        return headers

    async def get_user(self) -> User:
        """Получение профиля текущего пользователя (GET /user)."""
        return await self._user_api.get_user()

    async def aclose(self) -> None:
        """Закрытие асинхронного HTTP-клиента."""
        await self._transport.aclose()
