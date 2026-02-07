"""
Транспорт HTTP и стратегии авторизации для API ЛК НПД.

Содержит синхронный и асинхронный транспорт, 
авторизацию по ИНН/паролю; по SMS (телефон + код).
"""

import asyncio
import random
import string
import time
from abc import ABC, abstractmethod
from datetime import datetime
from functools import wraps
from json import JSONDecodeError
from typing import Dict, Any, Optional, Union

import httpx
from httpx import HTTPStatusError, Timeout

from .constants import (
    BASE_URL_V1,
    BASE_URL_V2,
    DEFAULT_HEADERS,
    TOKEN_EXPIRE_BUFFER_MS,
)

from .domain.exceptions import (
    AccessTokenNotFoundError,
    AuthorizationError,
    SmsChallengeError,
)

from .domain.entites import (
    AuthData, 
    Credentials, 
    DeviceInfo, 
    Token
)


# ---------------------------------------------------------------------------
# Хелперы: устройство и тело запроса
# ---------------------------------------------------------------------------


def create_device_id(length: int = 22) -> str:
    """Генерация случайного идентификатора устройства для deviceInfo."""
    return "".join(
        random.choices(string.ascii_lowercase + string.digits, k=length)
    )


def create_device_info(device_id: Optional[str] = None) -> DeviceInfo:
    """Создание объекта DeviceInfo с опциональным device_id."""
    return DeviceInfo(source_device_id=device_id or create_device_id())


def build_body_with_device(device_info: DeviceInfo, **kwargs: Any) -> Dict[str, Any]:
    """Сборка тела запроса с deviceInfo и произвольными полями."""
    return {
        "deviceInfo": device_info.to_payload(),
        **kwargs,
    }


# ---------------------------------------------------------------------------
# Хелперы: токен и заголовки
# ---------------------------------------------------------------------------


def parse_token_from_response(data: Dict[str, Any]) -> Token:
    """Парсинг токена из JSON-ответа API авторизации."""
    raw_access_expire = data.get("tokenExpireIn").replace("Z", "+00:00")
    raw_refresh_expire = data.get("refreshTokenExpiresIn", "").replace("Z", "+00:00")

    return Token(
        access_token=data.get("token"),
        access_expire_in=datetime.fromisoformat(raw_access_expire),
        refresh_token=data.get("refreshToken", ""),
        refresh_expire_in=datetime.fromisoformat(raw_refresh_expire),
    )


def is_token_fresh(expire_in: datetime) -> bool:
    """Проверка, что токен ещё действителен (с запасом по времени)."""
    now_ms = int(time.time() * 1000)
    expire_ms = int(expire_in.timestamp() * 1000)
    return expire_ms > now_ms + TOKEN_EXPIRE_BUFFER_MS


def build_bearer_headers(access_token: str) -> Dict[str, str]:
    """Формирование заголовка Authorization с Bearer-токеном."""
    return {"authorization": f"Bearer {access_token}"}


def auth_details_from_response(data: Dict[str, Any]) -> AuthData:
    """Сборка AuthDetails из JSON-ответа с profile и токеном."""
    profile: Dict[str, Any] = data.get("profile", {})
    token = parse_token_from_response(data)
    
    return AuthData(
        inn=profile.get("inn", ""),
        token=token,
        display_name=profile.get("displayName")
    )


# ---------------------------------------------------------------------------
# Обработка ошибок авторизации
# ---------------------------------------------------------------------------


def _extract_auth_error_message(response: httpx.Response) -> str:
    """Извлечение сообщения об ошибке из ответа API."""
    try:
        body = response.json()
        if isinstance(body, dict) and "message" in body:
            return str(body["message"])
    except (JSONDecodeError, TypeError):
        pass
    return "Unknown"


def _handle_auth_errors(func: Any) -> Any:
    """Декоратор: перехват HTTP/JSON ошибок при авторизации и замена на AuthorizationError."""

    @wraps(func)
    async def _async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await func(self, *args, **kwargs)
        except HTTPStatusError as ex:
            msg = _extract_auth_error_message(ex.response)
            raise AuthorizationError(
                f"Ошибка авторизации: {msg}",
                response=ex.response,
            ) from None
        except JSONDecodeError:
            raise AuthorizationError(
                "Некорректный JSON в ответе авторизации",
            ) from None
        except (KeyError, UnboundLocalError, TypeError):
            raise AuthorizationError(
                "Неожиданная структура ответа авторизации",
            ) from None

    @wraps(func)
    def _sync_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return func(self, *args, **kwargs)
        except HTTPStatusError as ex:
            msg = _extract_auth_error_message(ex.response)
            raise AuthorizationError(
                f"Ошибка авторизации: {msg}",
                response=ex.response,
            ) from None
        except JSONDecodeError:
            raise AuthorizationError(
                "Некорректный JSON в ответе авторизации",
            ) from None
        except (KeyError, UnboundLocalError, TypeError):
            raise AuthorizationError(
                "Неожиданная структура ответа авторизации",
            ) from None

    if asyncio.iscoroutinefunction(func):
        return _async_wrapper
    return _sync_wrapper


# ---------------------------------------------------------------------------
# Транспорт (S — один класс = один контракт)
# ---------------------------------------------------------------------------


class Transport(ABC):
    """Абстрактный HTTP-транспорт для запросов к API."""

    @abstractmethod
    def post(
        self,
        path: str,
        json: Optional[dict] = None,
        *,
        base_url: Optional[str] = None,
        extra_headers: Optional[dict] = None,
    ) -> Any:
        """Отправка POST-запроса. В sync-реализации — Response, в async — awaitable."""
        ...

    @property
    @abstractmethod
    def raw_client(self) -> Union[httpx.Client, httpx.AsyncClient]:
        """Нижележащий httpx-клиент для прямых вызовов."""
        ...


class SyncTransport(Transport):
    """Синхронный HTTP-транспорт на базе httpx.Client."""

    def __init__(
        self,
        base_url: str = BASE_URL_V1,
        headers: Optional[dict] = None,
        timeout: float = 5.0,
        connect_timeout: float = 5.0,
        read_timeout: float = 5.0,
        write_timeout: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {**DEFAULT_HEADERS, **(headers or {})}
        self._client = httpx.Client(
            base_url=base_url,
            headers=self._headers,
            timeout=Timeout(
                timeout=timeout,
                connect=connect_timeout,
                read=read_timeout,
                write=write_timeout,
            ),
        )

    def post(
        self,
        path: str,
        json: Optional[dict] = None,
        *,
        base_url: Optional[str] = None,
        extra_headers: Optional[dict] = None,
    ) -> httpx.Response:
        """Синхронная отправка POST."""
        url = (base_url or self._base_url).rstrip("/") + "/" + path.lstrip("/")
        merged_headers = {**(extra_headers or {})}
        
        return self._client.post(
            url=url, 
            json=json, 
            headers=merged_headers or None
        )

    @property
    def raw_client(self) -> httpx.Client:
        return self._client

    def close(self) -> None:
        """Закрытие клиента."""
        self._client.close()


class AsyncTransport(Transport):
    """Асинхронный HTTP-транспорт на базе httpx.AsyncClient."""

    def __init__(
        self,
        base_url: str = BASE_URL_V1,
        headers: Optional[dict] = None,
        timeout: float = 5.0,
        connect_timeout: float = 5.0,
        read_timeout: float = 5.0,
        write_timeout: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {**DEFAULT_HEADERS, **(headers or {})}
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=self._headers,
            timeout=Timeout(
                timeout=timeout,
                connect=connect_timeout,
                read=read_timeout,
                write=write_timeout,
            ),
        )

    async def post(
        self,
        path: str,
        json: Optional[dict] = None,
        *,
        base_url: Optional[str] = None,
        extra_headers: Optional[dict] = None,
    ) -> httpx.Response:
        """Асинхронная отправка POST."""
        url = (base_url or self._base_url).rstrip("/") + "/" + path.lstrip("/")
        merged_headers = {**(extra_headers or {})}
        return await self._client.post(
            url=url, 
            json=json, 
            headers=merged_headers or None
        )

    @property
    def raw_client(self) -> httpx.AsyncClient:
        return self._client

    async def aclose(self) -> None:
        """Закрытие асинхронного клиента."""
        await self._client.aclose()


# ---------------------------------------------------------------------------
# Базовая стратегия авторизации (D — зависимость от абстракции)
# ---------------------------------------------------------------------------


class AuthStrategy(ABC):
    """Абстракция стратегии авторизации: получение заголовков с токеном."""

    @property
    @abstractmethod
    def session(self) -> Optional[AuthData]:
        """Текущая сессия после успешной авторизации."""
        ...

    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Есть ли активная сессия."""
        ...

    @abstractmethod
    def token_is_fresh(self) -> bool:
        """Действителен ли текущий access-токен (с учётом запаса по времени)."""
        ...


# ---------------------------------------------------------------------------
# Авторизация по логину/паролю (синхронная)
# ---------------------------------------------------------------------------


class PasswordAuth(AuthStrategy):
    """Авторизация по логину и паролю (ИНН). Получение и обновление токена."""

    def __init__(
        self,
        transport: SyncTransport,
        credentials: Credentials,
    ) -> None:
        self._transport = transport
        self._credentials = credentials
        self._device = create_device_info()
        self._session: Optional[AuthData] = None

    def _body(self, **kwargs: Any) -> dict:
        """Тело запроса с deviceInfo и переданными полями."""
        return build_body_with_device(self._device, **kwargs)

    def _request(self, path: str, body: dict) -> dict:
        """Синхронный POST с поднятием ошибки по статусу и разбором JSON."""
        response = self._transport.post(
            path=path, 
            json=body
        )
        
        response.raise_for_status()
        return response.json()

    @_handle_auth_errors
    def obtain_token(self) -> AuthData:
        """Получение токена по логину и паролю."""
        body = self._body(
            username=self._credentials.username,
            password=self._credentials.password,
        )
        
        data = self._request(
            path="/auth/lkfl", 
            body=body
        )
        
        self._session = auth_details_from_response(data=data)
        return self._session

    @_handle_auth_errors
    def refresh_token(self) -> str:
        """Обновление access-токена по refresh-токену."""
        if not self._session:
            raise AccessTokenNotFoundError("Нет сессии для обновления")
        
        body = self._body(refreshToken=self._session.token.refresh_token)
        
        data = self._request(
            path="/auth/token", 
            body=body
        )
        
        new_token = data.get("token")
        if not new_token:
            raise AccessTokenNotFoundError(
                "В ответе обновления токена отсутствует token"
            )
        
        self._session.token.access_token = new_token
        return new_token

    @property
    def session(self) -> Optional[AuthData]:
        return self._session

    @property
    def is_authenticated(self) -> bool:
        return self._session is not None

    def token_is_fresh(self) -> bool:
        if not self._session:
            return False
        return is_token_fresh(expire_in=self._session.token.access_expire_in)

    def get_auth_headers(self) -> dict:
        """Заголовки с Bearer-токеном; при необходимости выполняет obtain/refresh."""
        if not self.is_authenticated:
            self.obtain_token()
        if not self.token_is_fresh():
            self.refresh_token()
        return build_bearer_headers(access_token=self._session.token.access_token)


# ---------------------------------------------------------------------------
# Авторизация по логину/паролю (асинхронная)
# ---------------------------------------------------------------------------


class PasswordAuthAsync(AuthStrategy):
    """Асинхронная авторизация по логину и паролю."""

    def __init__(
        self,
        transport: AsyncTransport,
        credentials: Credentials,
    ) -> None:
        self._transport = transport
        self._credentials = credentials
        self._device = create_device_info()
        self._session: Optional[AuthData] = None

    def _body(self, **kwargs: Any) -> dict:
        return build_body_with_device(self._device, **kwargs)

    async def _request(self, path: str, body: dict) -> dict:
        """Асинхронный POST с поднятием ошибки и разбором JSON."""
        response = await self._transport.post(
            path=path, 
            json=body
        )
        
        response.raise_for_status()
        return response.json()

    @_handle_auth_errors
    async def obtain_token(self) -> AuthData:
        """Получение токена по логину и паролю."""
        body = self._body(
            username=self._credentials.username,
            password=self._credentials.password,
        )
        
        data = await self._request(
            path="/auth/lkfl", 
            body=body
        )
        
        self._session = auth_details_from_response(data=data)
        return self._session

    @_handle_auth_errors
    async def refresh_token(self) -> str:
        """Обновление access-токена по refresh-токену."""
        if not self._session:
            raise AccessTokenNotFoundError("Нет сессии для обновления")
        
        body = self._body(refreshToken=self._session.token.refresh_token)
        
        data = await self._request(
            path="/auth/token",
            body=body
        )
        
        new_token = data.get("token")
        if not new_token:
            raise AccessTokenNotFoundError(
                "В ответе обновления токена отсутствует token"
            )
        
        self._session.token.access_token = new_token
        return new_token

    @property
    def session(self) -> Optional[AuthData]:
        return self._session

    @property
    def is_authenticated(self) -> bool:
        return self._session is not None

    def token_is_fresh(self) -> bool:
        if not self._session:
            return False
        return is_token_fresh(expire_in=self._session.token.access_expire_in)

    async def get_auth_headers(self) -> dict:
        """Заголовки с Bearer-токеном; при необходимости выполняет obtain/refresh."""
        if not self.is_authenticated:
            await self.obtain_token()
        if not self.token_is_fresh():
            await self.refresh_token()
        return build_bearer_headers(access_token=self._session.token.access_token)


# ---------------------------------------------------------------------------
# Авторизация по SMS (синхронная)
# ---------------------------------------------------------------------------


class PhoneSmsAuth(AuthStrategy):
    """Авторизация по номеру телефона и коду из SMS: старт челленджа → верификация → сессия."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport
        self._device = create_device_info()
        self._session: Optional[AuthData] = None
        self._challenge_token: Optional[str] = None
        self._phone: Optional[str] = None

    def start_challenge(
        self,
        phone: str,
        require_tp_active: bool = True,
    ) -> str:
        """Старт SMS-челленджа. Возвращает challenge_token для шага verify."""
        body = {
            "phone": phone,
            "requireTpToBeActive": require_tp_active,
            "deviceData": {"sourceType": "WEB"},
        }
        
        response = self._transport.post(
            path="/auth/challenge/sms/start",
            json=body,
            base_url=BASE_URL_V2
        )
        
        response.raise_for_status()
        data = response.json()
        
        token = data.get("challengeToken")
        if not token:
            raise SmsChallengeError(
                "В ответе start отсутствует challengeToken"
            )
        
        self._challenge_token = token
        self._phone = phone
        return token

    def verify_and_login(self, phone: str, code: str) -> AuthData:
        """Верификация кода из SMS и получение сессии. Вызывать после start_challenge с тем же phone."""
        if not self._challenge_token or self._phone != phone:
            raise SmsChallengeError(
                "Сначала вызовите start_challenge(phone) и используйте тот же phone в verify"
            )
        
        body = {
            "phone": phone,
            "code": code,
            "challengeToken": self._challenge_token,
            "deviceInfo": self._device.to_payload(),
        }
        
        response = self._transport.post(
            path="/auth/challenge/sms/verify", 
            json=body
        )
        
        response.raise_for_status()
        data = response.json()
        
        self._session = auth_details_from_response(data=data)
        self._challenge_token = None
        return self._session

    def _body(self, **kwargs: Any) -> dict:
        return build_body_with_device(self._device, **kwargs)

    def _request(self, path: str, body: dict) -> dict:
        response = self._transport.post(
            path=path, 
            json=body
        )
        
        response.raise_for_status()
        return response.json()

    @_handle_auth_errors
    def refresh_token(self) -> str:
        """Обновление access-токена по refresh-токену."""
        if not self._session:
            raise AccessTokenNotFoundError("Нет сессии для обновления")
        
        body = self._body(refreshToken=self._session.token.refresh_token)
        
        data = self._request(
            path="/auth/token", 
            body=body
        )
        
        new_token = data.get("token")
        if not new_token:
            raise AccessTokenNotFoundError(
                "В ответе обновления токена отсутствует token"
            )
        
        self._session.token.access_token = new_token
        return new_token

    @property
    def session(self) -> Optional[AuthData]:
        return self._session

    @property
    def is_authenticated(self) -> bool:
        return self._session is not None

    def token_is_fresh(self) -> bool:
        if not self._session:
            return False
        return is_token_fresh(expire_in=self._session.token.access_expire_in)

    def get_auth_headers(self) -> dict:
        """Заголовки с Bearer-токеном. Требует предварительного verify_and_login."""
        if not self.is_authenticated:
            raise AuthorizationError(
                "Нет сессии. Вызовите start_challenge(phone), затем verify_and_login(phone, code)."
            )
        if not self.token_is_fresh():
            self.refresh_token()
        return build_bearer_headers(access_token=self._session.token.access_token)


# ---------------------------------------------------------------------------
# Авторизация по SMS (асинхронная)
# ---------------------------------------------------------------------------


class PhoneSmsAuthAsync(AuthStrategy):
    """Асинхронная авторизация по номеру телефона и коду из SMS."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport
        self._device = create_device_info()
        self._session: Optional[AuthData] = None
        self._challenge_token: Optional[str] = None
        self._phone: Optional[str] = None

    async def start_challenge(
        self,
        phone: str,
        require_tp_active: bool = True,
    ) -> str:
        """Старт SMS-челленджа. Возвращает challenge_token для шага verify."""
        body = {
            "phone": phone,
            "requireTpToBeActive": require_tp_active,
            "deviceData": {"sourceType": "WEB"},
        }

        response = await self._transport.post(
            path="/auth/challenge/sms/start",
            json=body,
            base_url=BASE_URL_V2,
        )

        response.raise_for_status()
        data = response.json()
        
        token = data.get("challengeToken")
        if not token:
            raise SmsChallengeError(
                "В ответе start отсутствует challengeToken"
            )
        
        self._challenge_token = token
        self._phone = phone
        return token

    async def verify_and_login(self, phone: str, code: str) -> AuthData:
        """Верификация кода из SMS и получение сессии. Вызывать после start_challenge с тем же phone."""
        if not self._challenge_token or self._phone != phone:
            raise SmsChallengeError(
                "Сначала вызовите start_challenge(phone) и используйте тот же phone в verify"
            )
        
        body = {
            "phone": phone,
            "code": code,
            "challengeToken": self._challenge_token,
            "deviceInfo": self._device.to_payload(),
        }
        
        response = await self._transport.post(
            path="/auth/challenge/sms/verify", 
            json=body
        )
        
        response.raise_for_status()
        data = response.json()
        
        self._session = auth_details_from_response(data)
        self._challenge_token = None
        return self._session

    def _body(self, **kwargs: Any) -> dict:
        return build_body_with_device(self._device, **kwargs)

    async def _request(self, path: str, body: dict) -> dict:
        response = await self._transport.post(
            path=path, 
            json=body
        )
        
        response.raise_for_status()
        return response.json()

    @_handle_auth_errors
    async def refresh_token(self) -> str:
        """Обновление access-токена по refresh-токену."""
        if not self._session:
            raise AccessTokenNotFoundError("Нет сессии для обновления")
        
        body = self._body(refreshToken=self._session.token.refresh_token)
        
        data = await self._request(
            path="/auth/token", 
            body=body
        )

        new_token = data.get("token")
        if not new_token:
            raise AccessTokenNotFoundError(
                "В ответе обновления токена отсутствует token"
            )
        
        self._session.token.access_token = new_token
        return new_token

    @property
    def session(self) -> Optional[AuthData]:
        return self._session

    @property
    def is_authenticated(self) -> bool:
        return self._session is not None

    def token_is_fresh(self) -> bool:
        if not self._session:
            return False
        return is_token_fresh(expire_in=self._session.token.access_expire_in)

    async def get_auth_headers(self) -> dict:
        """Заголовки с Bearer-токеном. Требует предварительного verify_and_login."""
        if not self.is_authenticated:
            raise AuthorizationError(
                "Нет сессии. Вызовите start_challenge(phone), затем verify_and_login(phone, code)."
            )
        if not self.token_is_fresh():
            await self.refresh_token()
        return build_bearer_headers(access_token=self._session.token.access_token)
