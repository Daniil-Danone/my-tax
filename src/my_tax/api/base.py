"""
Базовые классы для ручек API.

Дают общий контракт: транспорт + получение заголовков авторизации
и метод _request_get для GET-запросов с разбором JSON.
"""

from abc import ABC
from typing import Any, Awaitable, Callable, Dict

from .._http import AsyncTransport, SyncTransport


class BaseSyncApi(ABC):
    """
    Базовый класс для синхронных ручек API.

    Принимает транспорт и callable для получения заголовков авторизации.
    Наследники вызывают _request_get(path) для GET и получают уже разобранный JSON.
    """

    def __init__(
        self,
        transport: SyncTransport,
        get_headers: Callable[[], Dict[str, str]],
    ) -> None:
        self._transport = transport
        self._get_headers = get_headers

    def _request_get(self, path: str) -> Dict[str, Any]:
        """
        Выполнение GET-запроса по path с подстановкой авторизации.

        Возвращает ответ как словарь (response.json()).
        Поднимает httpx.HTTPStatusError при ошибке статуса.
        """
        headers = self._get_headers()
        response = self._transport.raw_client.get(path, headers=headers)
        response.raise_for_status()
        return response.json()


class BaseAsyncApi(ABC):
    """
    Базовый класс для асинхронных ручек API.

    Принимает транспорт и async callable для получения заголовков авторизации.
    Наследники вызывают await _request_get(path) для GET и получают разобранный JSON.
    """

    def __init__(
        self,
        transport: AsyncTransport,
        get_headers: Callable[[], Awaitable[Dict[str, str]]],
    ) -> None:
        """
        get_headers — корутина или async-функция без аргументов, возвращающая dict заголовков.
        """
        self._transport = transport
        self._get_headers = get_headers

    async def _request_get(self, path: str) -> Dict[str, Any]:
        """
        Выполнение GET-запроса по path с подстановкой авторизации.

        Возвращает ответ как словарь (response.json()).
        Поднимает httpx.HTTPStatusError при ошибке статуса.
        """
        headers = await self._get_headers()
        response = await self._transport.raw_client.get(path, headers=headers)
        response.raise_for_status()
        return response.json()
