"""
Стратегии авторизации для API ЛК НПД.

Авторизация по ИНН/паролю и по SMS (телефон + код).
"""

from functools import wraps
from json import JSONDecodeError
from typing import Any, Optional

from httpx import HTTPStatusError

from .constants import BASE_URL_V2
from .exceptions import (
    AccessTokenNotFoundError,
    AuthorizationError,
    SmsChallengeError,
)
from ._helpers import (
    AuthStrategy,
    auth_details_from_response,
    build_bearer_headers,
    build_body_with_device,
    create_device_info,
    is_token_fresh,
    _extract_auth_error_message,
)
from .types import AuthData, Credentials, Token
from ._transport import Transport


# ---------------------------------------------------------------------------
# Декоратор обработки ошибок авторизации
# ---------------------------------------------------------------------------


def _handle_auth_errors(func: Any) -> Any:
    """Декоратор: перехват HTTP/JSON ошибок при авторизации и замена на AuthorizationError."""

    @wraps(func)
    async def _wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await func(self, *args, **kwargs)
        except HTTPStatusError as ex:
            msg = _extract_auth_error_message(ex.response)
            raise AuthorizationError(
                f"Ошибка авторизации: {msg}",
                response=ex.response,
            ) from ex
        except JSONDecodeError as ex:
            raise AuthorizationError(
                "Некорректный JSON в ответе авторизации",
            ) from ex
        except (KeyError, TypeError) as ex:
            raise AuthorizationError(
                "Неожиданная структура ответа авторизации",
            ) from ex

    return _wrapper


# ---------------------------------------------------------------------------
# Авторизация по логину/паролю
# ---------------------------------------------------------------------------


class PasswordAuth(AuthStrategy):
    """Авторизация по логину и паролю."""

    def __init__(
        self,
        transport: Transport,
        credentials: Credentials,
    ) -> None:
        self._transport = transport
        self._credentials = credentials
        self._device = create_device_info()
        self._session: Optional[AuthData] = None

    def _body(self, **kwargs: Any) -> dict:
        return build_body_with_device(self._device, **kwargs)

    async def _request(self, path: str, body: dict) -> dict:
        """POST с поднятием ошибки и разбором JSON."""
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

        self._session.token = self._session.token.model_copy(
            update={"access_token": new_token}
        )
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

        if self._session is None:
            raise AuthorizationError("Нет сессии после obtain/refresh")

        return build_bearer_headers(access_token=self._session.token.access_token)


# ---------------------------------------------------------------------------
# Авторизация по SMS
# ---------------------------------------------------------------------------


class PhoneSmsAuth(AuthStrategy):
    """Авторизация по номеру телефона и коду из SMS."""

    def __init__(self, transport: Transport) -> None:
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

    async def verify_and_login(
        self,
        phone: str,
        code: str,
        challenge_token: Optional[str] = None,
    ) -> AuthData:
        """
        Верификация кода из SMS и получение сессии.

        Args:
            phone: Номер телефона.
            code: Код из SMS.
            challenge_token: Токен челленджа. Если не передан — используется
                токен из start_challenge(). Передавайте явно, когда start_challenge
                и verify_and_login вызываются в разных запросах / экземплярах клиента.
        """
        token = challenge_token or self._challenge_token
        if not token:
            raise SmsChallengeError(
                "Передайте challenge_token или вызовите start_challenge(phone) перед verify_and_login"
            )

        body = {
            "phone": phone,
            "code": code,
            "challengeToken": token,
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

        self._session.token = self._session.token.model_copy(
            update={"access_token": new_token}
        )
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

        if self._session is None:
            raise AuthorizationError("Нет сессии после refresh")

        return build_bearer_headers(access_token=self._session.token.access_token)
