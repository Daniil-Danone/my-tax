"""
Синхронный и асинхронный клиенты API ЛК НПД.

Поддерживают авторизацию по ИНН/паролю и по телефону (SMS).
Опционально — сохранение состояния авторизации в Redis.
Обработка 401 (refresh токена и один retry) — на уровне клиента в методе request().
"""

import asyncio
import json
import threading
from datetime import datetime
from typing import Any, Optional, Protocol, Union

import httpx

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

from .domain.entites import (
    AuthData,
    Credentials,
    Token,
    User
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

def _serialize_session(auth: AuthData) -> str:
    """Сериализация сессии в JSON-строку."""
    return AuthData.model_dump_json(auth)


def _deserialize_session(payload: Union[str, bytes]) -> Optional[AuthData]:
    """Десериализация сессии из JSON-строки. При ошибке — None."""
    try:
        raw = payload.decode() if isinstance(payload, bytes) else payload
        return AuthData.model_validate_json(raw)
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
        self._refresh_lock = threading.Lock()
        self._user_api = UserSyncApi(self)

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

    def get_auth_headers(self, force_refresh: bool = False) -> dict[str, str]:
        """
        Заголовки с Bearer-токеном для запросов к API.

        Сначала проверяется Redis (если передан и не force_refresh): при валидной
        сессии в кэше заголовки берутся из неё. Иначе выполняется авторизация
        (пароль или телефон), при force_refresh — принудительное обновление токена.
        Результат при наличии redis сохраняется в кэш.
        """
        if not force_refresh:
            cached = self._load_session_from_redis()
            if cached is not None and is_token_fresh(cached.token.access_expire_in):
                return build_bearer_headers(cached.token.access_token)

        auth = self._get_active_auth()
        if force_refresh and auth.is_authenticated:
            auth.refresh_token()
        headers = auth.get_auth_headers()

        session = auth.session
        if session is not None:
            self._save_session_to_redis(session)

        return headers

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """
        Запрос к API с подстановкой авторизации и обработкой 401.

        При 401 — один retry: обновление токена (под lock) и повтор запроса.
        Вызов raise_for_status() не выполняется — это делает вызывающий код.
        """
        headers = self.get_auth_headers(force_refresh=False)
        response = self._transport.raw_client.request(
            method=method, 
            url=path, 
            headers=headers,
            **kwargs
        )
        
        if response.status_code == 401:
            with self._refresh_lock:
                new_headers = self.get_auth_headers(force_refresh=True)
                response = self._transport.raw_client.request(
                    method=method, 
                    url=path, 
                    headers=new_headers, 
                    **kwargs
                )

        return response

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
        self._refresh_lock = asyncio.Lock()
        self._user_api = UserAsyncApi(self)

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

    async def get_auth_headers(self, force_refresh: bool = False) -> dict[str, str]:
        """
        Заголовки с Bearer-токеном для запросов к API.

        Сначала проверяется Redis (если передан и не force_refresh): при валидной
        сессии в кэше заголовки берутся из неё. Иначе выполняется авторизация
        (пароль или телефон), при force_refresh — принудительное обновление токена.
        Результат при наличии redis сохраняется в кэш.
        """
        if not force_refresh:
            cached = await self._load_session_from_redis()
            if cached is not None and is_token_fresh(cached.token.access_expire_in):
                return build_bearer_headers(cached.token.access_token)

        auth = self._get_active_auth()
        if force_refresh and auth.is_authenticated:
            await auth.refresh_token()
        headers = await auth.get_auth_headers()

        session = auth.session
        if session is not None:
            await self._save_session_to_redis(session)

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
        """Закрытие асинхронного HTTP-клиента."""
        await self._transport.aclose()
